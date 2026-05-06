"""
APF Safety Filter — Artificial Potential Field collision avoidance.

Based on: SkySim (Shibu et al., 2025)
    "SkySim: A ROS2-based Simulation Environment for Natural Language
     Control of Drone Swarms using Large Language Models"
    arXiv:2602.01226

Runs at configurable rate (default 20 Hz). Given a set of desired
waypoints and current drone positions, applies repulsive forces to
prevent collisions, enforces kinematic limits, and clips positions
within a geo-fence.

All positions in local NED meters (x=North, y=East, z=Down).
For altitude: use positive z_up (above ground), the filter
handles inversion internally.

Usage:
    from droneresearch.safety.apf import APFSafetyFilter, Pose3D

    apf = APFSafetyFilter(
        min_separation=2.0,     # meters between drones
        max_speed=3.0,          # m/s
        geofence_radius=50.0,   # meters from origin
        geofence_alt=(1.0, 30.0)# (min_alt, max_alt) in meters
    )

    # Current positions of all drones: {id: Pose3D}
    positions = {
        "D1": Pose3D(0, 0, 10),
        "D2": Pose3D(3, 0, 10),
        "D3": Pose3D(6, 0, 10),
    }

    # Desired waypoints (from LLM / mission planner)
    desired = {
        "D1": Pose3D(0,  5, 10),
        "D2": Pose3D(5,  5, 10),
        "D3": Pose3D(10, 5, 10),
    }

    # Safe waypoints after APF filtering
    safe = apf.filter(positions, desired)
"""
import math
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple


@dataclass
class Pose3D:
    """3D position in local NED meters (x=North, y=East, z_up=altitude above ground)."""
    x:   float = 0.0
    y:   float = 0.0
    z:   float = 0.0   # positive = UP (altitude)

    def dist(self, other: "Pose3D") -> float:
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )

    def dist_2d(self, other: "Pose3D") -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def __add__(self, other: "Pose3D") -> "Pose3D":
        return Pose3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __mul__(self, s: float) -> "Pose3D":
        return Pose3D(self.x * s, self.y * s, self.z * s)

    def norm(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalized(self) -> "Pose3D":
        n = self.norm()
        if n < 1e-9:
            return Pose3D(0, 0, 0)
        return Pose3D(self.x / n, self.y / n, self.z / n)

    def clamp(self, max_norm: float) -> "Pose3D":
        n = self.norm()
        if n > max_norm:
            return self.normalized() * max_norm
        return self

    def __repr__(self) -> str:
        return f"Pose3D({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"


@dataclass
class Geofence:
    """Cylindrical geofence: horizontal radius + altitude band."""
    origin_x:   float = 0.0
    origin_y:   float = 0.0
    radius:     float = 50.0      # meters horizontal
    alt_min:    float = 1.0       # meters above ground
    alt_max:    float = 30.0      # meters above ground

    def contains(self, p: Pose3D) -> bool:
        r = math.sqrt((p.x - self.origin_x)**2 + (p.y - self.origin_y)**2)
        return r <= self.radius and self.alt_min <= p.z <= self.alt_max

    def clip(self, p: Pose3D) -> Pose3D:
        """Clip position to geofence boundary."""
        dx, dy = p.x - self.origin_x, p.y - self.origin_y
        r = math.sqrt(dx**2 + dy**2)
        if r > self.radius:
            scale = self.radius / r
            dx *= scale
            dy *= scale
        z = max(self.alt_min, min(self.alt_max, p.z))
        return Pose3D(self.origin_x + dx, self.origin_y + dy, z)


class APFSafetyFilter:
    """
    Artificial Potential Field safety filter for drone swarms.

    Applies repulsive potentials between drones and attractive potentials
    toward desired waypoints, then clips to kinematic and geofence limits.

    Parameters
    ----------
    min_separation  : Minimum safe distance between drones (meters)
    max_speed       : Maximum allowed velocity step per update (m/s * dt)
    geofence_radius : Horizontal geofence radius from origin (meters)
    geofence_alt    : (min_alt, max_alt) altitude band (meters)
    repulsion_gain  : Strength of repulsive force between drones
    attraction_gain : Strength of attractive force toward waypoints
    obstacle_radius : Safety margin — repulsion activates within this range
    """

    def __init__(
        self,
        min_separation:  float = 2.0,
        max_speed:       float = 3.0,
        geofence_radius: float = 50.0,
        geofence_alt:    Tuple[float, float] = (1.0, 30.0),
        repulsion_gain:  float = 2.0,
        attraction_gain: float = 1.0,
        obstacle_radius: float = 4.0,
        dt:              float = 0.05,   # 20 Hz
    ):
        self.min_separation  = min_separation
        self.max_speed       = max_speed
        self.repulsion_gain  = repulsion_gain
        self.attraction_gain = attraction_gain
        self.obstacle_radius = obstacle_radius
        self.dt              = dt
        self.geofence        = Geofence(
            radius  = geofence_radius,
            alt_min = geofence_alt[0],
            alt_max = geofence_alt[1],
        )
        self._obstacles: List[Pose3D] = []   # static obstacles

    def add_obstacle(self, x: float, y: float, z: float = 0.0):
        """Add a static obstacle (e.g. building, tree)."""
        self._obstacles.append(Pose3D(x, y, z))

    def clear_obstacles(self):
        self._obstacles.clear()

    def filter(
        self,
        positions: Dict[str, Pose3D],
        desired:   Dict[str, Pose3D],
    ) -> Dict[str, Pose3D]:
        """
        Apply APF to move each drone toward desired position
        while avoiding other drones and obstacles.

        Returns safe waypoints for each drone.
        """
        safe: Dict[str, Pose3D] = {}
        ids   = list(positions.keys())

        for drone_id in ids:
            pos = positions.get(drone_id)
            des = desired.get(drone_id, pos)
            if pos is None:
                continue

            # Attractive force: toward desired position
            diff_x = des.x - pos.x
            diff_y = des.y - pos.y
            diff_z = des.z - pos.z
            attr = Pose3D(diff_x, diff_y, diff_z)
            attr_clamped = attr.clamp(self.max_speed * self.dt) * self.attraction_gain

            # Repulsive force: away from other drones
            rep = Pose3D(0, 0, 0)
            for other_id in ids:
                if other_id == drone_id:
                    continue
                other = positions[other_id]
                d = pos.dist(other)
                if d < self.obstacle_radius and d > 1e-6:
                    # Repulsion magnitude: inversely proportional to distance
                    mag = self.repulsion_gain * (1.0 / d - 1.0 / self.obstacle_radius) / (d ** 2)
                    direction = Pose3D(
                        pos.x - other.x,
                        pos.y - other.y,
                        pos.z - other.z,
                    ).normalized()
                    rep = rep + direction * (mag * self.dt)

            # Repulsion from static obstacles
            for obs in self._obstacles:
                d = pos.dist(obs)
                if d < self.obstacle_radius and d > 1e-6:
                    mag = self.repulsion_gain * (1.0 / d - 1.0 / self.obstacle_radius) / (d ** 2)
                    direction = Pose3D(
                        pos.x - obs.x,
                        pos.y - obs.y,
                        pos.z - obs.z,
                    ).normalized()
                    rep = rep + direction * (mag * self.dt)

            # Total force → new position
            total = Pose3D(
                attr_clamped.x + rep.x,
                attr_clamped.y + rep.y,
                attr_clamped.z + rep.z,
            ).clamp(self.max_speed * self.dt)

            candidate = Pose3D(
                pos.x + total.x,
                pos.y + total.y,
                pos.z + total.z,
            )

            # Apply geofence
            safe[drone_id] = self.geofence.clip(candidate)

        return safe

    def check_separation(self, positions: Dict[str, Pose3D]) -> List[Tuple[str, str, float]]:
        """
        Check minimum separation violations.
        Returns list of (drone_a, drone_b, distance) for any violations.
        """
        violations = []
        ids = list(positions.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                d = positions[ids[i]].dist(positions[ids[j]])
                if d < self.min_separation:
                    violations.append((ids[i], ids[j], d))
        return violations


class APFFilterLoop:
    """
    Runs APFSafetyFilter at 20 Hz as a background thread.
    Continuously reads current positions and desired setpoints,
    publishes safe setpoints via callback.

    Usage:
        loop = APFFilterLoop(
            apf=APFSafetyFilter(),
            get_positions=lambda: {...},
            get_desired=lambda: {...},
            on_safe=lambda safe: send_to_drones(safe),
            hz=20.0,
        )
        loop.start()
        ...
        loop.stop()
    """

    def __init__(
        self,
        apf:           APFSafetyFilter,
        get_positions: Callable[[], Dict[str, Pose3D]],
        get_desired:   Callable[[], Dict[str, Pose3D]],
        on_safe:       Callable[[Dict[str, Pose3D]], None],
        hz:            float = 20.0,
        on_violation:  Optional[Callable[[List], None]] = None,
    ):
        self.apf           = apf
        self._get_pos      = get_positions
        self._get_des      = get_desired
        self._on_safe      = on_safe
        self._on_violation = on_violation
        self._dt           = 1.0 / hz
        self._running      = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, daemon=True, name="apf-filter"
        )
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            t0 = time.monotonic()
            try:
                positions = self._get_pos()
                desired   = self._get_des()
                safe      = self.apf.filter(positions, desired)
                self._on_safe(safe)
                if self._on_violation:
                    violations = self.apf.check_separation(positions)
                    if violations:
                        self._on_violation(violations)
            except Exception as e:
                print(f"[apf] filter error: {e}")
            elapsed = time.monotonic() - t0
            time.sleep(max(0, self._dt - elapsed))

"""
CoordinatorUAVModel — swarm coordinator with leader-follower FSM.

Based on: "A Modular and Scalable System Architecture for Heterogeneous
UAV Swarms Using ROS 2 and PX4-Autopilot" (2025)

Responsibilities:
    - Detects and registers swarm members
    - Manages leader-follower roles
    - Controls formation geometry
    - Synchronizes state transitions across the swarm
    - Can run as GCS (ground station) OR onboard a UAV

The CoordinatorUAVModel can be either:
    1. Ground-based: laptop/desktop, no MAVLink connection of its own
    2. UAV-based: flies as leader, controls others via telemetry

Usage:
    # Ground station coordinator
    coord = CoordinatorUAVModel.as_ground_station()
    coord.register("D1", uav1)
    coord.register("D2", uav2)
    coord.set_leader("D1")
    coord.set_formation("line", spacing=5.0)
    coord.takeoff_all(altitude=10.0)

    # UAV-based coordinator (leader drone)
    coord = CoordinatorUAVModel("LEAD", "tcp:127.0.0.1:5760")
    coord.connect()
    coord.register("D2", uav2)
    coord.register("D3", uav3)
    coord.set_formation("v", spacing=4.0)
    coord.start(altitude=10.0)
"""
import math
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

from droneresearch.core.fsm import DroneState, StateMachine
from droneresearch.models.generic_uav import GenericUAVModel
from droneresearch.safety import APFSafetyFilter, Pose3D


# Formation offsets (north_m, east_m) per follower index
def _calc_offsets(shape: str, count: int, spacing: float) -> List[Tuple[float, float]]:
    offsets = []
    if shape == "line":
        for i in range(count):
            offsets.append((0.0, spacing * (i - (count - 1) / 2)))
    elif shape == "v":
        for i in range(count):
            side = 1 if i % 2 == 0 else -1
            row  = (i + 1) // 2
            offsets.append((-row * spacing, side * row * spacing * 0.75))
    elif shape == "grid":
        cols = math.ceil(math.sqrt(count + 1))
        for i in range(count):
            row = (i + 1) // cols
            col = (i + 1) %  cols
            offsets.append((row * spacing, (col - cols/2) * spacing))
    elif shape == "circle":
        radius = spacing * count / (2 * math.pi) if count > 1 else spacing
        for i in range(count):
            angle = 2 * math.pi * i / max(count, 1)
            offsets.append((radius * math.sin(angle), radius * math.cos(angle)))
    elif shape == "wedge":
        for i in range(count):
            offsets.append((-(i + 1) * spacing * 0.8, (i % 2 * 2 - 1) * (i + 1) * spacing * 0.5))
    else:
        offsets = [(0.0, i * spacing) for i in range(count)]
    return offsets


class CoordinatorUAVModel(GenericUAVModel):
    """
    Swarm coordinator — manages leader-follower formation.

    Can operate as a ground station (no own MAVLink) or as a flying leader.
    """

    FORMATIONS = ("line", "v", "grid", "circle", "wedge")

    def __init__(
        self,
        drone_id:          str  = "COORDINATOR",
        connection_string: Optional[str] = None,
        log_dir:           str  = "logs",
        auto_log:          bool = False,
        is_ground_station: bool = False,
    ):
        if connection_string:
            super().__init__(drone_id, connection_string, log_dir=log_dir, auto_log=auto_log)
        else:
            # Ground station mode — no MAVLink connection
            from droneresearch.sdk.drone import Drone
            # Bypass Drone.__init__ by creating a minimal stub
            self.id           = drone_id
            self._conn        = None
            self._logger      = None
            self._store       = None
            self._mission     = None
            self._event_cbs   = {}
            from droneresearch.core.fsm import StateMachine
            self.fsm          = StateMachine(drone_id=drone_id)
            self.swarm_role   = "coordinator"
            self.leader_id    = None
            self.formation_offset = (0.0, 0.0, 0.0)
            self.swarm_id     = None

        self._is_ground_station = is_ground_station or (connection_string is None)
        self._members: Dict[str, GenericUAVModel] = {}
        self._leader_id: Optional[str] = None
        self._formation   = "line"
        self._spacing_m   = 5.0
        self._follow_thread: Optional[threading.Thread] = None
        self._following   = False
        self._on_member_change: Optional[Callable] = None
        self._lock        = threading.Lock()
        self._apf = APFSafetyFilter(
            min_separation  = 3.0,
            max_speed       = 5.0,
            geofence_radius = 200.0,
            geofence_alt    = (1.0, 120.0),
            repulsion_gain  = 3.0,
            obstacle_radius = 5.0,
        )

    # ── Factory ───────────────────────────────────────────────────────────

    @classmethod
    def as_ground_station(cls) -> "CoordinatorUAVModel":
        return cls(drone_id="GCS", connection_string=None, is_ground_station=True)

    # ── Member management ─────────────────────────────────────────────────

    def register(self, drone_id: str, uav: GenericUAVModel):
        """Add a UAV to the swarm."""
        with self._lock:
            self._members[drone_id] = uav
        print(f"[coordinator] Registered {drone_id} (total: {len(self._members)})")
        if self._on_member_change:
            self._on_member_change(list(self._members.keys()))

    def unregister(self, drone_id: str):
        with self._lock:
            self._members.pop(drone_id, None)
        print(f"[coordinator] Unregistered {drone_id}")

    def members(self) -> List[GenericUAVModel]:
        with self._lock:
            return list(self._members.values())

    def member_ids(self) -> List[str]:
        with self._lock:
            return list(self._members.keys())

    def on_member_change(self, cb: Callable):
        self._on_member_change = cb

    # ── Leader assignment ─────────────────────────────────────────────────

    def set_leader(self, drone_id: str):
        """Designate a swarm member as leader."""
        with self._lock:
            if drone_id not in self._members:
                raise ValueError(f"Unknown drone: {drone_id}")
            self._leader_id = drone_id
            for did, uav in self._members.items():
                if did == drone_id:
                    uav.set_role("leader")
                else:
                    uav.set_role("follower", leader_id=drone_id)
        print(f"[coordinator] Leader: {drone_id}")

    @property
    def leader(self) -> Optional[GenericUAVModel]:
        if not self._leader_id:
            return None
        return self._members.get(self._leader_id)

    # ── Formation ─────────────────────────────────────────────────────────

    def set_formation(self, shape: str, spacing: float = 5.0):
        """
        Set formation shape and spacing.
        shape: "line" | "v" | "grid" | "circle" | "wedge"
        """
        if shape not in self.FORMATIONS:
            raise ValueError(f"Unknown formation: {shape}. Choose: {self.FORMATIONS}")
        self._formation = shape
        self._spacing_m = spacing
        self._assign_offsets()
        print(f"[coordinator] Formation: {shape}, spacing: {spacing}m")

    def _assign_offsets(self):
        with self._lock:
            followers = [
                (did, uav)
                for did, uav in self._members.items()
                if uav.swarm_role == "follower"
            ]
        offsets = _calc_offsets(self._formation, len(followers), self._spacing_m)
        for i, (did, uav) in enumerate(followers):
            off = offsets[i] if i < len(offsets) else (0.0, 0.0)
            uav.set_formation_offset(off[0], off[1], 0.0)

    # ── Swarm commands ────────────────────────────────────────────────────

    def takeoff_all(self, altitude: float = 10.0, stagger_s: float = 1.0):
        """Staggered takeoff to avoid prop wash interference."""
        for uav in self.members():
            uav.start(altitude=altitude)
            time.sleep(stagger_s)

    def land_all(self):
        for uav in self.members():
            uav.stop()

    def rtl_all(self):
        for uav in self.members():
            uav.return_home()

    def arm_all(self):
        self._broadcast(lambda u: u.arm())

    def disarm_all(self):
        self._broadcast(lambda u: u.disarm())

    def set_mode_all(self, mode: str):
        self._broadcast(lambda u: u.set_mode(mode))

    # ── Formation following loop ──────────────────────────────────────────

    def start_formation_follow(self, update_hz: float = 2.0):
        """
        Start continuous formation following.
        Followers update their goto target based on leader position every 1/hz seconds.
        """
        if self._following:
            return
        self._following = True
        self._follow_thread = threading.Thread(
            target=self._follow_loop,
            args=(1.0 / update_hz,),
            daemon=True,
            name="formation-follow",
        )
        self._follow_thread.start()
        print(f"[coordinator] Formation follow started ({update_hz}Hz)")

    def stop_formation_follow(self):
        self._following = False
        print("[coordinator] Formation follow stopped")

    def _uav_pose(self, uav: GenericUAVModel, ref_lat: float, ref_lon: float) -> Optional[Pose3D]:
        """Convert UAV GPS position to local NED Pose3D relative to ref point."""
        try:
            t = uav.telemetry
            if t.lat == 0.0 and t.lon == 0.0:
                return None
            north = (t.lat - ref_lat) * 111320.0
            east  = (t.lon - ref_lon) * 111320.0 * math.cos(math.radians(ref_lat))
            return Pose3D(north, east, t.alt_rel)
        except Exception:
            return None

    def _follow_loop(self, dt: float):
        _dbg_tick = 0
        while self._following:
            _dbg_tick += 1
            leader = self.leader
            if _dbg_tick % 10 == 1:
                print(f"  [follow] tick={_dbg_tick} leader={leader.id if leader else None} "
                      f"state={leader.fsm.state.name if leader else 'N/A'} "
                      f"airborne={leader.fsm.is_airborne if leader else False}")
            if leader and leader.fsm.is_airborne:
                lt = leader.telemetry
                with self._lock:
                    followers = [
                        uav for uav in self._members.values()
                        if uav.swarm_role == "follower" and uav.fsm.is_airborne
                    ]
                if _dbg_tick % 10 == 1:
                    print(f"  [follow] followers={[u.id+':'+u.fsm.state.name for u in followers]}")

                # Alle aktuellen Positionen (lokale NED relativ zu Leader-Home)
                ref_lat, ref_lon = lt.lat, lt.lon
                current: Dict[str, Pose3D] = {}
                for uav in followers:
                    p = self._uav_pose(uav, ref_lat, ref_lon)
                    if p:
                        current[uav.id] = p
                leader_pose = Pose3D(0.0, 0.0, lt.alt_rel)
                current[leader.id] = leader_pose

                # Gewünschte Formations-Zielpositionen
                desired: Dict[str, Pose3D] = {leader.id: leader_pose}
                for uav in followers:
                    n, e, a = uav.formation_offset
                    yaw_rad = math.radians(lt.yaw)
                    rot_n = n * math.cos(yaw_rad) - e * math.sin(yaw_rad)
                    rot_e = n * math.sin(yaw_rad) + e * math.cos(yaw_rad)
                    desired[uav.id] = Pose3D(rot_n, rot_e, lt.alt_rel + a)

                # APF-Filter: sichere Zwischenpositionen berechnen
                if len(current) >= 2:
                    safe = self._apf.filter(current, desired)
                else:
                    safe = desired

                # Goto-Befehle senden (GUIDED sicherstellen)
                for uav in followers:
                    sp = safe.get(uav.id)
                    if sp is None:
                        sp = desired.get(uav.id)
                    if sp is None:
                        continue
                    tgt_lat = ref_lat + sp.x / 111320.0
                    tgt_lon = ref_lon + sp.y / (
                        111320.0 * math.cos(math.radians(ref_lat)) + 1e-9
                    )
                    try:
                        if uav.telemetry.flight_mode.upper() != "GUIDED":
                            uav._conn.set_mode("GUIDED")
                        uav._conn.goto(tgt_lat, tgt_lon, sp.z)
                    except Exception:
                        pass

                # APF-Kollisionsprüfung — nur warnen
                if len(current) >= 2:
                    viols = self._apf.check_separation(current)
                    for a_id, b_id, dist in viols:
                        print(f"  [APF WARNUNG] {a_id} ↔ {b_id}: {dist:.2f}m")

            time.sleep(dt)

    # ── Status ────────────────────────────────────────────────────────────

    def swarm_status(self) -> dict:
        return {
            "leader":    self._leader_id,
            "formation": self._formation,
            "spacing":   self._spacing_m,
            "following": self._following,
            "members":   {did: uav.status() for did, uav in self._members.items()},
        }

    # ── Internal ──────────────────────────────────────────────────────────

    def _broadcast(self, fn: Callable, wait: bool = False):
        import threading
        threads = [
            threading.Thread(target=fn, args=(u,), daemon=True)
            for u in self.members()
        ]
        for t in threads:
            t.start()
        if wait:
            for t in threads:
                t.join(timeout=30)

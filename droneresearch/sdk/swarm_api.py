"""
Swarm — high-level multi-drone API.

Usage:
    from droneresearch.swarm import Swarm

    swarm = Swarm()
    swarm.add("D1", "tcp:127.0.0.1:5760")
    swarm.add("D2", "tcp:127.0.0.1:5761")
    swarm.connect_all()
    swarm.arm_all()
    swarm.takeoff_all(altitude=10)
    swarm.formation("circle", spacing=5.0, leader="D1")
    swarm.land_all()
"""
import math
import threading
import time
from typing import Callable, Dict, List, Optional

from droneresearch.sdk.drone import Drone


class Swarm:
    FORMATIONS = ("line", "v", "grid", "circle")

    def __init__(self, log_dir: str = "logs", auto_log: bool = True):
        self._drones:   Dict[str, Drone] = {}
        self._log_dir   = log_dir
        self._auto_log  = auto_log
        self._lock      = threading.Lock()
        self._event_cbs: dict = {}

    # ── Drone management ─────────────────────────────────────────────────

    def add(self, drone_id: str, connection_string: str) -> Drone:
        d = Drone(connection_string, drone_id=drone_id,
                  log_dir=self._log_dir, auto_log=self._auto_log)
        with self._lock:
            self._drones[drone_id] = d
        return d

    def remove(self, drone_id: str):
        with self._lock:
            d = self._drones.pop(drone_id, None)
        if d:
            d.disconnect()

    def get(self, drone_id: str) -> Optional[Drone]:
        return self._drones.get(drone_id)

    @property
    def drones(self) -> List[Drone]:
        with self._lock:
            return list(self._drones.values())

    @property
    def count(self) -> int:
        return len(self._drones)

    # ── Connection ────────────────────────────────────────────────────────

    def connect_all(self, timeout: float = 15.0) -> Dict[str, bool]:
        results = {}
        threads = []
        for did, drone in list(self._drones.items()):
            def _connect(d=drone, did=did):
                results[did] = d.connect(timeout=timeout)
            t = threading.Thread(target=_connect, daemon=True)
            threads.append(t)
            t.start()
        for t in threads:
            t.join(timeout=timeout + 2)
        return results

    def disconnect_all(self):
        for d in self.drones:
            d.disconnect()

    # ── Commands (parallel) ───────────────────────────────────────────────

    def arm_all(self, force: bool = False):
        self._broadcast(lambda d: d.arm(force=force))

    def disarm_all(self, force: bool = False):
        self._broadcast(lambda d: d.disarm(force=force))

    def takeoff_all(self, altitude: float = 10.0):
        self._broadcast(lambda d: d.takeoff(altitude=altitude))

    def land_all(self):
        self._broadcast(lambda d: d.land())

    def rtl_all(self):
        self._broadcast(lambda d: d.rtl())

    def set_mode_all(self, mode: str):
        self._broadcast(lambda d: d.set_mode(mode))

    def set_speed_all(self, speed_ms: float):
        self._broadcast(lambda d: d.set_speed(speed_ms))

    # ── Formation ─────────────────────────────────────────────────────────

    def formation(self, shape: str, spacing: float = 5.0, leader: Optional[str] = None):
        """
        Fly formation around leader drone.

        shape: "line" | "v" | "grid" | "circle"
        spacing: distance between drones in meters
        leader: drone ID of formation leader (default: first drone)
        """
        drones = self.drones
        if not drones:
            return
        leader_drone = self._drones.get(leader) if leader else drones[0]
        offsets = self._calc_offsets(shape, len(drones), spacing)
        lat0, lon0, alt0 = leader_drone.position

        for i, drone in enumerate(drones):
            if drone is leader_drone:
                continue
            off = offsets[i] if i < len(offsets) else (0, 0)
            dlat = off[0] / 111320.0
            dlon = off[1] / (111320.0 * math.cos(math.radians(lat0)) + 1e-9)
            target_lat = lat0 + dlat
            target_lon = lon0 + dlon
            threading.Thread(
                target=drone.goto,
                args=(target_lat, target_lon, alt0),
                daemon=True,
            ).start()

    # ── Data ─────────────────────────────────────────────────────────────

    def telemetry_all(self) -> Dict[str, dict]:
        return {did: d.telemetry.snapshot() for did, d in self._drones.items()}

    def on(self, event: str, callback: Callable):
        self._event_cbs.setdefault(event, []).append(callback)

    # ── Internal ──────────────────────────────────────────────────────────

    def _broadcast(self, fn: Callable, wait: bool = False):
        threads = []
        for drone in self.drones:
            t = threading.Thread(target=fn, args=(drone,), daemon=True)
            threads.append(t)
            t.start()
        if wait:
            for t in threads:
                t.join(timeout=30)

    @staticmethod
    def _calc_offsets(shape: str, count: int, spacing: float) -> List[tuple]:
        # Delegated to the canonical implementation in droneresearch.sdk.formations.
        # ``count`` here is the *total* drone count (incl. leader) for backwards
        # compatibility; the canonical function expects follower count, so
        # subtract 1. The caller in ``formation()`` indexes offsets[i] with i
        # being the drone index (incl. leader); the leader's slot is unused.
        from droneresearch.sdk.formations import formation_offsets
        return list(formation_offsets(shape, max(0, count - 1), spacing))

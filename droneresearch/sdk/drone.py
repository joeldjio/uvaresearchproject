"""
Drone — the main public API class.

This is what researchers import and use in their scripts.

Usage:
    from droneresearch import Drone

    drone = Drone("tcp:127.0.0.1:5760")
    drone.connect()
    drone.arm()
    drone.takeoff(10)

    @drone.on("altitude")
    def on_alt(v):
        if v > 15:
            drone.set_speed(3.0)

    drone.wait_for_landing()
    drone.disconnect()
"""
import time
import threading
from typing import Callable, Optional

from droneresearch.core.connection import MAVLinkConnection
from droneresearch.core.telemetry import TelemetryState
from droneresearch.control.mission import MissionEngine, Waypoint
from droneresearch.data.logger import TelemetryLogger
from droneresearch.data.store import TelemetryStore


class Drone:
    """
    High-level drone API.

    All blocking methods (arm, takeoff, goto, …) accept a timeout parameter
    and raise TimeoutError if the operation does not complete in time.
    """

    def __init__(
        self,
        connection_string: str,
        drone_id:     str  = "drone",
        log_dir:      str  = "logs",
        auto_log:     bool = True,
    ):
        self.id               = drone_id
        self._conn            = MAVLinkConnection(connection_string)
        self._logger          = TelemetryLogger(log_dir) if auto_log else None
        self._store           = TelemetryStore()
        self._mission         = MissionEngine(self._conn)
        self._event_cbs: dict = {}
        self._stop            = threading.Event()

        # Wire core events → high-level events
        self._conn.on("telemetry",    self._on_telemetry)
        self._conn.on("armed",        lambda v: self._emit("armed", v))
        self._conn.on("mode",         lambda v: self._emit("mode", v))
        self._conn.on("statustext",   lambda t, s: self._emit("statustext", t, s))
        self._conn.on("connected",    lambda: self._emit("connected"))
        self._conn.on("disconnected", lambda: self._emit("disconnected"))
        self._conn.on(
            "command_ack",
            lambda name, code, res, ok: self._emit("command_ack", name, code, res, ok),
        )

    # ── Connection ────────────────────────────────────────────────────────

    def connect(self, timeout: float = 15.0) -> bool:
        ok = self._conn.connect(timeout=timeout)
        if ok and self._logger:
            self._logger.start(drone_id=self.id)
        return ok

    def disconnect(self):
        if self._logger:
            self._logger.stop()
        self._conn.disconnect()

    @property
    def connected(self) -> bool:
        return self._conn.connected

    # ── Telemetry (direct attribute access) ───────────────────────────────

    @property
    def telemetry(self) -> TelemetryState:
        return self._conn.telemetry

    @property
    def lat(self) -> float:
        return self._conn.telemetry.lat

    @property
    def lon(self) -> float:
        return self._conn.telemetry.lon

    @property
    def altitude(self) -> float:
        return self._conn.telemetry.alt_rel

    @property
    def heading(self) -> float:
        return self._conn.telemetry.yaw

    @property
    def armed(self) -> bool:
        return self._conn.telemetry.armed

    @property
    def mode(self) -> str:
        return self._conn.telemetry.flight_mode

    @property
    def battery(self) -> float:
        return self._conn.telemetry.battery_pct

    @property
    def groundspeed(self) -> float:
        return self._conn.telemetry.groundspeed

    @property
    def position(self) -> tuple:
        t = self._conn.telemetry
        return (t.lat, t.lon, t.alt_rel)

    # ── Commands ──────────────────────────────────────────────────────────

    def arm(self, timeout: float = 10.0, force: bool = False) -> bool:
        self._conn.arm(force=force)
        return self._wait_for(lambda: self._conn.telemetry.armed, timeout)

    def disarm(self, timeout: float = 5.0, force: bool = False) -> bool:
        self._conn.disarm(force=force)
        return self._wait_for(lambda: not self._conn.telemetry.armed, timeout)

    def set_mode(self, mode: str, timeout: float = 5.0) -> bool:
        self._conn.set_mode(mode)
        return self._wait_for(
            lambda: self._conn.telemetry.flight_mode.upper() == mode.upper(),
            timeout,
        )

    def takeoff(self, altitude: float = 10.0, timeout: float = 30.0) -> bool:
        if not self.armed:
            self.arm()
        self.set_mode("GUIDED")
        self._conn.takeoff(altitude)
        return self._wait_for(
            lambda: self._conn.telemetry.alt_rel >= altitude * 0.85,
            timeout,
        )

    def land(self, timeout: float = 60.0) -> bool:
        self._conn.land()
        return self._wait_for(
            lambda: not self._conn.telemetry.armed,
            timeout,
        )

    def rtl(self):
        self._conn.rtl()

    def goto(self, lat: float, lon: float, alt: float, timeout: float = 60.0) -> bool:
        self.set_mode("GUIDED")
        self._conn.goto(lat, lon, alt)
        return self._wait_for(
            lambda: self._distance_to(lat, lon) < 2.0,
            timeout,
        )

    def set_speed(self, speed_ms: float):
        self._conn.set_speed(speed_ms)

    def wait(self, seconds: float):
        time.sleep(seconds)

    def wait_for_landing(self, timeout: float = 300.0) -> bool:
        return self._wait_for(lambda: not self._conn.telemetry.armed, timeout)

    # ── Mission ───────────────────────────────────────────────────────────

    @property
    def mission(self) -> MissionEngine:
        return self._mission

    def run_mission(self, waypoints: list, wait: bool = True, timeout: float = 600.0) -> bool:
        self._mission.clear()
        for wp in waypoints:
            if isinstance(wp, dict):
                self._mission.add(Waypoint(**wp))
            else:
                self._mission.add(wp)
        self._mission.upload()
        self._mission.start()
        if wait:
            return self._mission.wait_done(timeout=timeout)
        return True

    # ── Data access ───────────────────────────────────────────────────────

    @property
    def store(self) -> TelemetryStore:
        return self._store

    def get_history(self, last_n: int = 100) -> list:
        return self._store.get(self.id, last_n=last_n)

    def export_csv(self) -> str:
        return self._store.export_csv(self.id)

    # ── Events ────────────────────────────────────────────────────────────

    def on(self, event: str, callback: Callable = None):
        """Register event callback. Can be used as decorator."""
        if callback is None:
            def decorator(fn):
                self._event_cbs.setdefault(event, []).append(fn)
                return fn
            return decorator
        self._event_cbs.setdefault(event, []).append(callback)

    def off(self, event: str, callback: Callable):
        if event in self._event_cbs:
            self._event_cbs[event] = [c for c in self._event_cbs[event] if c is not callback]

    # ── Internal ──────────────────────────────────────────────────────────

    def _emit(self, event: str, *args):
        for cb in self._event_cbs.get(event, []):
            try:
                cb(*args)
            except Exception as e:
                print(f"[drone] event error ({event}): {e}")

    def _on_telemetry(self, tel: TelemetryState):
        snap = tel.snapshot()
        self._store.push(self.id, snap)
        if self._logger:
            self._logger.log(snap)
        self._emit("telemetry", tel)
        self._emit("altitude",   tel.alt_rel)
        self._emit("position",   tel.lat, tel.lon, tel.alt_rel)
        self._emit("attitude",   tel.roll, tel.pitch, tel.yaw)
        self._emit("battery",    tel.battery_pct)
        self._emit("speed",      tel.groundspeed)

    def _wait_for(self, condition: Callable, timeout: float) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if condition():
                return True
            time.sleep(0.1)
        return False

    def _distance_to(self, lat: float, lon: float) -> float:
        import math
        t = self._conn.telemetry
        dlat = math.radians(lat - t.lat)
        dlon = math.radians(lon - t.lon)
        a = (math.sin(dlat/2)**2 +
             math.cos(math.radians(t.lat)) * math.cos(math.radians(lat)) *
             math.sin(dlon/2)**2)
        return 6371000 * 2 * math.asin(math.sqrt(a))

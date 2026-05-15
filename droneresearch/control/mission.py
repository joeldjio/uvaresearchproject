"""
MissionEngine — upload/run/monitor MAVLink missions.

Waypoint format follows MAVLink MISSION_ITEM_INT.

Usage:
    mission = MissionEngine(connection)
    mission.add(Waypoint(lat=48.137, lon=11.575, alt=20))
    mission.add(Waypoint(lat=48.138, lon=11.576, alt=20))
    mission.upload()
    mission.start()
    mission.wait_done()
"""
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional, Callable

from droneresearch.core.connection import MAVLinkConnection


@dataclass
class Waypoint:
    lat:     float
    lon:     float
    alt:     float = 10.0
    speed:   Optional[float] = None   # m/s, None = keep current
    hold:    float = 0.0              # seconds to loiter
    cmd:     int   = 16               # MAV_CMD_NAV_WAYPOINT
    radius:  float = 2.0              # acceptance radius m


class MissionEngine:
    def __init__(self, connection: MAVLinkConnection):
        self._conn      = connection
        self._waypoints: List[Waypoint] = []
        self._current   = -1
        self._running   = False
        self._done_event  = threading.Event()
        self._abort_event = threading.Event()
        self._last_seq    = -1
        self._on_waypoint: Optional[Callable] = None
        self._on_done:     Optional[Callable] = None

        connection.on("message", self._on_message)

    # ── Build mission ─────────────────────────────────────────────────────

    def clear(self):
        self._waypoints.clear()

    def add(self, wp: Waypoint):
        self._waypoints.append(wp)

    def from_list(self, points: List[dict]):
        self._waypoints = [
            Waypoint(lat=p["lat"], lon=p["lon"], alt=p.get("alt", 10.0))
            for p in points
        ]

    # ── Upload & control ──────────────────────────────────────────────────

    def upload(self) -> bool:
        """Upload all queued waypoints to the autopilot.

        .. warning::
            This is **blocking** for ~50ms per waypoint plus 100ms init.
            For 30 waypoints that's ~1.6s, so **always call from a worker
            thread**, never from the UI / Qt main thread.

        Implementation notes:

        * Inter-item pacing uses ``self._abort_event.wait`` instead of
          ``time.sleep`` so :meth:`abort` interrupts an in-flight upload
          immediately (previously it would run to completion and only the
          subsequent ``start`` was aborted).
        * Both ``mission_count_send`` and ``mission_item_int_send`` calls
          are exception-safe \u2014 a single failed send aborts the upload
          with ``False`` rather than leaving the autopilot in an
          inconsistent state.
        """
        mav = self._conn._mav
        if not mav or not self._waypoints:
            return False
        # Allow upload() to be called again after a previous abort().
        self._abort_event.clear()

        try:
            count = len(self._waypoints) + 1   # +1 for home
            mav.mav.mission_count_send(
                mav.target_system, mav.target_component, count, 0
            )
        except Exception as e:
            print(f"[mission] mission_count_send failed: {e}")
            return False
        # 100 ms grace for the autopilot to allocate the mission buffer.
        if self._abort_event.wait(0.1):
            return False

        # Home (index 0)
        t = self._conn.telemetry
        try:
            mav.mav.mission_item_int_send(
                mav.target_system, mav.target_component,
                0, 0, 16, 1, 1,
                0, 0, 0, 0,
                int(t.home_lat * 1e7) or int(t.lat * 1e7),
                int(t.home_lon * 1e7) or int(t.lon * 1e7),
                t.home_alt or t.alt, 0
            )
        except Exception as e:
            print(f"[mission] home item send failed: {e}")
            return False
        if self._abort_event.wait(0.05):
            return False

        for i, wp in enumerate(self._waypoints):
            try:
                mav.mav.mission_item_int_send(
                    mav.target_system, mav.target_component,
                    i + 1, 3, wp.cmd, 0, 1,
                    wp.hold, wp.radius, 0, 0,
                    int(wp.lat * 1e7), int(wp.lon * 1e7), wp.alt, 0
                )
            except Exception as e:
                print(f"[mission] item {i+1} send failed: {e}")
                return False
            # cancel-aware pacing
            if self._abort_event.wait(0.05):
                return False
        return True

    def start(self) -> bool:
        if not self._conn.set_mode("AUTO"):
            return False
        self._running = True
        self._done_event.clear()
        self._current = 0
        self._last_seq = -1
        return True

    def pause(self) -> bool:
        return self._conn.set_mode("LOITER")

    def resume(self) -> bool:
        return self._conn.set_mode("AUTO")

    def abort(self) -> bool:
        self._running = False
        # Interrupt any in-flight upload() loop and unblock wait_done().
        self._abort_event.set()
        self._done_event.set()
        return self._conn.rtl()

    def wait_done(self, timeout: float = 600.0) -> bool:
        return self._done_event.wait(timeout=timeout)

    # ── Callbacks ─────────────────────────────────────────────────────────

    def on_waypoint_reached(self, cb: Callable):
        self._on_waypoint = cb

    def on_mission_done(self, cb: Callable):
        self._on_done = cb

    # ── Internal ──────────────────────────────────────────────────────────

    def _on_message(self, msg):
        t = msg.get_type()
        if t == "MISSION_CURRENT":
            self._current = msg.seq
            if self._on_waypoint:
                self._on_waypoint(msg.seq)
        elif t == "MISSION_ITEM_REACHED":
            self._last_seq = msg.seq
            if self._on_waypoint:
                self._on_waypoint(msg.seq)
            # Last waypoint reached -> mission done
            if self._running and msg.seq >= len(self._waypoints):
                self._mark_done()
        elif t == "MISSION_ACK" and msg.type == 0:
            # Successful upload-ack ignored; only completion-ack matters here.
            pass
        elif t == "HEARTBEAT":
            # Mode left AUTO while a mission is running -> mark done so
            # wait_done() can return instead of hanging forever.
            mode = (self._conn.telemetry.flight_mode or "").upper()
            if self._running and mode not in ("AUTO", "GUIDED") and self._current > 0:
                self._mark_done()

    def _mark_done(self):
        if self._done_event.is_set():
            return
        self._running = False
        self._done_event.set()
        if self._on_done:
            try:
                self._on_done()
            except Exception:
                pass

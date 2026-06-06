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
from typing import Callable, List, Optional

from droneresearch.core.connection import MAVLinkConnection


@dataclass
class Waypoint:
    lat: float
    lon: float
    alt: float = 10.0
    speed: Optional[float] = None  # m/s, None = keep current
    hold: float = 0.0  # seconds to loiter
    cmd: int = 16  # MAV_CMD_NAV_WAYPOINT
    radius: float = 2.0  # acceptance radius m


class MissionEngine:
    _HANDSHAKE_TIMEOUT = 0.25  # seconds to wait for MISSION_REQUEST(0)

    def __init__(self, connection: MAVLinkConnection):
        self._conn = connection
        self._waypoints: List[Waypoint] = []
        self._current = -1
        self._running = False
        self._done_event = threading.Event()
        self._abort_event = threading.Event()
        self._last_seq = -1
        self._on_waypoint: Optional[Callable] = None
        self._on_done: Optional[Callable] = None
        # Upload-time state (initialised in upload())
        self._req_events: dict = {}
        self._ack_event = threading.Event()
        self._ack_result: int = -1

        connection.on("message", self._on_message)

    # ── Build mission ─────────────────────────────────────────────────────

    def clear(self):
        self._waypoints.clear()

    def add(self, wp: Waypoint):
        self._waypoints.append(wp)

    def from_list(self, points: List[dict]):
        self._waypoints = [
            Waypoint(lat=p["lat"], lon=p["lon"], alt=p.get("alt", 10.0)) for p in points
        ]

    # ── Upload & control ──────────────────────────────────────────────────

    def upload(self) -> bool:
        """Upload all queued waypoints to the autopilot.

        .. warning::
            This is **blocking** for ~50ms per waypoint (push-all path) or
            until the autopilot completes the handshake (request-based path).
            Always call from a worker thread, never from the UI / Qt main
            thread.

        Uses a **hybrid protocol**:

        1. Sends ``MISSION_COUNT`` and waits up to
           :attr:`_HANDSHAKE_TIMEOUT` seconds for a ``MISSION_REQUEST(0)``
           from the autopilot.
        2. If the request arrives → full request/response handshake
           (correct MAVLink behaviour).
        3. Otherwise → legacy push-all with 50 ms inter-item pacing
           (ArduPilot-compatible fallback).

        Abort via :meth:`abort` is honoured at every step.
        """
        mav = self._conn._mav
        if not mav or not self._waypoints:
            return False
        # Allow upload() to be called again after a previous abort().
        self._abort_event.clear()

        n = len(self._waypoints) + 1  # +1 for home
        self._req_events = {i: threading.Event() for i in range(n)}
        self._ack_event = threading.Event()
        self._ack_result = -1
        self._conn.on("message", self._on_upload_msg)

        try:
            return self._do_upload(mav, n)
        finally:
            try:
                self._conn.off("message", self._on_upload_msg)
            except AttributeError:
                pass
            self._req_events = {}
            self._ack_event.clear()

    def _do_upload(self, mav, n: int) -> bool:
        """Send MISSION_COUNT and choose handshake vs. push-all path."""
        try:
            mav.mav.mission_count_send(mav.target_system, mav.target_component, n, 0)
        except Exception as e:
            print(f"[mission] mission_count_send failed: {e}")
            return False

        # Wait for MISSION_REQUEST(0), checking abort every 10 ms.
        deadline = time.time() + self._HANDSHAKE_TIMEOUT
        while time.time() < deadline:
            if self._abort_event.is_set():
                return False
            if self._req_events[0].is_set():
                break
            time.sleep(0.01)
        use_handshake = self._req_events[0].is_set()

        if use_handshake:
            return self._upload_handshake(mav, n)
        else:
            return self._upload_push_all(mav, n)

    def _upload_handshake(self, mav, n: int) -> bool:
        """Request-based handshake: send each item only after MISSION_REQUEST."""
        for seq in range(n):
            # seq 0 was already signalled (it triggered this path).
            if seq > 0:
                if self._abort_event.is_set():
                    return False
                if not self._req_events[seq].wait(timeout=3.0):
                    print(f"[mission] timeout waiting for MISSION_REQUEST({seq})")
                    return False
            if not self._send_item(mav, seq):
                return False
        # Wait for final MISSION_ACK.
        if not self._ack_event.wait(timeout=5.0):
            print("[mission] timeout waiting for MISSION_ACK")
            return False
        return self._ack_result == 0  # MAV_MISSION_ACCEPTED

    def _upload_push_all(self, mav, n: int) -> bool:
        """Legacy push-all with 50 ms cancel-aware pacing (ArduPilot fallback)."""
        if self._abort_event.is_set():
            return False
        if not self._send_item(mav, 0):
            return False
        for seq in range(1, n):
            if self._abort_event.wait(0.05):
                return False
            if not self._send_item(mav, seq):
                return False
        return True

    def _send_item(self, mav, seq: int) -> bool:
        """Send a single MISSION_ITEM_INT for *seq*."""
        t = self._conn.telemetry
        try:
            if seq == 0:  # home
                mav.mav.mission_item_int_send(
                    mav.target_system,
                    mav.target_component,
                    0,
                    0,
                    16,
                    1,
                    1,
                    0,
                    0,
                    0,
                    0,
                    int(t.home_lat * 1e7) or int(t.lat * 1e7),
                    int(t.home_lon * 1e7) or int(t.lon * 1e7),
                    t.home_alt or t.alt,
                    0,
                )
            else:
                wp = self._waypoints[seq - 1]
                mav.mav.mission_item_int_send(
                    mav.target_system,
                    mav.target_component,
                    seq,
                    3,
                    wp.cmd,
                    0,
                    1,
                    wp.hold,
                    wp.radius,
                    0,
                    0,
                    int(wp.lat * 1e7),
                    int(wp.lon * 1e7),
                    wp.alt,
                    0,
                )
        except Exception as e:
            print(f"[mission] send item {seq} failed: {e}")
            return False
        return True

    def _on_upload_msg(self, msg) -> None:
        """Listener registered for the duration of upload() only."""
        t = msg.get_type()
        if t in ("MISSION_REQUEST", "MISSION_REQUEST_INT"):
            seq = getattr(msg, "seq", None)
            if seq is not None and seq in self._req_events:
                self._req_events[seq].set()
        elif t == "MISSION_ACK":
            self._ack_result = getattr(msg, "type", -1)
            self._ack_event.set()

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

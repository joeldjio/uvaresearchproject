"""
MAVLinkConnection — core MAVLink connection layer.

Supports:
  - ArduPilot (Copter, Plane, Rover)
  - PX4
  - Serial, TCP, UDP connections

Usage:
    conn = MAVLinkConnection("tcp:127.0.0.1:5760")
    conn.connect()
    print(conn.telemetry.lat, conn.telemetry.lon)
    conn.disconnect()
"""
import math
import threading
import time
from typing import Callable, Dict, List, Optional

from droneresearch.core.telemetry import TelemetryState

try:
    from pymavlink import mavutil, mavextra
    _MAVLINK_OK = True
except ImportError:
    _MAVLINK_OK = False


# ArduPilot custom mode map
_ARDUPILOT_MODES = {
    0: "STABILIZE", 1: "ACRO", 2: "ALT_HOLD", 3: "AUTO",
    4: "GUIDED",    5: "LOITER", 6: "RTL",     7: "CIRCLE",
    9: "LAND",     11: "DRIFT", 13: "SPORT",  14: "FLIP",
    15: "AUTOTUNE",16: "POSHOLD",17: "BRAKE", 18: "THROW",
    19: "AVOID_ADSB",20: "GUIDED_NOGPS",21: "SMART_RTL",
    22: "FLOWHOLD", 23: "FOLLOW", 24: "ZIGZAG",
}

# PX4 main mode map
_PX4_MAIN_MODES = {
    1: "MANUAL", 2: "ALTCTL", 3: "POSCTL",
    4: "AUTO",   5: "ACRO",  6: "OFFBOARD",
    7: "STABILIZED", 8: "RATTITUDE",
}

_PX4_SUB_MODES_AUTO = {
    1: "READY", 2: "TAKEOFF", 3: "LOITER",
    4: "MISSION", 5: "RTL",   6: "LAND",
    8: "FOLLOW_TARGET",
}


class MAVLinkConnection:
    """
    Thread-safe MAVLink connection.

    Events (register with .on(event, callback)):
        "connected"    — fired once connection is established
        "disconnected" — fired on disconnect
        "telemetry"    — fired on every telemetry update (TelemetryState)
        "message"      — fired on every raw MAVLink message
        "statustext"   — fired on STATUSTEXT (text, severity)
        "armed"        — fired when armed state changes (bool)
        "mode"         — fired when flight mode changes (str)
    """

    STREAM_RATES = {
        1:  4,   # RAW_SENSORS
        2:  4,   # EXTENDED_STATUS (battery, etc.)
        3:  2,   # RC_CHANNELS
        6:  4,   # POSITION (GPS)
        10: 10,  # EXTRA1 (attitude)
        11: 4,   # EXTRA2 (VFR_HUD)
        12: 2,   # EXTRA3 (AHRS, wind)
    }

    def __init__(self, connection_string: str, source_system: int = 255):
        if not _MAVLINK_OK:
            raise ImportError("pymavlink not installed: pip install pymavlink")
        self.connection_string = connection_string
        self.source_system     = source_system
        self.telemetry         = TelemetryState()
        self._mav              = None
        self._thread           = None
        self._stop             = threading.Event()
        self._connected        = False
        self._listeners: Dict[str, List[Callable]] = {}
        self._lock             = threading.Lock()

    # ── Public API ───────────────────────────────────────────────────────────

    def connect(self, timeout: float = 15.0) -> bool:
        if self._connected:
            return True
        self._stop.clear()
        try:
            self._mav = mavutil.mavlink_connection(
                self.connection_string,
                source_system=self.source_system,
                autoreconnect=True,
            )
            hb = self._mav.wait_heartbeat(timeout=timeout)
            if hb is None:
                return False
        except Exception as e:
            self._emit("statustext", f"Connection error: {e}", 3)
            return False

        self._detect_autopilot(hb)
        self._connected = True
        self._request_streams()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="mav-rx")
        self._thread.start()
        self._emit("connected")
        return True

    def disconnect(self):
        self._stop.set()
        self._connected = False
        if self._mav:
            try:
                self._mav.close()
            except Exception:
                pass
            self._mav = None
        self._emit("disconnected")

    @property
    def connected(self) -> bool:
        return self._connected

    def on(self, event: str, callback: Callable):
        self._listeners.setdefault(event, []).append(callback)

    def off(self, event: str, callback: Callable):
        if event in self._listeners:
            self._listeners[event] = [c for c in self._listeners[event] if c is not callback]

    # ── Commands ─────────────────────────────────────────────────────────────

    def arm(self, force: bool = False) -> bool:
        param2 = 21196.0 if force else 0.0
        return self._command_long(400, 1.0, param2)

    def disarm(self, force: bool = False) -> bool:
        param2 = 21196.0 if force else 0.0
        return self._command_long(400, 0.0, param2)

    def set_mode(self, mode: str) -> bool:
        mode = mode.upper()
        if self.telemetry.autopilot == "px4":
            return self._set_mode_px4(mode)
        return self._set_mode_ardupilot(mode)

    def takeoff(self, altitude: float = 10.0) -> bool:
        return self._command_long(22, 0, 0, 0, 0, 0, 0, altitude)

    def land(self) -> bool:
        return self._command_long(21)

    def rtl(self) -> bool:
        return self._command_long(20)

    def goto(self, lat: float, lon: float, alt: float) -> bool:
        if not self._mav:
            return False
        self._mav.mav.mission_item_send(
            self._mav.target_system,
            self._mav.target_component,
            0, 3, 16, 2, 1, 0, 0, 0, 0,
            lat, lon, alt,
        )
        return True

    def set_speed(self, speed_ms: float) -> bool:
        return self._command_long(178, 1, speed_ms, -1, 0)

    def send_raw(self, msg_type: str, **kwargs):
        if self._mav:
            getattr(self._mav.mav, f"{msg_type}_send")(**kwargs)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _emit(self, event: str, *args):
        for cb in self._listeners.get(event, []):
            try:
                cb(*args)
            except Exception as e:
                print(f"[core] listener error ({event}): {e}")

    def _command_long(self, cmd, p1=0, p2=0, p3=0, p4=0, p5=0, p6=0, p7=0) -> bool:
        if not self._mav:
            return False
        self._mav.mav.command_long_send(
            self._mav.target_system,
            self._mav.target_component,
            cmd, 0, p1, p2, p3, p4, p5, p6, p7,
        )
        return True

    def _detect_autopilot(self, heartbeat):
        ap = heartbeat.autopilot
        if ap == 3:
            self.telemetry.update(autopilot="ardupilot")
        elif ap == 12:
            self.telemetry.update(autopilot="px4")
        else:
            self.telemetry.update(autopilot="unknown")

    def _request_streams(self):
        if not self._mav:
            return
        for sid, rate in self.STREAM_RATES.items():
            self._mav.mav.request_data_stream_send(
                self._mav.target_system,
                self._mav.target_component,
                sid, rate, 1,
            )

    def _set_mode_ardupilot(self, mode: str) -> bool:
        mode_map = {v: k for k, v in _ARDUPILOT_MODES.items()}
        num = mode_map.get(mode)
        if num is None:
            return False
        return self._command_long(176, 1, num)

    def _set_mode_px4(self, mode: str) -> bool:
        base_mode = 1
        for num, name in _PX4_MAIN_MODES.items():
            if name == mode:
                return self._command_long(176, base_mode, num)
        return False

    def _loop(self):
        while not self._stop.is_set():
            if not self._mav:
                break
            try:
                msg = self._mav.recv_match(blocking=True, timeout=1.0)
            except Exception:
                break
            if msg is None:
                continue
            self._parse(msg)

    def _parse(self, msg):
        t = msg.get_type()
        tel = self.telemetry
        self._emit("message", msg)

        if t == "HEARTBEAT":
            armed = bool(msg.base_mode & 0x80)
            if armed != tel.armed:
                tel.update(armed=armed)
                self._emit("armed", armed)
            mode = self._decode_mode(msg)
            if mode != tel.flight_mode:
                tel.update(flight_mode=mode)
                self._emit("mode", mode)
            tel.update(last_heartbeat=time.time(), system_status=msg.system_status)

        elif t == "GLOBAL_POSITION_INT":
            tel.update(
                lat=msg.lat / 1e7, lon=msg.lon / 1e7,
                alt=msg.alt / 1000.0, alt_rel=msg.relative_alt / 1000.0,
                vx=msg.vx / 100.0, vy=msg.vy / 100.0, vz=msg.vz / 100.0,
                last_gps=time.time(),
            )
            self._emit("telemetry", tel)

        elif t == "GPS_RAW_INT":
            tel.update(gps_fix=msg.fix_type, satellites=msg.satellites_visible)

        elif t == "ATTITUDE":
            tel.update(
                roll=math.degrees(msg.roll),
                pitch=math.degrees(msg.pitch),
                yaw=math.degrees(msg.yaw) % 360,
                last_attitude=time.time(),
            )
            self._emit("telemetry", tel)

        elif t == "VFR_HUD":
            tel.update(
                airspeed=msg.airspeed, groundspeed=msg.groundspeed,
                alt=msg.alt, climb=msg.climb, throttle=msg.throttle,
            )

        elif t == "BATTERY_STATUS":
            if msg.voltages and msg.voltages[0] != 65535:
                tel.update(battery_v=msg.voltages[0] / 1000.0)
            tel.update(
                current_a=msg.current_battery / 100.0 if msg.current_battery >= 0 else 0.0,
                battery_pct=float(msg.battery_remaining) if msg.battery_remaining >= 0 else -1.0,
            )

        elif t == "SYS_STATUS":
            if msg.battery_remaining >= 0:
                tel.update(battery_pct=float(msg.battery_remaining))

        elif t == "RAW_IMU":
            tel.update(
                accel_x=msg.xacc / 1000.0, accel_y=msg.yacc / 1000.0, accel_z=msg.zacc / 1000.0,
                gyro_x=msg.xgyro / 1000.0, gyro_y=msg.ygyro / 1000.0, gyro_z=msg.zgyro / 1000.0,
            )

        elif t == "HOME_POSITION":
            tel.update(
                home_lat=msg.latitude / 1e7,
                home_lon=msg.longitude / 1e7,
                home_alt=msg.altitude / 1000.0,
            )

        elif t == "STATUSTEXT":
            self._emit("statustext", msg.text, msg.severity)

    def _decode_mode(self, hb) -> str:
        ap = self.telemetry.autopilot
        if ap == "ardupilot":
            return _ARDUPILOT_MODES.get(hb.custom_mode, f"MODE_{hb.custom_mode}")
        elif ap == "px4":
            main = (hb.custom_mode >> 16) & 0xFF
            sub  = (hb.custom_mode >> 24) & 0xFF
            name = _PX4_MAIN_MODES.get(main, f"MAIN_{main}")
            if main == 4:
                name = _PX4_SUB_MODES_AUTO.get(sub, name)
            return name
        return f"MODE_{hb.custom_mode}"

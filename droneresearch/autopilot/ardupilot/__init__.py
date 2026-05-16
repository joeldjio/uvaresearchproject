"""
ArduPilot-specific extensions on top of MAVLinkBackend.

ArduPilot-specific features:
    - Extended mode list (THROW, SMART_RTL, ZIGZAG, etc.)
    - Parameter read/write
    - Rally points
    - Fence management
    - Scripting (Lua)
"""
import time
from typing import Optional

from droneresearch.autopilot.mavlink.backend import MAVLinkBackend


class ArduPilotBackend(MAVLinkBackend):
    """
    ArduPilot-specific backend.
    Extends MAVLinkBackend with ArduPilot-only features.
    """

    MODES = {
        0:"STABILIZE",1:"ACRO",2:"ALT_HOLD",3:"AUTO",4:"GUIDED",
        5:"LOITER",6:"RTL",7:"CIRCLE",9:"LAND",11:"DRIFT",
        13:"SPORT",14:"FLIP",15:"AUTOTUNE",16:"POSHOLD",
        17:"BRAKE",18:"THROW",19:"AVOID_ADSB",20:"GUIDED_NOGPS",
        21:"SMART_RTL",23:"FLOWHOLD",24:"FOLLOW",25:"ZIGZAG",
        26:"SYSTEMID",27:"AUTOROTATE",28:"AUTO_RTL",
    }

    def set_mode(self, mode: str) -> bool:
        mode_map = {v: k for k, v in self.MODES.items()}
        num = mode_map.get(mode.upper())
        if num is not None:
            self._cmd_long(176, 1, num)
            return True
        return False

    def set_parameter(self, name: str, value: float) -> bool:
        if not self._conn:
            return False
        self._conn.mav.param_set_send(
            self._conn.target_system,
            self._conn.target_component,
            name.encode("utf-8"),
            float(value),
            9,  # MAV_PARAM_TYPE_REAL32
        )
        return True

    def get_parameter(self, name: str, timeout: float = 5.0) -> Optional[float]:
        if not self._conn:
            return None
        self._conn.mav.param_request_read_send(
            self._conn.target_system,
            self._conn.target_component,
            name.encode("utf-8"),
            -1,
        )
        t0 = time.time()
        while time.time() - t0 < timeout:
            msg = self._conn.recv_match(type="PARAM_VALUE", blocking=True, timeout=1.0)
            if msg and msg.param_id.strip("\x00") == name:
                return msg.param_value
        return None


__all__ = ["ArduPilotBackend"]

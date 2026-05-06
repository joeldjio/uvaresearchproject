"""
TelemetryState — thread-safe snapshot of all drone telemetry.
Updated by MAVLinkConnection on every incoming message.
"""
import threading
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TelemetryState:
    # GPS
    lat:           float = 0.0
    lon:           float = 0.0
    alt:           float = 0.0          # m AMSL
    alt_rel:       float = 0.0          # m above home
    gps_fix:       int   = 0            # 0=no fix, 3=3D
    satellites:    int   = 0
    # Attitude
    roll:          float = 0.0          # deg
    pitch:         float = 0.0          # deg
    yaw:           float = 0.0          # deg (heading)
    # Velocity
    vx:            float = 0.0          # m/s north
    vy:            float = 0.0          # m/s east
    vz:            float = 0.0          # m/s down
    airspeed:      float = 0.0
    groundspeed:   float = 0.0
    climb:         float = 0.0
    # Battery
    battery_v:     float = 0.0
    battery_pct:   float = -1.0         # -1 = unknown
    current_a:     float = 0.0
    # Status
    armed:         bool  = False
    flight_mode:   str   = "UNKNOWN"
    autopilot:     str   = "UNKNOWN"    # "ardupilot" | "px4"
    system_status: int   = 0
    # RC
    throttle:      float = 0.0          # 0–100 %
    # IMU raw
    accel_x:       float = 0.0
    accel_y:       float = 0.0
    accel_z:       float = 0.0
    gyro_x:        float = 0.0
    gyro_y:        float = 0.0
    gyro_z:        float = 0.0
    # Home
    home_lat:      float = 0.0
    home_lon:      float = 0.0
    home_alt:      float = 0.0
    # Timestamps
    last_heartbeat: float = 0.0
    last_gps:       float = 0.0
    last_attitude:  float = 0.0

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def update(self, **kwargs):
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                k: getattr(self, k)
                for k in self.__dataclass_fields__
                if not k.startswith("_")
            }

    @property
    def is_stale(self) -> bool:
        return (time.time() - self.last_heartbeat) > 5.0

    @property
    def has_gps(self) -> bool:
        return self.gps_fix >= 3

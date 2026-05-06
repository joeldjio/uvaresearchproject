"""
AutopilotBackend — abstract base for all autopilot backends.

Concrete implementations:
    droneresearch.autopilot.mavlink  → ArduPilot + PX4 via MAVLink
    droneresearch.autopilot.px4      → PX4 native via uXRCE-DDS
    droneresearch.autopilot.ardupilot → ArduPilot-specific extensions

Every backend must implement this interface. The Drone SDK uses
only this interface — swap backends without changing mission code.
"""
from abc import ABC, abstractmethod
from typing import Callable, Optional


class TelemetrySnapshot:
    """Minimal shared telemetry contract across all backends."""
    __slots__ = (
        "lat", "lon", "alt", "alt_rel",
        "roll", "pitch", "yaw",
        "vx", "vy", "vz", "groundspeed",
        "armed", "flight_mode",
        "battery_v", "battery_pct",
        "gps_fix", "satellites",
        "timestamp",
    )
    def __init__(self):
        for s in self.__slots__:
            object.__setattr__(self, s, 0.0 if s != "flight_mode" else "UNKNOWN")
        object.__setattr__(self, "armed", False)
        object.__setattr__(self, "timestamp", 0.0)


class AutopilotBackend(ABC):
    """Abstract autopilot backend interface."""

    @abstractmethod
    def connect(self, connection_string: str, **kwargs) -> bool:
        """Establish connection. Returns True on success."""

    @abstractmethod
    def disconnect(self):
        """Close connection cleanly."""

    @property
    @abstractmethod
    def telemetry(self) -> TelemetrySnapshot:
        """Latest telemetry snapshot."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Connection health."""

    @abstractmethod
    def arm(self, force: bool = False) -> bool:
        """Arm motors."""

    @abstractmethod
    def disarm(self, force: bool = False) -> bool:
        """Disarm motors."""

    @abstractmethod
    def takeoff(self, altitude: float) -> bool:
        """Takeoff to altitude (meters AGL)."""

    @abstractmethod
    def land(self) -> bool:
        """Land in place."""

    @abstractmethod
    def rtl(self) -> bool:
        """Return to launch."""

    @abstractmethod
    def goto(self, lat: float, lon: float, alt: float) -> bool:
        """Fly to GPS coordinate."""

    @abstractmethod
    def set_mode(self, mode: str) -> bool:
        """Set flight mode by name."""

    @abstractmethod
    def send_command(self, cmd_id: int, *params) -> bool:
        """Send raw autopilot command."""

    def on_message(self, msg_type: str, cb: Callable):
        """Optional: register raw message callback."""

    def request_stream(self, stream_id: int, rate_hz: float):
        """Optional: request telemetry stream at given rate."""

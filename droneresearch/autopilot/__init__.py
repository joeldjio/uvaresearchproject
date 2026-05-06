"""
autopilot — hardware abstraction layer for drone autopilots.

Usage:
    from droneresearch.autopilot import AutopilotBackend
    from droneresearch.autopilot.mavlink import MAVLinkBackend
    from droneresearch.autopilot.ardupilot import ArduPilotBackend

    backend = MAVLinkBackend()
    backend.connect("tcp:127.0.0.1:5760")
"""
from droneresearch.autopilot.base import AutopilotBackend, TelemetrySnapshot

def get_backend(autopilot: str = "mavlink"):
    """
    Factory: returns the appropriate backend for a given autopilot string.
    autopilot: "mavlink" | "ardupilot" | "px4"
    """
    if autopilot in ("mavlink", "generic"):
        from droneresearch.autopilot.mavlink import MAVLinkBackend
        return MAVLinkBackend()
    elif autopilot == "ardupilot":
        from droneresearch.autopilot.ardupilot import ArduPilotBackend
        return ArduPilotBackend()
    elif autopilot == "px4":
        from droneresearch.ros.px4_bridge import PX4ROS2Bridge
        return PX4ROS2Bridge()
    else:
        raise ValueError(f"Unknown autopilot: {autopilot}. Choose: mavlink, ardupilot, px4")

__all__ = ["AutopilotBackend", "TelemetrySnapshot", "get_backend"]

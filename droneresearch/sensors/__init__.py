"""
Sensor integration modules for UAV perception.

Modules:
    depth_camera : ROS2 depth camera/point cloud subscriber
"""
from __future__ import annotations

__all__ = []

# Optional ROS2 depth camera support
try:
    from droneresearch.sensors.depth_camera import DepthCameraSubscriber
    __all__.append("DepthCameraSubscriber")
    _DEPTH_CAMERA_OK = True
except ImportError:
    _DEPTH_CAMERA_OK = False

# Made with Bob

"""
Shared, reference-counted ``rclpy`` context.

Multiple bridges (PX4, VSwarm, Frontier, generic) used to each call
``rclpy.init()`` and ``rclpy.shutdown()`` independently. The second
``init()`` would raise ``RCLError`` and any out-of-order ``shutdown()``
killed every other bridge's executor.

This module provides a thread-safe wrapper:

    from droneresearch.ros.context import acquire_ros, release_ros

    acquire_ros()       # first caller -> rclpy.init()
    try:
        ...             # create Node, spin, etc.
    finally:
        release_ros()   # last caller -> rclpy.shutdown()

The context is idempotent across bridges and safe to acquire from any
thread. Call counts are tracked in ``ros_refcount()`` for diagnostics.
"""
from __future__ import annotations

import threading
from typing import Optional

try:
    import rclpy
    _ROS2_OK = True
except ImportError:
    rclpy = None  # type: ignore
    _ROS2_OK = False


_LOCK = threading.Lock()
_COUNT = 0


def is_available() -> bool:
    """Return True if ``rclpy`` was importable at module load."""
    return _ROS2_OK


def acquire_ros() -> bool:
    """Increment the ROS refcount; call ``rclpy.init()`` on first use.

    Returns True if ROS is now initialized and available, False if
    ``rclpy`` is not installed.
    """
    global _COUNT
    if not _ROS2_OK:
        return False
    with _LOCK:
        if _COUNT == 0:
            try:
                if not rclpy.ok():
                    rclpy.init()
            except Exception as e:
                # init may legitimately fail if some other process owns
                # the context; surface the error but don't increment.
                print(f"[ros-context] rclpy.init() failed: {e}")
                return False
        _COUNT += 1
        return True


def release_ros() -> None:
    """Decrement the ROS refcount; call ``rclpy.shutdown()`` when it
    reaches zero. Safe to call more times than ``acquire_ros`` (extra
    calls are clamped at zero with a warning)."""
    global _COUNT
    if not _ROS2_OK:
        return
    with _LOCK:
        if _COUNT <= 0:
            print("[ros-context] release_ros() called more times than acquire \u2014 ignoring")
            _COUNT = 0
            return
        _COUNT -= 1
        if _COUNT == 0:
            try:
                if rclpy.ok():
                    rclpy.shutdown()
            except Exception as e:
                print(f"[ros-context] rclpy.shutdown() error: {e}")


def ros_refcount() -> int:
    with _LOCK:
        return _COUNT


__all__ = ["acquire_ros", "release_ros", "ros_refcount", "is_available"]

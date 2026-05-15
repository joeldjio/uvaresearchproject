"""Tests for the refcount-protected rclpy context."""
from __future__ import annotations

import threading

import pytest

from droneresearch.ros import context as ros_ctx
from droneresearch.ros.context import (
    acquire_ros,
    is_available,
    release_ros,
    ros_refcount,
)


@pytest.fixture(autouse=True)
def reset_refcount():
    """Make sure each test starts from a clean state."""
    # Drain any lingering refcount from previous tests
    while ros_refcount() > 0:
        release_ros()
    yield
    while ros_refcount() > 0:
        release_ros()


class TestRefcountSemantics:
    def test_initial_refcount_is_zero(self):
        assert ros_refcount() == 0

    def test_acquire_increments(self):
        ok = acquire_ros()
        if not is_available():
            # No rclpy installed -> acquire returns False, no increment.
            assert ok is False
            assert ros_refcount() == 0
            pytest.skip("rclpy not installed")
        assert ok is True
        assert ros_refcount() == 1

    def test_multiple_acquires_stack(self):
        if not is_available():
            pytest.skip("rclpy not installed")
        for expected in (1, 2, 3):
            acquire_ros()
            assert ros_refcount() == expected

    def test_release_decrements(self):
        if not is_available():
            pytest.skip("rclpy not installed")
        acquire_ros()
        acquire_ros()
        release_ros()
        assert ros_refcount() == 1
        release_ros()
        assert ros_refcount() == 0

    def test_extra_release_is_clamped_at_zero(self, capsys):
        release_ros()         # nothing to release
        release_ros()         # still nothing
        assert ros_refcount() == 0
        # The implementation prints a warning; we just check it doesn't crash.


class TestThreadSafety:
    """Concurrent acquire/release must produce a deterministic final count."""

    def test_balanced_concurrent_calls_end_at_zero(self):
        if not is_available():
            pytest.skip("rclpy not installed")

        N = 20
        barrier = threading.Barrier(N)
        errors: list = []

        def worker():
            try:
                barrier.wait()
                acquire_ros()
                release_ros()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert errors == []
        assert ros_refcount() == 0


class TestNoRclpyMode:
    """When rclpy is absent the API stays callable and is_no-op-safe."""

    def test_acquire_returns_false_without_rclpy(self, monkeypatch):
        # Force the "no rclpy" code-path even if rclpy is installed locally.
        monkeypatch.setattr(ros_ctx, "_ROS2_OK", False)
        assert acquire_ros() is False
        assert ros_refcount() == 0
        # release_ros is a no-op in this mode and must not raise.
        release_ros()

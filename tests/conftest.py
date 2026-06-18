"""
Shared pytest fixtures for the droneresearch test suite.

The suite is intentionally hardware-free: no MAVLink, no ROS2, no Qt event
loop. Anything that needs those is mocked here.
"""
from __future__ import annotations

import sys
import threading
from typing import Any, Dict, List, Callable
from unittest.mock import MagicMock, patch

import pytest


# ── Mock ROS2 modules before any imports ────────────────────────────────────
# This prevents ImportError when tests try to import ROS2-dependent modules

def _mock_rclpy():
    """Create a mock rclpy module with proper __spec__ attribute."""
    mock_rclpy = MagicMock()
    mock_rclpy.__spec__ = MagicMock()
    mock_rclpy.__spec__.name = "rclpy"
    return mock_rclpy


# Install mocks early
sys.modules['rclpy'] = _mock_rclpy()
sys.modules['cv_bridge'] = MagicMock()
sys.modules['px4_msgs'] = MagicMock()
sys.modules['px4_msgs.msg'] = MagicMock()


# ── Fake telemetry/connection for MissionEngine tests ──────────────────────


class FakeTelemetry:
    """Minimal stand-in for ``droneresearch.core.telemetry.TelemetryState``.

    Only carries the attributes used by :class:`MissionEngine.upload` and
    ``MissionEngine._on_message`` so we don't have to drag in the real
    dataclass (and its lock) into pure-logic tests.
    """

    def __init__(self):
        self.lat        = 47.0
        self.lon        = 8.0
        self.alt        = 100.0
        self.alt_rel    = 0.0
        self.home_lat   = 0.0
        self.home_lon   = 0.0
        self.home_alt   = 0.0
        self.armed      = False
        self.flight_mode = "AUTO"
        self.groundspeed = 0.0
        self.autopilot  = "ardupilot"
    
    def update(self, **kwargs):
        """Update telemetry attributes."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


class FakeMav:
    """Captures ``mav.mav.*_send(...)`` calls for inspection in tests."""

    def __init__(self):
        self.target_system    = 1
        self.target_component = 1
        self.mav              = MagicMock()


class FakeConnection:
    """In-memory MAVLinkConnection-shaped object.

    Records listeners registered via :meth:`on` and lets tests fire synthetic
    messages back via :meth:`emit_message`. Mode/RTL/set_mode return True by
    default so MissionEngine.start()/abort() succeed.
    """

    def __init__(self):
        self._mav      = FakeMav()
        self.telemetry = FakeTelemetry()
        self._listeners: Dict[str, List[Callable]] = {}
        self.rtl_calls = 0
        self.mode_set: List[str] = []

    # ── MissionEngine API surface ────────────────────────────────────────
    def on(self, event: str, cb: Callable) -> None:
        self._listeners.setdefault(event, []).append(cb)

    def set_mode(self, mode: str) -> bool:
        self.mode_set.append(mode)
        self.telemetry.flight_mode = mode
        return True

    def rtl(self) -> bool:
        self.rtl_calls += 1
        return True
    
    def arm(self, force: bool = False) -> bool:
        """Arm the drone (test stub)."""
        self.telemetry.armed = True
        return True
    
    def disarm(self, force: bool = False) -> bool:
        """Disarm the drone (test stub)."""
        self.telemetry.armed = False
        return True
    
    def takeoff(self, altitude: float) -> bool:
        """Takeoff command (test stub)."""
        return True
    
    def land(self) -> bool:
        """Land command (test stub)."""
        return True
    
    def goto(self, lat: float, lon: float, alt: float) -> bool:
        """Goto command (test stub)."""
        return True
    
    def send_raw(self, msg_type: str, **kwargs):
        """Send raw MAVLink message (test stub with whitelist check)."""
        # Import here to avoid circular dependency
        from droneresearch.core.connection import MAVLinkConnection
        
        if msg_type not in MAVLinkConnection.ALLOWED_RAW_MESSAGES:
            raise ValueError(
                f"Message type '{msg_type}' not in whitelist. "
                f"Allowed types: {sorted(MAVLinkConnection.ALLOWED_RAW_MESSAGES)}"
            )
        # In tests, just record that it was called
        if not hasattr(self, 'raw_messages_sent'):
            self.raw_messages_sent = []
        self.raw_messages_sent.append((msg_type, kwargs))

    # ── Test helpers ─────────────────────────────────────────────────────
    def emit_message(self, msg) -> None:
        """Deliver a synthetic MAVLink message to all "message" listeners."""
        for cb in self._listeners.get("message", []):
            cb(msg)


class FakeMavMessage:
    """Duck-typed MAVLink message — only ``get_type()`` and a few attrs."""

    def __init__(self, msg_type: str, **kwargs: Any):
        self._type = msg_type
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_type(self) -> str:
        return self._type


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def fake_conn() -> FakeConnection:
    return FakeConnection()


@pytest.fixture
def fake_mav():
    """Provide FakeMav instance for tests that need mav.mav.*_send() inspection."""
    return FakeMav()


@pytest.fixture
def make_msg():
    """Factory: ``make_msg("MISSION_ITEM_REACHED", seq=3)``."""
    return FakeMavMessage


# ── Qt application fixture (UI tests) ───────────────────────────────────────


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication for UI tests.

    Creates a full QApplication (not just QCoreApplication) to support
    E2E tests that create windows. QtWebEngine requires AA_ShareOpenGLContexts
    to be set BEFORE any QtWebEngine imports.
    """
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        import sys
        
        # CRITICAL: Set AA_ShareOpenGLContexts BEFORE importing QtWebEngine
        # This must happen before QApplication creation AND before any
        # QtWebEngineWidgets imports (which may happen in UI modules)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        
        # Now safe to import QtWebEngine components
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
        except ImportError:
            pass  # QtWebEngine not installed, tests will skip if needed
        
    except ImportError:
        pytest.skip("PySide6 not installed — skipping UI tests")

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    # Do not call app.quit() — pytest may reuse it across the session.


@pytest.fixture
def snap_factory():
    """Build a telemetry snapshot dict with sensible defaults."""
    def _make(**overrides):
        snap = {
            "lat": 47.0, "lon": 8.0, "alt_rel": 10.0, "alt": 100.0,
            "groundspeed": 0.0, "yaw": 0.0, "roll": 0.0, "pitch": 0.0,
            "armed": False, "flight_mode": "GUIDED",
            "battery_pct": 100.0, "battery_v": 12.6,
            "satellites": 12, "gps_fix": 3,
            "climb": 0.0, "throttle": 0.0, "connected": True,
        }
        snap.update(overrides)
        return snap
    return _make


@pytest.fixture
def swarm_ctx(qapp):
    """Create a SwarmContext for testing swarm algorithms."""
    try:
        from tools.ui.context.swarm_context import SwarmContext
        from tools.ui.backend import MultiDroneBackend
    except ImportError:
        pytest.skip("UI modules not available")
    
    backend = MultiDroneBackend()
    ctx = SwarmContext(backend)
    yield ctx
    # Cleanup
    if ctx._swarm_algorithms_active:
        ctx.stopSwarmAlgorithms()

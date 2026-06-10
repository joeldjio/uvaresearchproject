"""
Shared pytest fixtures for the droneresearch test suite.

The suite is intentionally hardware-free: no MAVLink, no ROS2, no Qt event
loop. Anything that needs those is mocked here.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Callable
from unittest.mock import MagicMock

import pytest


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
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        import sys
        
        # CRITICAL: Set AA_ShareOpenGLContexts BEFORE importing QtWebEngine
        # This must happen before QApplication creation AND before any
        # QtWebEngineWidgets imports (which may happen in UI modules)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        
        # Now safe to import QtWebEngine components
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
        except ImportError:
            pass  # QtWebEngine not installed, tests will skip if needed
        
    except ImportError:
        pytest.skip("PyQt6 not installed — skipping UI tests")

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

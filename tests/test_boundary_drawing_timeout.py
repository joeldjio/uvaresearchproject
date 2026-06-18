"""
Test for Fix 5: Boundary Drawing Timeout

Verifies that boundary drawing mode auto-cancels after 5 minutes
and provides a manual cancel button.
"""

from unittest.mock import Mock
import time

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# Ensure QApplication exists for QTimer tests
@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_drawing_timeout_timer_exists():
    """Test that MissionContext has drawing timeout timer."""
    from tools.ui.context.mission_context import MissionContext
    
    ctx = MissionContext()
    
    # Verify timer exists
    assert hasattr(ctx, '_drawing_timeout_timer')
    assert ctx._drawing_timeout_timer is not None


def test_start_drawing_starts_timeout(qapp):
    """Test that startDrawingBoundary starts the timeout timer."""
    from tools.ui.context.mission_context import MissionContext
    
    ctx = MissionContext()
    
    # Start drawing
    ctx.startDrawingBoundary()
    
    # Process events to let timer start
    qapp.processEvents()
    
    # Verify timer is active
    assert ctx._drawing_timeout_timer.isActive()
    assert ctx._drawing_mode is True


def test_finish_drawing_stops_timeout(qapp):
    """Test that finishDrawingBoundary stops the timeout timer."""
    from tools.ui.context.mission_context import MissionContext
    
    ctx = MissionContext()
    
    # Start and finish drawing
    ctx.startDrawingBoundary()
    qapp.processEvents()
    assert ctx._drawing_timeout_timer.isActive()
    
    ctx.finishDrawingBoundary()
    qapp.processEvents()
    
    # Verify timer is stopped
    assert not ctx._drawing_timeout_timer.isActive()
    assert ctx._drawing_mode is False


def test_cancel_drawing_method_exists():
    """Test that cancelDrawingBoundary method exists."""
    from tools.ui.context.mission_context import MissionContext
    
    ctx = MissionContext()
    
    # Verify method exists
    assert hasattr(ctx, 'cancelDrawingBoundary')
    assert callable(ctx.cancelDrawingBoundary)


def test_cancel_drawing_clears_points():
    """Test that cancelDrawingBoundary clears boundary points."""
    from tools.ui.context.mission_context import MissionContext
    
    ctx = MissionContext()
    
    # Start drawing and add points
    ctx.startDrawingBoundary()
    ctx.addBoundaryPoint(47.397742, 8.545594)
    ctx.addBoundaryPoint(47.397742, 8.546594)
    
    assert len(ctx._boundary_points) == 2
    
    # Cancel drawing
    ctx.cancelDrawingBoundary()
    
    # Verify points cleared and mode disabled
    assert len(ctx._boundary_points) == 0
    assert ctx._drawing_mode is False
    assert not ctx._drawing_timeout_timer.isActive()


def test_timeout_callback_disables_drawing_mode():
    """Test that timeout callback disables drawing mode."""
    from tools.ui.context.mission_context import MissionContext
    
    ctx = MissionContext()
    
    # Start drawing
    ctx.startDrawingBoundary()
    assert ctx._drawing_mode is True
    
    # Manually trigger timeout
    ctx._on_drawing_timeout()
    
    # Verify drawing mode disabled
    assert ctx._drawing_mode is False


def test_timeout_duration_is_5_minutes():
    """Test that timeout is set to 5 minutes (300000ms)."""
    from tools.ui.context.mission_context import MissionContext
    
    ctx = MissionContext()
    
    # Start drawing
    ctx.startDrawingBoundary()
    
    # Verify timer interval is 5 minutes
    # Note: QTimer.interval() returns the interval in milliseconds
    assert ctx._drawing_timeout_timer.interval() == 300000  # 5 minutes


def test_timeout_is_single_shot():
    """Test that timeout timer is single-shot (doesn't repeat)."""
    from tools.ui.context.mission_context import MissionContext
    
    ctx = MissionContext()
    
    # Verify timer is single-shot
    assert ctx._drawing_timeout_timer.isSingleShot()


def test_start_drawing_log_message():
    """Test that start drawing emits log message with timeout info."""
    from tools.ui.context.mission_context import MissionContext
    
    ctx = MissionContext()
    
    # Mock log handler
    log_messages = []
    ctx.logMessage.connect(lambda level, text: log_messages.append((level, text)))
    
    # Start drawing
    ctx.startDrawingBoundary()
    
    # Verify log message mentions timeout
    assert len(log_messages) > 0
    assert any("5min timeout" in msg[1] or "timeout" in msg[1].lower() for msg in log_messages)


def test_timeout_log_message():
    """Test that timeout emits warning log message."""
    from tools.ui.context.mission_context import MissionContext
    
    ctx = MissionContext()
    
    # Mock log handler
    log_messages = []
    ctx.logMessage.connect(lambda level, text: log_messages.append((level, text)))
    
    # Start drawing and trigger timeout
    ctx.startDrawingBoundary()
    ctx._on_drawing_timeout()
    
    # Verify timeout warning was logged
    timeout_logs = [msg for msg in log_messages if "timeout" in msg[1].lower() or "timed out" in msg[1].lower()]
    assert len(timeout_logs) > 0
    assert any(msg[0] == "WARN" for msg in timeout_logs)


def test_cancel_log_message():
    """Test that cancel emits log message."""
    from tools.ui.context.mission_context import MissionContext
    
    ctx = MissionContext()
    
    # Mock log handler
    log_messages = []
    ctx.logMessage.connect(lambda level, text: log_messages.append((level, text)))
    
    # Start and cancel drawing
    ctx.startDrawingBoundary()
    ctx.cancelDrawingBoundary()
    
    # Verify cancel message was logged
    cancel_logs = [msg for msg in log_messages if "cancel" in msg[1].lower()]
    assert len(cancel_logs) > 0


def test_multiple_start_stop_cycles(qapp):
    """Test that timer works correctly across multiple start/stop cycles."""
    from tools.ui.context.mission_context import MissionContext
    
    ctx = MissionContext()
    
    # Cycle 1
    ctx.startDrawingBoundary()
    qapp.processEvents()
    assert ctx._drawing_timeout_timer.isActive()
    ctx.finishDrawingBoundary()
    qapp.processEvents()
    assert not ctx._drawing_timeout_timer.isActive()
    
    # Cycle 2
    ctx.startDrawingBoundary()
    qapp.processEvents()
    assert ctx._drawing_timeout_timer.isActive()
    ctx.cancelDrawingBoundary()
    qapp.processEvents()
    assert not ctx._drawing_timeout_timer.isActive()
    
    # Cycle 3
    ctx.startDrawingBoundary()
    qapp.processEvents()
    assert ctx._drawing_timeout_timer.isActive()
    ctx._on_drawing_timeout()
    qapp.processEvents()
    assert not ctx._drawing_timeout_timer.isActive()

# Made with Bob

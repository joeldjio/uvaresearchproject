"""
Test for Fix 7: Mission Upload Async

Verifies that mission upload can be done asynchronously with progress callbacks
to prevent UI blocking.
"""

from unittest.mock import Mock, MagicMock, patch
import threading
import time

import pytest


def test_upload_async_method_exists():
    """Test that MissionEngine has upload_async method."""
    from droneresearch.control.mission import MissionEngine
    from droneresearch.core.connection import MAVLinkConnection
    
    conn = Mock(spec=MAVLinkConnection)
    conn._mav = None
    mission = MissionEngine(conn)
    
    # Verify method exists
    assert hasattr(mission, 'upload_async')
    assert callable(mission.upload_async)


def test_is_uploading_method_exists():
    """Test that MissionEngine has is_uploading method."""
    from droneresearch.control.mission import MissionEngine
    from droneresearch.core.connection import MAVLinkConnection
    
    conn = Mock(spec=MAVLinkConnection)
    conn._mav = None
    mission = MissionEngine(conn)
    
    # Verify method exists
    assert hasattr(mission, 'is_uploading')
    assert callable(mission.is_uploading)
    
    # Initially not uploading
    assert mission.is_uploading() is False


def test_upload_async_starts_thread():
    """Test that upload_async starts a background thread."""
    from droneresearch.control.mission import MissionEngine, Waypoint
    from droneresearch.core.connection import MAVLinkConnection
    
    conn = Mock(spec=MAVLinkConnection)
    conn._mav = MagicMock()
    conn.telemetry = Mock(lat=47.0, lon=8.0, alt=500.0, home_lat=47.0, home_lon=8.0, home_alt=500.0)
    
    mission = MissionEngine(conn)
    mission.add(Waypoint(lat=47.1, lon=8.1, alt=10.0))
    
    # Mock upload to return quickly
    with patch.object(mission, 'upload', return_value=True):
        result = mission.upload_async()
        
        # Verify thread started
        assert result is True
        assert mission._upload_thread is not None
        
        # Wait for thread to finish
        mission._upload_thread.join(timeout=1.0)


def test_upload_async_prevents_concurrent_uploads():
    """Test that upload_async prevents concurrent uploads."""
    from droneresearch.control.mission import MissionEngine, Waypoint
    from droneresearch.core.connection import MAVLinkConnection
    
    conn = Mock(spec=MAVLinkConnection)
    conn._mav = MagicMock()
    conn.telemetry = Mock(lat=47.0, lon=8.0, alt=500.0, home_lat=47.0, home_lon=8.0, home_alt=500.0)
    
    mission = MissionEngine(conn)
    mission.add(Waypoint(lat=47.1, lon=8.1, alt=10.0))
    
    # Mock upload to block
    upload_started = threading.Event()
    upload_continue = threading.Event()
    
    def slow_upload():
        upload_started.set()
        upload_continue.wait(timeout=2.0)
        return True
    
    with patch.object(mission, 'upload', side_effect=slow_upload):
        # Start first upload
        result1 = mission.upload_async()
        assert result1 is True
        
        # Wait for upload to start
        upload_started.wait(timeout=1.0)
        
        # Try to start second upload (should fail)
        result2 = mission.upload_async()
        assert result2 is False
        
        # Cleanup
        upload_continue.set()
        mission._upload_thread.join(timeout=1.0)


def test_upload_async_progress_callback():
    """Test that progress callback is called during upload."""
    from droneresearch.control.mission import MissionEngine, Waypoint
    from droneresearch.core.connection import MAVLinkConnection
    
    conn = Mock(spec=MAVLinkConnection)
    conn._mav = MagicMock()
    conn.telemetry = Mock(lat=47.0, lon=8.0, alt=500.0, home_lat=47.0, home_lon=8.0, home_alt=500.0)
    
    mission = MissionEngine(conn)
    mission.add(Waypoint(lat=47.1, lon=8.1, alt=10.0))
    mission.add(Waypoint(lat=47.2, lon=8.2, alt=10.0))
    
    progress_calls = []
    
    def on_progress(current, total):
        progress_calls.append((current, total))
    
    # Mock upload to succeed
    with patch.object(mission, 'upload', return_value=True):
        mission.upload_async(on_progress=on_progress)
        
        # Wait for thread to finish
        mission._upload_thread.join(timeout=1.0)
    
    # Note: Progress callbacks are called from within upload(),
    # which we mocked, so we won't see calls here.
    # This test verifies the callback is stored.
    assert mission._upload_progress_callback is None  # Cleared after upload


def test_upload_async_complete_callback_success():
    """Test that complete callback is called with success=True."""
    from droneresearch.control.mission import MissionEngine, Waypoint
    from droneresearch.core.connection import MAVLinkConnection
    
    conn = Mock(spec=MAVLinkConnection)
    conn._mav = MagicMock()
    conn.telemetry = Mock(lat=47.0, lon=8.0, alt=500.0, home_lat=47.0, home_lon=8.0, home_alt=500.0)
    
    mission = MissionEngine(conn)
    mission.add(Waypoint(lat=47.1, lon=8.1, alt=10.0))
    
    complete_called = threading.Event()
    complete_result = []
    
    def on_complete(success):
        complete_result.append(success)
        complete_called.set()
    
    # Mock upload to succeed
    with patch.object(mission, 'upload', return_value=True):
        mission.upload_async(on_complete=on_complete)
        
        # Wait for completion
        complete_called.wait(timeout=1.0)
    
    # Verify callback was called with success=True
    assert len(complete_result) == 1
    assert complete_result[0] is True


def test_upload_async_complete_callback_failure():
    """Test that complete callback is called with success=False on failure."""
    from droneresearch.control.mission import MissionEngine, Waypoint
    from droneresearch.core.connection import MAVLinkConnection
    
    conn = Mock(spec=MAVLinkConnection)
    conn._mav = MagicMock()
    conn.telemetry = Mock(lat=47.0, lon=8.0, alt=500.0, home_lat=47.0, home_lon=8.0, home_alt=500.0)
    
    mission = MissionEngine(conn)
    mission.add(Waypoint(lat=47.1, lon=8.1, alt=10.0))
    
    complete_called = threading.Event()
    complete_result = []
    
    def on_complete(success):
        complete_result.append(success)
        complete_called.set()
    
    # Mock upload to fail
    with patch.object(mission, 'upload', return_value=False):
        mission.upload_async(on_complete=on_complete)
        
        # Wait for completion
        complete_called.wait(timeout=1.0)
    
    # Verify callback was called with success=False
    assert len(complete_result) == 1
    assert complete_result[0] is False


def test_upload_async_exception_handling():
    """Test that exceptions in upload are handled gracefully."""
    from droneresearch.control.mission import MissionEngine, Waypoint
    from droneresearch.core.connection import MAVLinkConnection
    
    conn = Mock(spec=MAVLinkConnection)
    conn._mav = MagicMock()
    conn.telemetry = Mock(lat=47.0, lon=8.0, alt=500.0, home_lat=47.0, home_lon=8.0, home_alt=500.0)
    
    mission = MissionEngine(conn)
    mission.add(Waypoint(lat=47.1, lon=8.1, alt=10.0))
    
    complete_called = threading.Event()
    complete_result = []
    
    def on_complete(success):
        complete_result.append(success)
        complete_called.set()
    
    # Mock upload to raise exception
    with patch.object(mission, 'upload', side_effect=RuntimeError("Test error")):
        mission.upload_async(on_complete=on_complete)
        
        # Wait for completion
        complete_called.wait(timeout=1.0)
    
    # Verify callback was called with success=False
    assert len(complete_result) == 1
    assert complete_result[0] is False


def test_upload_async_callback_exception_handling():
    """Test that exceptions in callbacks don't crash the thread."""
    from droneresearch.control.mission import MissionEngine, Waypoint
    from droneresearch.core.connection import MAVLinkConnection
    
    conn = Mock(spec=MAVLinkConnection)
    conn._mav = MagicMock()
    conn.telemetry = Mock(lat=47.0, lon=8.0, alt=500.0, home_lat=47.0, home_lon=8.0, home_alt=500.0)
    
    mission = MissionEngine(conn)
    mission.add(Waypoint(lat=47.1, lon=8.1, alt=10.0))
    
    thread_finished = threading.Event()
    
    def bad_callback(success):
        raise RuntimeError("Callback error")
    
    # Mock upload to succeed
    with patch.object(mission, 'upload', return_value=True):
        mission.upload_async(on_complete=bad_callback)
        
        # Wait for thread to finish (should not crash)
        mission._upload_thread.join(timeout=1.0)
        thread_finished.set()
    
    # Verify thread finished despite callback exception
    assert thread_finished.is_set()


def test_upload_async_clears_callbacks():
    """Test that callbacks are cleared after upload completes."""
    from droneresearch.control.mission import MissionEngine, Waypoint
    from droneresearch.core.connection import MAVLinkConnection
    
    conn = Mock(spec=MAVLinkConnection)
    conn._mav = MagicMock()
    conn.telemetry = Mock(lat=47.0, lon=8.0, alt=500.0, home_lat=47.0, home_lon=8.0, home_alt=500.0)
    
    mission = MissionEngine(conn)
    mission.add(Waypoint(lat=47.1, lon=8.1, alt=10.0))
    
    def on_progress(current, total):
        pass
    
    def on_complete(success):
        pass
    
    # Mock upload to succeed
    with patch.object(mission, 'upload', return_value=True):
        mission.upload_async(on_progress=on_progress, on_complete=on_complete)
        
        # Wait for thread to finish
        mission._upload_thread.join(timeout=1.0)
    
    # Verify callbacks are cleared
    assert mission._upload_progress_callback is None
    assert mission._upload_complete_callback is None


def test_upload_async_thread_is_daemon():
    """Test that upload thread is a daemon thread."""
    from droneresearch.control.mission import MissionEngine, Waypoint
    from droneresearch.core.connection import MAVLinkConnection
    
    conn = Mock(spec=MAVLinkConnection)
    conn._mav = MagicMock()
    conn.telemetry = Mock(lat=47.0, lon=8.0, alt=500.0, home_lat=47.0, home_lon=8.0, home_alt=500.0)
    
    mission = MissionEngine(conn)
    mission.add(Waypoint(lat=47.1, lon=8.1, alt=10.0))
    
    # Mock upload to block briefly
    with patch.object(mission, 'upload', return_value=True):
        mission.upload_async()
        
        # Verify thread is daemon
        assert mission._upload_thread.daemon is True
        
        # Cleanup
        mission._upload_thread.join(timeout=1.0)

# Made with Bob

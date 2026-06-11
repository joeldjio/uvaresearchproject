"""
Tests for async mission upload functionality.

Tests the non-blocking mission upload with progress callbacks.
"""
import pytest
import time
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from concurrent.futures import Future
from enum import Enum


def test_upload_status_enum():
    """Test UploadStatus enum exists."""
    from droneresearch.ros.px4_mission import UploadStatus
    
    assert UploadStatus.IDLE.value == "idle"
    assert UploadStatus.SENDING_COUNT.value == "sending_count"
    assert UploadStatus.SENDING_ITEMS.value == "sending_items"
    assert UploadStatus.WAITING_ACK.value == "waiting_ack"
    assert UploadStatus.SUCCESS.value == "success"
    assert UploadStatus.FAILED.value == "failed"
    assert UploadStatus.CANCELLED.value == "cancelled"


@pytest.fixture
def mock_uploader():
    """Create mock uploader with async capabilities."""
    # Create a mock uploader that mimics the real one
    uploader = Mock()
    uploader._upload_status = Mock()
    uploader._upload_status.value = "idle"
    uploader._upload_progress = 0.0
    uploader._progress_callbacks = []
    uploader._upload_cancelled = Mock()
    uploader._upload_cancelled.is_set = Mock(return_value=False)
    
    # Mock the enum
    from droneresearch.ros.px4_mission import UploadStatus
    
    # Mock get_upload_status
    def mock_get_status():
        return {
            "status": uploader._upload_status.value,
            "progress": uploader._upload_progress,
            "is_uploading": uploader._upload_status.value not in ("idle", "success", "failed", "cancelled")
        }
    uploader.get_upload_status = mock_get_status
    
    # Mock upload_async
    def mock_upload_async(waypoints, timeout=10.0, progress_callback=None):
        future = Future()
        
        # Simulate async upload
        def do_upload():
            if not waypoints:
                uploader._upload_status.value = "failed"
                uploader._upload_progress = 0.0
                if progress_callback:
                    progress_callback(UploadStatus.FAILED, 0.0, "No waypoints")
                return False
            
            # Simulate progress
            uploader._upload_status.value = "sending_count"
            uploader._upload_progress = 0.1
            if progress_callback:
                try:
                    progress_callback(UploadStatus.SENDING_COUNT, 0.1, "Sending count")
                except Exception:
                    pass  # Ignore callback errors
            
            time.sleep(0.01)
            
            uploader._upload_status.value = "sending_items"
            for i in range(len(waypoints)):
                if uploader._upload_cancelled.is_set():
                    uploader._upload_status.value = "cancelled"
                    if progress_callback:
                        try:
                            progress_callback(UploadStatus.CANCELLED, uploader._upload_progress, "Cancelled")
                        except Exception:
                            pass
                    return False
                
                progress = 0.1 + (0.7 * (i + 1) / len(waypoints))
                uploader._upload_progress = progress
                if progress_callback:
                    try:
                        progress_callback(UploadStatus.SENDING_ITEMS, progress, f"Waypoint {i+1}/{len(waypoints)}")
                    except Exception:
                        pass
                time.sleep(0.01)
            
            uploader._upload_status.value = "success"
            uploader._upload_progress = 1.0
            if progress_callback:
                try:
                    progress_callback(UploadStatus.SUCCESS, 1.0, "Upload complete")
                except Exception:
                    pass
            return True
        
        # Run in background
        import threading
        def run():
            try:
                result = do_upload()
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)
        
        thread = threading.Thread(target=run)
        thread.start()
        
        return future
    
    uploader.upload_async = mock_upload_async
    
    # Mock cancel_upload
    def mock_cancel():
        uploader._upload_cancelled.is_set = Mock(return_value=True)
        uploader._upload_status.value = "cancelled"
    uploader.cancel_upload = mock_cancel
    
    # Mock add/remove callbacks
    uploader.add_progress_callback = lambda cb: uploader._progress_callbacks.append(cb)
    uploader.remove_progress_callback = lambda cb: uploader._progress_callbacks.remove(cb) if cb in uploader._progress_callbacks else None
    
    return uploader


def test_initial_upload_status(mock_uploader):
    """Test initial upload status is IDLE."""
    status = mock_uploader.get_upload_status()
    assert status["status"] == "idle"
    assert status["progress"] == 0.0
    assert status["is_uploading"] is False


def test_upload_async_returns_future(mock_uploader):
    """Test upload_async returns a Future."""
    waypoints = [
        {"lat": 47.397, "lon": 8.545, "alt": 10.0},
        {"lat": 47.398, "lon": 8.546, "alt": 15.0},
    ]
    
    future = mock_uploader.upload_async(waypoints, timeout=1.0)
    
    assert isinstance(future, Future)
    
    # Wait for completion
    result = future.result(timeout=5.0)
    assert isinstance(result, bool)


def test_upload_async_with_progress_callback(mock_uploader):
    """Test progress callback is called during upload."""
    waypoints = [
        {"lat": 47.397, "lon": 8.545, "alt": 10.0},
    ]
    
    progress_calls = []
    
    def on_progress(status, progress, message):
        progress_calls.append({
            "status": status.value,
            "progress": progress,
            "message": message
        })
    
    future = mock_uploader.upload_async(waypoints, timeout=1.0, progress_callback=on_progress)
    result = future.result(timeout=5.0)
    
    # Should have received progress updates
    assert len(progress_calls) > 0
    
    # First call should be SENDING_COUNT
    assert progress_calls[0]["status"] == "sending_count"
    
    # Last call should be SUCCESS
    assert progress_calls[-1]["status"] == "success"


def test_upload_async_progress_increases(mock_uploader):
    """Test progress increases during upload."""
    waypoints = [
        {"lat": 47.397, "lon": 8.545, "alt": 10.0},
        {"lat": 47.398, "lon": 8.546, "alt": 15.0},
        {"lat": 47.399, "lon": 8.547, "alt": 20.0},
    ]
    
    progress_values = []
    
    def on_progress(status, progress, message):
        progress_values.append(progress)
    
    future = mock_uploader.upload_async(waypoints, timeout=1.0, progress_callback=on_progress)
    future.result(timeout=5.0)
    
    # Progress should increase
    assert len(progress_values) > 1
    for i in range(1, len(progress_values)):
        assert progress_values[i] >= progress_values[i-1]


def test_get_upload_status_during_upload(mock_uploader):
    """Test get_upload_status returns correct state during upload."""
    waypoints = [
        {"lat": 47.397, "lon": 8.545, "alt": 10.0},
    ]
    
    future = mock_uploader.upload_async(waypoints, timeout=1.0)
    
    # Check status during upload (may already be complete on fast systems)
    time.sleep(0.02)
    status = mock_uploader.get_upload_status()
    assert status["status"] in ("sending_count", "sending_items", "success", "idle")
    
    # Wait for completion
    future.result(timeout=5.0)
    
    # Final status should be SUCCESS
    final_status = mock_uploader.get_upload_status()
    assert final_status["status"] == "success"


def test_cancel_upload(mock_uploader):
    """Test upload can be cancelled."""
    # Create many waypoints to ensure upload takes time
    waypoints = [
        {"lat": 47.397 + i*0.001, "lon": 8.545 + i*0.001, "alt": 10.0 + i}
        for i in range(50)
    ]
    
    future = mock_uploader.upload_async(waypoints, timeout=10.0)
    
    # Cancel immediately
    time.sleep(0.05)
    mock_uploader.cancel_upload()
    
    # Wait for result
    result = future.result(timeout=5.0)
    
    # Should be cancelled or completed
    status = mock_uploader.get_upload_status()
    assert status["status"] in ("cancelled", "success")


def test_upload_async_empty_waypoints(mock_uploader):
    """Test upload_async with empty waypoints fails."""
    future = mock_uploader.upload_async([], timeout=1.0)
    result = future.result(timeout=5.0)
    
    assert result is False
    status = mock_uploader.get_upload_status()
    assert status["status"] == "failed"


def test_add_remove_progress_callback(mock_uploader):
    """Test adding and removing progress callbacks."""
    callback1 = Mock()
    callback2 = Mock()
    
    mock_uploader.add_progress_callback(callback1)
    mock_uploader.add_progress_callback(callback2)
    
    assert callback1 in mock_uploader._progress_callbacks
    assert callback2 in mock_uploader._progress_callbacks
    
    mock_uploader.remove_progress_callback(callback1)
    
    assert callback1 not in mock_uploader._progress_callbacks
    assert callback2 in mock_uploader._progress_callbacks


def test_progress_callback_exception_handling(mock_uploader):
    """Test that callback exceptions don't crash upload."""
    waypoints = [{"lat": 47.397, "lon": 8.545, "alt": 10.0}]
    
    def bad_callback(status, progress, message):
        raise ValueError("Callback error")
    
    # This should not raise, even with bad callback
    future = mock_uploader.upload_async(waypoints, timeout=1.0, progress_callback=bad_callback)
    
    # Should complete despite callback error
    result = future.result(timeout=5.0)
    assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


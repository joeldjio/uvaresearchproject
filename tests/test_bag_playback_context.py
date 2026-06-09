"""
Tests for BagPlaybackContext
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


def test_bag_playback_context_import():
    """Test that BagPlaybackContext can be imported"""
    from tools.ui.context.bag_playback_context import BagPlaybackContext
    assert BagPlaybackContext is not None


def test_bag_playback_initial_state():
    """Test initial state of BagPlaybackContext"""
    from tools.ui.context.bag_playback_context import BagPlaybackContext
    
    ctx = BagPlaybackContext()
    assert ctx.state == "stopped"
    assert ctx.progress == 0.0
    assert ctx.duration == 0.0
    assert ctx.playbackRate == 1.0


def test_bag_playback_rate_bounds():
    """Test playback rate is clamped to valid range"""
    from tools.ui.context.bag_playback_context import BagPlaybackContext
    
    ctx = BagPlaybackContext()
    
    # Test lower bound
    ctx.playbackRate = 0.05
    assert ctx.playbackRate == 0.1
    
    # Test upper bound
    ctx.playbackRate = 15.0
    assert ctx.playbackRate == 10.0
    
    # Test valid value
    ctx.playbackRate = 2.5
    assert ctx.playbackRate == 2.5


@patch('subprocess.run')
def test_load_bag_info(mock_run):
    """Test bag info extraction"""
    from tools.ui.context.bag_playback_context import BagPlaybackContext
    
    # Mock ros2 bag info output
    mock_run.return_value = Mock(
        returncode=0,
        stdout="Duration: 123.45s\nMessages: 1000\n"
    )
    
    ctx = BagPlaybackContext()
    
    # Create a temporary bag path
    with patch('pathlib.Path.exists', return_value=True):
        ctx.loadBag("/fake/path/test.mcap")
    
    # Verify duration was extracted
    assert ctx.duration == 123.45


@patch('subprocess.Popen')
def test_play_starts_process(mock_popen):
    """Test that play() starts ros2 bag play subprocess"""
    from tools.ui.context.bag_playback_context import BagPlaybackContext
    
    mock_process = Mock()
    mock_process.poll.return_value = None  # Process running
    mock_popen.return_value = mock_process
    
    ctx = BagPlaybackContext()
    ctx._bag_path = Path("/fake/test.mcap")
    ctx._duration = 100.0
    
    ctx.play()
    
    # Verify subprocess was started
    assert mock_popen.called
    args = mock_popen.call_args[0][0]
    assert "ros2" in args
    assert "bag" in args
    assert "play" in args
    assert ctx.state == "playing"


def test_stop_cleans_up():
    """Test that stop() cleans up resources"""
    from tools.ui.context.bag_playback_context import BagPlaybackContext
    
    ctx = BagPlaybackContext()
    mock_process = Mock()
    mock_process.poll.return_value = None
    ctx._process = mock_process
    ctx._state = "playing"
    
    ctx.stop()
    
    # Verify cleanup
    assert ctx.state == "stopped"
    assert ctx.progress == 0.0
    assert mock_process.terminate.called
    assert ctx._process is None  # Process should be cleared


@patch('subprocess.Popen')
def test_seek_restarts_with_offset(mock_popen):
    """Test that seek() restarts playback with offset"""
    from tools.ui.context.bag_playback_context import BagPlaybackContext
    
    mock_process = Mock()
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process
    
    ctx = BagPlaybackContext()
    ctx._bag_path = Path("/fake/test.mcap")
    ctx._duration = 100.0
    ctx._state = "playing"
    
    # Seek to 50% (50 seconds)
    ctx.seek(0.5)
    
    # Verify subprocess was restarted with offset
    args = mock_popen.call_args[0][0]
    assert "--start-offset" in args
    offset_idx = args.index("--start-offset")
    assert float(args[offset_idx + 1]) == 50.0

# Made with Bob

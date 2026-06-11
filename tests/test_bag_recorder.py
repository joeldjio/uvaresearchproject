"""
Tests for ROS2 Bag Recorder.

These tests are hardware-free and use mocks for ROS2 dependencies.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_bag_dir():
    """Create temporary directory for bag files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_rclpy():
    """Mock rclpy module."""
    with patch.dict('sys.modules', {'rclpy': Mock()}):
        yield


@pytest.fixture
def recorder(temp_bag_dir, mock_rclpy):
    """Create ROS2BagRecorder instance with mocked dependencies."""
    from droneresearch.ros.bag_recorder import ROS2BagRecorder
    return ROS2BagRecorder(output_dir=temp_bag_dir)


def test_recorder_initialization(recorder, temp_bag_dir):
    """Test recorder initializes correctly."""
    assert recorder.output_dir == Path(temp_bag_dir)
    assert recorder.output_dir.exists()
    assert not recorder.is_recording()


def test_start_recording_no_topics(recorder):
    """Test starting recording without topics fails."""
    result = recorder.start_recording(topics=[])
    assert result is False
    assert not recorder.is_recording()


@patch('subprocess.Popen')
def test_start_recording_success(mock_popen, recorder):
    """Test successful recording start."""
    mock_process = Mock()
    mock_process.poll.return_value = None  # Process still running
    mock_popen.return_value = mock_process
    
    topics = ["/fmu/out/vehicle_odometry", "/fmu/out/vehicle_status"]
    result = recorder.start_recording(topics=topics)
    
    assert result is True
    assert recorder.is_recording()
    
    # Verify subprocess was called with correct arguments
    mock_popen.assert_called_once()
    call_args = mock_popen.call_args[0][0]
    assert "ros2" in call_args
    assert "bag" in call_args
    assert "record" in call_args
    assert all(topic in call_args for topic in topics)


@patch('subprocess.Popen')
def test_start_recording_custom_name(mock_popen, recorder):
    """Test recording with custom bag name."""
    mock_process = Mock()
    mock_popen.return_value = mock_process
    
    result = recorder.start_recording(
        topics=["/test/topic"],
        bag_name="my_custom_bag"
    )
    
    assert result is True
    assert "my_custom_bag" in str(recorder._current_bag_path)


@patch('subprocess.Popen')
def test_start_recording_already_recording(mock_popen, recorder):
    """Test starting recording when already recording fails."""
    mock_process = Mock()
    mock_process.poll.return_value = None  # Process still running
    mock_popen.return_value = mock_process
    
    # Start first recording
    recorder.start_recording(topics=["/test/topic"])
    
    # Try to start second recording
    result = recorder.start_recording(topics=["/another/topic"])
    
    assert result is False
    assert mock_popen.call_count == 1  # Only called once


@patch('subprocess.Popen')
def test_stop_recording(mock_popen, recorder):
    """Test stopping recording."""
    mock_process = Mock()
    mock_process.poll.return_value = None  # Process still running
    mock_popen.return_value = mock_process
    
    # Start recording
    recorder.start_recording(topics=["/test/topic"])
    assert recorder.is_recording()
    
    # Stop recording
    result = recorder.stop_recording()
    
    assert result is True
    assert not recorder.is_recording()
    mock_process.terminate.assert_called_once()


def test_stop_recording_not_recording(recorder):
    """Test stopping when not recording."""
    result = recorder.stop_recording()
    assert result is False


@patch('subprocess.Popen')
def test_get_recording_status_not_recording(mock_popen, recorder):
    """Test status when not recording."""
    status = recorder.get_recording_status()
    
    assert status["recording"] is False
    assert status["duration_sec"] == 0.0
    assert status["bag_path"] == ""
    assert status["size_mb"] == 0.0


@patch('subprocess.Popen')
def test_get_recording_status_while_recording(mock_popen, recorder, temp_bag_dir):
    """Test status while recording."""
    mock_process = Mock()
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process
    
    # Create fake bag directory
    bag_path = Path(temp_bag_dir) / "test_bag"
    bag_path.mkdir()
    (bag_path / "data.db3").write_text("fake data")
    
    recorder.start_recording(topics=["/test/topic"])
    recorder._current_bag_path = bag_path
    
    status = recorder.get_recording_status()
    
    assert status["recording"] is True
    assert status["duration_sec"] > 0.0
    assert "test_bag" in status["bag_path"]
    assert status["size_mb"] > 0.0


def test_list_bags_empty(recorder):
    """Test listing bags when directory is empty."""
    bags = recorder.list_bags()
    assert bags == []


@patch('subprocess.run')
def test_list_bags_with_bags(mock_run, recorder, temp_bag_dir):
    """Test listing existing bags."""
    # Create fake bag directory
    bag_path = Path(temp_bag_dir) / "test_bag_20260609"
    bag_path.mkdir()
    (bag_path / "metadata.yaml").write_text("fake metadata")
    (bag_path / "data.db3").write_text("fake data" * 1000)
    
    # Mock ros2 bag info output
    mock_run.return_value = Mock(
        returncode=0,
        stdout="""
Files:             data.db3
Bag size:          10.5 KiB
Storage id:        sqlite3
Duration:          45.2s
Start:             Jun  9 2026 09:15:00.123
End:               Jun  9 2026 09:15:45.323
Messages:          1234
Topic information: Topic: /fmu/out/vehicle_odometry | Type: px4_msgs/msg/VehicleOdometry | Count: 1234
        """
    )
    
    bags = recorder.list_bags()
    
    assert len(bags) == 1
    assert bags[0].path == str(bag_path)
    assert bags[0].duration_sec == 45.2
    assert bags[0].message_count == 1234
    assert "/fmu/out/vehicle_odometry" in bags[0].topics


@patch('subprocess.Popen')
def test_play_bag(mock_popen, recorder, temp_bag_dir):
    """Test playing back a bag."""
    # Create fake bag
    bag_path = Path(temp_bag_dir) / "test_bag"
    bag_path.mkdir()
    (bag_path / "metadata.yaml").write_text("fake")
    
    result = recorder.play_bag(str(bag_path), rate=2.0)
    
    assert result is True
    mock_popen.assert_called_once()
    call_args = mock_popen.call_args[0][0]
    assert "ros2" in call_args
    assert "bag" in call_args
    assert "play" in call_args
    assert "2.0" in call_args


def test_play_bag_not_found(recorder):
    """Test playing non-existent bag fails."""
    result = recorder.play_bag("/nonexistent/bag")
    assert result is False


@patch('subprocess.Popen')
def test_compression_modes(mock_popen, recorder):
    """Test different compression modes."""
    mock_process = Mock()
    mock_popen.return_value = mock_process
    
    # Test zstd (default)
    recorder.start_recording(topics=["/test"], compression="zstd")
    call_args = mock_popen.call_args[0][0]
    assert "zstd" in call_args
    recorder.stop_recording()
    
    # Test lz4
    recorder.start_recording(topics=["/test"], compression="lz4")
    call_args = mock_popen.call_args[0][0]
    assert "lz4" in call_args
    recorder.stop_recording()
    
    # Test none
    recorder.start_recording(topics=["/test"], compression="none")
    call_args = mock_popen.call_args[0][0]
    assert "none" in call_args


@patch('subprocess.Popen')
def test_cleanup_on_deletion(mock_popen, recorder):
    """Test recorder stops recording on deletion."""
    mock_process = Mock()
    mock_process.poll.return_value = None
    mock_process.wait.return_value = None
    mock_popen.return_value = mock_process
    
    recorder.start_recording(topics=["/test"])
    assert recorder.is_recording()
    
    # Manually call __del__ since Python's GC is non-deterministic
    recorder.__del__()
    
    # Process should have been terminated
    mock_process.terminate.assert_called()


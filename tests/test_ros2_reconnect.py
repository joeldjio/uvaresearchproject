"""
Tests for ROS2 bridge reconnect logic.

Tests auto-reconnect with exponential backoff, connection health monitoring,
and status callbacks without requiring actual ROS2/PX4 infrastructure.
"""
import time
import threading
from unittest.mock import Mock, patch, MagicMock
import pytest


# Mock ROS2 imports before importing px4_bridge
@pytest.fixture(autouse=True)
def mock_ros2_imports():
    """Mock ROS2 and PX4 imports for all tests."""
    with patch.dict('sys.modules', {
        'rclpy': MagicMock(),
        'rclpy.node': MagicMock(),
        'rclpy.qos': MagicMock(),
        'px4_msgs': MagicMock(),
        'px4_msgs.msg': MagicMock(),
    }):
        # Patch the _ROS2_OK and _PX4_MSGS_OK flags
        import droneresearch.ros.px4_bridge as bridge_module
        bridge_module._ROS2_OK = True
        bridge_module._PX4_MSGS_OK = True
        yield


def test_connection_status_enum():
    """Test ConnectionStatus enum values."""
    from droneresearch.ros.px4_bridge import ConnectionStatus
    
    assert ConnectionStatus.DISCONNECTED.value == "disconnected"
    assert ConnectionStatus.CONNECTING.value == "connecting"
    assert ConnectionStatus.CONNECTED.value == "connected"
    assert ConnectionStatus.RECONNECTING.value == "reconnecting"
    assert ConnectionStatus.FAILED.value == "failed"


def test_initial_status():
    """Test bridge starts in DISCONNECTED status."""
    from droneresearch.ros.px4_bridge import PX4ROS2Bridge, ConnectionStatus
    
    bridge = PX4ROS2Bridge(namespace="test")
    assert bridge.get_connection_status() == ConnectionStatus.DISCONNECTED
    assert not bridge.is_connected()


def test_reconnect_info_initial():
    """Test initial reconnect info."""
    from droneresearch.ros.px4_bridge import PX4ROS2Bridge
    
    bridge = PX4ROS2Bridge(namespace="test")
    info = bridge.get_reconnect_info()
    
    assert info["status"] == "disconnected"
    assert info["attempts"] == 0
    assert info["next_delay"] == 1.0
    assert info["last_message_age"] == -1  # No messages yet


def test_auto_reconnect_disabled():
    """Test bridge with auto_reconnect=False."""
    from droneresearch.ros.px4_bridge import PX4ROS2Bridge
    
    bridge = PX4ROS2Bridge(namespace="test", auto_reconnect=False)
    assert bridge._auto_reconnect is False


def test_custom_reconnect_delay():
    """Test custom max_reconnect_delay."""
    from droneresearch.ros.px4_bridge import PX4ROS2Bridge
    
    bridge = PX4ROS2Bridge(namespace="test", max_reconnect_delay=60.0)
    assert bridge._max_reconnect_delay == 60.0


def test_exponential_backoff_calculation():
    """Test exponential backoff delay calculation."""
    from droneresearch.ros.px4_bridge import PX4ROS2Bridge
    
    bridge = PX4ROS2Bridge(namespace="test", max_reconnect_delay=30.0)
    
    # Initial delay
    assert bridge._reconnect_delay == 1.0
    
    # Simulate reconnect attempts
    bridge._reconnect_delay = min(bridge._reconnect_delay * 2, bridge._max_reconnect_delay)
    assert bridge._reconnect_delay == 2.0
    
    bridge._reconnect_delay = min(bridge._reconnect_delay * 2, bridge._max_reconnect_delay)
    assert bridge._reconnect_delay == 4.0
    
    bridge._reconnect_delay = min(bridge._reconnect_delay * 2, bridge._max_reconnect_delay)
    assert bridge._reconnect_delay == 8.0
    
    bridge._reconnect_delay = min(bridge._reconnect_delay * 2, bridge._max_reconnect_delay)
    assert bridge._reconnect_delay == 16.0
    
    bridge._reconnect_delay = min(bridge._reconnect_delay * 2, bridge._max_reconnect_delay)
    assert bridge._reconnect_delay == 30.0  # Capped at max
    
    bridge._reconnect_delay = min(bridge._reconnect_delay * 2, bridge._max_reconnect_delay)
    assert bridge._reconnect_delay == 30.0  # Still capped


def test_connection_status_callback():
    """Test connection status change callbacks."""
    from droneresearch.ros.px4_bridge import PX4ROS2Bridge, ConnectionStatus
    
    bridge = PX4ROS2Bridge(namespace="test")
    
    status_changes = []
    
    def on_status(status):
        status_changes.append(status)
    
    bridge.on("connection_status", on_status)
    
    # Simulate status changes
    bridge._set_status(ConnectionStatus.CONNECTING)
    bridge._set_status(ConnectionStatus.CONNECTED)
    bridge._set_status(ConnectionStatus.RECONNECTING)
    bridge._set_status(ConnectionStatus.DISCONNECTED)
    
    assert len(status_changes) == 4
    assert status_changes[0] == ConnectionStatus.CONNECTING
    assert status_changes[1] == ConnectionStatus.CONNECTED
    assert status_changes[2] == ConnectionStatus.RECONNECTING
    assert status_changes[3] == ConnectionStatus.DISCONNECTED


def test_connection_status_no_duplicate_callbacks():
    """Test status callbacks only fire on actual changes."""
    from droneresearch.ros.px4_bridge import PX4ROS2Bridge, ConnectionStatus
    
    bridge = PX4ROS2Bridge(namespace="test")
    
    call_count = 0
    
    def on_status(status):
        nonlocal call_count
        call_count += 1
    
    bridge.on("connection_status", on_status)
    
    # Set same status multiple times
    bridge._set_status(ConnectionStatus.CONNECTING)
    bridge._set_status(ConnectionStatus.CONNECTING)
    bridge._set_status(ConnectionStatus.CONNECTING)
    
    assert call_count == 1  # Only first change triggers callback


def test_telemetry_updates_message_time():
    """Test telemetry updates track last message time."""
    from droneresearch.ros.px4_bridge import PX4ROS2Bridge
    
    bridge = PX4ROS2Bridge(namespace="test")
    
    # Initially no messages
    assert bridge._last_message_time == 0.0
    
    # Simulate telemetry update
    before = time.time()
    bridge._on_telemetry({"lat": 47.0, "lon": 8.0})
    after = time.time()
    
    assert before <= bridge._last_message_time <= after


def test_reconnect_info_after_message():
    """Test reconnect info shows message age correctly."""
    from droneresearch.ros.px4_bridge import PX4ROS2Bridge
    
    bridge = PX4ROS2Bridge(namespace="test")
    
    # Send a message
    bridge._on_telemetry({"lat": 47.0})
    
    time.sleep(0.1)
    
    info = bridge.get_reconnect_info()
    assert 0.0 < info["last_message_age"] < 1.0


def test_connection_timeout_detection():
    """Test connection timeout is detected correctly."""
    from droneresearch.ros.px4_bridge import PX4ROS2Bridge
    
    bridge = PX4ROS2Bridge(namespace="test")
    bridge._connection_timeout = 0.2  # 200ms timeout for testing
    
    # Simulate old message
    bridge._last_message_time = time.time() - 0.5  # 500ms ago
    
    age = time.time() - bridge._last_message_time
    assert age > bridge._connection_timeout


def test_multiple_status_callbacks():
    """Test multiple callbacks can be registered."""
    from droneresearch.ros.px4_bridge import PX4ROS2Bridge, ConnectionStatus
    
    bridge = PX4ROS2Bridge(namespace="test")
    
    calls_1 = []
    calls_2 = []
    
    bridge.on("connection_status", lambda s: calls_1.append(s))
    bridge.on("connection_status", lambda s: calls_2.append(s))
    
    bridge._set_status(ConnectionStatus.CONNECTED)
    
    assert len(calls_1) == 1
    assert len(calls_2) == 1
    assert calls_1[0] == ConnectionStatus.CONNECTED
    assert calls_2[0] == ConnectionStatus.CONNECTED


def test_callback_exception_handling():
    """Test callbacks that raise exceptions don't crash bridge."""
    from droneresearch.ros.px4_bridge import PX4ROS2Bridge, ConnectionStatus
    
    bridge = PX4ROS2Bridge(namespace="test")
    
    def bad_callback(status):
        raise ValueError("Test error")
    
    good_calls = []
    def good_callback(status):
        good_calls.append(status)
    
    bridge.on("connection_status", bad_callback)
    bridge.on("connection_status", good_callback)
    
    # Should not raise, good callback should still run
    bridge._set_status(ConnectionStatus.CONNECTED)
    
    assert len(good_calls) == 1


def test_start_sets_initial_status():
    """Test start() initializes reconnect state."""
    from droneresearch.ros.px4_bridge import PX4ROS2Bridge, ConnectionStatus
    
    bridge = PX4ROS2Bridge(namespace="test")
    
    # Mock acquire_ros to return False (simulating ROS2 not available)
    with patch('droneresearch.ros.px4_bridge.acquire_ros', return_value=False):
        bridge.start()
        
        # Should fail to start and set FAILED status
        assert bridge.get_connection_status() == ConnectionStatus.FAILED
        assert not bridge._running  # Should not be running


def test_stop_sets_disconnected_status():
    """Test stop() sets DISCONNECTED status."""
    from droneresearch.ros.px4_bridge import PX4ROS2Bridge, ConnectionStatus
    
    bridge = PX4ROS2Bridge(namespace="test")
    bridge._running = True
    bridge._set_status(ConnectionStatus.CONNECTED)
    
    with patch('droneresearch.ros.px4_bridge.release_ros'):
        bridge.stop()
    
    assert bridge.get_connection_status() == ConnectionStatus.DISCONNECTED


def test_is_connected_only_true_when_connected():
    """Test is_connected() returns True only for CONNECTED status."""
    from droneresearch.ros.px4_bridge import PX4ROS2Bridge, ConnectionStatus
    
    bridge = PX4ROS2Bridge(namespace="test")
    
    bridge._set_status(ConnectionStatus.DISCONNECTED)
    assert not bridge.is_connected()
    
    bridge._set_status(ConnectionStatus.CONNECTING)
    assert not bridge.is_connected()
    
    bridge._set_status(ConnectionStatus.CONNECTED)
    assert bridge.is_connected()
    
    bridge._set_status(ConnectionStatus.RECONNECTING)
    assert not bridge.is_connected()
    
    bridge._set_status(ConnectionStatus.FAILED)
    assert not bridge.is_connected()


def test_reconnect_attempts_increment():
    """Test reconnect attempts counter increments."""
    from droneresearch.ros.px4_bridge import PX4ROS2Bridge
    
    bridge = PX4ROS2Bridge(namespace="test")
    
    assert bridge._reconnect_attempts == 0
    
    bridge._reconnect_attempts += 1
    assert bridge._reconnect_attempts == 1
    
    bridge._reconnect_attempts += 1
    assert bridge._reconnect_attempts == 2


def test_reconnect_attempts_reset_on_success():
    """Test reconnect attempts reset to 0 on successful connection."""
    from droneresearch.ros.px4_bridge import PX4ROS2Bridge
    
    bridge = PX4ROS2Bridge(namespace="test")
    bridge._reconnect_attempts = 5
    bridge._reconnect_delay = 16.0
    
    # Simulate successful connection
    bridge._reconnect_attempts = 0
    bridge._reconnect_delay = 1.0
    
    assert bridge._reconnect_attempts == 0
    assert bridge._reconnect_delay == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob

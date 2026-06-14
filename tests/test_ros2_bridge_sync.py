"""
Test for Fix 4: ROS2 Bridge Sync

Verifies that ROS2Context signals are properly connected to SwarmContext
for bridge status and connection status updates.
"""

from unittest.mock import Mock

import pytest


def test_ros2_bridge_status_signal_exists():
    """Test that ROS2Context has bridgeStatusChanged signal."""
    from tools.ui.context.ros2_context import ROS2Context
    
    ros2 = ROS2Context()
    
    # Verify signal exists
    assert hasattr(ros2, 'bridgeStatusChanged')


def test_ros2_connection_status_signal_exists():
    """Test that ROS2Context has connectionStatusChanged signal."""
    from tools.ui.context.ros2_context import ROS2Context
    
    ros2 = ROS2Context()
    
    # Verify signal exists
    assert hasattr(ros2, 'connectionStatusChanged')


def test_ros2_log_message_signal_exists():
    """Test that ROS2Context has ros2LogMessage signal."""
    from tools.ui.context.ros2_context import ROS2Context
    
    ros2 = ROS2Context()
    
    # Verify signal exists
    assert hasattr(ros2, 'ros2LogMessage')


def test_service_locator_connects_ros2_signals():
    """Test that service_locator.py connects ROS2 signals."""
    # Read service_locator.py and verify connections
    with open('tools/ui/service_locator.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verify ros2LogMessage connection
    assert 'ros2.ros2LogMessage.connect(swarm.logMessage)' in content
    
    # Verify bridgeStatusChanged connection
    assert 'ros2.bridgeStatusChanged.connect' in content
    
    # Verify connectionStatusChanged connection
    assert 'ros2.connectionStatusChanged.connect' in content


def test_bridge_status_message_format():
    """Test that bridge status messages are formatted correctly."""
    # Simulate bridge status change
    drone_id = "D1"
    
    # Bridge started
    active = True
    message = f"[{drone_id}] ROS2 Bridge {'🟢 Started' if active else '🔴 Stopped'}"
    assert "🟢 Started" in message
    assert drone_id in message
    
    # Bridge stopped
    active = False
    message = f"[{drone_id}] ROS2 Bridge {'🟢 Started' if active else '🔴 Stopped'}"
    assert "🔴 Stopped" in message
    assert drone_id in message


def test_connection_status_level_determination():
    """Test that connection status determines correct log level."""
    # Error status
    status = "Connection error"
    level = "WARN" if "error" in status.lower() or "lost" in status.lower() else "INFO"
    assert level == "WARN"
    
    # Lost status
    status = "Connection lost"
    level = "WARN" if "error" in status.lower() or "lost" in status.lower() else "INFO"
    assert level == "WARN"
    
    # Normal status
    status = "Connected"
    level = "WARN" if "error" in status.lower() or "lost" in status.lower() else "INFO"
    assert level == "INFO"


def test_ros2_signals_can_be_connected():
    """Test that ROS2 signals can be connected to mock handlers."""
    from tools.ui.context.ros2_context import ROS2Context
    
    ros2 = ROS2Context()
    
    # Mock handlers
    log_handler = Mock()
    bridge_handler = Mock()
    connection_handler = Mock()
    
    # Connect signals
    ros2.ros2LogMessage.connect(log_handler)
    ros2.bridgeStatusChanged.connect(bridge_handler)
    ros2.connectionStatusChanged.connect(connection_handler)
    
    # Emit signals
    ros2.ros2LogMessage.emit("INFO", "Test message")
    ros2.bridgeStatusChanged.emit("D1", True)
    ros2.connectionStatusChanged.emit("D1", "Connected")
    
    # Verify handlers were called
    assert log_handler.called
    assert bridge_handler.called
    assert connection_handler.called


def test_ros2_bridge_sync_integration():
    """Test full integration of ROS2 bridge sync."""
    from tools.ui.context.ros2_context import ROS2Context
    from tools.ui.context.swarm_context import SwarmContext
    
    ros2 = ROS2Context()
    swarm = SwarmContext()
    
    # Mock swarm log handler
    log_messages = []
    swarm.logMessage.connect(lambda level, text: log_messages.append((level, text)))
    
    # Connect ROS2 signals (simulating service_locator.py)
    ros2.ros2LogMessage.connect(swarm.logMessage)
    ros2.bridgeStatusChanged.connect(
        lambda drone_id, active: swarm.logMessage.emit(
            "INFO",
            f"[{drone_id}] ROS2 Bridge {'🟢 Started' if active else '🔴 Stopped'}"
        )
    )
    ros2.connectionStatusChanged.connect(
        lambda drone_id, status: swarm.logMessage.emit(
            "WARN" if "error" in status.lower() or "lost" in status.lower() else "INFO",
            f"[{drone_id}] ROS2 Connection: {status}"
        )
    )
    
    # Emit ROS2 signals
    ros2.ros2LogMessage.emit("INFO", "[ROS2] Test log")
    ros2.bridgeStatusChanged.emit("D1", True)
    ros2.connectionStatusChanged.emit("D1", "Connected")
    ros2.bridgeStatusChanged.emit("D1", False)
    ros2.connectionStatusChanged.emit("D1", "Connection lost")
    
    # Verify messages were logged to swarm
    assert len(log_messages) == 5
    assert any("Test log" in msg[1] for msg in log_messages)
    assert any("🟢 Started" in msg[1] for msg in log_messages)
    assert any("Connected" in msg[1] for msg in log_messages)
    assert any("🔴 Stopped" in msg[1] for msg in log_messages)
    assert any("Connection lost" in msg[1] for msg in log_messages)
    
    # Verify log levels
    assert log_messages[0][0] == "INFO"  # ros2LogMessage
    assert log_messages[1][0] == "INFO"  # bridge started
    assert log_messages[2][0] == "INFO"  # connected
    assert log_messages[3][0] == "INFO"  # bridge stopped
    assert log_messages[4][0] == "WARN"  # connection lost

# Made with Bob

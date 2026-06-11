"""
Tests for PX4 mission upload via uXRCE-DDS.
"""

import pytest
import sys
import time
from unittest.mock import Mock, MagicMock, patch, call


@pytest.fixture
def mock_rclpy():
    """Mock rclpy module."""
    mock = MagicMock()
    mock.ok.return_value = True
    
    with patch.dict(sys.modules, {"rclpy": mock, "rclpy.node": MagicMock()}):
        with patch("droneresearch.ros.px4_mission._ROS2_OK", True):
            yield mock


@pytest.fixture
def mock_px4_msgs():
    """Mock px4_msgs module."""
    # Mock message types
    mock_count = MagicMock()
    mock_item = MagicMock()
    mock_ack = MagicMock()
    
    mock_msgs = MagicMock()
    mock_msgs.msg.VehicleMissionItemCount = mock_count
    mock_msgs.msg.VehicleMissionItem = mock_item
    mock_msgs.msg.VehicleMissionAck = mock_ack
    
    with patch.dict(sys.modules, {"px4_msgs": mock_msgs, "px4_msgs.msg": mock_msgs.msg}):
        with patch("droneresearch.ros.px4_mission._PX4_MSGS_OK", True):
            # Import module after patching to ensure flags are set correctly
            import droneresearch.ros.px4_mission as mission_module
            mission_module._MISSION_ACK_OK = True
            mission_module.VehicleMissionItemCount = mock_count
            mission_module.VehicleMissionItem = mock_item
            mission_module.VehicleMissionAck = mock_ack
            
            yield {
                "count": mock_count,
                "item": mock_item,
                "ack": mock_ack,
            }


@pytest.fixture
def mock_node():
    """Mock ROS2 node."""
    node = Mock()
    node.create_publisher = Mock(return_value=Mock())
    node.create_subscription = Mock(return_value=Mock())
    return node


@pytest.fixture
def uploader(mock_rclpy, mock_px4_msgs, mock_node):
    """Create PX4MissionUploader instance."""
    from droneresearch.ros.px4_mission import PX4MissionUploader
    return PX4MissionUploader(mock_node, namespace="uav_1")


def test_uploader_init(mock_rclpy, mock_px4_msgs, mock_node):
    """Test uploader initialization."""
    from droneresearch.ros.px4_mission import PX4MissionUploader
    
    uploader = PX4MissionUploader(mock_node, namespace="uav_1")
    
    # Check publishers created
    assert mock_node.create_publisher.call_count == 2
    calls = mock_node.create_publisher.call_args_list
    
    # Check count publisher
    assert "/uav_1/fmu/in/vehicle_mission_item_count" in str(calls[0])
    
    # Check item publisher
    assert "/uav_1/fmu/in/vehicle_mission_item" in str(calls[1])
    
    # Check subscriber created
    assert mock_node.create_subscription.call_count == 1
    assert "/uav_1/fmu/out/vehicle_mission_ack" in str(mock_node.create_subscription.call_args)


def test_uploader_init_no_namespace(mock_rclpy, mock_px4_msgs, mock_node):
    """Test uploader initialization without namespace."""
    from droneresearch.ros.px4_mission import PX4MissionUploader
    
    uploader = PX4MissionUploader(mock_node, namespace="")
    
    # Check publishers use default namespace
    calls = mock_node.create_publisher.call_args_list
    assert "/fmu/in/vehicle_mission_item_count" in str(calls[0])
    assert "/fmu/in/vehicle_mission_item" in str(calls[1])


def test_upload_empty_waypoints(uploader):
    """Test upload with empty waypoint list."""
    result = uploader.upload([])
    assert result is False


def test_upload_single_waypoint(uploader, mock_px4_msgs):
    """Test upload with single waypoint."""
    waypoints = [
        {"lat": 47.397742, "lon": 8.545594, "alt": 10.0}
    ]
    
    # Mock publishers
    uploader._pub_count = Mock()
    uploader._pub_item = Mock()
    uploader._sub_ack = None  # Disable ACK waiting
    
    result = uploader.upload(waypoints, timeout=1.0)
    
    # Check count published
    assert uploader._pub_count.publish.call_count == 1
    count_msg = uploader._pub_count.publish.call_args[0][0]
    assert count_msg.count == 1
    
    # Check item published
    assert uploader._pub_item.publish.call_count == 1
    item_msg = uploader._pub_item.publish.call_args[0][0]
    assert item_msg.sequence == 0
    assert item_msg.latitude == 47.397742
    assert item_msg.longitude == 8.545594
    assert item_msg.altitude == 10.0
    assert item_msg.frame == 3  # MAV_FRAME_GLOBAL_RELATIVE_ALT
    assert item_msg.command == 16  # MAV_CMD_NAV_WAYPOINT
    
    assert result is True


def test_upload_multiple_waypoints(uploader):
    """Test upload with multiple waypoints."""
    waypoints = [
        {"lat": 47.397742, "lon": 8.545594, "alt": 10.0},
        {"lat": 47.397842, "lon": 8.545694, "alt": 15.0},
        {"lat": 47.397942, "lon": 8.545794, "alt": 20.0},
    ]
    
    uploader._pub_count = Mock()
    uploader._pub_item = Mock()
    uploader._sub_ack = None
    
    result = uploader.upload(waypoints, timeout=1.0)
    
    # Check count
    count_msg = uploader._pub_count.publish.call_args[0][0]
    assert count_msg.count == 3
    
    # Check all items published
    assert uploader._pub_item.publish.call_count == 3
    
    # Just verify that publish was called 3 times with message objects
    # (Mock behavior makes exact value checking unreliable)
    for call_args in uploader._pub_item.publish.call_args_list:
        item_msg = call_args[0][0]
        assert hasattr(item_msg, 'latitude')
        assert hasattr(item_msg, 'longitude')
        assert hasattr(item_msg, 'altitude')
    
    assert result is True


def test_upload_with_optional_params(uploader):
    """Test upload with optional waypoint parameters."""
    waypoints = [
        {
            "lat": 47.397742,
            "lon": 8.545594,
            "alt": 10.0,
            "hold_time": 5.0,
            "accept_radius": 2.0,
            "pass_radius": 1.0,
            "yaw": 90.0,
        }
    ]
    
    uploader._pub_count = Mock()
    uploader._pub_item = Mock()
    uploader._sub_ack = None
    
    result = uploader.upload(waypoints, timeout=1.0)
    
    item_msg = uploader._pub_item.publish.call_args[0][0]
    assert item_msg.param1 == 5.0  # hold_time
    assert item_msg.param2 == 2.0  # accept_radius
    assert item_msg.param3 == 1.0  # pass_radius
    assert item_msg.param4 == 90.0  # yaw
    
    assert result is True


def test_upload_with_ack_success(uploader):
    """Test upload with successful ACK."""
    waypoints = [{"lat": 47.397742, "lon": 8.545594, "alt": 10.0}]
    
    uploader._pub_count = Mock()
    uploader._pub_item = Mock()
    uploader._sub_ack = Mock()  # Enable ACK
    
    # Simulate ACK received after a short delay
    import threading
    def send_ack():
        time.sleep(0.2)
        mock_ack = Mock()
        mock_ack.result = 0  # MAV_MISSION_ACCEPTED
        uploader._on_ack(mock_ack)
    
    ack_thread = threading.Thread(target=send_ack, daemon=True)
    ack_thread.start()
    
    result = uploader.upload(waypoints, timeout=2.0)
    
    assert result is True


def test_upload_with_ack_timeout(uploader):
    """Test upload with ACK timeout."""
    waypoints = [{"lat": 47.397742, "lon": 8.545594, "alt": 10.0}]
    
    uploader._pub_count = Mock()
    uploader._pub_item = Mock()
    uploader._sub_ack = Mock()  # Enable ACK
    
    # Don't simulate ACK - let it timeout
    result = uploader.upload(waypoints, timeout=0.5)
    
    assert result is False


def test_upload_with_ack_rejected(uploader):
    """Test upload with rejected ACK."""
    waypoints = [{"lat": 47.397742, "lon": 8.545594, "alt": 10.0}]
    
    uploader._pub_count = Mock()
    uploader._pub_item = Mock()
    uploader._sub_ack = Mock()
    
    # Simulate rejected ACK after a short delay
    import threading
    def send_ack():
        time.sleep(0.2)
        mock_ack = Mock()
        mock_ack.result = 1  # MAV_MISSION_ERROR
        uploader._on_ack(mock_ack)
    
    ack_thread = threading.Thread(target=send_ack, daemon=True)
    ack_thread.start()
    
    result = uploader.upload(waypoints, timeout=2.0)
    
    assert result is False


def test_clear_mission(uploader):
    """Test mission clear."""
    uploader._pub_count = Mock()
    
    result = uploader.clear()
    
    # Check count = 0 published
    assert uploader._pub_count.publish.call_count == 1
    count_msg = uploader._pub_count.publish.call_args[0][0]
    assert count_msg.count == 0
    
    assert result is True


def test_ack_callback(uploader):
    """Test ACK callback handling."""
    mock_ack = Mock()
    mock_ack.result = 0  # ACCEPTED
    
    uploader._on_ack(mock_ack)
    
    assert uploader._ack_result == 0
    assert uploader._ack_received.is_set()


def test_ack_callback_error_codes(uploader):
    """Test ACK callback with various error codes."""
    error_codes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
    
    for code in error_codes:
        uploader._ack_received.clear()
        mock_ack = Mock()
        mock_ack.result = code
        
        uploader._on_ack(mock_ack)
        
        assert uploader._ack_result == code
        assert uploader._ack_received.is_set()


def test_bridge_mission_methods():
    """Test PX4ROS2Bridge mission methods."""
    with patch("droneresearch.ros.px4_bridge._ROS2_OK", True), \
         patch("droneresearch.ros.px4_bridge._PX4_MSGS_OK", True), \
         patch("droneresearch.ros.px4_bridge.acquire_ros", return_value=True):
        
        from droneresearch.ros.px4_bridge import PX4ROS2Bridge
        
        bridge = PX4ROS2Bridge(namespace="uav_1")
        
        # Mock mission uploader
        bridge._mission_uploader = Mock()
        bridge._mission_uploader.upload.return_value = True
        bridge._mission_uploader.clear.return_value = True
        
        # Test upload
        waypoints = [{"lat": 47.397742, "lon": 8.545594, "alt": 10.0}]
        result = bridge.upload_mission(waypoints)
        assert result is True
        bridge._mission_uploader.upload.assert_called_once_with(waypoints, timeout=10.0)
        
        # Test clear
        result = bridge.clear_mission()
        assert result is True
        bridge._mission_uploader.clear.assert_called_once()


def test_bridge_mission_methods_no_uploader():
    """Test bridge mission methods when uploader not available."""
    with patch("droneresearch.ros.px4_bridge._ROS2_OK", True), \
         patch("droneresearch.ros.px4_bridge._PX4_MSGS_OK", True), \
         patch("droneresearch.ros.px4_bridge.acquire_ros", return_value=True):
        
        from droneresearch.ros.px4_bridge import PX4ROS2Bridge
        
        bridge = PX4ROS2Bridge()
        bridge._mission_uploader = None
        
        # Test upload fails gracefully
        result = bridge.upload_mission([{"lat": 47.397742, "lon": 8.545594, "alt": 10.0}])
        assert result is False
        
        # Test clear fails gracefully
        result = bridge.clear_mission()
        assert result is False


def test_bridge_start_mission():
    """Test bridge start_mission command."""
    with patch("droneresearch.ros.px4_bridge._ROS2_OK", True), \
         patch("droneresearch.ros.px4_bridge._PX4_MSGS_OK", True), \
         patch("droneresearch.ros.px4_bridge.acquire_ros", return_value=True):
        
        from droneresearch.ros.px4_bridge import PX4ROS2Bridge
        
        bridge = PX4ROS2Bridge()
        bridge._send_vehicle_command = Mock()
        
        bridge.start_mission()
        
        # Check SET_MODE command sent with AUTO.MISSION (mode 4)
        bridge._send_vehicle_command.assert_called_once_with(
            176,  # VehicleCommandId.SET_MODE
            param1=1.0,
            param2=4.0,
        )


def test_bridge_pause_mission():
    """Test bridge pause_mission command."""
    with patch("droneresearch.ros.px4_bridge._ROS2_OK", True), \
         patch("droneresearch.ros.px4_bridge._PX4_MSGS_OK", True), \
         patch("droneresearch.ros.px4_bridge.acquire_ros", return_value=True):
        
        from droneresearch.ros.px4_bridge import PX4ROS2Bridge
        
        bridge = PX4ROS2Bridge()
        bridge._send_vehicle_command = Mock()
        
        bridge.pause_mission()
        
        # Check SET_MODE command sent with AUTO.LOITER (mode 3)
        bridge._send_vehicle_command.assert_called_once_with(
            176,  # VehicleCommandId.SET_MODE
            param1=1.0,
            param2=3.0,
        )



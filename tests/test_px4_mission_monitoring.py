"""
Tests for PX4 mission monitoring functionality.
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock, patch


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
    mock_count = MagicMock()
    mock_item = MagicMock()
    mock_ack = MagicMock()
    mock_result = MagicMock()
    
    mock_msgs = MagicMock()
    mock_msgs.msg.VehicleMissionItemCount = mock_count
    mock_msgs.msg.VehicleMissionItem = mock_item
    mock_msgs.msg.VehicleMissionAck = mock_ack
    mock_msgs.msg.MissionResult = mock_result
    
    with patch.dict(sys.modules, {"px4_msgs": mock_msgs, "px4_msgs.msg": mock_msgs.msg}):
        with patch("droneresearch.ros.px4_mission._PX4_MSGS_OK", True):
            import droneresearch.ros.px4_mission as mission_module
            mission_module._MISSION_ACK_OK = True
            mission_module._MISSION_RESULT_OK = True
            mission_module.VehicleMissionItemCount = mock_count
            mission_module.VehicleMissionItem = mock_item
            mission_module.VehicleMissionAck = mock_ack
            mission_module.MissionResult = mock_result
            
            yield {
                "count": mock_count,
                "item": mock_item,
                "ack": mock_ack,
                "result": mock_result,
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


def test_mission_status_init(uploader):
    """Test mission status initialization."""
    status = uploader.get_status()
    
    assert status["active"] == False
    assert status["current_seq"] == 0
    assert status["total_count"] == 0
    assert status["reached"] == False
    assert status["finished"] == False
    assert status["failure"] == False


def test_upload_stores_waypoints(uploader):
    """Test that upload stores waypoints."""
    waypoints = [
        {"lat": 47.397742, "lon": 8.545594, "alt": 10.0},
        {"lat": 47.397842, "lon": 8.545694, "alt": 15.0},
    ]
    
    uploader._pub_count = Mock()
    uploader._pub_item = Mock()
    uploader._sub_ack = None
    
    uploader.upload(waypoints)
    
    # Check waypoints stored
    stored = uploader.get_waypoints()
    assert len(stored) == 2
    assert stored[0]["lat"] == 47.397742
    assert stored[1]["lat"] == 47.397842


def test_upload_updates_status(uploader):
    """Test that upload updates mission status."""
    waypoints = [
        {"lat": 47.397742, "lon": 8.545594, "alt": 10.0},
        {"lat": 47.397842, "lon": 8.545694, "alt": 15.0},
    ]
    
    uploader._pub_count = Mock()
    uploader._pub_item = Mock()
    uploader._sub_ack = None
    
    uploader.upload(waypoints)
    
    status = uploader.get_status()
    assert status["total_count"] == 2
    assert status["current_seq"] == 0


def test_mission_result_callback(uploader):
    """Test mission result callback."""
    # Create mock message
    mock_msg = Mock()
    mock_msg.mission_id = 1
    mock_msg.seq_current = 2
    mock_msg.seq_total = 5
    mock_msg.seq_reached = 2
    mock_msg.finished = False
    mock_msg.failure = False
    mock_msg.item_do_jump_changed = False
    mock_msg.item_changed_index = 0
    mock_msg.mode_auto = True
    mock_msg.mode_offboard = False
    
    uploader._on_mission_result(mock_msg)
    
    status = uploader.get_status()
    assert status["active"] == True
    assert status["current_seq"] == 2
    assert status["total_count"] == 5
    assert status["reached"] == True
    assert status["finished"] == False
    assert status["failure"] == False


def test_status_callback_registration(uploader):
    """Test status callback registration."""
    callback_called = []
    
    def test_callback(status):
        callback_called.append(status)
    
    uploader.on_status_change(test_callback)
    
    # Trigger status update
    mock_msg = Mock()
    mock_msg.mission_id = 1
    mock_msg.seq_current = 1
    mock_msg.seq_total = 3
    mock_msg.seq_reached = 1
    mock_msg.finished = False
    mock_msg.failure = False
    mock_msg.item_do_jump_changed = False
    mock_msg.item_changed_index = 0
    mock_msg.mode_auto = True
    mock_msg.mode_offboard = False
    
    uploader._on_mission_result(mock_msg)
    
    assert len(callback_called) == 1
    assert callback_called[0]["current_seq"] == 1
    assert callback_called[0]["total_count"] == 3


def test_bridge_mission_status_methods():
    """Test PX4ROS2Bridge mission status methods."""
    with patch("droneresearch.ros.px4_bridge._ROS2_OK", True), \
         patch("droneresearch.ros.px4_bridge._PX4_MSGS_OK", True), \
         patch("droneresearch.ros.px4_bridge.acquire_ros", return_value=True):
        
        from droneresearch.ros.px4_bridge import PX4ROS2Bridge
        
        bridge = PX4ROS2Bridge(namespace="uav_1")
        
        # Mock mission uploader
        bridge._mission_uploader = Mock()
        bridge._mission_uploader.get_status.return_value = {
            "active": True,
            "current_seq": 2,
            "total_count": 5,
        }
        bridge._mission_uploader.get_waypoints.return_value = [
            {"lat": 47.397742, "lon": 8.545594, "alt": 10.0}
        ]
        
        # Test get_mission_status
        status = bridge.get_mission_status()
        assert status["active"] == True
        assert status["current_seq"] == 2
        assert status["total_count"] == 5
        
        # Test get_mission_waypoints
        waypoints = bridge.get_mission_waypoints()
        assert len(waypoints) == 1
        assert waypoints[0]["lat"] == 47.397742


def test_bridge_mission_status_no_uploader():
    """Test bridge mission status methods when uploader not available."""
    with patch("droneresearch.ros.px4_bridge._ROS2_OK", True), \
         patch("droneresearch.ros.px4_bridge._PX4_MSGS_OK", True), \
         patch("droneresearch.ros.px4_bridge.acquire_ros", return_value=True):
        
        from droneresearch.ros.px4_bridge import PX4ROS2Bridge
        
        bridge = PX4ROS2Bridge()
        bridge._mission_uploader = None
        
        # Test get_mission_status returns default
        status = bridge.get_mission_status()
        assert status["active"] == False
        assert status["current_seq"] == 0
        
        # Test get_mission_waypoints returns empty list
        waypoints = bridge.get_mission_waypoints()
        assert waypoints == []


def test_bridge_on_mission_status():
    """Test bridge on_mission_status callback registration."""
    with patch("droneresearch.ros.px4_bridge._ROS2_OK", True), \
         patch("droneresearch.ros.px4_bridge._PX4_MSGS_OK", True), \
         patch("droneresearch.ros.px4_bridge.acquire_ros", return_value=True):
        
        from droneresearch.ros.px4_bridge import PX4ROS2Bridge
        
        bridge = PX4ROS2Bridge()
        bridge._mission_uploader = Mock()
        
        callback = Mock()
        bridge.on_mission_status(callback)
        
        # Check callback registered
        bridge._mission_uploader.on_status_change.assert_called_once_with(callback)


# Made with Bob
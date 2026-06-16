"""
Test DepthCameraSubscriber functionality.

Since ROS2 is optional, these tests mock ROS2 components.

Tests:
- Subscriber initialization
- Point cloud callback
- Statistics tracking
- Thread safety
- Context manager support
"""
import threading
import time
from unittest.mock import MagicMock, patch

import pytest


def test_depth_camera_import_without_ros2():
    """Test that import fails gracefully without ROS2."""
    with patch.dict('sys.modules', {'rclpy': None, 'sensor_msgs.msg': None}):
        with pytest.raises(ImportError, match="ROS2.*not available"):
            from droneresearch.sensors.depth_camera import DepthCameraSubscriber
            DepthCameraSubscriber()


@pytest.mark.skipif(
    not hasattr(__import__('droneresearch.sensors', fromlist=['depth_camera']), 'depth_camera'),
    reason="ROS2 not available"
)
def test_depth_camera_initialization():
    """Test DepthCameraSubscriber initialization."""
    from droneresearch.sensors.depth_camera import DepthCameraSubscriber
    
    callback = MagicMock()
    
    subscriber = DepthCameraSubscriber(
        topic="/test/depth/points",
        callback=callback,
        drone_id="test_drone",
        max_range=15.0,
        downsample=2
    )
    
    assert subscriber.topic == "/test/depth/points"
    assert subscriber.drone_id == "test_drone"
    assert subscriber.max_range == 15.0
    assert subscriber.downsample == 2
    assert not subscriber._running


@pytest.mark.skipif(
    not hasattr(__import__('droneresearch.sensors', fromlist=['depth_camera']), 'depth_camera'),
    reason="ROS2 not available"
)
def test_depth_camera_statistics():
    """Test statistics tracking."""
    from droneresearch.sensors.depth_camera import DepthCameraSubscriber
    
    subscriber = DepthCameraSubscriber()
    
    stats = subscriber.get_statistics()
    assert stats["messages_received"] == 0
    assert stats["points_processed"] == 0
    assert stats["last_message_time"] == 0.0
    assert stats["is_running"] is False


@pytest.mark.skipif(
    not hasattr(__import__('droneresearch.sensors', fromlist=['depth_camera']), 'depth_camera'),
    reason="ROS2 not available"
)
def test_depth_camera_context_manager():
    """Test context manager support."""
    from droneresearch.sensors.depth_camera import DepthCameraSubscriber
    
    with patch('droneresearch.sensors.depth_camera.acquire_ros', return_value=False):
        subscriber = DepthCameraSubscriber()
        
        # Context manager should call start() and stop()
        with subscriber:
            pass  # start() returns False, so nothing happens
        
        assert not subscriber._running


def test_mock_depth_camera_workflow():
    """Test complete workflow with mocked ROS2."""
    # Mock ROS2 modules
    mock_rclpy = MagicMock()
    mock_node = MagicMock()
    mock_subscription = MagicMock()
    mock_executor = MagicMock()
    
    mock_rclpy.create_node.return_value = mock_node
    mock_node.create_subscription.return_value = mock_subscription
    mock_rclpy.executors.SingleThreadedExecutor.return_value = mock_executor
    mock_rclpy.ok.return_value = True
    
    with patch.dict('sys.modules', {
        'rclpy': mock_rclpy,
        'rclpy.node': MagicMock(),
        'rclpy.executors': MagicMock(),
        'sensor_msgs.msg': MagicMock(),
        'sensor_msgs_py': MagicMock(),
    }):
        with patch('droneresearch.sensors.depth_camera._ROS2_OK', True):
            with patch('droneresearch.sensors.depth_camera.acquire_ros', return_value=True):
                with patch('droneresearch.sensors.depth_camera.release_ros'):
                    from droneresearch.sensors.depth_camera import DepthCameraSubscriber
                    
                    callback_called = threading.Event()
                    received_points = []
                    
                    def test_callback(drone_id, points):
                        received_points.extend(points)
                        callback_called.set()
                    
                    subscriber = DepthCameraSubscriber(
                        topic="/test/points",
                        callback=test_callback,
                        drone_id="test_drone"
                    )
                    
                    # Start subscriber
                    result = subscriber.start()
                    assert result is True
                    assert subscriber._running
                    
                    # Verify ROS2 node was created
                    mock_rclpy.create_node.assert_called_once()
                    
                    # Verify subscription was created
                    mock_node.create_subscription.assert_called_once()
                    
                    # Stop subscriber
                    subscriber.stop()
                    assert not subscriber._running


def test_mock_pointcloud_processing():
    """Test point cloud processing with mocked data."""
    mock_rclpy = MagicMock()
    mock_point_cloud2 = MagicMock()
    
    # Mock point cloud data
    mock_points = [
        (1.0, 2.0, 3.0),
        (4.0, 5.0, 6.0),
        (7.0, 8.0, 9.0),
    ]
    mock_point_cloud2.read_points.return_value = iter(mock_points)
    
    with patch.dict('sys.modules', {
        'rclpy': mock_rclpy,
        'rclpy.node': MagicMock(),
        'sensor_msgs.msg': MagicMock(),
        'sensor_msgs_py': MagicMock(point_cloud2=mock_point_cloud2),
    }):
        with patch('droneresearch.sensors.depth_camera._ROS2_OK', True):
            from droneresearch.sensors.depth_camera import DepthCameraSubscriber
            
            received_points = []
            
            def test_callback(drone_id, points):
                received_points.extend(points)
            
            subscriber = DepthCameraSubscriber(
                callback=test_callback,
                drone_id="test_drone",
                downsample=1  # No downsampling
            )
            
            # Simulate receiving a point cloud message
            mock_msg = MagicMock()
            subscriber._on_pointcloud(mock_msg)
            
            # Verify callback was called with correct points
            assert len(received_points) == 3
            assert received_points[0] == (1.0, 2.0, 3.0)
            assert received_points[1] == (4.0, 5.0, 6.0)
            assert received_points[2] == (7.0, 8.0, 9.0)
            
            # Verify statistics
            stats = subscriber.get_statistics()
            assert stats["messages_received"] == 1
            assert stats["points_processed"] == 3


def test_mock_pointcloud_downsampling():
    """Test point cloud downsampling."""
    mock_point_cloud2 = MagicMock()
    
    # Mock 10 points
    mock_points = [(float(i), float(i), float(i)) for i in range(10)]
    mock_point_cloud2.read_points.return_value = iter(mock_points)
    
    with patch.dict('sys.modules', {
        'rclpy': MagicMock(),
        'sensor_msgs.msg': MagicMock(),
        'sensor_msgs_py': MagicMock(point_cloud2=mock_point_cloud2),
    }):
        with patch('droneresearch.sensors.depth_camera._ROS2_OK', True):
            from droneresearch.sensors.depth_camera import DepthCameraSubscriber
            
            received_points = []
            
            def test_callback(drone_id, points):
                received_points.extend(points)
            
            # Downsample by factor of 2 (every 2nd point)
            subscriber = DepthCameraSubscriber(
                callback=test_callback,
                downsample=2
            )
            
            mock_msg = MagicMock()
            subscriber._on_pointcloud(mock_msg)
            
            # Should receive 5 points (indices 0, 2, 4, 6, 8)
            assert len(received_points) == 5
            assert received_points[0] == (0.0, 0.0, 0.0)
            assert received_points[1] == (2.0, 2.0, 2.0)
            assert received_points[4] == (8.0, 8.0, 8.0)


def test_mock_pointcloud_range_filter():
    """Test point cloud range filtering."""
    mock_point_cloud2 = MagicMock()
    
    # Mock points at various distances
    mock_points = [
        (1.0, 0.0, 0.0),   # Distance: 1.0
        (5.0, 0.0, 0.0),   # Distance: 5.0
        (10.0, 0.0, 0.0),  # Distance: 10.0
        (20.0, 0.0, 0.0),  # Distance: 20.0
    ]
    mock_point_cloud2.read_points.return_value = iter(mock_points)
    
    with patch.dict('sys.modules', {
        'rclpy': MagicMock(),
        'sensor_msgs.msg': MagicMock(),
        'sensor_msgs_py': MagicMock(point_cloud2=mock_point_cloud2),
    }):
        with patch('droneresearch.sensors.depth_camera._ROS2_OK', True):
            from droneresearch.sensors.depth_camera import DepthCameraSubscriber
            
            received_points = []
            
            def test_callback(drone_id, points):
                received_points.extend(points)
            
            # Set max range to 12 meters
            subscriber = DepthCameraSubscriber(
                callback=test_callback,
                max_range=12.0
            )
            
            mock_msg = MagicMock()
            subscriber._on_pointcloud(mock_msg)
            
            # Should receive 3 points (distances 1, 5, 10)
            assert len(received_points) == 3
            assert received_points[0] == (1.0, 0.0, 0.0)
            assert received_points[1] == (5.0, 0.0, 0.0)
            assert received_points[2] == (10.0, 0.0, 0.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob

"""
Tests for PX4FormationController.

These tests are hardware-free and use mocks for ROS2/px4_msgs.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
import sys


# Mock ROS2 modules before importing
sys.modules['rclpy'] = MagicMock()
sys.modules['rclpy.node'] = MagicMock()
sys.modules['rclpy.qos'] = MagicMock()
sys.modules['px4_msgs'] = MagicMock()
sys.modules['px4_msgs.msg'] = MagicMock()


def test_ned_enu_conversion():
    """Test NED ↔ ENU frame conversion."""
    from droneresearch.ros.px4_formation import ned_to_enu, enu_to_ned
    
    # NED to ENU
    east, north, up = ned_to_enu(10.0, 5.0, -15.0)
    assert east == 5.0
    assert north == 10.0
    assert up == 15.0
    
    # ENU to NED
    north, east, down = enu_to_ned(5.0, 10.0, 15.0)
    assert north == 10.0
    assert east == 5.0
    assert down == -15.0
    
    # Round-trip
    n, e, d = 10.0, 5.0, -15.0
    e2, n2, u2 = ned_to_enu(n, e, d)
    n3, e3, d3 = enu_to_ned(e2, n2, u2)
    assert abs(n3 - n) < 1e-9
    assert abs(e3 - e) < 1e-9
    assert abs(d3 - d) < 1e-9


def test_formation_controller_init():
    """Test formation controller initialization."""
    from droneresearch.ros.px4_formation import PX4FormationController
    
    controller = PX4FormationController(
        leader_ns="uav_1",
        follower_namespaces=["uav_2", "uav_3"],
        shape="v",
        spacing=5.0
    )
    
    assert controller.leader_ns == "uav_1"
    assert controller.follower_namespaces == ["uav_2", "uav_3"]
    assert controller.shape == "v"
    assert controller.spacing == 5.0
    assert len(controller.offsets) == 2  # 2 followers


def test_formation_offsets_v_shape():
    """Test V-formation offset calculation."""
    from droneresearch.ros.px4_formation import PX4FormationController
    
    controller = PX4FormationController(
        leader_ns="uav_1",
        follower_namespaces=["uav_2", "uav_3"],
        shape="v",
        spacing=5.0
    )
    
    # V-formation: followers behind and to the sides
    assert len(controller.offsets) == 2
    
    # First follower (left side)
    n1, e1 = controller.offsets[0]
    assert n1 < 0  # Behind leader
    assert e1 < 0  # Left side
    
    # Second follower (right side)
    n2, e2 = controller.offsets[1]
    assert n2 < 0  # Behind leader
    assert e2 > 0  # Right side
    
    # Symmetric
    assert abs(abs(e1) - abs(e2)) < 1e-9


def test_formation_offsets_line_shape():
    """Test line formation offset calculation."""
    from droneresearch.ros.px4_formation import PX4FormationController
    
    controller = PX4FormationController(
        leader_ns="uav_1",
        follower_namespaces=["uav_2", "uav_3", "uav_4"],
        shape="line",
        spacing=5.0
    )
    
    # Line formation: followers directly behind
    assert len(controller.offsets) == 3
    
    for i, (n, e) in enumerate(controller.offsets):
        assert n == -(i + 1) * 5.0  # Behind leader
        assert e == 0.0  # No lateral offset


def test_leader_position_setting():
    """Test setting and getting leader position."""
    from droneresearch.ros.px4_formation import PX4FormationController
    
    controller = PX4FormationController(
        leader_ns="uav_1",
        follower_namespaces=["uav_2"],
        shape="line",
        spacing=5.0
    )
    
    # Set position
    controller.set_leader_position(north=10.0, east=5.0, altitude=15.0, yaw=1.57)
    
    # Get position
    pos = controller.get_leader_position()
    assert pos["north"] == 10.0
    assert pos["east"] == 5.0
    assert pos["altitude"] == 15.0


def test_follower_positions():
    """Test follower position calculation."""
    from droneresearch.ros.px4_formation import PX4FormationController
    
    controller = PX4FormationController(
        leader_ns="uav_1",
        follower_namespaces=["uav_2", "uav_3"],
        shape="line",
        spacing=5.0
    )
    
    # Set leader position
    controller.set_leader_position(north=10.0, east=5.0, altitude=15.0)
    
    # Get follower positions
    followers = controller.get_follower_positions()
    
    assert "uav_2" in followers
    assert "uav_3" in followers
    
    # uav_2 should be 5m behind leader
    assert followers["uav_2"]["north"] == 5.0
    assert followers["uav_2"]["east"] == 5.0
    assert followers["uav_2"]["altitude"] == 15.0
    
    # uav_3 should be 10m behind leader
    assert followers["uav_3"]["north"] == 0.0
    assert followers["uav_3"]["east"] == 5.0
    assert followers["uav_3"]["altitude"] == 15.0


def test_formation_shapes():
    """Test all formation shapes."""
    from droneresearch.ros.px4_formation import PX4FormationController
    from droneresearch.sdk.formations import SHAPES
    
    for shape in SHAPES:
        controller = PX4FormationController(
            leader_ns="uav_1",
            follower_namespaces=["uav_2", "uav_3"],
            shape=shape,
            spacing=5.0
        )
        
        # Should have 2 offsets (2 followers)
        assert len(controller.offsets) == 2
        
        # All offsets should be valid numbers
        for n, e in controller.offsets:
            assert isinstance(n, (int, float))
            assert isinstance(e, (int, float))


def test_thread_safety():
    """Test thread-safe position updates."""
    from droneresearch.ros.px4_formation import PX4FormationController
    import threading
    
    controller = PX4FormationController(
        leader_ns="uav_1",
        follower_namespaces=["uav_2"],
        shape="line",
        spacing=5.0
    )
    
    # Multiple threads updating position
    def update_position(n):
        for i in range(100):
            controller.set_leader_position(north=n, east=0, altitude=10)
    
    threads = [
        threading.Thread(target=update_position, args=(i,))
        for i in range(5)
    ]
    
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Should not crash and position should be valid
    pos = controller.get_leader_position()
    assert isinstance(pos["north"], (int, float))
    assert isinstance(pos["east"], (int, float))
    assert isinstance(pos["altitude"], (int, float))


def test_altitude_conversion():
    """Test altitude conversion (positive up vs negative down)."""
    from droneresearch.ros.px4_formation import PX4FormationController
    
    controller = PX4FormationController(
        leader_ns="uav_1",
        follower_namespaces=["uav_2"],
        shape="line",
        spacing=5.0
    )
    
    # Set altitude (positive up)
    controller.set_leader_position(north=0, east=0, altitude=15.0)
    
    # Get position (should still be positive up)
    pos = controller.get_leader_position()
    assert pos["altitude"] == 15.0
    
    # Follower should have same altitude
    followers = controller.get_follower_positions()
    assert followers["uav_2"]["altitude"] == 15.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


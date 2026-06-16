"""
Test obstacle timeout and cleanup in PerceptionEnhancedAPF.

Tests:
- Obstacle expiration after timeout
- Periodic cleanup mechanism
- Obstacle refresh on re-detection
- Statistics tracking
"""
import time

import pytest

from droneresearch.safety.apf import Pose3D
from droneresearch.safety.perception_avoidance import PerceptionEnhancedAPF


def test_obstacle_timeout_basic():
    """Test that obstacles expire after configured timeout."""
    apf = PerceptionEnhancedAPF(
        voxel_size=1.0,
        obstacle_timeout=0.2  # 200ms timeout
    )
    
    # Add obstacle
    points = [(1.0, 1.0, 10.0)]
    apf.update_from_pointcloud("drone_1", points)
    
    # Verify obstacle exists
    stats = apf.get_statistics()
    assert stats["active_voxels"] == 1
    
    # Wait for timeout
    time.sleep(0.25)
    
    # Trigger cleanup by adding new point
    apf.update_from_pointcloud("drone_1", [(5.0, 5.0, 10.0)])
    
    # Old obstacle should be gone
    stats = apf.get_statistics()
    assert stats["active_voxels"] == 1  # Only new obstacle


def test_obstacle_refresh():
    """Test that re-detecting an obstacle refreshes its timestamp."""
    apf = PerceptionEnhancedAPF(
        voxel_size=1.0,
        obstacle_timeout=0.3  # 300ms timeout
    )
    
    # Add obstacle
    points = [(1.0, 1.0, 10.0)]
    apf.update_from_pointcloud("drone_1", points)
    
    # Wait 150ms (half timeout)
    time.sleep(0.15)
    
    # Re-detect same obstacle (refreshes timestamp)
    apf.update_from_pointcloud("drone_1", points)
    
    # Wait another 200ms (total 350ms, but obstacle was refreshed at 150ms)
    time.sleep(0.2)
    
    # Trigger cleanup
    apf.update_from_pointcloud("drone_1", [(5.0, 5.0, 10.0)])
    
    # Obstacle should still exist (refreshed timestamp)
    stats = apf.get_statistics()
    assert stats["active_voxels"] == 2  # Both obstacles


def test_multiple_obstacles_different_timeouts():
    """Test that obstacles expire independently based on their timestamps."""
    apf = PerceptionEnhancedAPF(
        voxel_size=1.0,
        obstacle_timeout=0.3  # 300ms timeout
    )
    
    # Add first obstacle
    apf.update_from_pointcloud("drone_1", [(1.0, 1.0, 10.0)])
    
    # Wait 150ms
    time.sleep(0.15)
    
    # Add second obstacle
    apf.update_from_pointcloud("drone_1", [(2.0, 2.0, 10.0)])
    
    # Wait 200ms (first obstacle at 350ms, second at 200ms)
    time.sleep(0.2)
    
    # Trigger cleanup
    apf.update_from_pointcloud("drone_1", [(5.0, 5.0, 10.0)])
    
    # First obstacle should be expired, second and third should remain
    stats = apf.get_statistics()
    assert stats["active_voxels"] == 2


def test_cleanup_frequency():
    """Test that cleanup runs on every update."""
    apf = PerceptionEnhancedAPF(
        voxel_size=1.0,
        obstacle_timeout=0.1  # 100ms timeout
    )
    
    # Add obstacle
    apf.update_from_pointcloud("drone_1", [(1.0, 1.0, 10.0)])
    
    # Wait for obstacle to expire
    time.sleep(0.15)
    
    # Add new points (cleanup runs on every update)
    apf.update_from_pointcloud("drone_1", [(2.0, 2.0, 10.0)])
    
    # Expired obstacle should be cleaned up immediately
    stats = apf.get_statistics()
    # Should have only the new obstacle
    assert stats["active_voxels"] == 1


def test_get_nearby_obstacles_respects_timeout():
    """Test that get_nearby_obstacles only returns non-expired obstacles."""
    apf = PerceptionEnhancedAPF(
        voxel_size=1.0,
        obstacle_timeout=0.2  # 200ms timeout
    )
    
    # Add obstacles
    apf.update_from_pointcloud("drone_1", [(1.0, 1.0, 10.0), (2.0, 2.0, 10.0)])
    
    # Verify both obstacles are found
    origin = Pose3D(0, 0, 10)
    nearby = apf.get_nearby_obstacles(origin, radius=5.0)
    assert len(nearby) == 2
    
    # Wait for timeout
    time.sleep(0.25)
    
    # Expired obstacles should not be returned
    nearby = apf.get_nearby_obstacles(origin, radius=5.0)
    assert len(nearby) == 0


def test_filter_with_expired_obstacles():
    """Test that APF filter ignores expired obstacles."""
    apf = PerceptionEnhancedAPF(
        voxel_size=1.0,
        obstacle_timeout=0.2,
        min_separation=2.0,
        obstacle_radius=4.0
    )
    
    # Add obstacle between two drones
    apf.update_from_pointcloud("drone_1", [(5.0, 0.0, 10.0)])
    
    # Initial positions
    positions = {
        "D1": Pose3D(0, 0, 10),
        "D2": Pose3D(10, 0, 10)
    }
    
    # Desired positions (would pass through obstacle)
    desired = {
        "D1": Pose3D(10, 0, 10),
        "D2": Pose3D(0, 0, 10)
    }
    
    # Filter with active obstacle
    safe1 = apf.filter(positions, desired)
    
    # Drones should be repelled by obstacle
    # D1 moving right should be pushed away from obstacle at (5,0,10)
    assert safe1["D1"].x < desired["D1"].x  # Repelled, doesn't reach full desired
    
    # Wait for obstacle to expire
    time.sleep(0.25)
    
    # Filter again with expired obstacle
    safe2 = apf.filter(positions, desired)
    
    # Without obstacle, drones should move more freely toward desired
    # (still limited by max_speed, but not repelled by obstacle)
    assert safe2["D1"].x >= safe1["D1"].x  # Can move further without obstacle


def test_statistics_accuracy():
    """Test that statistics accurately reflect obstacle state."""
    apf = PerceptionEnhancedAPF(
        voxel_size=1.0,
        obstacle_timeout=0.2
    )
    
    # Add 5 points (3 unique voxels)
    points = [
        (1.0, 1.0, 10.0),  # Voxel (1,1,10)
        (1.1, 1.1, 10.1),  # Same voxel (1,1,10)
        (2.0, 2.0, 10.0),  # Voxel (2,2,10)
        (2.2, 2.2, 10.2),  # Same voxel (2,2,10)
        (3.0, 3.0, 10.0),  # Voxel (3,3,10)
    ]
    apf.update_from_pointcloud("drone_1", points)
    
    stats = apf.get_statistics()
    assert stats["total_points_processed"] == 5
    assert stats["active_voxels"] == 3
    assert stats["obstacle_count"] == 3
    
    # Wait for expiration
    time.sleep(0.25)
    
    # Add new point to trigger cleanup
    apf.update_from_pointcloud("drone_1", [(4.0, 4.0, 10.0)])
    
    stats = apf.get_statistics()
    assert stats["total_points_processed"] == 6  # Cumulative
    assert stats["active_voxels"] == 1  # Only new obstacle
    assert stats["obstacle_count"] == 1


def test_long_running_obstacle_map():
    """Test obstacle map behavior over extended period with continuous updates."""
    apf = PerceptionEnhancedAPF(
        voxel_size=1.0,
        obstacle_timeout=0.15  # 150ms timeout
    )
    
    # Simulate continuous sensor updates over 1 second
    for i in range(10):
        # Add obstacles at moving position
        x = float(i)
        points = [(x, 0.0, 10.0), (x + 0.5, 0.0, 10.0)]
        apf.update_from_pointcloud("drone_1", points)
        time.sleep(0.1)
    
    # Only recent obstacles should remain (within 150ms)
    # With 100ms sleep, last 1-2 updates should be within timeout
    stats = apf.get_statistics()
    # Should have 2-4 voxels (last update + maybe previous)
    assert 2 <= stats["active_voxels"] <= 4
    
    # Total points processed should be 20
    assert stats["total_points_processed"] == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob

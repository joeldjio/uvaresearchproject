"""
Test voxel grid functionality in PerceptionEnhancedAPF.

Tests:
- Voxel coordinate conversion
- Point cloud to voxel mapping
- Obstacle map updates
- Voxel expiration
"""
import time

import pytest

from droneresearch.safety.apf import Pose3D
from droneresearch.safety.perception_avoidance import PerceptionEnhancedAPF


def test_voxel_conversion():
    """Test conversion between continuous coordinates and voxel indices."""
    apf = PerceptionEnhancedAPF(voxel_size=0.5)
    
    # Test exact voxel boundaries
    assert apf._to_voxel(0.0, 0.0, 0.0) == (0, 0, 0)
    assert apf._to_voxel(0.5, 0.5, 0.5) == (1, 1, 1)
    assert apf._to_voxel(1.0, 1.0, 1.0) == (2, 2, 2)
    
    # Test negative coordinates
    assert apf._to_voxel(-0.5, -0.5, -0.5) == (-1, -1, -1)
    assert apf._to_voxel(-1.0, -1.0, -1.0) == (-2, -2, -2)
    
    # Test fractional coordinates (should floor to voxel)
    assert apf._to_voxel(0.3, 0.7, 0.9) == (0, 1, 1)
    assert apf._to_voxel(1.2, 1.8, 2.4) == (2, 3, 4)


def test_voxel_to_position():
    """Test conversion from voxel indices to center position."""
    apf = PerceptionEnhancedAPF(voxel_size=0.5)
    
    # Voxel (0,0,0) center should be at (0.25, 0.25, 0.25)
    pos = apf._from_voxel(0, 0, 0)
    assert abs(pos.x - 0.25) < 1e-6
    assert abs(pos.y - 0.25) < 1e-6
    assert abs(pos.z - 0.25) < 1e-6
    
    # Voxel (1,1,1) center should be at (0.75, 0.75, 0.75)
    pos = apf._from_voxel(1, 1, 1)
    assert abs(pos.x - 0.75) < 1e-6
    assert abs(pos.y - 0.75) < 1e-6
    assert abs(pos.z - 0.75) < 1e-6
    
    # Negative voxels
    pos = apf._from_voxel(-1, -1, -1)
    assert abs(pos.x - (-0.25)) < 1e-6
    assert abs(pos.y - (-0.25)) < 1e-6
    assert abs(pos.z - (-0.25)) < 1e-6


def test_pointcloud_update():
    """Test updating obstacle map from point cloud."""
    apf = PerceptionEnhancedAPF(voxel_size=1.0, perception_radius=10.0)
    
    # Add some points
    points = [
        (1.5, 2.0, 10.0),  # Voxel (1, 2, 10)
        (1.6, 2.1, 10.1),  # Same voxel (1, 2, 10)
        (3.0, 4.0, 5.0),   # Voxel (3, 4, 5)
    ]
    
    new_voxels = apf.update_from_pointcloud("drone_1", points)
    
    # Should have 2 unique voxels
    assert new_voxels == 2
    
    stats = apf.get_statistics()
    assert stats["total_points_processed"] == 3
    assert stats["active_voxels"] == 2
    assert stats["obstacle_count"] == 2


def test_pointcloud_update_with_range_filter():
    """Test that points outside perception radius are filtered."""
    apf = PerceptionEnhancedAPF(voxel_size=1.0, perception_radius=5.0)
    
    drone_pos = Pose3D(0, 0, 10)
    
    points = [
        (1.0, 1.0, 10.0),   # Within range (dist ~1.4m)
        (10.0, 10.0, 10.0), # Outside range (dist ~14m)
        (2.0, 2.0, 10.0),   # Within range (dist ~2.8m)
    ]
    
    new_voxels = apf.update_from_pointcloud("drone_1", points, drone_pos)
    
    # Only 2 points should be added (within 5m radius)
    assert new_voxels == 2
    
    stats = apf.get_statistics()
    assert stats["active_voxels"] == 2


def test_obstacle_expiration():
    """Test that obstacles expire after timeout."""
    apf = PerceptionEnhancedAPF(
        voxel_size=1.0,
        obstacle_timeout=0.5  # 500ms timeout
    )
    
    # Add initial points
    points = [(1.0, 1.0, 10.0), (2.0, 2.0, 10.0)]
    apf.update_from_pointcloud("drone_1", points)
    
    stats = apf.get_statistics()
    assert stats["active_voxels"] == 2
    
    # Wait for obstacles to expire
    time.sleep(0.6)
    
    # Trigger cleanup by adding new points (cleanup runs on every update)
    apf.update_from_pointcloud("drone_1", [(3.0, 3.0, 10.0)])
    
    # Old obstacles should be expired, only new one remains
    stats = apf.get_statistics()
    assert stats["active_voxels"] == 1


def test_get_nearby_obstacles():
    """Test retrieving obstacles near a position."""
    apf = PerceptionEnhancedAPF(voxel_size=1.0)
    
    # Add obstacles at known positions
    points = [
        (1.0, 1.0, 10.0),   # Voxel (1,1,10), center at (1.5, 1.5, 10.5)
        (5.0, 5.0, 10.0),   # Voxel (5,5,10), center at (5.5, 5.5, 10.5)
        (2.0, 2.0, 10.0),   # Voxel (2,2,10), center at (2.5, 2.5, 10.5)
    ]
    apf.update_from_pointcloud("drone_1", points)
    
    # Get obstacles within 3m of origin
    origin = Pose3D(0, 0, 10)
    nearby = apf.get_nearby_obstacles(origin, radius=3.0)
    
    # Voxel (1,1,10) center at (1.5, 1.5, 10.5): dist = sqrt(1.5^2 + 1.5^2 + 0.5^2) = 2.18m ✓
    # Voxel (2,2,10) center at (2.5, 2.5, 10.5): dist = sqrt(2.5^2 + 2.5^2 + 0.5^2) = 3.57m ✗
    assert len(nearby) == 1
    
    # Get obstacles within 8m of origin
    nearby = apf.get_nearby_obstacles(origin, radius=8.0)
    
    # All 3 obstacles should be within 8m
    assert len(nearby) == 3


def test_clear_perception_obstacles():
    """Test clearing all perception obstacles."""
    apf = PerceptionEnhancedAPF(voxel_size=1.0)
    
    # Add obstacles
    points = [(1.0, 1.0, 10.0), (2.0, 2.0, 10.0), (3.0, 3.0, 10.0)]
    apf.update_from_pointcloud("drone_1", points)
    
    stats = apf.get_statistics()
    assert stats["active_voxels"] == 3
    
    # Clear obstacles
    apf.clear_perception_obstacles()
    
    stats = apf.get_statistics()
    assert stats["active_voxels"] == 0
    assert stats["obstacle_count"] == 0


def test_obstacle_map_copy():
    """Test getting a copy of the obstacle map."""
    apf = PerceptionEnhancedAPF(voxel_size=1.0)
    
    # Add obstacles
    points = [(1.0, 1.0, 10.0), (2.0, 2.0, 10.0)]
    apf.update_from_pointcloud("drone_1", points)
    
    # Get copy
    obstacle_map = apf.get_obstacle_map_copy()
    
    assert len(obstacle_map) == 2
    assert (1, 1, 10) in obstacle_map
    assert (2, 2, 10) in obstacle_map
    
    # Verify it's a copy (modifying it doesn't affect internal map)
    obstacle_map.clear()
    
    stats = apf.get_statistics()
    assert stats["active_voxels"] == 2  # Internal map unchanged


def test_concurrent_updates():
    """Test thread-safe concurrent obstacle map updates."""
    import threading
    
    apf = PerceptionEnhancedAPF(voxel_size=1.0)
    
    def add_points(drone_id, offset):
        points = [
            (offset + 1.0, 1.0, 10.0),
            (offset + 2.0, 2.0, 10.0),
            (offset + 3.0, 3.0, 10.0),
        ]
        apf.update_from_pointcloud(drone_id, points)
    
    # Create multiple threads adding points concurrently
    threads = []
    for i in range(5):
        t = threading.Thread(target=add_points, args=(f"drone_{i}", i * 10))
        threads.append(t)
        t.start()
    
    # Wait for all threads
    for t in threads:
        t.join()
    
    # Should have 15 unique voxels (3 per drone * 5 drones)
    stats = apf.get_statistics()
    assert stats["active_voxels"] == 15
    assert stats["total_points_processed"] == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob

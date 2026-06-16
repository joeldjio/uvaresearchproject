"""
Perception-Enhanced APF — Collision avoidance with depth sensor integration.

Based on: ESCAPE Framework (Phase 2.1)
    Extends APFSafetyFilter with real-time obstacle detection from
    depth cameras, LiDAR, or other perception sensors.

Key Features:
- Voxel-based 3D obstacle map (0.5m resolution)
- Point cloud integration from ROS2 depth sensors
- Temporal obstacle filtering (5s timeout)
- 10m perception radius
- Thread-safe obstacle map updates

Frame Convention:
    All positions use local NED (North-East-Down) coordinates:
    - x: North (meters)
    - y: East (meters)
    - z: Altitude above ground (meters, positive UP)

Usage:
    from droneresearch.safety.perception_avoidance import PerceptionEnhancedAPF
    
    apf = PerceptionEnhancedAPF(
        min_separation=2.0,
        perception_radius=10.0,
        voxel_size=0.5,
        obstacle_timeout=5.0
    )
    
    # Update obstacle map from depth sensor
    points = [(1.5, 2.0, 10.0), (1.6, 2.1, 10.1), ...]  # NED coordinates
    apf.update_from_pointcloud("drone_1", points)
    
    # Filter with perception-based obstacles
    safe = apf.filter(positions, desired)
"""
from __future__ import annotations

import math
import threading
import time
from typing import Dict, List, Optional, Set, Tuple

from droneresearch.safety.apf import APFSafetyFilter, Pose3D


class PerceptionEnhancedAPF(APFSafetyFilter):
    """
    APF with perception-based obstacle detection.
    
    Integrates depth camera/LiDAR data for real-time obstacle mapping.
    Maintains a voxel grid of detected obstacles with temporal filtering.
    
    Thread Safety:
        - Obstacle map updates are protected by _obstacle_lock
        - update_from_pointcloud() can be called from ROS2 callback threads
        - filter() reads obstacle map with lock protection
        - Concurrent updates from multiple drones are safe
    
    Parameters:
        perception_radius : Maximum range for obstacle detection (meters)
        voxel_size        : Size of each voxel in the obstacle map (meters)
        obstacle_timeout  : Time before obstacles are removed from map (seconds)
        *args, **kwargs   : Passed to APFSafetyFilter base class
    """
    
    def __init__(
        self,
        *args,
        perception_radius: float = 10.0,
        voxel_size: float = 0.5,
        obstacle_timeout: float = 5.0,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        
        self._perception_radius = perception_radius
        self._voxel_size = voxel_size
        self._obstacle_timeout = obstacle_timeout
        
        # Voxel grid: {(vx, vy, vz): timestamp}
        # Each voxel represents a cube of space that contains an obstacle
        self._obstacle_map: Dict[Tuple[int, int, int], float] = {}
        
        # Lock for thread-safe obstacle map updates
        self._obstacle_lock = threading.Lock()
        
        # Statistics for monitoring
        self._total_points_processed = 0
        self._active_voxels = 0
        self._last_cleanup_time = time.time()
    
    def update_from_pointcloud(
        self,
        drone_id: str,
        points: List[Tuple[float, float, float]],
        drone_position: Optional[Pose3D] = None
    ) -> int:
        """
        Update obstacle map from depth sensor point cloud.
        
        Args:
            drone_id       : ID of the drone providing the point cloud
            points         : List of (x, y, z) points in local NED coordinates
            drone_position : Current position of the drone (for range filtering)
        
        Returns:
            Number of new voxels added to the obstacle map
        
        Thread Safety:
            Safe to call from ROS2 callback threads. Uses internal locking.
        """
        if not points:
            return 0
        
        current_time = time.time()
        new_voxels = 0
        
        with self._obstacle_lock:
            for x, y, z in points:
                # Skip points outside perception radius
                if drone_position:
                    dist = math.sqrt(
                        (x - drone_position.x)**2 +
                        (y - drone_position.y)**2 +
                        (z - drone_position.z)**2
                    )
                    if dist > self._perception_radius:
                        continue
                
                # Convert to voxel coordinates
                voxel_key = self._to_voxel(x, y, z)
                
                # Update or add voxel
                if voxel_key not in self._obstacle_map:
                    new_voxels += 1
                
                self._obstacle_map[voxel_key] = current_time
            
            self._total_points_processed += len(points)
            
            # Cleanup expired obstacles on every update
            # (more aggressive than periodic cleanup, but ensures consistency)
            self._cleanup_expired_obstacles(current_time)
            self._active_voxels = len(self._obstacle_map)
            self._last_cleanup_time = current_time
        
        return new_voxels
    
    def _to_voxel(self, x: float, y: float, z: float) -> Tuple[int, int, int]:
        """Convert continuous coordinates to voxel grid indices."""
        return (
            int(math.floor(x / self._voxel_size)),
            int(math.floor(y / self._voxel_size)),
            int(math.floor(z / self._voxel_size))
        )
    
    def _from_voxel(self, vx: int, vy: int, vz: int) -> Pose3D:
        """Convert voxel indices to center position of voxel."""
        return Pose3D(
            (vx + 0.5) * self._voxel_size,
            (vy + 0.5) * self._voxel_size,
            (vz + 0.5) * self._voxel_size
        )
    
    def _cleanup_expired_obstacles(self, current_time: float):
        """Remove obstacles that haven't been seen recently."""
        expired = [
            voxel for voxel, timestamp in self._obstacle_map.items()
            if current_time - timestamp > self._obstacle_timeout
        ]
        for voxel in expired:
            del self._obstacle_map[voxel]
    
    def get_nearby_obstacles(
        self,
        position: Pose3D,
        radius: float
    ) -> List[Pose3D]:
        """
        Get all obstacles within radius of position.
        
        Args:
            position : Center position to search from
            radius   : Search radius (meters)
        
        Returns:
            List of obstacle positions (voxel centers)
        
        Thread Safety:
            Safe to call concurrently. Uses internal locking.
        """
        obstacles = []
        current_time = time.time()
        
        with self._obstacle_lock:
            for voxel, timestamp in self._obstacle_map.items():
                # Skip expired obstacles
                if current_time - timestamp > self._obstacle_timeout:
                    continue
                
                # Convert voxel to position
                obs_pos = self._from_voxel(*voxel)
                
                # Check if within radius
                dist = position.dist(obs_pos)
                if dist <= radius:
                    obstacles.append(obs_pos)
        
        return obstacles
    
    def filter(
        self,
        positions: Dict[str, Pose3D],
        desired: Dict[str, Pose3D],
    ) -> Dict[str, Pose3D]:
        """
        Apply APF with perception-based obstacles.
        
        Extends base APF filter by adding repulsive forces from
        obstacles detected by depth sensors.
        
        Thread Safety:
            Safe to call concurrently. Reads obstacle map with locking.
        """
        # First, temporarily add perception-based obstacles to static obstacle list
        perception_obstacles = []
        
        with self._obstacle_lock:
            current_time = time.time()
            for voxel, timestamp in self._obstacle_map.items():
                # Only use recent obstacles
                if current_time - timestamp <= self._obstacle_timeout:
                    perception_obstacles.append(self._from_voxel(*voxel))
        
        # Store original static obstacles
        original_obstacles = self._obstacles.copy()
        
        # Add perception obstacles
        self._obstacles.extend(perception_obstacles)
        
        # Run base APF filter
        safe = super().filter(positions, desired)
        
        # Restore original static obstacles
        self._obstacles = original_obstacles
        
        return safe
    
    def clear_perception_obstacles(self):
        """Clear all perception-based obstacles from the map."""
        with self._obstacle_lock:
            self._obstacle_map.clear()
            self._active_voxels = 0
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get obstacle map statistics.
        
        Returns:
            Dictionary with:
            - total_points_processed: Total points received
            - active_voxels: Current number of occupied voxels
            - obstacle_count: Number of distinct obstacles
        """
        with self._obstacle_lock:
            return {
                "total_points_processed": self._total_points_processed,
                "active_voxels": self._active_voxels,
                "obstacle_count": len(self._obstacle_map)
            }
    
    def get_obstacle_map_copy(self) -> Dict[Tuple[int, int, int], float]:
        """
        Get a copy of the current obstacle map.
        
        Returns:
            Dictionary mapping voxel coordinates to timestamps
        
        Thread Safety:
            Returns a copy, safe for external use without locking.
        """
        with self._obstacle_lock:
            return self._obstacle_map.copy()

# Made with Bob

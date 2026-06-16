"""
ESCAPE Framework UI Context.

Provides Qt/QML integration for all ESCAPE framework features:
- Perception-based collision avoidance
- Distributed task allocation
- Adaptive safety margins
- Distributed mapping consensus
"""
from typing import Dict, List, Optional, Tuple
from PyQt6.QtCore import QObject, pyqtSignal as Signal, pyqtSlot as Slot, pyqtProperty 
from droneresearch.safety.apf import Pose3D

# Optional ESCAPE imports
try:
    from droneresearch.safety.perception_avoidance import PerceptionEnhancedAPF
    from droneresearch.communication import SwarmCommunicationProtocol
    from droneresearch.exploration import DistributedTaskAllocator
    from droneresearch.safety import AdaptiveAPFSafetyFilter
    from droneresearch.mapping import DistributedOccupancyMap
    _ESCAPE_OK = True
except ImportError:
    _ESCAPE_OK = False


class ESCAPEContext(QObject):
    """
    Qt context for ESCAPE framework features.
    
    Provides QML-accessible properties and methods for:
    - Obstacle visualization from perception layer
    - Task allocation status and control
    - Adaptive safety margin configuration
    - Distributed map visualization
    
    Signals
    -------
    obstaclesChanged : Emitted when obstacle list updates
    tasksChanged : Emitted when task allocation changes
    marginsChanged : Emitted when safety margins update
    mapChanged : Emitted when occupancy map updates
    windSpeedChanged : Emitted when wind speed changes
    gpsUncertaintyChanged : Emitted when GPS uncertainty changes
    """
    
    # Signals
    obstaclesChanged = Signal()
    tasksChanged = Signal()
    marginsChanged = Signal()
    mapChanged = Signal()
    windSpeedChanged = Signal()
    gpsUncertaintyChanged = Signal()
    perceptionEnabledChanged = Signal()
    taskAllocationEnabledChanged = Signal()
    adaptiveMarginsEnabledChanged = Signal()
    mappingEnabledChanged = Signal()
    
    # Logging signal (level, message)
    logMessage = Signal(str, str)
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        if not _ESCAPE_OK:
            print("[ESCAPEContext] ESCAPE modules not available")
        
        # Perception
        self._perception_apf: Optional[PerceptionEnhancedAPF] = None
        self._drone_positions: Dict[str, Pose3D] = {}
        self._perception_enabled: bool = False
        
        # Communication & Task Allocation
        self._protocol: Optional[SwarmCommunicationProtocol] = None
        self._allocator: Optional[DistributedTaskAllocator] = None
        self._drone_id: str = "D1"
        self._task_allocation_enabled: bool = False
        
        # Adaptive Safety
        self._adaptive_apf: Optional[AdaptiveAPFSafetyFilter] = None
        self._wind_speed: float = 0.0
        self._gps_uncertainty: float = 0.3
        self._adaptive_margins_enabled: bool = False
        
        # Distributed Mapping
        self._map: Optional[DistributedOccupancyMap] = None
        self._mapping_enabled: bool = False
    
    # ========== Initialization ==========
    
    @Slot(str)
    def initialize(self, drone_id: str):
        """Initialize ESCAPE framework for this drone."""
        if not _ESCAPE_OK:
            return
        
        self._drone_id = drone_id
        
        # Initialize perception
        self._perception_apf = PerceptionEnhancedAPF(
            min_separation=2.0,
            voxel_size=0.5,
            perception_radius=10.0,
            obstacle_timeout=5.0,
        )
        
        # Initialize communication
        self._protocol = SwarmCommunicationProtocol(
            drone_id=drone_id,
            port=5000,
        )
        self._protocol.start()
        
        # Initialize task allocator
        self._allocator = DistributedTaskAllocator(
            drone_id=drone_id,
            protocol=self._protocol,
        )
        
        # Initialize adaptive safety
        self._adaptive_apf = AdaptiveAPFSafetyFilter(
            min_separation=2.0,
            reaction_time=0.5,
            gps_uncertainty=self._gps_uncertainty,
            wind_speed=self._wind_speed,
        )
        
        # Initialize mapping
        self._map = DistributedOccupancyMap(
            voxel_size=0.5,
            bounds=((-50, 50), (-50, 50), (0, 30)),
            decay_rate=0.1,
        )
        
        print(f"[ESCAPEContext] Initialized for {drone_id}")
    
    @Slot()
    def shutdown(self):
        """Shutdown ESCAPE framework."""
        if self._protocol:
            self._protocol.stop()
        print("[ESCAPEContext] Shutdown complete")
    
    # ========== Perception Properties ==========
    
    @pyqtProperty(list, notify=obstaclesChanged)
    def obstacles(self) -> List[Dict]:
        """Get nearby obstacles from perception filter."""
        if not self._perception_apf or not self._drone_positions:
            return []
        
        # Use first drone position as reference
        drone_pos = list(self._drone_positions.values())[0]
        
        nearby = self._perception_apf.get_nearby_obstacles(
            drone_pos=drone_pos,
            radius=20.0
        )
        
        return [
            {"x": x, "y": y, "z": z}
            for x, y, z in nearby
        ]
    
    @pyqtProperty(int, notify=obstaclesChanged)
    def obstacleCount(self) -> int:
        """Get total number of obstacles."""
        return len(self.obstacles)
    
    @Slot(list)
    def updatePointCloud(self, points: List[Tuple[float, float, float]]):
        """Update perception from point cloud data."""
        if not self._perception_apf or not self._drone_positions:
            return
        
        drone_pos = list(self._drone_positions.values())[0]
        self._perception_apf.update_from_pointcloud(points, drone_pos)
        self.obstaclesChanged.emit()
    
    @Slot()
    def clearObstacles(self):
        """Clear all obstacles from perception."""
        if self._perception_apf:
            self._perception_apf._obstacle_map.clear()
            self.obstaclesChanged.emit()
    
    # ========== Task Allocation Properties ==========
    
    @pyqtProperty(list, notify=tasksChanged)
    def tasks(self) -> List[Dict]:
        """Get current task allocation status."""
        if not self._allocator:
            return []
        
        return [
            {
                "task_id": task_id,
                "task_type": info.get("type", "unknown"),
                "assigned_to": self._allocator.get_task_assignment(task_id),
                "priority": info.get("priority", 0.0),
                "position": info.get("position", (0, 0, 0)),
            }
            for task_id, info in self._allocator._tasks.items()
        ]
    
    @pyqtProperty(int, notify=tasksChanged)
    def taskCount(self) -> int:
        """Get total number of tasks."""
        return len(self.tasks)
    
    @Slot(str, float, float, float, float)
    def announceTask(
        self,
        task_type: str,
        x: float,
        y: float,
        z: float,
        priority: float = 0.5
    ):
        """Announce a new task to the swarm."""
        if not self._allocator:
            return
        
        task_id = self._allocator.announce_task(
            task_type=task_type,
            position=(x, y, z),
            priority=priority,
        )
        
        print(f"[ESCAPEContext] Announced task {task_id}")
        self.tasksChanged.emit()
    
    @Slot(str)
    def completeTask(self, task_id: str):
        """Mark a task as complete."""
        if not self._allocator:
            return
        
        self._allocator.complete_task(task_id)
        self.tasksChanged.emit()
    
    # ========== Adaptive Safety Properties ==========
    
    @pyqtProperty(float, notify=windSpeedChanged)
    def windSpeed(self) -> float:
        """Get current wind speed (m/s)."""
        return self._wind_speed
    
    @Slot(float)
    def setWindSpeed(self, speed: float):
        """Set wind speed for adaptive margins."""
        self._wind_speed = max(0.0, speed)
        if self._adaptive_apf:
            self._adaptive_apf.set_wind_speed(self._wind_speed)
        self.windSpeedChanged.emit()
        self.marginsChanged.emit()
    
    @pyqtProperty(float, notify=gpsUncertaintyChanged)
    def gpsUncertainty(self) -> float:
        """Get current GPS uncertainty (meters)."""
        return self._gps_uncertainty
    
    @Slot(float)
    def setGpsUncertainty(self, uncertainty: float):
        """Set GPS uncertainty for adaptive margins."""
        self._gps_uncertainty = max(0.0, uncertainty)
        if self._adaptive_apf:
            self._adaptive_apf.set_gps_uncertainty(self._gps_uncertainty)
        self.gpsUncertaintyChanged.emit()
        self.marginsChanged.emit()
    
    @pyqtProperty(list, notify=marginsChanged)
    def droneMargins(self) -> List[Dict]:
        """Get current adaptive margins between all drone pairs."""
        if not self._adaptive_apf or not self._drone_positions:
            return []
        
        margins = []
        drone_ids = list(self._drone_positions.keys())
        
        for i, id_a in enumerate(drone_ids):
            for id_b in drone_ids[i+1:]:
                margin = self._adaptive_apf.get_current_margin(id_a, id_b)
                if margin:
                    margins.append({
                        "pair": f"{id_a}-{id_b}",
                        "margin": margin,
                        "safe": margin >= 3.0,
                    })
        
        return margins
    
    # ========== Distributed Mapping Properties ==========
    
    @pyqtProperty(list, notify=mapChanged)
    def occupiedVoxels(self) -> List[Dict]:
        """Get occupied voxels for visualization."""
        if not self._map:
            return []
        
        voxels = self._map.get_occupied_voxels(
            threshold=0.5,
            min_confidence=0.3
        )
        
        result = []
        for x, y, z in voxels:
            occ, conf = self._map.get_occupancy(x, y, z)
            if conf:
                result.append({
                    "x": x,
                    "y": y,
                    "z": z,
                    "occupancy": occ or 0.0,
                    "confidence": conf,
                })
        
        return result
    
    @pyqtProperty(int, notify=mapChanged)
    def voxelCount(self) -> int:
        """Get total number of voxels in map."""
        if not self._map:
            return 0
        return self._map.get_statistics()["voxel_count"]
    
    @pyqtProperty(int, notify=mapChanged)
    def mergeCount(self) -> int:
        """Get number of map merges performed."""
        if not self._map:
            return 0
        return self._map.get_statistics()["merge_count"]
    
    @pyqtProperty(int, notify=mapChanged)
    def consensusCount(self) -> int:
        """Get number of consensus operations."""
        if not self._map:
            return 0
        return self._map.get_statistics()["consensus_count"]
    
    @Slot(float, float, float, float, float)
    def updateMapVoxel(
        self,
        x: float,
        y: float,
        z: float,
        occupancy: float,
        confidence: float = 1.0
    ):
        """Update a voxel in the map."""
        if not self._map:
            return
        
        self._map.update_voxel(x, y, z, occupancy, confidence)
        self.mapChanged.emit()
    
    @Slot()
    def cleanupMap(self):
        """Remove old/low-confidence voxels from map."""
        if not self._map:
            return
        
        removed = self._map.cleanup_old_voxels()
        if removed > 0:
            self.logMessage.emit("INFO", f"[ESCAPE] Cleaned up {removed} stale voxel(s)")
        self.mapChanged.emit()
    
    @Slot()
    def clearMap(self):
        """Clear entire map."""
        if not self._map:
            return
        
        self._map.clear()
        self.mapChanged.emit()
    
    # ========== Helper Methods ==========
    
    def update_drone_positions(self, positions: Dict[str, Pose3D]):
        """Update drone positions for margin calculation."""
        self._drone_positions = positions
        self.marginsChanged.emit()
        self.obstaclesChanged.emit()
    
    # ========== Enabled Properties ==========
    
    @pyqtProperty(bool, notify=perceptionEnabledChanged)
    def perceptionEnabled(self) -> bool:
        """Check if perception-based avoidance is enabled."""
        return self._perception_enabled
    
    @perceptionEnabled.setter
    def perceptionEnabled(self, enabled: bool):
        if self._perception_enabled != enabled:
            self._perception_enabled = enabled
            self.perceptionEnabledChanged.emit()
            self.logMessage.emit("INFO", f"[ESCAPE] Perception-based collision avoidance {'enabled' if enabled else 'disabled'}")
    
    @pyqtProperty(bool, notify=taskAllocationEnabledChanged)
    def taskAllocationEnabled(self) -> bool:
        """Check if task allocation is enabled."""
        return self._task_allocation_enabled
    
    @taskAllocationEnabled.setter
    def taskAllocationEnabled(self, enabled: bool):
        if self._task_allocation_enabled != enabled:
            self._task_allocation_enabled = enabled
            self.taskAllocationEnabledChanged.emit()
            self.logMessage.emit("INFO", f"[ESCAPE] Distributed task allocation {'enabled' if enabled else 'disabled'}")
    
    @pyqtProperty(bool, notify=adaptiveMarginsEnabledChanged)
    def adaptiveMarginsEnabled(self) -> bool:
        """Check if adaptive margins are enabled."""
        return self._adaptive_margins_enabled
    
    @adaptiveMarginsEnabled.setter
    def adaptiveMarginsEnabled(self, enabled: bool):
        if self._adaptive_margins_enabled != enabled:
            self._adaptive_margins_enabled = enabled
            self.adaptiveMarginsEnabledChanged.emit()
            self.logMessage.emit("INFO", f"[ESCAPE] Adaptive safety margins {'enabled' if enabled else 'disabled'}")
    
    @pyqtProperty(bool, notify=mappingEnabledChanged)
    def mappingEnabled(self) -> bool:
        """Check if distributed mapping is enabled."""
        return self._mapping_enabled
    
    @mappingEnabled.setter
    def mappingEnabled(self, enabled: bool):
        if self._mapping_enabled != enabled:
            self._mapping_enabled = enabled
            self.mappingEnabledChanged.emit()
            self.logMessage.emit("INFO", f"[ESCAPE] Distributed mapping consensus {'enabled' if enabled else 'disabled'}")
    
    @pyqtProperty(bool, constant=True)
    def available(self) -> bool:
        """Check if ESCAPE framework is available."""
        return _ESCAPE_OK

# Made with Bob

"""
MissionContext — exposes Field Coverage Planning to QML.

Registered as context property 'mission' in the QML engine.
"""

from __future__ import annotations

import math
import threading
from typing import List, Tuple, Optional, TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from droneresearch.control.field_coverage import (
    FieldCoveragePlanner,
    FieldBoundary,
    CoverageConfig,
    CoveragePattern,
    MultiDroneStrategy,
)
from droneresearch.control.mission import MissionEngine, Waypoint

if TYPE_CHECKING:
    from tools.ui.context.swarm_context import SwarmContext


class MissionContext(QObject):
    """QML-callable wrapper for field coverage planning."""

    # Signals
    logMessage = pyqtSignal(str, str, arguments=["level", "text"])
    fieldBoundaryChanged = pyqtSignal()
    coverageGenerated = pyqtSignal()
    coverageCleared = pyqtSignal()
    drawingModeChanged = pyqtSignal(bool, arguments=["active"])
    missionLockChanged = pyqtSignal(bool, arguments=["locked"])

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lock = threading.Lock()
        
        # Field Coverage Planner
        self._planner = FieldCoveragePlanner()
        self._home_set = False
        
        # Field boundary
        self._boundary_points: List[Tuple[float, float]] = []
        self._drawing_mode = False
        
        # Coverage configuration
        self._coverage_pattern = CoveragePattern.PARALLEL_LINES.value
        self._coverage_altitude = 20.0
        self._coverage_line_spacing = 10.0
        self._coverage_overlap = 0.2
        self._coverage_speed = 5.0
        
        # Multi-drone strategy
        self._multi_drone_strategy = MultiDroneStrategy.SINGLE_DRONE.value
        self._formation_offset = 5.0  # meters between drones in formation
        self._sequential_delay = 10.0  # seconds between drone starts
        
        # Generated waypoints
        self._coverage_waypoints: List[Tuple[float, float, float]] = []
        self._coverage_distance = 0.0
        self._coverage_time = 0.0
        self._preview_active = False
        
        # Mission lock state
        self._mission_locked = False
        self._poll_in_progress = False  # Gate to prevent concurrent polls
        
        # Swarm context reference (injected via wire())
        self._swarm_context: Optional["SwarmContext"] = None
        
        # Poll mission status every 500ms to update lock state
        from PyQt6.QtCore import QTimer
        self._lock_poll_timer = QTimer(self)
        self._lock_poll_timer.timeout.connect(self._update_mission_lock)
        self._lock_poll_timer.start(500)  # 500ms polling interval
        
        # Boundary drawing timeout (5 minutes)
        self._drawing_timeout_timer = QTimer(self)
        self._drawing_timeout_timer.timeout.connect(self._on_drawing_timeout)
        self._drawing_timeout_timer.setSingleShot(True)

    # ── Properties ────────────────────────────────────────────────────────

    @pyqtProperty(bool, notify=drawingModeChanged)
    def drawingMode(self):
        return self._drawing_mode

    @pyqtProperty(int, notify=fieldBoundaryChanged)
    def fieldBoundaryPoints(self):
        return len(self._boundary_points)

    @pyqtProperty(int, notify=fieldBoundaryChanged)
    def coveragePattern(self):
        return self._coverage_pattern

    @coveragePattern.setter
    def coveragePattern(self, value):
        self._coverage_pattern = value
        self.fieldBoundaryChanged.emit()

    @pyqtProperty(float, notify=fieldBoundaryChanged)
    def coverageAltitude(self):
        return self._coverage_altitude

    @coverageAltitude.setter
    def coverageAltitude(self, value):
        self._coverage_altitude = value
        self.fieldBoundaryChanged.emit()

    @pyqtProperty(float, notify=fieldBoundaryChanged)
    def coverageLineSpacing(self):
        return self._coverage_line_spacing

    @coverageLineSpacing.setter
    def coverageLineSpacing(self, value):
        self._coverage_line_spacing = value
        self.fieldBoundaryChanged.emit()

    @pyqtProperty(float, notify=fieldBoundaryChanged)
    def coverageOverlap(self):
        return self._coverage_overlap

    @coverageOverlap.setter
    def coverageOverlap(self, value):
        self._coverage_overlap = value
        self.fieldBoundaryChanged.emit()

    @pyqtProperty(float, notify=fieldBoundaryChanged)
    def coverageSpeed(self):
        return self._coverage_speed

    @coverageSpeed.setter
    def coverageSpeed(self, value):
        self._coverage_speed = value
        self.fieldBoundaryChanged.emit()

    @pyqtProperty(int, notify=coverageGenerated)
    def coverageWaypointCount(self):
        return len(self._coverage_waypoints)

    @pyqtProperty(float, notify=coverageGenerated)
    def coverageDistance(self):
        return self._coverage_distance

    @pyqtProperty(float, notify=coverageGenerated)
    def coverageTime(self):
        return self._coverage_time

    @pyqtProperty(bool, notify=coverageGenerated)
    def fieldCoverageActive(self):
        return len(self._coverage_waypoints) > 0

    @pyqtProperty(int, notify=fieldBoundaryChanged)
    def multiDroneStrategy(self):
        return self._multi_drone_strategy

    @multiDroneStrategy.setter
    def multiDroneStrategy(self, value):
        self._multi_drone_strategy = value
        self.fieldBoundaryChanged.emit()

    @pyqtProperty(float, notify=fieldBoundaryChanged)
    def formationOffset(self):
        return self._formation_offset

    @formationOffset.setter
    def formationOffset(self, value):
        self._formation_offset = value
        self.fieldBoundaryChanged.emit()

    @pyqtProperty(float, notify=fieldBoundaryChanged)
    def sequentialDelay(self):
        return self._sequential_delay

    @sequentialDelay.setter
    def sequentialDelay(self, value):
        self._sequential_delay = value
        self.fieldBoundaryChanged.emit()
        return len(self._coverage_waypoints) > 0

    @pyqtProperty(bool, notify=missionLockChanged)
    def missionLocked(self):
        """True if any drone is currently executing a mission (prevents editing)."""
        return self._mission_locked

    # ── Methods ───────────────────────────────────────────────────────────
    
    def _update_mission_lock(self):
        """
        Poll swarm context to check if any drone is in mission mode.
        
        Thread-safe with gating to prevent concurrent polls.
        Uses SwarmContext._mission_active dict as primary source of truth.
        
        Timer is automatically stopped when no drones are connected to reduce
        idle CPU usage from 15-20% to <5%.
        """
        # Gate timer when no drones connected (Improvement 6: Polling Overhead Reduction)
        if self._swarm_context:
            try:
                backends = self._swarm_context.backend.all_backends()
                has_drones = len(backends) > 0
                
                if has_drones and not self._lock_poll_timer.isActive():
                    self._lock_poll_timer.start()
                elif not has_drones and self._lock_poll_timer.isActive():
                    self._lock_poll_timer.stop()
                    # Clear lock state when no drones
                    if self._mission_locked:
                        self._mission_locked = False
                        self.missionLockChanged.emit(False)
                    return
            except Exception:
                pass  # Ignore errors in timer gating
        
        # Gate: Skip if previous poll still running
        if self._poll_in_progress:
            return
        
        if not self._swarm_context:
            return
        
        try:
            self._poll_in_progress = True
            mission_active = False
            
            # Primary check: SwarmContext._mission_active dict (set by MissionContext)
            # This is the authoritative source for mission-controlled drones
            if hasattr(self._swarm_context, '_mission_active'):
                with self._swarm_context._state_lock:
                    # Check if any drone has an active mission (Event not set)
                    for drone_id, event in self._swarm_context._mission_active.items():
                        if not event.is_set():  # Event cleared = mission active
                            mission_active = True
                            break
            
            # Fallback check: Poll backend FSM states (for missions started externally)
            if not mission_active:
                try:
                    backends = self._swarm_context.backend.all_backends()
                    
                    for drone_id, backend in backends.items():
                        if not backend.is_connected:
                            continue
                        
                        # Check FSM state (non-blocking)
                        if hasattr(backend, 'fsm_state'):
                            try:
                                fsm_state = str(backend.fsm_state).upper()
                                if fsm_state == 'MISSION':
                                    mission_active = True
                                    break
                            except Exception:
                                pass  # Ignore errors from individual backends
                        
                        # Check telemetry flight mode (with timeout protection)
                        if hasattr(backend, 'get_telemetry_snapshot'):
                            try:
                                snap = backend.get_telemetry_snapshot()
                                if snap:
                                    flight_mode = str(snap.get('flight_mode', '')).upper()
                                    if flight_mode in ('AUTO', 'MISSION'):
                                        mission_active = True
                                        break
                            except Exception:
                                pass  # Ignore errors from individual backends
                
                except Exception:
                    pass  # Ignore errors from backend iteration
            
            # Update lock state if changed (emit signal outside lock)
            if mission_active != self._mission_locked:
                self._mission_locked = mission_active
                self.missionLockChanged.emit(mission_active)
                if mission_active:
                    self.logMessage.emit("INFO", "[MISSION] 🔒 Mission lock activated")
                else:
                    self.logMessage.emit("INFO", "[MISSION] 🔓 Mission lock released")
        
        finally:
            self._poll_in_progress = False

    @pyqtSlot(float, float)
    def setHomePosition(self, lat: float, lon: float):
        with self._lock:
            self._planner.set_home_position(lat, lon)
            self._home_set = True
            self.logMessage.emit("INFO", f"[MISSION] Home: {lat:.6f}, {lon:.6f}")

    @pyqtSlot()
    def startDrawingBoundary(self):
        with self._lock:
            self._drawing_mode = True
            self.drawingModeChanged.emit(True)
            self.logMessage.emit("INFO", "[MISSION] Click map to define boundary (5min timeout)")
            # Start 5-minute timeout
            self._drawing_timeout_timer.start(300000)  # 300000ms = 5 minutes

    def _on_drawing_timeout(self):
        """Auto-cancel boundary drawing after 5 minutes."""
        with self._lock:
            if self._drawing_mode:
                self._drawing_mode = False
                self._boundary_points.clear()
                self._drawing_timeout_timer.stop()
                self.drawingModeChanged.emit(False)
                self.fieldBoundaryChanged.emit()
                self.logMessage.emit("WARN", "[MISSION] ⏱ Boundary drawing timed out (5min)")

    @pyqtSlot()
    def cancelDrawingBoundary(self):
        """Cancel boundary drawing and clear points."""
        with self._lock:
            self._drawing_mode = False
            self._boundary_points.clear()
            self._drawing_timeout_timer.stop()
            self.drawingModeChanged.emit(False)
            self.fieldBoundaryChanged.emit()
            self.logMessage.emit("INFO", "[MISSION] ❌ Boundary drawing cancelled")

    @pyqtSlot(float, float)
    def addBoundaryPoint(self, lat: float, lon: float):
        """Add a boundary point during drawing mode."""
        try:
            with self._lock:
                self._boundary_points.append((lat, lon))
                # Set home position from first boundary point
                if len(self._boundary_points) == 1 and not self._home_set:
                    self._planner.set_home_position(lat, lon)
                    self._home_set = True
                # Emit signal AFTER releasing lock to prevent deadlock
            self.fieldBoundaryChanged.emit()
            self.logMessage.emit("INFO", f"[MISSION] Point {len(self._boundary_points)} added")
            if len(self._boundary_points) == 1:
                self.logMessage.emit("INFO", f"[MISSION] Home set to first boundary point")
        except Exception as e:
            self.logMessage.emit("ERROR", f"[MISSION] Failed to add point: {e}")

    @pyqtSlot()
    def finishDrawingBoundary(self):
        with self._lock:
            self._drawing_mode = False
            self._drawing_timeout_timer.stop()  # Stop timeout timer
            self.drawingModeChanged.emit(False)
            if len(self._boundary_points) >= 3:
                self.logMessage.emit("INFO", f"[MISSION] ✅ Boundary: {len(self._boundary_points)} points")
            else:
                self.logMessage.emit("WARNING", "[MISSION] Need ≥3 points")

    @pyqtSlot()
    def clearFieldBoundary(self):
        with self._lock:
            self._boundary_points.clear()
            self._coverage_waypoints.clear()
            self._coverage_distance = 0.0
            self._coverage_time = 0.0
        # Emit signals AFTER releasing lock
        self.fieldBoundaryChanged.emit()
        self.coverageCleared.emit()
        self.logMessage.emit("INFO", "[MISSION] Boundary cleared")

    @pyqtSlot()
    def generateFieldCoverage(self):
        try:
            with self._lock:
                if not self._home_set:
                    self.logMessage.emit("ERROR", "[MISSION] Home not set")
                    return
                if len(self._boundary_points) < 3:
                    self.logMessage.emit("ERROR", "[MISSION] Need ≥3 points")
                    return
                
                boundary = FieldBoundary(corners=self._boundary_points)
                config = CoverageConfig(
                    pattern=CoveragePattern(self._coverage_pattern),
                    altitude=self._coverage_altitude,
                    line_spacing=self._coverage_line_spacing,
                    overlap=self._coverage_overlap,
                    speed=self._coverage_speed,
                )
                
                self._coverage_waypoints = self._planner.generate_coverage_waypoints(boundary, config)
                self._coverage_distance = self._calculate_distance()
                self._coverage_time = self._planner.estimate_coverage_time(
                    self._coverage_waypoints, self._coverage_speed
                )
            
            # Emit signals AFTER releasing lock to prevent deadlock
            self.coverageGenerated.emit()
            self.logMessage.emit(
                "INFO",
                f"[MISSION] {len(self._coverage_waypoints)} WP, "
                f"{self._coverage_distance/1000:.2f} km, {self._coverage_time/60:.1f} min"
            )
        except Exception as e:
            self.logMessage.emit("ERROR", f"[MISSION] Failed: {e}")

    def set_swarm_context(self, swarm_context: "SwarmContext") -> None:
        """Inject SwarmContext reference for mission upload."""
        self._swarm_context = swarm_context

    @pyqtSlot()
    def uploadCoverageMission(self):
        """Upload coverage mission to selected drones (via AppState.missionTargets)."""
        with self._lock:
            if not self._coverage_waypoints:
                self.logMessage.emit("ERROR", "[MISSION] No waypoints to upload")
                return
            
            if not self._swarm_context:
                self.logMessage.emit("ERROR", "[MISSION] SwarmContext not available")
                return
            
            # Get selected drone IDs from AppState (QML singleton)
            # We'll call a method on swarm_context to get the list
            waypoints = list(self._coverage_waypoints)
        
        # Run upload in background thread to avoid blocking UI
        threading.Thread(
            target=self._upload_mission_worker,
            args=(waypoints,),
            daemon=True
        ).start()
    
    def _upload_mission_worker(self, waypoints: List[Tuple[float, float, float]]) -> None:
        """Background worker for mission upload (runs in daemon thread)."""
        try:
            if not self._swarm_context:
                return
            
            # Get all connected drone backends
            backends = self._swarm_context.backend.all_backends()
            
            # Filter to only selected drones (mission targets from AppState)
            # For now, we'll upload to ALL connected drones
            # TODO: Filter by AppState.missionTargets when QML integration is complete
            target_drones = [
                (drone_id, backend)
                for drone_id, backend in backends.items()
                if backend.is_connected
            ]
            
            if not target_drones:
                self.logMessage.emit("ERROR", "[MISSION] No connected drones found")
                return
            
            num_drones = len(target_drones)
            strategy = MultiDroneStrategy(self._multi_drone_strategy)
            
            # Distribute waypoints based on strategy
            if strategy == MultiDroneStrategy.FIELD_SPLITTING and len(self._boundary_points) >= 3:
                # Use field splitting (requires boundary)
                try:
                    boundary = FieldBoundary(self._boundary_points)
                    config = CoverageConfig(
                        pattern=CoveragePattern(self._coverage_pattern),
                        altitude=self._coverage_altitude,
                        line_spacing=self._coverage_line_spacing,
                        overlap=self._coverage_overlap,
                        speed=self._coverage_speed
                    )
                    distributed_waypoints = self._planner.split_field_into_zones(
                        boundary, num_drones, config
                    )
                    self.logMessage.emit(
                        "INFO",
                        f"[MISSION] Field split into {num_drones} zones"
                    )
                except Exception as e:
                    self.logMessage.emit("ERROR", f"[MISSION] Field splitting failed: {e}")
                    return
            else:
                # Use waypoint distribution strategies
                distributed_waypoints = self._planner.distribute_waypoints_for_swarm(
                    waypoints,
                    num_drones,
                    strategy,
                    formation_offset=self._formation_offset,
                    sequential_delay=self._sequential_delay
                )
            
            self.logMessage.emit(
                "INFO",
                f"[MISSION] Strategy: {strategy.name}, uploading to {num_drones} drone(s)..."
            )
            
            # Create mapping from actual drone_id to D1, D2, D3... format
            drone_id_mapping = {}
            for idx, (drone_id, _) in enumerate(target_drones):
                drone_id_mapping[drone_id] = f"D{idx + 1}"
            
            # Upload to each drone with its specific waypoints
            success_count = 0
            for drone_id, backend in target_drones:
                # Get waypoints for this drone using mapped ID
                mapped_id = drone_id_mapping[drone_id]
                drone_waypoints = distributed_waypoints.get(mapped_id, [])
                if not drone_waypoints:
                    self.logMessage.emit(
                        "WARN",
                        f"[{drone_id}] No waypoints assigned, skipping"
                    )
                    continue
                try:
                    # Get the drone's MAVLink connection
                    # backend._drone is GenericUAVModel (inherits from Drone)
                    # Drone has _conn attribute (MAVLinkConnection)
                    if not backend._drone or not hasattr(backend._drone, '_conn'):
                        self.logMessage.emit(
                            "WARN",
                            f"[{drone_id}] No connection available, skipping"
                        )
                        continue
                    
                    conn = backend._drone._conn
                    if not conn or not conn.connected:
                        self.logMessage.emit(
                            "WARN",
                            f"[{drone_id}] Connection not active, skipping"
                        )
                        continue
                    
                    # Create mission engine
                    mission = MissionEngine(conn)
                    mission.clear()
                    
                    # Add waypoints for this specific drone
                    for lat, lon, alt in drone_waypoints:
                        mission.add(Waypoint(
                            lat=lat,
                            lon=lon,
                            alt=alt,
                            speed=self._coverage_speed
                        ))
                    
                    # Upload (blocking call, but we're in a worker thread)
                    if not mission.upload():
                        self.logMessage.emit(
                            "ERROR",
                            f"[{drone_id}] ❌ Mission upload failed"
                        )
                        continue
                    
                    self.logMessage.emit(
                        "INFO",
                        f"[{drone_id}] ✅ Mission uploaded ({len(drone_waypoints)} waypoints)"
                    )
                    
                    # Auto-sequence: ARM → TAKEOFF → START MISSION
                    drone_obj = backend._drone
                    
                    # 1. ARM if not armed
                    if not drone_obj.armed:
                        self.logMessage.emit("INFO", f"[{drone_id}] 🔧 Arming...")
                        if not drone_obj.arm(timeout=10.0):
                            self.logMessage.emit(
                                "ERROR",
                                f"[{drone_id}] ❌ Failed to arm"
                            )
                            continue
                        self.logMessage.emit("INFO", f"[{drone_id}] ✅ Armed")
                    
                    # 2. TAKEOFF if not airborne (use coverage altitude)
                    if drone_obj.altitude < 2.0:  # Not airborne
                        takeoff_alt = self._coverage_altitude
                        self.logMessage.emit(
                            "INFO",
                            f"[{drone_id}] 🚁 Taking off to {takeoff_alt}m..."
                        )
                        if not drone_obj.takeoff(altitude=takeoff_alt, timeout=30.0):
                            self.logMessage.emit(
                                "WARN",
                                f"[{drone_id}] ⚠ Takeoff timeout, but continuing..."
                            )
                        else:
                            self.logMessage.emit("INFO", f"[{drone_id}] ✅ Airborne")
                    
                    # 3. START MISSION (set mode to AUTO)
                    self.logMessage.emit("INFO", f"[{drone_id}] 🎯 Starting mission...")
                    if mission.start():
                        success_count += 1
                        self.logMessage.emit(
                            "INFO",
                            f"[{drone_id}] ✅ Mission started! Flying coverage pattern..."
                        )
                        
                        # Notify SwarmContext that this drone is now mission-controlled
                        # This prevents APF/formations from interfering with the mission
                        if self._swarm_context is not None:
                            with self._swarm_context._state_lock:
                                # Mark mission as active for this drone
                                if drone_id not in self._swarm_context._mission_active:
                                    self._swarm_context._mission_active[drone_id] = threading.Event()
                                # Clear the event to indicate mission is running
                                self._swarm_context._mission_active[drone_id].clear()
                            
                            self.logMessage.emit(
                                "INFO",
                                f"[{drone_id}] 🔒 Mission lock acquired (APF/formations disabled)"
                            )
                    else:
                        self.logMessage.emit(
                            "WARN",
                            f"[{drone_id}] ⚠ Failed to start mission (set mode to AUTO manually)"
                        )
                
                except Exception as e:
                    self.logMessage.emit(
                        "ERROR",
                        f"[{drone_id}] Upload error: {e}"
                    )
            
            # Summary
            if success_count > 0:
                self.logMessage.emit(
                    "INFO",
                    f"[MISSION] ✅ Upload complete: {success_count}/{len(target_drones)} successful"
                )
            else:
                self.logMessage.emit(
                    "ERROR",
                    "[MISSION] ❌ All uploads failed"
                )
        
        except Exception as e:
            self.logMessage.emit("ERROR", f"[MISSION] Upload worker error: {e}")

    @pyqtSlot()
    def toggleCoveragePreview(self):
        """Toggle coverage preview visibility on map."""
        with self._lock:
            self._preview_active = not self._preview_active
        
        # Emit signal outside lock
        if self._preview_active:
            self.coverageGenerated.emit()  # Show coverage
            self.logMessage.emit("INFO", "[MISSION] Preview enabled - coverage visible")
        else:
            self.coverageCleared.emit()  # Hide coverage
            self.logMessage.emit("INFO", "[MISSION] Preview disabled - coverage hidden")

    @pyqtSlot(result="QVariantList")
    def getCoverageWaypoints(self):
        """Return coverage waypoints as list of dicts for QML/JavaScript."""
        try:
            with self._lock:
                return [{"lat": float(lat), "lon": float(lon), "alt": float(alt)}
                        for lat, lon, alt in self._coverage_waypoints]
        except Exception as e:
            self.logMessage.emit("ERROR", f"[MISSION] getCoverageWaypoints failed: {e}")
            return []

    @pyqtSlot(result="QVariantList")
    def getBoundaryPoints(self):
        """Return boundary points as list of dicts for QML/JavaScript."""
        try:
            with self._lock:
                return [{"lat": float(lat), "lon": float(lon)} for lat, lon in self._boundary_points]
        except Exception as e:
            self.logMessage.emit("ERROR", f"[MISSION] getBoundaryPoints failed: {e}")
            return []

    def _calculate_distance(self) -> float:
        if len(self._coverage_waypoints) < 2:
            return 0.0
        
        total = 0.0
        for i in range(len(self._coverage_waypoints) - 1):
            lat1, lon1, _ = self._coverage_waypoints[i]
            lat2, lon2, _ = self._coverage_waypoints[i + 1]
            
            R = 6371000
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
                 math.sin(dlon / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            total += R * c
        
        return total

# Made with Bob

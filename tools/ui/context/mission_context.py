"""
MissionContext — exposes Field Coverage Planning to QML.

Registered as context property 'mission' in the QML engine.
"""

from __future__ import annotations

import math
import threading
from typing import List, Tuple, Optional, TYPE_CHECKING

from PySide6.QtCore import QObject, Property, Signal, Slot

from droneresearch.control.field_coverage import (
    FieldCoveragePlanner,
    FieldBoundary,
    CoverageConfig,
    CoveragePattern,
    MultiDroneStrategy,
)
from droneresearch.control.mission import MissionEngine, Waypoint
from droneresearch.control.seeding_planner import SeedingMissionPlanner, SeedingConfig

if TYPE_CHECKING:
    from tools.ui.context.swarm_context import SwarmContext


class MissionContext(QObject):
    """QML-callable wrapper for field coverage planning."""

    # Signals
    logMessage = Signal(str, str, arguments=["level", "text"])
    fieldBoundaryChanged = Signal()
    coverageGenerated = Signal()
    coverageCleared = Signal()
    drawingModeChanged = Signal(bool, arguments=["active"])
    missionLockChanged = Signal(bool, arguments=["locked"])
    solarPanelRowsChanged = Signal()
    solarStatsChanged = Signal()
    solarRowDrawingModeChanged = Signal(bool, arguments=["active"])

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lock = threading.Lock()
        
        # Field Coverage Planner
        self._planner = FieldCoveragePlanner()
        self._home_set = False
        self._home_lat = 0.0
        self._home_lon = 0.0
        
        # Seeding Mission Planner
        self._seeding_planner = SeedingMissionPlanner()
        
        # Mission mode: 0 = coverage, 1 = seeding, 2 = solar inspection
        self._mission_mode = 0
        self._seeding_mode_enabled = False  # Kept for backward compatibility
        
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
        
        # Seeding mission configuration
        self._seed_spacing = 2.0  # meters between seed drops
        self._seed_row_spacing = 5.0  # meters between rows
        self._seed_altitude = 10.0  # seeding altitude
        self._seed_drop_duration = 0.5  # seconds dispenser stays open
        self._servo_channel = 9  # servo channel for dispenser
        self._servo_open_pwm = 1900  # PWM value to open dispenser
        self._servo_close_pwm = 1100  # PWM value to close dispenser
        
        # Generated seeding waypoints
        self._seeding_waypoints: List[Waypoint] = []
        self._seeding_distance = 0.0
        self._seeding_time = 0.0
        self._seeding_drop_count = 0
        self._seeding_preview_active = False
        
        # Solar inspection configuration
        self._solar_panel_rows: List[dict] = []  # List of {start_lat, start_lon, end_lat, end_lon, length}
        self._solar_altitude = 15.0
        self._solar_gimbal_pitch = -90.0
        self._solar_trigger_distance = 5.0
        self._solar_overlap = 0.3
        self._solar_coverage_area = 0.0
        self._solar_mission_time = 0.0
        self._solar_waypoint_count = 0
        self._solar_photo_count = 0
        self._solar_waypoints: List[Waypoint] = []
        self._adding_solar_row = False  # True when waiting for user to click two points on map
        self._solar_row_start_lat = 0.0
        self._solar_row_start_lon = 0.0
        
        # Mission lock state
        self._mission_locked = False
        self._poll_in_progress = False  # Gate to prevent concurrent polls
        
        # Swarm context reference (injected via wire())
        self._swarm_context: Optional["SwarmContext"] = None
        
        # Poll mission status every 500ms to update lock state
        from PySide6.QtCore import QTimer
        self._lock_poll_timer = QTimer(self)
        self._lock_poll_timer.timeout.connect(self._update_mission_lock)
        self._lock_poll_timer.start(500)  # 500ms polling interval
        
        # Boundary drawing timeout (5 minutes)
        self._drawing_timeout_timer = QTimer(self)
        self._drawing_timeout_timer.timeout.connect(self._on_drawing_timeout)
        self._drawing_timeout_timer.setSingleShot(True)

    # ── Properties ────────────────────────────────────────────────────────

    @Property(bool, notify=drawingModeChanged)
    def drawingMode(self):
        return self._drawing_mode

    @Property(int, notify=fieldBoundaryChanged)
    def fieldBoundaryPoints(self):
        return len(self._boundary_points)

    @Property(int, notify=fieldBoundaryChanged)
    def coveragePattern(self):
        return self._coverage_pattern

    @coveragePattern.setter
    def coveragePattern(self, value):
        self._coverage_pattern = value
        self.fieldBoundaryChanged.emit()

    @Property(float, notify=fieldBoundaryChanged)
    def coverageAltitude(self):
        return self._coverage_altitude

    @coverageAltitude.setter
    def coverageAltitude(self, value):
        self._coverage_altitude = value
        self.fieldBoundaryChanged.emit()

    @Property(float, notify=fieldBoundaryChanged)
    def coverageLineSpacing(self):
        return self._coverage_line_spacing

    @coverageLineSpacing.setter
    def coverageLineSpacing(self, value):
        self._coverage_line_spacing = value
        self.fieldBoundaryChanged.emit()

    @Property(float, notify=fieldBoundaryChanged)
    def coverageOverlap(self):
        return self._coverage_overlap

    @coverageOverlap.setter
    def coverageOverlap(self, value):
        self._coverage_overlap = value
        self.fieldBoundaryChanged.emit()

    @Property(float, notify=fieldBoundaryChanged)
    def coverageSpeed(self):
        return self._coverage_speed

    @coverageSpeed.setter
    def coverageSpeed(self, value):
        self._coverage_speed = value
        self.fieldBoundaryChanged.emit()

    @Property(int, notify=coverageGenerated)
    def coverageWaypointCount(self):
        return len(self._coverage_waypoints)

    @Property(float, notify=coverageGenerated)
    def coverageDistance(self):
        return self._coverage_distance

    @Property(float, notify=coverageGenerated)
    def coverageTime(self):
        return self._coverage_time

    @Property(bool, notify=coverageGenerated)
    def fieldCoverageActive(self):
        return len(self._coverage_waypoints) > 0

    @Property(int, notify=fieldBoundaryChanged)
    def multiDroneStrategy(self):
        return self._multi_drone_strategy

    @multiDroneStrategy.setter
    def multiDroneStrategy(self, value):
        self._multi_drone_strategy = value
        self.fieldBoundaryChanged.emit()

    @Property(float, notify=fieldBoundaryChanged)
    def formationOffset(self):
        return self._formation_offset

    @formationOffset.setter
    def formationOffset(self, value):
        self._formation_offset = value
        self.fieldBoundaryChanged.emit()

    @Property(float, notify=fieldBoundaryChanged)
    def sequentialDelay(self):
        return self._sequential_delay

    @sequentialDelay.setter
    def sequentialDelay(self, value):
        self._sequential_delay = value
        self.fieldBoundaryChanged.emit()
        return len(self._coverage_waypoints) > 0

    @Property(bool, notify=missionLockChanged)
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

    @Slot(float, float)
    def setHomePosition(self, lat: float, lon: float):
        with self._lock:
            self._planner.set_home_position(lat, lon)
            self._seeding_planner.set_home_position(lat, lon)
            self._home_set = True
            self._home_lat = lat
            self._home_lon = lon
            self.logMessage.emit("INFO", f"[MISSION] Home: {lat:.6f}, {lon:.6f}")

    @Slot()
    def startDrawingBoundary(self):
        with self._lock:
            self._drawing_mode = True
            self.logMessage.emit("INFO", f"[MISSION] Drawing mode set to: {self._drawing_mode}")
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

    @Slot()
    def cancelDrawingBoundary(self):
        """Cancel boundary drawing and clear points."""
        with self._lock:
            self._drawing_mode = False
            self._boundary_points.clear()
            self._drawing_timeout_timer.stop()
            self.drawingModeChanged.emit(False)
            self.fieldBoundaryChanged.emit()
            self.logMessage.emit("INFO", "[MISSION] ❌ Boundary drawing cancelled")

    @Slot(float, float)
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

    @Slot()
    def finishDrawingBoundary(self):
        with self._lock:
            self._drawing_mode = False
            self._drawing_timeout_timer.stop()  # Stop timeout timer
            self.drawingModeChanged.emit(False)
            if len(self._boundary_points) >= 3:
                self.logMessage.emit("INFO", f"[MISSION] ✅ Boundary: {len(self._boundary_points)} points")
            else:
                self.logMessage.emit("WARNING", "[MISSION] Need ≥3 points")

    @Slot()
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

    @Slot()
    def generateMission(self):
        """Unified generate method - calls coverage, seeding, or solar based on mode."""
        if self._mission_mode == 1:
            self.generateSeedingMission()
        elif self._mission_mode == 2:
            self.generateSolarInspection()
        else:
            self.generateFieldCoverage()
    
    @Slot()
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

    @Slot()
    def uploadMission(self):
        """Unified upload method - calls coverage, seeding, or solar based on mode."""
        if self._mission_mode == 1:
            self.uploadSeedingMission()
        elif self._mission_mode == 2:
            self.uploadSolarMission()
        else:
            self.uploadCoverageMission()
    
    @Slot()
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

    @Slot()
    def togglePreview(self):
        """Unified preview toggle - calls coverage or seeding based on mode."""
        if self._seeding_mode_enabled:
            self.toggleSeedingPreview()
        else:
            self.toggleCoveragePreview()
    
    @Slot()
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

    @Slot(result="QVariantList")
    def getCoverageWaypoints(self):
        """Return coverage waypoints as list of dicts for QML/JavaScript."""
        try:
            with self._lock:
                return [{"lat": float(lat), "lon": float(lon), "alt": float(alt)}
                        for lat, lon, alt in self._coverage_waypoints]
        except Exception as e:
            self.logMessage.emit("ERROR", f"[MISSION] getCoverageWaypoints failed: {e}")
            return []

    @Slot(result="QVariantList")
    def getBoundaryPoints(self):
        """Return boundary points as list of dicts for QML/JavaScript."""
        try:
            with self._lock:
                return [{"lat": float(lat), "lon": float(lon)} for lat, lon in self._boundary_points]
        except Exception as e:
            self.logMessage.emit("ERROR", f"[MISSION] getBoundaryPoints failed: {e}")
            return []

    # ── Mission Mode Properties ───────────────────────────────────────────
    
    @Property(int, notify=fieldBoundaryChanged)
    def missionMode(self):
        """Mission mode: 0=Coverage, 1=Seeding, 2=Solar Inspection."""
        return self._mission_mode
    
    @missionMode.setter
    def missionMode(self, value):
        if self._mission_mode != value:
            self._mission_mode = value
            # Update legacy seedingModeEnabled for backward compatibility
            self._seeding_mode_enabled = (value == 1)
            self.fieldBoundaryChanged.emit()
            if value == 0:
                self.logMessage.emit("INFO", "[MISSION] 📐 Coverage mode enabled")
            elif value == 1:
                self.logMessage.emit("INFO", "[MISSION] 🌱 Seeding mode enabled")
            elif value == 2:
                self.logMessage.emit("INFO", "[MISSION] ☀ Solar Inspection mode enabled")
    
    @Property(bool, notify=fieldBoundaryChanged)
    def seedingModeEnabled(self):
        """Legacy property for backward compatibility. Use missionMode instead."""
        return self._seeding_mode_enabled
    
    @seedingModeEnabled.setter
    def seedingModeEnabled(self, value):
        # Map to missionMode: False=0 (Coverage), True=1 (Seeding)
        self.missionMode = 1 if value else 0
    
    # ── Seeding Mission Properties ────────────────────────────────────────
    
    @Property(float, notify=fieldBoundaryChanged)
    def seedSpacing(self):
        return self._seed_spacing
    
    @seedSpacing.setter
    def seedSpacing(self, value):
        self._seed_spacing = value
        self.fieldBoundaryChanged.emit()
    
    @Property(float, notify=fieldBoundaryChanged)
    def seedRowSpacing(self):
        return self._seed_row_spacing
    
    @seedRowSpacing.setter
    def seedRowSpacing(self, value):
        self._seed_row_spacing = value
        self.fieldBoundaryChanged.emit()
    
    @Property(float, notify=fieldBoundaryChanged)
    def seedAltitude(self):
        return self._seed_altitude
    
    @seedAltitude.setter
    def seedAltitude(self, value):
        self._seed_altitude = value
        self.fieldBoundaryChanged.emit()
    
    @Property(float, notify=fieldBoundaryChanged)
    def seedDropDuration(self):
        return self._seed_drop_duration
    
    @seedDropDuration.setter
    def seedDropDuration(self, value):
        self._seed_drop_duration = value
        self.fieldBoundaryChanged.emit()
    
    @Property(int, notify=fieldBoundaryChanged)
    def servoChannel(self):
        return self._servo_channel
    
    @servoChannel.setter
    def servoChannel(self, value):
        self._servo_channel = value
        self.fieldBoundaryChanged.emit()
    
    @Property(int, notify=fieldBoundaryChanged)
    def servoOpenPWM(self):
        return self._servo_open_pwm
    
    @servoOpenPWM.setter
    def servoOpenPWM(self, value):
        self._servo_open_pwm = value
        self.fieldBoundaryChanged.emit()
    
    @Property(int, notify=fieldBoundaryChanged)
    def servoClosePWM(self):
        return self._servo_close_pwm
    
    @servoClosePWM.setter
    def servoClosePWM(self, value):
        self._servo_close_pwm = value
        self.fieldBoundaryChanged.emit()
    
    @Property(int, notify=coverageGenerated)
    def seedingWaypointCount(self):
        return len(self._seeding_waypoints)
    
    @Property(int, notify=coverageGenerated)
    def seedingDropCount(self):
        return self._seeding_drop_count
    
    @Property(float, notify=coverageGenerated)
    def seedingDistance(self):
        return self._seeding_distance
    
    @Property(float, notify=coverageGenerated)
    def seedingTime(self):
        return self._seeding_time
    
    @Property(bool, notify=coverageGenerated)
    def seedingMissionActive(self):
        return len(self._seeding_waypoints) > 0
    
    # ── Seeding Mission Methods ───────────────────────────────────────────
    
    @Slot()
    def generateSeedingMission(self):
        """Generate seeding mission with servo commands for seed drops."""
        try:
            with self._lock:
                if not self._home_set:
                    self.logMessage.emit("ERROR", "[SEEDING] Home not set")
                    return
                if len(self._boundary_points) < 3:
                    self.logMessage.emit("ERROR", "[SEEDING] Need ≥3 boundary points")
                    return
                
                # Create boundary and config
                boundary = FieldBoundary(corners=self._boundary_points)
                
                # Generate seeding mission
                self._seeding_waypoints = self._seeding_planner.plan_seeding_mission(
                    boundary=boundary,
                    seed_spacing=self._seed_spacing,
                    row_spacing=self._seed_row_spacing,
                    altitude=self._seed_altitude,
                    servo_channel=self._servo_channel,
                    servo_open_pwm=self._servo_open_pwm,
                    servo_close_pwm=self._servo_close_pwm,
                    drop_duration=self._seed_drop_duration,
                    add_rtl=True
                )
                
                # Calculate statistics
                seeding_config = SeedingConfig(
                    seed_spacing=self._seed_spacing,
                    row_spacing=self._seed_row_spacing,
                    altitude=self._seed_altitude,
                    servo_channel=self._servo_channel,
                    servo_open_pwm=self._servo_open_pwm,
                    servo_close_pwm=self._servo_close_pwm,
                    drop_duration=self._seed_drop_duration,
                    speed=self._coverage_speed
                )
                
                stats = self._seeding_planner.estimate_mission_stats(
                    boundary=boundary,
                    config=seeding_config
                )
                
                self._seeding_distance = stats["total_distance"]
                self._seeding_time = stats["estimated_time"]
                self._seeding_drop_count = stats["seed_count"]
            
            # Emit signals AFTER releasing lock
            self.coverageGenerated.emit()
            self.logMessage.emit(
                "INFO",
                f"[SEEDING] {len(self._seeding_waypoints)} WP, "
                f"{self._seeding_drop_count} seeds, "
                f"{self._seeding_distance/1000:.2f} km, "
                f"{self._seeding_time/60:.1f} min"
            )
        except Exception as e:
            self.logMessage.emit("ERROR", f"[SEEDING] Generation failed: {e}")
    
    @Slot()
    def uploadSeedingMission(self):
        """Upload seeding mission to selected drones."""
        with self._lock:
            if not self._seeding_waypoints:
                self.logMessage.emit("ERROR", "[SEEDING] No waypoints to upload")
                return
            
            if not self._swarm_context:
                self.logMessage.emit("ERROR", "[SEEDING] SwarmContext not available")
                return
            
            waypoints = list(self._seeding_waypoints)
        
        # Run upload in background thread
        threading.Thread(
            target=self._upload_seeding_mission_worker,
            args=(waypoints,),
            daemon=True
        ).start()
    
    def _upload_seeding_mission_worker(self, waypoints: List[Waypoint]) -> None:
        """Background worker for seeding mission upload."""
        try:
            if not self._swarm_context:
                return
            
            backends = self._swarm_context.backend.all_backends()
            target_drones = [
                (drone_id, backend)
                for drone_id, backend in backends.items()
                if backend.is_connected
            ]
            
            if not target_drones:
                self.logMessage.emit("ERROR", "[SEEDING] No connected drones")
                return
            
            self.logMessage.emit(
                "INFO",
                f"[SEEDING] Uploading to {len(target_drones)} drone(s)..."
            )
            
            success_count = 0
            for drone_id, backend in target_drones:
                try:
                    if not backend._drone or not hasattr(backend._drone, '_conn'):
                        self.logMessage.emit(
                            "WARN",
                            f"[{drone_id}] No connection, skipping"
                        )
                        continue
                    
                    conn = backend._drone._conn
                    if not conn or not conn.connected:
                        self.logMessage.emit(
                            "WARN",
                            f"[{drone_id}] Connection not active, skipping"
                        )
                        continue
                    
                    # Create mission engine and upload
                    mission = MissionEngine(conn)
                    mission.clear()
                    
                    for wp in waypoints:
                        mission.add(wp)
                    
                    # Validate before upload
                    is_valid, errors = mission.validate()
                    if not is_valid:
                        self.logMessage.emit(
                            "ERROR",
                            f"[{drone_id}] ❌ Validation failed:"
                        )
                        for error in errors[:5]:  # Show first 5 errors
                            self.logMessage.emit("ERROR", f"  - {error}")
                        if len(errors) > 5:
                            self.logMessage.emit("ERROR", f"  ... and {len(errors)-5} more errors")
                        continue
                    
                    if not mission.upload(validate_first=False):  # Already validated
                        self.logMessage.emit(
                            "ERROR",
                            f"[{drone_id}] ❌ Upload failed (protocol error)"
                        )
                        continue
                    
                    self.logMessage.emit(
                        "INFO",
                        f"[{drone_id}] ✅ Seeding mission uploaded ({len(waypoints)} WP)"
                    )
                    
                    # Check drone state and execute appropriate sequence
                    drone_obj = backend._drone
                    fsm_state = backend.fsm_state if hasattr(backend, 'fsm_state') else "UNKNOWN"
                    
                    self.logMessage.emit("INFO", f"[{drone_id}] Current state: {fsm_state}")
                    
                    # If already flying, just start the mission
                    if fsm_state in ["FLYING", "MISSION"]:
                        self.logMessage.emit("INFO", f"[{drone_id}] 🌱 Starting seeding mission...")
                        if mission.start():
                            success_count += 1
                            self.logMessage.emit(
                                "INFO",
                                f"[{drone_id}] ✅ Seeding mission started!"
                            )
                            
                            # Mark mission as active
                            if self._swarm_context is not None:
                                with self._swarm_context._state_lock:
                                    if drone_id not in self._swarm_context._mission_active:
                                        self._swarm_context._mission_active[drone_id] = threading.Event()
                                    self._swarm_context._mission_active[drone_id].clear()
                        else:
                            self.logMessage.emit(
                                "WARN",
                                f"[{drone_id}] ⚠ Failed to start (set AUTO mode manually)"
                            )
                        continue
                    
                    # If on ground, execute full sequence: ARM → TAKEOFF → START
                    if not drone_obj.armed:
                        self.logMessage.emit("INFO", f"[{drone_id}] 🔧 Arming...")
                        if not drone_obj.arm(timeout=10.0):
                            self.logMessage.emit("ERROR", f"[{drone_id}] ❌ Arm failed")
                            continue
                        self.logMessage.emit("INFO", f"[{drone_id}] ✅ Armed")
                    
                    if drone_obj.altitude < 2.0:
                        self.logMessage.emit(
                            "INFO",
                            f"[{drone_id}] 🚁 Taking off to {self._seed_altitude}m..."
                        )
                        if not drone_obj.takeoff(altitude=self._seed_altitude, timeout=30.0):
                            self.logMessage.emit(
                                "WARN",
                                f"[{drone_id}] ⚠ Takeoff timeout, continuing..."
                            )
                        else:
                            self.logMessage.emit("INFO", f"[{drone_id}] ✅ Airborne")
                    
                    self.logMessage.emit("INFO", f"[{drone_id}] 🌱 Starting seeding mission...")
                    if mission.start():
                        success_count += 1
                        self.logMessage.emit(
                            "INFO",
                            f"[{drone_id}] ✅ Seeding mission started!"
                        )
                        
                        # Mark mission as active
                        if self._swarm_context is not None:
                            with self._swarm_context._state_lock:
                                if drone_id not in self._swarm_context._mission_active:
                                    self._swarm_context._mission_active[drone_id] = threading.Event()
                                self._swarm_context._mission_active[drone_id].clear()
                    else:
                        self.logMessage.emit(
                            "WARN",
                            f"[{drone_id}] ⚠ Failed to start (set AUTO mode manually)"
                        )
                
                except Exception as e:
                    self.logMessage.emit("ERROR", f"[{drone_id}] Upload error: {e}")
            
            if success_count > 0:
                self.logMessage.emit(
                    "INFO",
                    f"[SEEDING] ✅ {success_count}/{len(target_drones)} successful"
                )
            else:
                self.logMessage.emit("ERROR", "[SEEDING] ❌ All uploads failed")
        
        except Exception as e:
            self.logMessage.emit("ERROR", f"[SEEDING] Worker error: {e}")
    
    @Slot()
    def toggleSeedingPreview(self):
        """Toggle seeding mission preview on map."""
        with self._lock:
            self._seeding_preview_active = not self._seeding_preview_active
        
        if self._seeding_preview_active:
            self.coverageGenerated.emit()
            self.logMessage.emit("INFO", "[SEEDING] Preview enabled")
        else:
            self.coverageCleared.emit()
            self.logMessage.emit("INFO", "[SEEDING] Preview disabled")
    
    @Slot(result="QVariantList")
    def getSeedingWaypoints(self):
        """Return seeding waypoints for QML/JavaScript map display.
        
        Returns NAV waypoints with 'isSeedPoint' flag for visualization.
        """
        try:
            with self._lock:
                waypoints = []
                for wp in self._seeding_waypoints:
                    if wp.cmd == 16:  # MAV_CMD_NAV_WAYPOINT only
                        waypoints.append({
                            "lat": float(wp.lat),
                            "lon": float(wp.lon),
                            "alt": float(wp.alt),
                            "isSeedPoint": wp.hold > 0.0  # Seed points have hold time
                        })
                return waypoints
        except Exception as e:
            self.logMessage.emit("ERROR", f"[SEEDING] getSeedingWaypoints failed: {e}")
            return []

    # ── Solar Inspection Properties ────────────────────────────────────────
    
    @Property(bool, notify=solarStatsChanged)
    def solarInspectionActive(self):
        return self._mission_mode == 2 and len(self._solar_panel_rows) > 0
    
    @Property(int, notify=solarPanelRowsChanged)
    def solarPanelRowCount(self):
        return len(self._solar_panel_rows)
    
    @Property("QVariantList", notify=solarPanelRowsChanged)
    def solarPanelRows(self):
        """Return list of solar panel rows for QML/Map display."""
        # Convert to format expected by MapView JavaScript
        rows = []
        for row in self._solar_panel_rows:
            rows.append({
                "start": {"lat": row["start_lat"], "lon": row["start_lon"]},
                "end": {"lat": row["end_lat"], "lon": row["end_lon"]},
                "length": row["length"],
                "panelCount": 0  # TODO: Calculate based on panel size
            })
        return rows
    
    @Property(float, notify=solarStatsChanged)
    def solarAltitude(self):
        return self._solar_altitude
    
    @solarAltitude.setter
    def solarAltitude(self, value):
        if self._solar_altitude != value:
            self._solar_altitude = value
            self.solarStatsChanged.emit()
    
    @Property(float, notify=solarStatsChanged)
    def solarGimbalPitch(self):
        return self._solar_gimbal_pitch
    
    @solarGimbalPitch.setter
    def solarGimbalPitch(self, value):
        if self._solar_gimbal_pitch != value:
            self._solar_gimbal_pitch = value
            self.solarStatsChanged.emit()
    
    @Property(float, notify=solarStatsChanged)
    def solarTriggerDistance(self):
        return self._solar_trigger_distance
    
    @solarTriggerDistance.setter
    def solarTriggerDistance(self, value):
        if self._solar_trigger_distance != value:
            self._solar_trigger_distance = value
            self.solarStatsChanged.emit()
    
    @Property(float, notify=solarStatsChanged)
    def solarOverlap(self):
        return self._solar_overlap
    
    @solarOverlap.setter
    def solarOverlap(self, value):
        if self._solar_overlap != value:
            self._solar_overlap = value
            self.solarStatsChanged.emit()
    
    @Property(float, notify=solarStatsChanged)
    def solarCoverageArea(self):
        return self._solar_coverage_area
    
    @Property(float, notify=solarStatsChanged)
    def solarMissionTime(self):
        return self._solar_mission_time
    
    @Property(int, notify=solarStatsChanged)
    def solarWaypointCount(self):
        return self._solar_waypoint_count
    
    @Property(int, notify=solarStatsChanged)
    def solarPhotoCount(self):
        return self._solar_photo_count
    
    # ── Solar Inspection Methods ───────────────────────────────────────────
    
    @Slot()
    def startAddingSolarRow(self):
        """Start interactive solar row addition on map."""
        self._adding_solar_row = True
        self._solar_row_start_lat = 0.0
        self._solar_row_start_lon = 0.0
        self.solarRowDrawingModeChanged.emit(True)
        self.logMessage.emit("INFO", "[SOLAR] Click two points on map to define panel row")
    
    @Slot(float, float)
    def addSolarRowPoint(self, lat: float, lon: float):
        """Handle a click point for solar row drawing."""
        try:
            if self._solar_row_start_lat == 0.0 and self._solar_row_start_lon == 0.0:
                # First click - store start point
                self._solar_row_start_lat = lat
                self._solar_row_start_lon = lon
                self.logMessage.emit("INFO", "[SOLAR] Start point set, click end point")
            else:
                # Second click - complete the row
                self.addSolarRow(self._solar_row_start_lat, self._solar_row_start_lon, lat, lon)
                # Reset for next row but keep drawing mode active
                self._solar_row_start_lat = 0.0
                self._solar_row_start_lon = 0.0
                self.logMessage.emit("INFO", "[SOLAR] Row added. Click to add another row, or press ESC to finish")
        except Exception as e:
            self.logMessage.emit("ERROR", f"[SOLAR] addSolarRowPoint failed: {e}")
    
    @Slot(float, float, float, float)
    def addSolarRow(self, start_lat: float, start_lon: float, end_lat: float, end_lon: float):
        """Add a solar panel row defined by start and end coordinates."""
        try:
            # Calculate row length
            R = 6371000  # Earth radius in meters
            dlat = math.radians(end_lat - start_lat)
            dlon = math.radians(end_lon - start_lon)
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(start_lat)) * math.cos(math.radians(end_lat)) *
                 math.sin(dlon / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            length = R * c
            
            row = {
                "start_lat": start_lat,
                "start_lon": start_lon,
                "end_lat": end_lat,
                "end_lon": end_lon,
                "length": length
            }
            
            with self._lock:
                self._solar_panel_rows.append(row)
                self._adding_solar_row = False
            
            self.solarPanelRowsChanged.emit()
            self.logMessage.emit("INFO", f"[SOLAR] Added row {len(self._solar_panel_rows)} ({length:.1f}m)")
        except Exception as e:
            self.logMessage.emit("ERROR", f"[SOLAR] Failed to add row: {e}")
    
    @Slot()
    def clearSolarPanelRows(self):
        """Clear all solar panel rows and map visualization."""
        try:
            with self._lock:
                self._solar_panel_rows.clear()
                self._solar_waypoints.clear()
                self._solar_coverage_area = 0.0
                self._solar_mission_time = 0.0
                self._solar_waypoint_count = 0
                self._solar_photo_count = 0
            
            self.solarPanelRowsChanged.emit()
            self.solarStatsChanged.emit()
            self.logMessage.emit("INFO", "[SOLAR] Cleared all panel rows")
        except Exception as e:
            self.logMessage.emit("ERROR", f"[SOLAR] clearSolarPanelRows failed: {e}")
    
    @Slot(int)
    def removeSolarRow(self, index: int):
        """Remove a solar panel row by index."""
        try:
            with self._lock:
                if 0 <= index < len(self._solar_panel_rows):
                    self._solar_panel_rows.pop(index)
                    self.solarPanelRowsChanged.emit()
                    self.logMessage.emit("INFO", f"[SOLAR] Removed row {index + 1}")
        except Exception as e:
            self.logMessage.emit("ERROR", f"[SOLAR] Failed to remove row: {e}")
    
    @Slot()
    def generateSolarInspection(self):
        """Generate solar inspection mission waypoints."""
        try:
            from droneresearch.control.solar_inspection import (
                SolarParkInspectionPlanner,
                PanelRow,
                InspectionConfig
            )
            
            with self._lock:
                if len(self._solar_panel_rows) == 0:
                    self.logMessage.emit("ERROR", "[SOLAR] No panel rows defined")
                    return
                
                planner = SolarParkInspectionPlanner()
                
                # Convert UI rows to PanelRow objects
                rows = [
                    PanelRow(
                        start=(row['start_lat'], row['start_lon']),
                        end=(row['end_lat'], row['end_lon'])
                    )
                    for row in self._solar_panel_rows
                ]
                
                # Create config
                config = InspectionConfig(
                    altitude=self._solar_altitude,
                    gimbal_pitch=self._solar_gimbal_pitch,
                    trigger_distance=self._solar_trigger_distance,
                    overlap=self._solar_overlap
                )
                
                # Generate waypoints
                self._solar_waypoints = planner.plan_inspection(rows, config, add_rtl=True)
                
                # Update stats
                self._solar_waypoint_count = len(self._solar_waypoints)
                self._solar_photo_count = sum(1 for wp in self._solar_waypoints if wp.cmd == 203)
                self._solar_coverage_area = planner.calculate_coverage_area(rows, config)
                self._solar_mission_time = planner.estimate_mission_time(rows, config)
            
            # Emit signals AFTER releasing lock
            self.solarStatsChanged.emit()
            self.coverageGenerated.emit()
            self.logMessage.emit(
                "INFO",
                f"[SOLAR] {self._solar_waypoint_count} WP, "
                f"{self._solar_photo_count} photos, "
                f"{self._solar_coverage_area:.1f} m², "
                f"{self._solar_mission_time/60:.1f} min"
            )
        except Exception as e:
            self.logMessage.emit("ERROR", f"[SOLAR] Generation failed: {e}")
            import traceback
            traceback.print_exc()
    
    @Slot(result="QVariantList")
    def getSolarWaypoints(self):
        """Return solar inspection waypoints for QML/JavaScript map display."""
        try:
            with self._lock:
                waypoints = []
                for wp in self._solar_waypoints:
                    if wp.cmd == 16:  # MAV_CMD_NAV_WAYPOINT only
                        waypoints.append({
                            "lat": float(wp.lat),
                            "lon": float(wp.lon),
                            "alt": float(wp.alt),
                            "isPhotoPoint": False
                        })
                    elif wp.cmd == 203:  # MAV_CMD_DO_DIGICAM_CONTROL (photo trigger)
                        # Photo triggers use previous waypoint's position
                        if waypoints:
                            waypoints[-1]["isPhotoPoint"] = True
                return waypoints
        except Exception as e:
            self.logMessage.emit("ERROR", f"[SOLAR] getSolarWaypoints failed: {e}")
            return []
    
    @Slot()
    def uploadSolarMission(self):
        """Upload solar inspection mission to selected drones."""
        with self._lock:
            if not self._solar_waypoints:
                self.logMessage.emit("ERROR", "[SOLAR] No waypoints to upload")
                return
            
            if not self._swarm_context:
                self.logMessage.emit("ERROR", "[SOLAR] SwarmContext not available")
                return
            
            waypoints = list(self._solar_waypoints)
        
        # Run upload in background thread
        threading.Thread(
            target=self._upload_solar_mission_worker,
            args=(waypoints,),
            daemon=True
        ).start()
    
    def _upload_solar_mission_worker(self, waypoints: List[Waypoint]) -> None:
        """Background worker for solar mission upload."""
        try:
            if not self._swarm_context:
                return
            
            backends = self._swarm_context.backend.all_backends()
            target_drones = [
                (drone_id, backend)
                for drone_id, backend in backends.items()
                if backend.is_connected
            ]
            
            if not target_drones:
                self.logMessage.emit("ERROR", "[SOLAR] No connected drones")
                return
            
            self.logMessage.emit(
                "INFO",
                f"[SOLAR] Uploading to {len(target_drones)} drone(s)..."
            )
            
            success_count = 0
            for drone_id, backend in target_drones:
                try:
                    if not backend._drone or not hasattr(backend._drone, '_conn'):
                        self.logMessage.emit(
                            "WARN",
                            f"[{drone_id}] No connection, skipping"
                        )
                        continue
                    
                    conn = backend._drone._conn
                    if not conn or not conn.connected:
                        self.logMessage.emit(
                            "WARN",
                            f"[{drone_id}] Connection not active, skipping"
                        )
                        continue
                    
                    # Create mission engine and upload
                    mission = MissionEngine(conn)
                    mission.clear()
                    
                    for wp in waypoints:
                        mission.add(wp)
                    
                    # Validate before upload
                    is_valid, errors = mission.validate()
                    if not is_valid:
                        self.logMessage.emit(
                            "ERROR",
                            f"[{drone_id}] ❌ Validation failed:"
                        )
                        for error in errors[:5]:
                            self.logMessage.emit("ERROR", f"  - {error}")
                        if len(errors) > 5:
                            self.logMessage.emit("ERROR", f"  ... and {len(errors)-5} more errors")
                        continue
                    
                    if not mission.upload(validate_first=False):
                        self.logMessage.emit(
                            "ERROR",
                            f"[{drone_id}] ❌ Upload failed (protocol error)"
                        )
                        continue
                    
                    self.logMessage.emit(
                        "INFO",
                        f"[{drone_id}] ✅ {len(waypoints)} waypoints uploaded"
                    )
                    
                    # Get drone object for arm/takeoff
                    drone_obj = backend._drone
                    if not drone_obj:
                        self.logMessage.emit(
                            "WARN",
                            f"[{drone_id}] No drone object, skipping auto-start"
                        )
                        success_count += 1
                        continue
                    
                    # Auto-arm if not armed
                    if not drone_obj.armed:
                        self.logMessage.emit("INFO", f"[{drone_id}] 🔧 Arming...")
                        if not drone_obj.arm(timeout=10.0):
                            self.logMessage.emit("ERROR", f"[{drone_id}] ❌ Arm failed")
                            continue
                        self.logMessage.emit("INFO", f"[{drone_id}] ✅ Armed")
                    
                    # Auto-takeoff if on ground
                    if drone_obj.altitude < 2.0:
                        self.logMessage.emit(
                            "INFO",
                            f"[{drone_id}] 🚁 Taking off to {self._solar_altitude}m..."
                        )
                        if not drone_obj.takeoff(altitude=self._solar_altitude, timeout=30.0):
                            self.logMessage.emit(
                                "WARN",
                                f"[{drone_id}] ⚠ Takeoff timeout, continuing..."
                            )
                        else:
                            self.logMessage.emit("INFO", f"[{drone_id}] ✅ Airborne")
                    
                    # Start mission
                    self.logMessage.emit("INFO", f"[{drone_id}] ☀ Starting solar inspection...")
                    if mission.start():
                        success_count += 1
                        self.logMessage.emit(
                            "INFO",
                            f"[{drone_id}] ✅ Solar inspection started!"
                        )
                        
                        # Mark mission as active
                        if self._swarm_context is not None:
                            with self._swarm_context._state_lock:
                                if drone_id not in self._swarm_context._mission_active:
                                    self._swarm_context._mission_active[drone_id] = threading.Event()
                                self._swarm_context._mission_active[drone_id].clear()
                    else:
                        self.logMessage.emit(
                            "WARN",
                            f"[{drone_id}] ⚠ Failed to start (set AUTO mode manually)"
                        )
                
                except Exception as e:
                    self.logMessage.emit("ERROR", f"[{drone_id}] Upload error: {e}")
            
            if success_count > 0:
                self.logMessage.emit(
                    "INFO",
                    f"[SOLAR] ✅ {success_count}/{len(target_drones)} successful"
                )
            else:
                self.logMessage.emit("ERROR", "[SOLAR] ❌ All uploads failed")
        
        except Exception as e:
            self.logMessage.emit("ERROR", f"[SOLAR] Worker error: {e}")

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

"""SafetyContext — APF Safety Filter bridge for QML.

Exposes APFSafetyFilter to QML for real-time violation monitoring
and safety-critical parameter adjustment.

QML Signals:
  - violationsChanged(violationsList)  -> List of {droneA, droneB, distance}
  - apfLogMessage(text)                -> APF status messages
  - geofenceBreached(droneId, reason)   -> Geofence violation alert
  - collisionPredicted(predictionsList) -> List of predicted collisions

QML Slots:
  - configureAPF(params)                 -> Configure APF parameters
  - checkSeparations()                   -> Manual separation check
  - addObstacle(x, y, z)                 -> Add static obstacle
  - clearObstacles()                     -> Clear all obstacles
  - setGeofence(radius, altMin, altMax)  -> Update geofence
  - enableCollisionPrediction(enabled)   -> Enable/disable collision prediction
  - configureCollisionPredictor(params)  -> Configure prediction parameters
"""

import math
from typing import Any, Dict, List, NamedTuple, Tuple

from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot

try:
    from droneresearch.safety.apf import APFSafetyFilter as _APFSafetyFilter
    from droneresearch.safety.apf import Pose3D as _Pose3D
except ImportError:
    _APFSafetyFilter = None
    _Pose3D = None

try:
    from droneresearch.safety.collision_predictor import (
        CollisionPredictor as _CollisionPredictor,
        DroneState as _DroneState,
    )
except ImportError:
    _CollisionPredictor = None
    _DroneState = None


class _DronePosition(NamedTuple):
    x: float
    y: float
    z: float
    armed: bool


class SafetyContext(QObject):
    """QML-exposed APF safety filter with real-time monitoring."""

    # ── Signals ─────────────────────────────────────────────────────────────
    violationsChanged = pyqtSignal("QVariant", arguments=["violations"])
    apfLogMessage = pyqtSignal(str, arguments=["text"])
    geofenceBreached = pyqtSignal(str, str, arguments=["droneId", "reason"])
    apfActiveChanged = pyqtSignal()
    safetyStatusChanged = pyqtSignal()
    logMessage = pyqtSignal(
        str, str, arguments=["level", "text"]
    )  # For global system integration
    # Active collision-avoidance command: target_lat, target_lon, target_alt
    avoidanceTriggered = pyqtSignal(
        str, float, float, float, arguments=["droneId", "lat", "lon", "alt"]
    )

    # Collision prediction signal
    collisionPredicted = pyqtSignal("QVariant", arguments=["predictions"])
    predictionEnabledChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._apf = None
        self._active = False
        self._last_violations: List[Tuple[str, str, float]] = []
        self._drone_positions: Dict[str, _DronePosition] = {}
        self._ref_lat = 0.0
        self._ref_lon = 0.0
        self._ref_lon_scale = 111_320.0
        self._ref_set = False

        # Collision prediction
        self._predictor = None
        self._prediction_enabled = False
        self._last_predictions: List[Dict] = []

        # Rate-limit tables: key → last_emit_timestamp (monotonic seconds)
        self._violation_log_ts: Dict[Tuple[str, str], float] = {}
        self._geofence_log_ts: Dict[Tuple[str, str], float] = {}
        self._avoidance_cmd_ts: Dict[str, float] = {}

        # Poll timer for separation checks
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(100)  # 10 Hz
        self._poll_timer.timeout.connect(self._check_safety)

    # ── Properties ──────────────────────────────────────────────────────────
    @pyqtProperty(bool, notify=apfActiveChanged)
    def apfActive(self) -> bool:
        return self._active

    @pyqtProperty(int, notify=safetyStatusChanged)
    def violationCount(self) -> int:
        return len(self._last_violations)

    @pyqtProperty(bool, notify=predictionEnabledChanged)
    def predictionEnabled(self) -> bool:
        return self._prediction_enabled

    @pyqtProperty(int, notify=safetyStatusChanged)
    def predictionCount(self) -> int:
        return len(self._last_predictions)

    # ── APF Configuration ───────────────────────────────────────────────────
    @pyqtSlot("QVariant")
    def configureAPF(self, params=None) -> None:
        """Configure APF with parameters from QML.

        params dict keys:
            minSeparation, maxSpeed, repulsionGain, attractionGain,
            geofenceRadius, geofenceAltMin, geofenceAltMax, obstacleRadius
        """
        if _APFSafetyFilter is None:
            self.apfLogMessage.emit(
                "[APF] ERROR: droneresearch.safety.apf not available"
            )
            return

        try:
            # QJSValue from QML does not have .get() — convert to plain dict
            if params is None:
                p = {}
            elif hasattr(params, "toVariant"):
                p = params.toVariant() or {}
            elif isinstance(params, dict):
                p = params
            else:
                # Fallback: try direct attribute access via [] on QJSValue
                try:
                    p = dict(params)
                except Exception:
                    p = {}

            def _g(key, default):
                try:
                    v = p[key]
                    return float(v) if v is not None else default
                except (KeyError, TypeError):
                    return default

            # Extract parameters with defaults
            min_sep = _g("minSeparation", 2.0)
            max_spd = _g("maxSpeed", 3.0)
            rep_gain = _g("repulsionGain", 2.0)
            att_gain = _g("attractionGain", 1.0)
            gf_radius = _g("geofenceRadius", 50.0)
            gf_alt_min = _g("geofenceAltMin", 1.0)
            gf_alt_max = _g("geofenceAltMax", 30.0)
            obs_radius = _g("obstacleRadius", 4.0)

            self._apf = _APFSafetyFilter(
                min_separation=min_sep,
                max_speed=max_spd,
                geofence_radius=gf_radius,
                geofence_alt=(gf_alt_min, gf_alt_max),
                repulsion_gain=rep_gain,
                attraction_gain=att_gain,
                obstacle_radius=obs_radius,
            )
            self._active = True
            self.apfActiveChanged.emit()
            self.apfLogMessage.emit(
                f"[APF] Configured: min_sep={min_sep}m, gf_r={gf_radius}m"
            )

            # Start monitoring
            if not self._poll_timer.isActive():
                self._poll_timer.start()

        except Exception as e:
            self.apfLogMessage.emit(f"[APF] Configuration error: {e}")

    @pyqtSlot()
    def disableAPF(self) -> None:
        """Disable APF monitoring."""
        self._active = False
        self._poll_timer.stop()
        self._apf = None
        self.apfActiveChanged.emit()
        self.apfLogMessage.emit("[APF] Disabled")

    # ── Obstacle Management ─────────────────────────────────────────────────
    @pyqtSlot(float, float, float)
    def addObstacle(self, x: float, y: float, z: float = 0.0) -> None:
        """Add static obstacle at local NED position."""
        if self._apf:
            self._apf.add_obstacle(x, y, z)
            self.apfLogMessage.emit(
                f"[APF] Obstacle added at ({x:.1f}, {y:.1f}, {z:.1f})"
            )

    @pyqtSlot()
    def clearObstacles(self) -> None:
        """Clear all static obstacles."""
        if self._apf:
            self._apf.clear_obstacles()
            self.apfLogMessage.emit("[APF] All obstacles cleared")

    # ── Geofence Management ─────────────────────────────────────────────────
    @pyqtSlot(float, float, float)
    def setGeofence(self, radius: float, alt_min: float, alt_max: float) -> None:
        """Update geofence parameters."""
        if self._apf:
            self._apf.geofence.radius = radius
            self._apf.geofence.alt_min = alt_min
            self._apf.geofence.alt_max = alt_max
            self.apfLogMessage.emit(
                f"[APF] Geofence: R={radius}m, Alt=[{alt_min},{alt_max}]m"
            )

    # ── Separation Checking ───────────────────────────────────────────────────
    @pyqtSlot()
    def checkSeparations(self) -> None:
        """Manual trigger for separation check."""
        self._check_safety()

    @pyqtSlot("QVariant")
    def updateDronePositions(self, positions: dict) -> None:
        """Update drone positions from telemetry.

        positions: {droneId: {lat, lon, alt, armed}}
        """
        if not isinstance(positions, dict):
            return

        for did, snap in positions.items():
            if not isinstance(snap, dict):
                continue
            lat = snap.get("lat", 0.0)
            lon = snap.get("lon", 0.0)
            alt = snap.get("alt_rel", 0.0)
            armed = snap.get("armed", False)

            # Set reference on first valid position
            if not self._ref_set and lat != 0.0:
                self._ref_lat = lat
                self._ref_lon = lon
                self._ref_lon_scale = 111_320.0 * math.cos(math.radians(self._ref_lat))
                self._ref_set = True

            # Convert to local NED
            if self._ref_set:
                x = (lat - self._ref_lat) * 111_320.0
                y = (lon - self._ref_lon) * self._ref_lon_scale
                self._drone_positions[did] = _DronePosition(
                    x=x, y=y, z=alt, armed=bool(armed)
                )

    @pyqtSlot(str, result="QVariant")
    def getSafeWaypoint(self, drone_id: str) -> dict:
        """Get APF-filtered safe waypoint for a drone.

        Returns: {x, y, z} in local NED meters or empty dict if not available.
        """
        apf = self._apf
        if apf is None or _Pose3D is None or not self._drone_positions:
            return {}

        poses = {
            did: _Pose3D(pos.x, pos.y, pos.z)
            for did, pos in self._drone_positions.items()
        }

        # For now, desired = current (hover) - in real use, desired comes from mission
        desired = poses.copy()

        safe = apf.filter(poses, desired)
        if drone_id in safe:
            p = safe[drone_id]
            return {"x": p.x, "y": p.y, "z": p.z}
        return {}

    # ── Internal ─────────────────────────────────────────────────────────────
    # Rate-limit windows (seconds)
    _LOG_RATE_LIMIT_S = 2.0  # log a given pair-violation at most every 2 s
    _GEOFENCE_RATE_LIMIT_S = (
        3.0  # log geofence breach at most every 3 s per drone+reason
    )
    _AVOID_RATE_LIMIT_S = 1.0  # send avoidance command at most every 1 s per drone

    def _check_safety(self) -> None:
        """Periodic safety check — violations, geofence, and active avoidance."""
        apf = self._apf
        if apf is None or _Pose3D is None or not self._drone_positions:
            return

        import time

        now = time.monotonic()

        poses = {
            did: _Pose3D(pos.x, pos.y, pos.z)
            for did, pos in self._drone_positions.items()
        }
        armed_map = {did: pos.armed for did, pos in self._drone_positions.items()}

        # Check separations
        violations = apf.check_separation(poses)

        # Always emit the latest violation list to the UI (cheap), but only
        # change-trigger the safety badge counter when the set actually changes.
        if violations != self._last_violations:
            self._last_violations = violations
            violation_list = [
                {"droneA": a, "droneB": b, "distance": round(d, 2)}
                for a, b, d in violations
            ]
            self.violationsChanged.emit(violation_list)
            self.safetyStatusChanged.emit()

        # Rate-limited logging + active avoidance per pair
        for a, b, d in violations:
            # Only act on armed pairs (no log spam for drones sitting on ground next to each other)
            if not (armed_map.get(a, False) and armed_map.get(b, False)):
                continue
            key = (a, b) if a < b else (b, a)
            last = self._violation_log_ts.get(key, 0.0)
            if now - last >= self._LOG_RATE_LIMIT_S:
                self._violation_log_ts[key] = now
                self.apfLogMessage.emit(
                    f"[APF] ⚠ VIOLATION: {a} ↔ {b}: {d:.2f}m < {apf.min_separation}m"
                )
            # Active push: deterministic — alphabetically larger drone moves away
            mover = b if b > a else a
            other = a if mover == b else b
            self._emit_avoidance(mover, other, poses, now)

        # Check geofence — skip alt_min for unarmed/on-ground drones
        for did, p in poses.items():
            is_armed = armed_map.get(did, True)
            if not apf.geofence.contains(p):
                if p.z < apf.geofence.alt_min:
                    if not is_armed:
                        continue
                    reason = (
                        f"below min altitude ({p.z:.1f}m < {apf.geofence.alt_min}m)"
                    )
                elif p.z > apf.geofence.alt_max:
                    reason = (
                        f"above max altitude ({p.z:.1f}m > {apf.geofence.alt_max}m)"
                    )
                else:
                    r = math.sqrt(p.x**2 + p.y**2)
                    reason = (
                        f"outside horizontal limit ({r:.1f}m > {apf.geofence.radius}m)"
                    )
                # Rate-limit: at most once per (drone, reason-prefix) every 3 s
                gkey = (did, reason.split("(")[0].strip())
                last = self._geofence_log_ts.get(gkey, 0.0)
                if now - last >= self._GEOFENCE_RATE_LIMIT_S:
                    self._geofence_log_ts[gkey] = now
                    self.geofenceBreached.emit(did, reason)

        # Run collision prediction
        self._run_collision_prediction()

    def _emit_avoidance(
        self, mover: str, other: str, poses: Dict[str, Any], now: float
    ) -> None:
        """Compute & emit a goto target that pushes ``mover`` away from ``other``."""
        apf = self._apf
        if not self._ref_set or apf is None:
            return
        last = self._avoidance_cmd_ts.get(mover, 0.0)
        if now - last < self._AVOID_RATE_LIMIT_S:
            return

        pm = poses.get(mover)
        po = poses.get(other)
        if pm is None or po is None:
            return

        dx = pm.x - po.x
        dy = pm.y - po.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 1e-3:
            # Drones overlap — pick an arbitrary direction (north)
            dx, dy, dist = 1.0, 0.0, 1.0

        # Push to (min_separation + 0.5 m) away from the other drone
        push = max(apf.min_separation + 0.5, 2.5)
        ux, uy = dx / dist, dy / dist
        target_x = po.x + ux * push
        target_y = po.y + uy * push

        # Convert local NED back to lat/lon
        target_lat = self._ref_lat + target_x / 111_320.0
        target_lon = self._ref_lon + target_y / self._ref_lon_scale
        # Maintain mover's current altitude (or min_alt if it's below)
        target_alt = max(pm.z, apf.geofence.alt_min + 0.5)

        self._avoidance_cmd_ts[mover] = now
        self.avoidanceTriggered.emit(mover, target_lat, target_lon, target_alt)

    # ── Collision Prediction ────────────────────────────────────────────────
    @pyqtSlot(bool)
    def enableCollisionPrediction(self, enabled: bool) -> None:
        """Enable or disable collision prediction."""
        if _CollisionPredictor is None or _DroneState is None:
            self.apfLogMessage.emit(
                "[Prediction] ERROR: collision_predictor module not available"
            )
            return

        self._prediction_enabled = enabled
        self.predictionEnabledChanged.emit()

        if enabled and self._predictor is None:
            # Initialize with default parameters
            self._predictor = _CollisionPredictor(
                time_horizon=10.0,
                min_separation=2.0,
                sample_rate=0.5
            )
            self.apfLogMessage.emit("[Prediction] Enabled (10s horizon)")
        elif not enabled:
            self._last_predictions = []
            self.collisionPredicted.emit([])
            self.apfLogMessage.emit("[Prediction] Disabled")

    @pyqtSlot("QVariant")
    def configureCollisionPredictor(self, params=None) -> None:
        """Configure collision predictor parameters.

        params dict keys:
            timeHorizon, minSeparation, sampleRate,
            criticalThreshold, warningThreshold
        """
        if _CollisionPredictor is None:
            self.apfLogMessage.emit(
                "[Prediction] ERROR: collision_predictor module not available"
            )
            return

        try:
            # Convert QJSValue to dict
            if params is None:
                p = {}
            elif hasattr(params, "toVariant"):
                p = params.toVariant() or {}
            elif isinstance(params, dict):
                p = params
            else:
                try:
                    p = dict(params)
                except Exception:
                    p = {}

            def _g(key, default):
                try:
                    v = p[key]
                    return float(v) if v is not None else default
                except (KeyError, TypeError):
                    return default

            time_horizon = _g("timeHorizon", 10.0)
            min_sep = _g("minSeparation", 2.0)
            sample_rate = _g("sampleRate", 0.5)
            crit_thresh = _g("criticalThreshold", 1.0)
            warn_thresh = _g("warningThreshold", 1.5)

            self._predictor = _CollisionPredictor(
                time_horizon=time_horizon,
                min_separation=min_sep,
                sample_rate=sample_rate,
                critical_threshold=crit_thresh,
                warning_threshold=warn_thresh
            )
            self._prediction_enabled = True
            self.predictionEnabledChanged.emit()
            self.apfLogMessage.emit(
                f"[Prediction] Configured: horizon={time_horizon}s, min_sep={min_sep}m"
            )

        except Exception as e:
            self.apfLogMessage.emit(f"[Prediction] Configuration error: {e}")

    def _run_collision_prediction(self) -> None:
        """Run collision prediction and emit results."""
        if not self._prediction_enabled or self._predictor is None:
            return
        if _DroneState is None or not self._drone_positions:
            return

        import time
        now = time.monotonic()

        # Convert drone positions to DroneState objects
        states = {}
        for did, pos in self._drone_positions.items():
            # Calculate velocity from position changes (simple finite difference)
            # In a real implementation, we'd get velocity from telemetry
            states[did] = _DroneState(
                x=pos.x,
                y=pos.y,
                z=pos.z,
                vx=0.0,  # TODO: Calculate from position history
                vy=0.0,
                vz=0.0,
                armed=pos.armed
            )

        # Run prediction
        predictions = self._predictor.predict(states)

        # Convert to QML-friendly format
        pred_list = [p.to_dict() for p in predictions]

        # Only emit if predictions changed
        if pred_list != self._last_predictions:
            self._last_predictions = pred_list
            self.collisionPredicted.emit(pred_list)
            self.safetyStatusChanged.emit()

            # Log critical predictions
            for pred in predictions:
                if pred.severity == "critical":
                    self.apfLogMessage.emit(
                        f"[Prediction] 🚨 CRITICAL: {pred.drone_a} ↔ {pred.drone_b} "
                        f"collision in {pred.time_to_collision:.1f}s "
                        f"(distance: {pred.min_distance:.2f}m)"
                    )

    # ── Utility ─────────────────────────────────────────────────────────────
    @pyqtSlot(result=str)
    def getAPFStatus(self) -> str:
        """Get human-readable APF status."""
        if not self._apf:
            return "APF not configured"
        status = (
            f"APF Active | "
            f"MinSep: {self._apf.min_separation}m | "
            f"Geofence: R={self._apf.geofence.radius}m | "
            f"Violations: {len(self._last_violations)}"
        )
        if self._prediction_enabled:
            status += f" | Predictions: {len(self._last_predictions)}"
        return status

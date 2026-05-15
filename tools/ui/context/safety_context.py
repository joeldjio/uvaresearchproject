"""SafetyContext — APF Safety Filter bridge for QML.

Exposes APFSafetyFilter to QML for real-time violation monitoring
and safety-critical parameter adjustment.

QML Signals:
  - violationsChanged(violationsList)  -> List of {droneA, droneB, distance}
  - apfLogMessage(text)                -> APF status messages
  - geofenceBreached(droneId, reason)   -> Geofence violation alert

QML Slots:
  - configureAPF(params)                 -> Configure APF parameters
  - checkSeparations()                   -> Manual separation check
  - addObstacle(x, y, z)                 -> Add static obstacle
  - clearObstacles()                     -> Clear all obstacles
  - setGeofence(radius, altMin, altMax)  -> Update geofence
"""
import math
from typing import Dict, List, Tuple

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, pyqtProperty, QTimer

try:
    from droneresearch.safety.apf import APFSafetyFilter as _APFSafetyFilter, Pose3D as _Pose3D
except ImportError:
    _APFSafetyFilter = None
    _Pose3D = None


class SafetyContext(QObject):
    """QML-exposed APF safety filter with real-time monitoring."""

    # ── Signals ─────────────────────────────────────────────────────────────
    violationsChanged = pyqtSignal("QVariant", arguments=["violations"])
    apfLogMessage = pyqtSignal(str, arguments=["text"])
    geofenceBreached = pyqtSignal(str, str, arguments=["droneId", "reason"])
    apfActiveChanged = pyqtSignal()
    safetyStatusChanged = pyqtSignal()
    logMessage = pyqtSignal(str, str, arguments=["level", "text"])  # For global system integration
    # Active collision-avoidance command: target_lat, target_lon, target_alt
    avoidanceTriggered = pyqtSignal(str, float, float, float, arguments=["droneId", "lat", "lon", "alt"])

    def __init__(self, parent=None):
        super().__init__(parent)
        self._apf = None
        self._active = False
        self._last_violations: List[Tuple[str, str, float]] = []
        self._drone_positions: Dict[str, Tuple[float, float, float]] = {}
        self._ref_lat = 0.0
        self._ref_lon = 0.0
        self._ref_set = False

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

    # ── APF Configuration ───────────────────────────────────────────────────
    @pyqtSlot("QVariant")
    def configureAPF(self, params=None) -> None:
        """Configure APF with parameters from QML.
        
        params dict keys:
            minSeparation, maxSpeed, repulsionGain, attractionGain,
            geofenceRadius, geofenceAltMin, geofenceAltMax, obstacleRadius
        """
        if _APFSafetyFilter is None:
            self.apfLogMessage.emit("[APF] ERROR: droneresearch.safety.apf not available")
            return

        try:
            # QJSValue from QML does not have .get() — convert to plain dict
            if params is None:
                p = {}
            elif hasattr(params, 'toVariant'):
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
            min_sep    = _g("minSeparation",  2.0)
            max_spd    = _g("maxSpeed",        3.0)
            rep_gain   = _g("repulsionGain",   2.0)
            att_gain   = _g("attractionGain",  1.0)
            gf_radius  = _g("geofenceRadius",  50.0)
            gf_alt_min = _g("geofenceAltMin",  1.0)
            gf_alt_max = _g("geofenceAltMax",  30.0)
            obs_radius = _g("obstacleRadius",  4.0)

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
            self.apfLogMessage.emit(f"[APF] Configured: min_sep={min_sep}m, gf_r={gf_radius}m")

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
            self.apfLogMessage.emit(f"[APF] Obstacle added at ({x:.1f}, {y:.1f}, {z:.1f})")

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
            self.apfLogMessage.emit(f"[APF] Geofence: R={radius}m, Alt=[{alt_min},{alt_max}]m")

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
                self._ref_set = True

            # Convert to local NED
            if self._ref_set:
                x = (lat - self._ref_lat) * 111_320.0
                y = (lon - self._ref_lon) * 111_320.0 * math.cos(math.radians(self._ref_lat))
                self._drone_positions[did] = (x, y, alt, armed)

    @pyqtSlot(str, result="QVariant")
    def getSafeWaypoint(self, drone_id: str) -> dict:
        """Get APF-filtered safe waypoint for a drone.
        
        Returns: {x, y, z} in local NED meters or empty dict if not available.
        """
        if not self._apf or not self._drone_positions:
            return {}

        # Build Pose3D positions (tuple may be 3 or 4 elements)
        poses = {did: _Pose3D(t[0], t[1], t[2]) for did, t in self._drone_positions.items()}

        # For now, desired = current (hover) - in real use, desired comes from mission
        desired = poses.copy()

        safe = self._apf.filter(poses, desired)
        if drone_id in safe:
            p = safe[drone_id]
            return {"x": p.x, "y": p.y, "z": p.z}
        return {}

    # ── Internal ─────────────────────────────────────────────────────────────
    # Rate-limit windows (seconds)
    _LOG_RATE_LIMIT_S = 2.0          # log a given pair-violation at most every 2 s
    _GEOFENCE_RATE_LIMIT_S = 3.0     # log geofence breach at most every 3 s per drone+reason
    _AVOID_RATE_LIMIT_S = 1.0        # send avoidance command at most every 1 s per drone

    def _check_safety(self) -> None:
        """Periodic safety check — violations, geofence, and active avoidance."""
        if not self._apf or not self._drone_positions:
            return

        import time
        now = time.monotonic()

        # Build Pose3D positions (tuple may be 3 or 4 elements)
        poses = {did: _Pose3D(t[0], t[1], t[2]) for did, t in self._drone_positions.items()}
        armed_map = {did: (t[3] if len(t) > 3 else True) for did, t in self._drone_positions.items()}

        # Check separations
        violations = self._apf.check_separation(poses)

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
                    f"[APF] ⚠ VIOLATION: {a} ↔ {b}: {d:.2f}m < {self._apf.min_separation}m"
                )
            # Active push: deterministic — alphabetically larger drone moves away
            mover = b if b > a else a
            other = a if mover == b else b
            self._emit_avoidance(mover, other, poses, now)

        # Check geofence — skip alt_min for unarmed/on-ground drones
        for did, p in poses.items():
            is_armed = armed_map.get(did, True)
            if not self._apf.geofence.contains(p):
                if p.z < self._apf.geofence.alt_min:
                    if not is_armed:
                        continue
                    reason = f"below min altitude ({p.z:.1f}m < {self._apf.geofence.alt_min}m)"
                elif p.z > self._apf.geofence.alt_max:
                    reason = f"above max altitude ({p.z:.1f}m > {self._apf.geofence.alt_max}m)"
                else:
                    r = math.sqrt(p.x**2 + p.y**2)
                    reason = f"outside horizontal limit ({r:.1f}m > {self._apf.geofence.radius}m)"
                # Rate-limit: at most once per (drone, reason-prefix) every 3 s
                gkey = (did, reason.split("(")[0].strip())
                last = self._geofence_log_ts.get(gkey, 0.0)
                if now - last >= self._GEOFENCE_RATE_LIMIT_S:
                    self._geofence_log_ts[gkey] = now
                    self.geofenceBreached.emit(did, reason)

    def _emit_avoidance(self, mover: str, other: str,
                        poses: Dict[str, "_Pose3D"], now: float) -> None:
        """Compute & emit a goto target that pushes ``mover`` away from ``other``."""
        if not self._ref_set:
            return
        last = self._avoidance_cmd_ts.get(mover, 0.0)
        if now - last < self._AVOID_RATE_LIMIT_S:
            return

        pm = poses.get(mover); po = poses.get(other)
        if pm is None or po is None:
            return

        dx = pm.x - po.x
        dy = pm.y - po.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 1e-3:
            # Drones overlap — pick an arbitrary direction (north)
            dx, dy, dist = 1.0, 0.0, 1.0

        # Push to (min_separation + 0.5 m) away from the other drone
        push = max(self._apf.min_separation + 0.5, 2.5)
        ux, uy = dx / dist, dy / dist
        target_x = po.x + ux * push
        target_y = po.y + uy * push

        # Convert local NED back to lat/lon
        target_lat = self._ref_lat + target_x / 111_320.0
        target_lon = self._ref_lon + target_y / (111_320.0 * math.cos(math.radians(self._ref_lat)))
        # Maintain mover's current altitude (or min_alt if it's below)
        target_alt = max(pm.z, self._apf.geofence.alt_min + 0.5)

        self._avoidance_cmd_ts[mover] = now
        self.avoidanceTriggered.emit(mover, target_lat, target_lon, target_alt)

    # ── Utility ─────────────────────────────────────────────────────────────
    @pyqtSlot(result=str)
    def getAPFStatus(self) -> str:
        """Get human-readable APF status."""
        if not self._apf:
            return "APF not configured"
        return (
            f"APF Active | "
            f"MinSep: {self._apf.min_separation}m | "
            f"Geofence: R={self._apf.geofence.radius}m | "
            f"Violations: {len(self._last_violations)}"
        )

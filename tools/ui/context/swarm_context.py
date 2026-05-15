"""
SwarmContext — exposes SwarmBackend to QML.

Registered as context property 'swarm' in the QML engine.
QML can call: swarm.addDrone(id, conn), swarm.armAll(), etc.
Signals: droneAdded, droneRemoved, telemetryUpdated, logMessage
"""
import threading
from typing import Dict

from PyQt6.QtCore import (
    QObject, pyqtSignal, pyqtSlot, pyqtProperty, QTimer
)

from tools.ui.backend import SwarmBackend, DroneBackend, DRONE_TYPE_GENERIC, DRONE_TYPE_OBSERVATION


class SwarmContext(QObject):
    """
    Thin QML-callable wrapper around SwarmBackend.
    All heavy logic stays in SwarmBackend; this class only
    translates pyqtSignal names and adds @pyqtSlot decorators
    so QML JS can call them directly.
    """

    # ── Signals forwarded to QML ──────────────────────────────────────────
    droneAdded       = pyqtSignal(str,        arguments=["droneId"])
    droneRemoved     = pyqtSignal(str,        arguments=["droneId"])
    telemetryUpdated = pyqtSignal("QVariant", arguments=["snapshot"])
    logMessage       = pyqtSignal(str, str,   arguments=["level", "text"])
    connectedChanged = pyqtSignal(str, bool,  arguments=["droneId", "connected"])
    fsmStateChanged  = pyqtSignal(str, str,   arguments=["droneId", "fsmState"])
    countsChanged    = pyqtSignal()
    
    # Swarm Algorithms signals
    formationUpdated = pyqtSignal(str, "QVariant", arguments=["leaderId", "positions"])
    consensusReached = pyqtSignal(str, str, arguments=["type", "result"])
    missionStatusChanged = pyqtSignal(str, arguments=["status"])
    missionFinished = pyqtSignal(str, bool, str, arguments=["droneId", "success", "reason"])

    def __init__(self, parent=None):
        super().__init__(parent)
        self._backend = SwarmBackend(parent=self)
        self._backend.drone_added.connect(self.droneAdded)
        self._backend.drone_removed.connect(self.droneRemoved)
        self._backend.swarm_telemetry_updated.connect(self._on_telemetry)
        self._backend.log_message.connect(self.logMessage)
        self._backend.fsm_state_changed.connect(self.fsmStateChanged)

        # ── Shared state — guarded by self._state_lock ────────────────────
        # Without this lock, mission/formation bookkeeping was mutated from
        # multiple daemon threads concurrently and lost updates silently.
        self._state_lock = threading.RLock()
        self._mission_active: Dict[str, threading.Event] = {}
        self._mission_threads: Dict[str, threading.Thread] = {}
        self._formation_launched: set = set()
        self._formation_cmd_ts: Dict[str, float] = {}
        self._formation_warn_ts: float = 0.0

        # Swarm Algorithms initialization
        self._init_swarm_algorithms()

    # ── QML-callable slots ────────────────────────────────────────────────

    @pyqtSlot(str, str)
    def addDrone(self, drone_id: str, connection_string: str) -> None:
        self.addDroneTyped(drone_id, connection_string, DRONE_TYPE_GENERIC)

    @pyqtSlot(str, str, str)
    def addDroneTyped(self, drone_id: str, connection_string: str, drone_type: str) -> None:
        self.logMessage.emit("INFO", f"[{drone_id}] 🔄 Connecting ({drone_type}) to {connection_string}...")
        b = self._backend.add_drone(drone_id, connection_string, drone_type=drone_type)
        b.connected_changed.connect(lambda ok, did=drone_id: self._on_connection_changed(did, ok))
        threading.Thread(target=b.connect, daemon=True).start()

    def _on_connection_changed(self, drone_id: str, connected: bool) -> None:
        self.connectedChanged.emit(drone_id, connected)
        if connected:
            self.logMessage.emit("INFO", f"[{drone_id}] ✅ Connected successfully")
        else:
            self.logMessage.emit("ERROR", f"[{drone_id}] ❌ Connection lost or failed")

    @pyqtSlot(str)
    def removeDrone(self, drone_id: str) -> None:
        self.logMessage.emit("INFO", f"[{drone_id}] 🗑 Removing drone from swarm")
        self._backend.remove_drone(drone_id)

    @pyqtSlot(str)
    def disconnectDrone(self, drone_id: str) -> None:
        b = self._backend.get_backend(drone_id)
        if b:
            self.logMessage.emit("INFO", f"[{drone_id}] ⏏ Disconnecting...")
            import threading
            threading.Thread(target=b.disconnect, daemon=True).start()

    @pyqtSlot(str)
    def reconnectDrone(self, drone_id: str) -> None:
        b = self._backend.get_backend(drone_id)
        if b:
            self.logMessage.emit("INFO", f"[{drone_id}] 🔄 Reconnecting to {b.connection_string}...")
            import threading
            threading.Thread(target=b.connect, daemon=True).start()

    @pyqtSlot()
    def armAll(self) -> None:
        self._backend.arm_all()

    @pyqtSlot()
    def disarmAll(self) -> None:
        self._backend.disarm_all()

    @pyqtSlot(float)
    def takeoffAll(self, altitude: float) -> None:
        self._backend.takeoff_all(altitude)

    @pyqtSlot()
    def landAll(self) -> None:
        self._backend.land_all()

    @pyqtSlot()
    def rtlAll(self) -> None:
        self._backend.rtl_all()

    @pyqtSlot(str)
    def armDrone(self, drone_id: str) -> None:
        b = self._backend.get_backend(drone_id)
        if b:
            b.arm()

    @pyqtSlot(str)
    def disarmDrone(self, drone_id: str) -> None:
        b = self._backend.get_backend(drone_id)
        if b:
            b.disarm()

    @pyqtSlot(str, float)
    def takeoffDrone(self, drone_id: str, altitude: float) -> None:
        b = self._backend.get_backend(drone_id)
        if b:
            b.takeoff(altitude)

    @pyqtSlot(str)
    def landDrone(self, drone_id: str) -> None:
        b = self._backend.get_backend(drone_id)
        if b:
            b.land()

    @pyqtSlot(str)
    def rtlDrone(self, drone_id: str) -> None:
        b = self._backend.get_backend(drone_id)
        if b:
            b.rtl()

    @pyqtSlot(str, float, float, float)
    def gotoDrone(self, drone_id: str, lat: float, lon: float, alt: float) -> None:
        b = self._backend.get_backend(drone_id)
        if b:
            b.goto(lat, lon, alt)

    @pyqtSlot(str, float, float, float)
    def smartGotoDrone(self, drone_id: str, lat: float, lon: float, alt: float) -> None:
        """Arm + takeoff if needed, then goto. Safe to call in any FSM state."""
        import time, threading

        b = self._backend.get_backend(drone_id)
        if not b:
            self.logMessage.emit("WARN", f"[{drone_id}] smartGoto: drone not found")
            return

        def _run():
            telem = b.get_telemetry_snapshot() if hasattr(b, "get_telemetry_snapshot") else {}
            armed = telem.get("armed", False) if telem else False

            if not armed:
                self.logMessage.emit("INFO", f"[{drone_id}] smartGoto: not armed — arming...")
                b.arm()
                # Wait for arm (up to 5s)
                for _ in range(50):
                    time.sleep(0.1)
                    t = b.get_telemetry_snapshot() if hasattr(b, "get_telemetry_snapshot") else {}
                    if t and t.get("armed", False):
                        break
                else:
                    self.logMessage.emit("ERROR", f"[{drone_id}] smartGoto: arm timeout")
                    return

                self.logMessage.emit("INFO", f"[{drone_id}] smartGoto: armed — taking off to {alt}m...")
                b.takeoff(alt)
                # Wait until airborne (alt_rel > 0.5m, up to 15s)
                for _ in range(150):
                    time.sleep(0.1)
                    t = b.get_telemetry_snapshot() if hasattr(b, "get_telemetry_snapshot") else {}
                    if t and t.get("alt_rel", 0) > 0.5:
                        break
                else:
                    self.logMessage.emit("WARN", f"[{drone_id}] smartGoto: takeoff timeout — trying goto anyway")

            self.logMessage.emit("INFO", f"[{drone_id}] smartGoto: flying to {lat:.6f}, {lon:.6f}, {alt}m")
            b.goto(lat, lon, alt)

        threading.Thread(target=_run, daemon=True).start()

    @pyqtSlot(str, float, float, float)
    def changeAltitude(self, drone_id: str, alt: float) -> None:
        self._backend.change_altitude(drone_id, alt)

    @pyqtSlot(str, str)
    def runMission(self, drone_id: str, waypoints_json: str) -> None:
        """Upload a JSON waypoints list and start AUTO mission on one drone.

        If the SDK has no ``upload_mission``/``set_waypoints``, fall back to
        sequential ``goto`` commands (waypoint-by-waypoint, polling distance).
        """
        import json, threading, time, math
        b = self._backend.get_backend(drone_id)
        if not b:
            self.logMessage.emit("WARN", f"[{drone_id}] runMission: drone not found")
            return
        try:
            wps = json.loads(waypoints_json)
        except Exception as exc:
            self.logMessage.emit("ERROR", f"[{drone_id}] runMission: invalid JSON — {exc}")
            return
        if not wps:
            self.logMessage.emit("WARN", f"[{drone_id}] runMission: empty waypoint list")
            return

        # Cancel any prior mission for this drone before starting a new one.
        with self._state_lock:
            prev = self._mission_active.get(drone_id)
            if prev is not None:
                prev.set()  # signal cancel to existing thread
            cancel_event = threading.Event()
            self._mission_active[drone_id] = cancel_event

        def _is_cancelled() -> bool:
            with self._state_lock:
                ev = self._mission_active.get(drone_id)
            return ev is None or ev.is_set() or ev is not cancel_event

        def _finish(success: bool, reason: str) -> None:
            with self._state_lock:
                if self._mission_active.get(drone_id) is cancel_event:
                    self._mission_active.pop(drone_id, None)
                    self._mission_threads.pop(drone_id, None)
            try:
                self.missionFinished.emit(drone_id, success, reason)
            except Exception:
                pass

        def _run():
            drone = b.drone
            if drone is None:
                self.logMessage.emit("ERROR", f"[{drone_id}] runMission: not connected")
                _finish(False, "not connected")
                return
            self.logMessage.emit("INFO", f"[{drone_id}] runMission: starting {len(wps)} waypoints…")

            # Path 1: native mission upload
            if hasattr(drone, "upload_mission"):
                try:
                    drone.upload_mission(wps)
                    if hasattr(drone, "start_mission"):
                        drone.start_mission()
                    else:
                        b.set_mode("AUTO")
                    self.logMessage.emit("INFO", f"[{drone_id}] runMission: native mission started")
                    _finish(True, "native mission dispatched")
                    return
                except Exception as exc:
                    self.logMessage.emit("WARN", f"[{drone_id}] runMission: upload_mission failed ({exc}) — falling back to sequential GOTO")

            # Path 2: legacy set_waypoints
            if hasattr(drone, "set_waypoints"):
                try:
                    drone.set_waypoints(wps)
                    if hasattr(drone, "start_mission"):
                        drone.start_mission()
                    else:
                        b.set_mode("AUTO")
                    self.logMessage.emit("INFO", f"[{drone_id}] runMission: legacy mission started")
                    _finish(True, "legacy mission dispatched")
                    return
                except Exception as exc:
                    self.logMessage.emit("WARN", f"[{drone_id}] runMission: set_waypoints failed ({exc}) — falling back to sequential GOTO")

            # Path 3: sequential goto fallback (works on every SDK with .goto())
            if not hasattr(b, "goto"):
                self.logMessage.emit("ERROR", f"[{drone_id}] runMission: backend has no goto() — cannot fly mission")
                _finish(False, "no goto support")
                return

            # Make sure drone is ready (armed + airborne)
            try:
                if hasattr(b, "get_telemetry_snapshot"):
                    t = b.get_telemetry_snapshot() or {}
                    if not t.get("armed", False):
                        self.logMessage.emit("INFO", f"[{drone_id}] runMission: arming…")
                        if hasattr(b, "arm"): b.arm()
                        # cancel-aware wait (3 s)
                        for _ in range(30):
                            if cancel_event.wait(0.1):
                                self.logMessage.emit("INFO", f"[{drone_id}] runMission: cancelled before arm")
                                _finish(False, "cancelled")
                                return
                            t = b.get_telemetry_snapshot() or {}
                            if t.get("armed", False): break
                    if t.get("alt_rel", 0) < 1.0:
                        target_alt = max(float(wps[0].get("alt", 10.0)), 5.0)
                        self.logMessage.emit("INFO", f"[{drone_id}] runMission: takeoff to {target_alt}m…")
                        if hasattr(b, "takeoff"): b.takeoff(target_alt)
                        for _ in range(80):
                            if cancel_event.wait(0.25):
                                self.logMessage.emit("INFO", f"[{drone_id}] runMission: cancelled during takeoff")
                                _finish(False, "cancelled")
                                return
                            t = b.get_telemetry_snapshot() or {}
                            if t.get("alt_rel", 0) >= target_alt * 0.9: break
            except Exception as exc:
                self.logMessage.emit("WARN", f"[{drone_id}] runMission: pre-flight check failed ({exc})")

            # Fly waypoints in order — per-WP timeout enforced by Event.wait
            WP_TIMEOUT_S = 60.0
            WP_POLL_S    = 0.25
            WP_RADIUS_M  = 3.0
            for i, wp in enumerate(wps):
                if _is_cancelled():
                    self.logMessage.emit("INFO", f"[{drone_id}] runMission: cancelled at WP {i+1}")
                    _finish(False, "cancelled")
                    return
                lat = float(wp["lat"]); lon = float(wp["lon"]); alt = float(wp.get("alt", 10.0))
                self.logMessage.emit("INFO", f"[{drone_id}] runMission: WP {i+1}/{len(wps)} → {lat:.5f}, {lon:.5f} @ {alt}m")
                try:
                    b.goto(lat, lon, alt)
                except Exception as exc:
                    self.logMessage.emit("ERROR", f"[{drone_id}] runMission: goto failed at WP {i+1} ({exc})")
                    _finish(False, f"goto failed @WP{i+1}: {exc}")
                    return
                # cancel-aware poll until reached or per-WP timeout
                t_start = time.monotonic()
                reached = False
                while time.monotonic() - t_start < WP_TIMEOUT_S:
                    if cancel_event.wait(WP_POLL_S):
                        self.logMessage.emit("INFO", f"[{drone_id}] runMission: cancelled at WP {i+1}")
                        _finish(False, "cancelled")
                        return
                    snap = b.get_telemetry_snapshot() if hasattr(b, "get_telemetry_snapshot") else {}
                    if not snap:
                        continue
                    cur_lat = snap.get("lat", 0.0); cur_lon = snap.get("lon", 0.0)
                    dlat = (lat - cur_lat) * 111320.0
                    dlon = (lon - cur_lon) * 111320.0 * math.cos(math.radians(cur_lat))
                    if math.sqrt(dlat * dlat + dlon * dlon) < WP_RADIUS_M:
                        reached = True
                        break
                if not reached:
                    self.logMessage.emit("WARN", f"[{drone_id}] runMission: WP {i+1} timeout after {WP_TIMEOUT_S:.0f}s — advancing")
            self.logMessage.emit("INFO", f"[{drone_id}] runMission: mission complete")
            _finish(True, "complete")

        th = threading.Thread(target=_run, daemon=True, name=f"mission-{drone_id}")
        with self._state_lock:
            self._mission_threads[drone_id] = th
        th.start()

    @pyqtSlot(str)
    def cancelMission(self, drone_id: str) -> None:
        """Cancel an active sequential-GOTO mission for one drone."""
        with self._state_lock:
            ev = self._mission_active.get(drone_id)
        if ev is not None:
            ev.set()
            self.logMessage.emit("INFO", f"[{drone_id}] cancelMission: requested")
        else:
            self.logMessage.emit("INFO", f"[{drone_id}] cancelMission: no active mission")

    @pyqtSlot()
    def cancelAllMissions(self) -> None:
        with self._state_lock:
            ids = list(self._mission_active.keys())
            for ev in self._mission_active.values():
                ev.set()
        if ids:
            self.logMessage.emit("INFO", f"cancelAllMissions: cancelled {len(ids)} mission(s)")

    @pyqtSlot(str, str)
    def runMissionMulti(self, drone_ids_json: str, waypoints_json: str) -> None:
        """Run the same waypoint mission on multiple drones in parallel."""
        import json
        try:
            ids = json.loads(drone_ids_json)
        except Exception as exc:
            self.logMessage.emit("ERROR", f"runMissionMulti: invalid drone list — {exc}")
            return
        if not ids:
            self.logMessage.emit("WARN", "runMissionMulti: no drones selected")
            return
        self.logMessage.emit("INFO", f"runMissionMulti: dispatching to {len(ids)} drone(s): {', '.join(ids)}")
        for did in ids:
            self.runMission(did, waypoints_json)

    @pyqtSlot(str, str)
    def setMode(self, drone_id: str, mode: str) -> None:
        """Switch flight mode for a single drone."""
        b = self._backend.get_backend(drone_id)
        if b:
            b.set_mode(mode)

    @pyqtSlot(str)
    def setModeAll(self, mode: str) -> None:
        """Switch flight mode for every connected drone."""
        for b in self._backend.all_backends().values():
            if b.is_connected:
                b.set_mode(mode)
        self.logMessage.emit("INFO", f"[SWARM] MODE → {mode} (all)")

    @pyqtSlot()
    def emergencyStopAll(self) -> None:
        """Force-disarm every drone immediately. Use only for emergencies."""
        n = 0
        for b in self._backend.all_backends().values():
            if b.is_connected:
                b.disarm(force=True)
                n += 1
        self.logMessage.emit(
            "ERROR", f"[SWARM] 🛑 EMERGENCY STOP — force-disarmed {n} drone(s)"
        )

    @pyqtSlot(str)
    def emergencyStop(self, drone_id: str) -> None:
        """Force-disarm one drone immediately."""
        b = self._backend.get_backend(drone_id)
        if b:
            b.disarm(force=True)
            self.logMessage.emit(
                "ERROR", f"[{drone_id}] 🛑 EMERGENCY STOP — force-disarmed"
            )

    @pyqtSlot(str, result=str)
    def droneFsmState(self, drone_id: str) -> str:
        b = self._backend.get_backend(drone_id)
        return b.fsm_state if b else "DISCONNECTED"

    @pyqtSlot(str, result="QVariant")
    def droneFsmHistory(self, drone_id: str) -> list:
        return self._backend.get_fsm_history(drone_id)

    @pyqtSlot(str, result=str)
    def droneType(self, drone_id: str) -> str:
        b = self._backend.get_backend(drone_id)
        return b.drone_type if b else DRONE_TYPE_GENERIC

    @pyqtSlot(str, str)
    def setDroneType(self, drone_id: str, drone_type: str) -> None:
        b = self._backend.get_backend(drone_id)
        if b:
            b.drone_type = drone_type
            self.logMessage.emit("INFO", f"[{drone_id}] Typ gesetzt: {drone_type}")
            self.telemetryUpdated.emit({})

    @pyqtSlot(str, result=str)
    def droneRole(self, drone_id: str) -> str:
        b = self._backend.get_backend(drone_id)
        return b.swarm_role if b else "none"

    @pyqtSlot(str, str, str)
    def setDroneRole(self, drone_id: str, role: str, leader_id: str) -> None:
        self._backend.set_drone_role(drone_id, role, leader_id)

    @pyqtSlot(str, float, float, float)
    def setFormationOffset(self, drone_id: str, north: float, east: float, alt: float) -> None:
        self._backend.set_drone_formation_offset(drone_id, north, east, alt)

    @pyqtSlot(str, float, float, float)
    def gimbalPoint(self, drone_id: str, pitch: float, roll: float, yaw: float) -> None:
        self._backend.gimbal_point(drone_id, pitch, roll, yaw)

    @pyqtSlot(str)
    def gimbalHome(self, drone_id: str) -> None:
        self._backend.gimbal_home(drone_id)

    @pyqtSlot(str, result="QVariant")
    def gimbalState(self, drone_id: str) -> dict:
        return self._backend.get_gimbal_state(drone_id)

    @pyqtSlot(result="QVariant")
    def droneIds(self) -> list:
        return list(self._backend.all_backends().keys())

    @pyqtSlot(result="QVariant")
    def availableSerialPorts(self) -> list:
        try:
            import serial.tools.list_ports
            return [p.device for p in serial.tools.list_ports.comports()]
        except Exception:
            return []

    @pyqtSlot(str, result=bool)
    def isDroneConnected(self, drone_id: str) -> bool:
        b = self._backend.get_backend(drone_id)
        return bool(b and b.is_connected)

    @pyqtSlot(str, result=str)
    def readFile(self, path: str) -> str:
        """Read a local file and return its contents as a string (for QML CSV loading)."""
        try:
            # Strip file:/// prefix if present
            clean = path
            if clean.startswith("file:///"):
                clean = clean[8:]
            elif clean.startswith("file://"):
                clean = clean[7:]
            with open(clean, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception as exc:
            return ""

    @pyqtSlot(str, str, result=bool)
    def writeFile(self, path: str, content: str) -> bool:
        """Write content to a local file (for log export from QML)."""
        try:
            import os
            clean = path
            if clean.startswith("file:///"):
                clean = clean[8:]
            elif clean.startswith("file://"):
                clean = clean[7:]
            parent = os.path.dirname(clean)
            if parent and not os.path.isdir(parent):
                os.makedirs(parent, exist_ok=True)
            with open(clean, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as exc:
            self.logMessage.emit("WARN", f"writeFile failed for {path}: {exc}")
            return False

    @pyqtSlot(str, result="QVariant")
    def droneSnapshot(self, drone_id: str) -> dict:
        b = self._backend.get_backend(drone_id)
        return b.get_telemetry_snapshot() or {} if b else {}

    @pyqtProperty(int, notify=countsChanged)
    def totalDrones(self) -> int:
        return len(self._backend.all_backends())

    @pyqtProperty(int, notify=countsChanged)
    def connectedDrones(self) -> int:
        return sum(1 for b in self._backend.all_backends().values() if b.is_connected)

    # ── Internal ──────────────────────────────────────────────────────────

    def _on_telemetry(self, all_snaps: dict) -> None:
        self.countsChanged.emit()
        self.telemetryUpdated.emit(all_snaps)

    # ── Swarm Algorithms ─────────────────────────────────────────────────────

    def _init_swarm_algorithms(self):
        """Initialize swarm algorithms state and timers"""
        import math
        from PyQt6.QtCore import QTimer
        
        # Algorithm state
        self._swarm_algorithms_active = False
        self._algorithms_timer = QTimer()
        self._algorithms_timer.timeout.connect(self._update_swarm_algorithms)
        self._algorithms_update_rate = 100  # ms
        
        # Boids parameters
        self._boids_enabled = False
        self._separation_weight = 1.5
        self._alignment_weight = 1.0
        self._cohesion_weight = 1.0
        self._perception_radius = 50
        self._boids_velocities = {}
        
        # Leader-Follower parameters
        self._leader_follower_enabled = False
        self._leader_drone_id = ""
        # Spacing between formation slots in metres. Letter-templates scale
        # this by 0.6, so 8 m gives ~4.8 m between adjacent slots — well
        # above the APF ``min_distance`` (2 m) so the safety system doesn't
        # constantly fight the formation goto commands.
        self._follow_distance = 8
        self._formation_type = 0  # Line
        # 0 == "use every connected follower". The previous default of 5
        # silently ignored every drone beyond the first four followers — which
        # made multi-drone swarms (e.g. 13 sims) look broken because 8 of them
        # never received any goto command.
        self._formation_size = 0
        
        # Consensus parameters
        self._consensus_enabled = False
        self._consensus_algorithm = 0  # Basic
        self._byzantine_tolerance = 1
        self._consensus_state = "Idle"
        
        # Behavior Trees parameters
        self._behavior_trees_enabled = False
        self._mission_type = 0  # Surveillance
        self._mission_priority = 1  # Balanced
        self._mission_status = "Idle"
        self._behavior_tree_active = False

    # ── Swarm Algorithms Properties ───────────────────────────────────────
    
    @pyqtProperty(bool, notify=countsChanged)
    def swarmAlgorithmsActive(self):
        return self._swarm_algorithms_active
    
    @pyqtProperty(int, notify=countsChanged)
    def algorithmsUpdateRate(self):
        return self._algorithms_update_rate
    
    @algorithmsUpdateRate.setter
    def algorithmsUpdateRate(self, value):
        self._algorithms_update_rate = value
        if self._swarm_algorithms_active:
            self._algorithms_timer.setInterval(value)
    
    # Boids properties
    @pyqtProperty(bool, notify=countsChanged)
    def boidsEnabled(self):
        return self._boids_enabled
    
    @boidsEnabled.setter
    def boidsEnabled(self, value):
        self._boids_enabled = value
    
    @pyqtProperty(float, notify=countsChanged)
    def separationWeight(self):
        return self._separation_weight
    
    @separationWeight.setter
    def separationWeight(self, value):
        self._separation_weight = value
    
    @pyqtProperty(float, notify=countsChanged)
    def alignmentWeight(self):
        return self._alignment_weight
    
    @alignmentWeight.setter
    def alignmentWeight(self, value):
        self._alignment_weight = value
    
    @pyqtProperty(float, notify=countsChanged)
    def cohesionWeight(self):
        return self._cohesion_weight
    
    @cohesionWeight.setter
    def cohesionWeight(self, value):
        self._cohesion_weight = value
    
    @pyqtProperty(int, notify=countsChanged)
    def perceptionRadius(self):
        return self._perception_radius
    
    @perceptionRadius.setter
    def perceptionRadius(self, value):
        self._perception_radius = value
    
    # Leader-Follower properties
    @pyqtProperty(bool, notify=countsChanged)
    def leaderFollowerEnabled(self):
        return self._leader_follower_enabled
    
    @leaderFollowerEnabled.setter
    def leaderFollowerEnabled(self, value):
        new_val = bool(value)
        if new_val == self._leader_follower_enabled:
            return
        self._leader_follower_enabled = new_val
        if not new_val:
            # Clear launch bookkeeping so a fresh enable triggers smartGoto
            # again on every follower.
            with self._state_lock:
                self._formation_launched.clear()
                self._formation_cmd_ts.clear()
        self.countsChanged.emit()
    
    @pyqtProperty(str, notify=countsChanged)
    def leaderDroneId(self):
        return self._leader_drone_id
    
    @leaderDroneId.setter
    def leaderDroneId(self, value):
        self._leader_drone_id = value
    
    @pyqtProperty(int, notify=countsChanged)
    def followDistance(self):
        return self._follow_distance
    
    @followDistance.setter
    def followDistance(self, value):
        self._follow_distance = value
    
    @pyqtProperty(int, notify=countsChanged)
    def formationType(self):
        return self._formation_type
    
    @formationType.setter
    def formationType(self, value):
        if int(value) == int(self._formation_type):
            return
        self._formation_type = int(value)
        self.countsChanged.emit()
    
    @pyqtProperty(int, notify=countsChanged)
    def formationSize(self):
        return self._formation_size
    
    @formationSize.setter
    def formationSize(self, value):
        v = max(0, int(value))
        if v == self._formation_size:
            return
        self._formation_size = v
        self.countsChanged.emit()
        self.logMessage.emit(
            "INFO",
            f"[SWARM] Formation size set to {v if v > 0 else 'ALL'}"
        )
    
    # Consensus properties
    @pyqtProperty(bool, notify=countsChanged)
    def consensusEnabled(self):
        return self._consensus_enabled
    
    @consensusEnabled.setter
    def consensusEnabled(self, value):
        self._consensus_enabled = value
    
    @pyqtProperty(int, notify=countsChanged)
    def consensusAlgorithm(self):
        return self._consensus_algorithm
    
    @consensusAlgorithm.setter
    def consensusAlgorithm(self, value):
        self._consensus_algorithm = value
    
    @pyqtProperty(int, notify=countsChanged)
    def byzantineTolerance(self):
        return self._byzantine_tolerance
    
    @byzantineTolerance.setter
    def byzantineTolerance(self, value):
        self._byzantine_tolerance = value
    
    @pyqtProperty(str, notify=countsChanged)
    def consensusState(self):
        return self._consensus_state
    
    # Behavior Trees properties
    @pyqtProperty(bool, notify=countsChanged)
    def behaviorTreesEnabled(self):
        return self._behavior_trees_enabled
    
    @behaviorTreesEnabled.setter
    def behaviorTreesEnabled(self, value):
        self._behavior_trees_enabled = value
    
    @pyqtProperty(int, notify=countsChanged)
    def missionType(self):
        return self._mission_type
    
    @missionType.setter
    def missionType(self, value):
        self._mission_type = value
    
    @pyqtProperty(int, notify=countsChanged)
    def missionPriority(self):
        return self._mission_priority
    
    @missionPriority.setter
    def missionPriority(self, value):
        self._mission_priority = value
    
    @pyqtProperty(str, notify=missionStatusChanged)
    def missionStatus(self):
        return self._mission_status
    
    # ── Swarm Algorithms Slots ─────────────────────────────────────────────
    
    @pyqtSlot()
    def startSwarmAlgorithms(self):
        """Start all enabled swarm algorithms.

        UX shortcut: if no algorithm is enabled yet but the user has a valid
        formation type set, auto-enable Leader-Follower and pick the first
        connected drone as the leader. Otherwise pressing START would silently
        do nothing.
        """
        # Auto-enable Leader-Follower if neither LF nor Boids is on
        if not (self._leader_follower_enabled or self._boids_enabled):
            self._leader_follower_enabled = True
            self.logMessage.emit("INFO", "[SWARM] Auto-enabled Leader-Follower mode")

        # Auto-pick a leader if Leader-Follower is on but no leader was set
        if self._leader_follower_enabled:
            connected = [
                did for did, b in self._backend.all_backends().items()
                if b.is_connected
            ]
            if not self._leader_drone_id or self._leader_drone_id not in connected:
                if connected:
                    self._leader_drone_id = sorted(connected)[0]
                    self.logMessage.emit(
                        "INFO",
                        f"[SWARM] Auto-selected leader: {self._leader_drone_id}",
                    )
                else:
                    self.logMessage.emit(
                        "WARN",
                        "[SWARM] Cannot start: no connected drones",
                    )
                    return

            ftypes = ["Line", "V-Shape", "Circle", "Grid", "RZ Logo", "Letter R", "Letter Z"]
            ft_name = ftypes[self._formation_type] if 0 <= self._formation_type < len(ftypes) else "?"
            self.logMessage.emit(
                "INFO",
                f"[SWARM] Formation: {ft_name} · leader={self._leader_drone_id} · "
                f"size={self._formation_size} · spacing={self._follow_distance}m",
            )

        self._swarm_algorithms_active = True
        self._algorithms_timer.start(self._algorithms_update_rate)
        self.logMessage.emit("INFO", "[SWARM] Starting swarm algorithms...")
        self.countsChanged.emit()
    
    @pyqtSlot()
    def stopSwarmAlgorithms(self):
        """Stop all swarm algorithms"""
        self._swarm_algorithms_active = False
        self._algorithms_timer.stop()
        self.logMessage.emit("INFO", "[SWARM] Stopping swarm algorithms...")
        self.countsChanged.emit()
    
    @pyqtSlot()
    def resetSwarmAlgorithms(self):
        """Reset all swarm algorithms"""
        self.stopSwarmAlgorithms()
        self._boids_velocities.clear()
        self._mission_status = "Idle"
        self._behavior_tree_active = False
        self._consensus_state = "Idle"
        self.logMessage.emit("INFO", "[SWARM] Algorithms reset")
        self.countsChanged.emit()
    
    @pyqtSlot()
    def startConsensusVote(self):
        """Start consensus voting"""
        if not self._consensus_enabled:
            return
        
        self._consensus_state = "Voting"
        self.logMessage.emit("INFO", "[SWARM] Starting consensus vote...")
        self.countsChanged.emit()
        
        # Simulate voting result
        import threading
        import time
        def _vote():
            time.sleep(2)
            self._consensus_state = "Consensus Reached"
            self.consensusReached.emit("target", "approved")
            self.logMessage.emit("INFO", "[SWARM] Consensus reached")
            self.countsChanged.emit()
        
        threading.Thread(target=_vote, daemon=True).start()
    
    @pyqtSlot()
    def executeBehaviorTreeMission(self):
        """Execute behavior tree mission"""
        if not self._behavior_trees_enabled:
            return
        
        self._mission_status = "Executing"
        self._behavior_tree_active = True
        self.missionStatusChanged.emit(self._mission_status)
        
        mission_types = ["Surveillance", "Search & Rescue", "Formation Flight", "Area Coverage"]
        mission = mission_types[self._mission_type]
        self.logMessage.emit("INFO", f"[SWARM] Starting mission: {mission}")
        
        import threading
        import time
        def _execute():
            steps = ["Planning", "Takeoff", "Execution", "Landing"]
            for step in steps:
                if not self._behavior_tree_active:
                    break
                self._mission_status = step
                self.missionStatusChanged.emit(self._mission_status)
                time.sleep(2)
            
            if self._behavior_tree_active:
                self._mission_status = "Completed"
                self._behavior_tree_active = False
                self.logMessage.emit("INFO", "[SWARM] Mission completed")
            
            self.missionStatusChanged.emit(self._mission_status)
        
        threading.Thread(target=_execute, daemon=True).start()
    
    # ── Swarm Algorithms Internal Methods ───────────────────────────────────
    
    def _update_swarm_algorithms(self):
        """Main update loop for swarm algorithms"""
        if not self._swarm_algorithms_active:
            return
        
        # Get current drone positions
        drone_positions = {}
        for drone_id, backend in self._backend.all_backends().items():
            if backend.is_connected:
                snap = backend.get_telemetry_snapshot()
                if snap and snap.get('lat') and snap.get('lon'):
                    drone_positions[drone_id] = (snap['lat'], snap['lon'], snap.get('alt', 0))
        
        if len(drone_positions) < 2:
            return
        
        # Run enabled algorithms
        if self._boids_enabled:
            self._update_boids(drone_positions)
        
        if self._leader_follower_enabled:
            self._update_leader_follower(drone_positions)
    
    def _update_boids(self, drone_positions):
        """Update boids algorithm"""
        # Simplified boids implementation
        for drone_id in drone_positions:
            if drone_id not in self._boids_velocities:
                self._boids_velocities[drone_id] = [0.0, 0.0, 0.0]
            
            # Simple cohesion towards center
            center_lat = sum(pos[0] for pos in drone_positions.values()) / len(drone_positions)
            center_lon = sum(pos[1] for pos in drone_positions.values()) / len(drone_positions)
            
            my_lat, my_lon, _ = drone_positions[drone_id]
            vel_lat = (center_lat - my_lat) * 0.0001 * self._cohesion_weight
            vel_lon = (center_lon - my_lon) * 0.0001 * self._cohesion_weight
            
            self._boids_velocities[drone_id] = [vel_lat, vel_lon, 0]
            
            # Send velocity command
            backend = self._backend.get_backend(drone_id)
            if backend and hasattr(backend, 'send_velocity'):
                backend.send_velocity(vel_lat, vel_lon, 0)
    
    def _update_leader_follower(self, drone_positions):
        """Update leader-follower algorithm.

        Computes the target position for every follower drone based on the
        currently selected formation type and dispatches a ``goto`` command
        via the drone backend (rate-limited to once per second per drone).
        """
        import time, math
        if not self._leader_drone_id or self._leader_drone_id not in drone_positions:
            return

        leader_pos = drone_positions[self._leader_drone_id]
        formation_positions = self._calculate_formation_positions(leader_pos, drone_positions)

        # Emit formation update for visualization. Convert tuples → plain
        # lists so JS sees a real array (`pos[0]`/`pos[1]` would otherwise be
        # `undefined`, causing a flood of "Invalid LatLng" errors in Leaflet).
        positions_list = [
            [float(p[0]), float(p[1]), float(p[2])]
            for p in formation_positions.values()
            if p and p[0] is not None and p[1] is not None
        ]
        if positions_list:
            self.formationUpdated.emit(self._leader_drone_id, positions_list)

        # Per-drone command throttle. 2 Hz keeps SDK chatter manageable while
        # still letting followers track a moving leader and recover from APF
        # interventions quickly enough to actually reach their slot.
        now = time.monotonic()
        _FORMATION_THROTTLE_S = 0.5

        skipped_disconnected = []
        for drone_id, target_pos in formation_positions.items():
            if drone_id == self._leader_drone_id:
                continue
            if drone_id not in drone_positions:
                skipped_disconnected.append(drone_id)
                continue
            with self._state_lock:
                last = self._formation_cmd_ts.get(drone_id, 0.0)
            if now - last < _FORMATION_THROTTLE_S:
                continue
            backend = self._backend.get_backend(drone_id)
            if not backend:
                continue
            target_lat, target_lon, target_alt = target_pos

            # Decide between smartGoto (arm+takeoff+goto) and plain goto.
            snap = backend.get_telemetry_snapshot() if hasattr(backend, "get_telemetry_snapshot") else {}
            armed = bool(snap.get("armed", False)) if snap else False
            airborne = (snap.get("alt_rel", 0) or 0) > 0.5 if snap else False

            with self._state_lock:
                already_launched = drone_id in self._formation_launched
            sent = False
            if not already_launched:
                # First-time launch into formation. smartGoto handles arming +
                # takeoff + goto in its own thread; mark as launched so we
                # don't spawn parallel threads on subsequent cycles while the
                # arm/takeoff sequence is still running.
                try:
                    self.smartGotoDrone(drone_id, target_lat, target_lon, target_alt)
                    with self._state_lock:
                        self._formation_launched.add(drone_id)
                    sent = True
                except Exception as exc:
                    self.logMessage.emit("WARN", f"[{drone_id}] formation smartGoto failed: {exc}")
            elif not armed or not airborne:
                # Already launched once but currently grounded — let smartGoto
                # re-engage (e.g. after a landing). Throttle still applies.
                try:
                    self.smartGotoDrone(drone_id, target_lat, target_lon, target_alt)
                    sent = True
                except Exception as exc:
                    self.logMessage.emit("WARN", f"[{drone_id}] formation re-launch failed: {exc}")
            elif hasattr(backend, "goto"):
                try:
                    backend.goto(target_lat, target_lon, target_alt)
                    sent = True
                except Exception as exc:
                    self.logMessage.emit("WARN", f"[{drone_id}] formation goto failed: {exc}")
            elif hasattr(backend, "send_position"):
                try:
                    backend.send_position(target_lat, target_lon, target_alt)
                    sent = True
                except Exception as exc:
                    self.logMessage.emit("WARN", f"[{drone_id}] formation send_position failed: {exc}")
            if sent:
                with self._state_lock:
                    self._formation_cmd_ts[drone_id] = now

        # Once per ~5s, log any followers that were registered but excluded
        # because they have no usable lat/lon (typically: not connected, or
        # telemetry hasn't arrived yet). Helps diagnose "only the leader is
        # moving" complaints.
        if skipped_disconnected:
            if now - self._formation_warn_ts > 5.0:
                self._formation_warn_ts = now
                self.logMessage.emit(
                    "WARN",
                    f"[SWARM] Formation: {len(skipped_disconnected)} follower(s) "
                    f"without telemetry (skipped): {', '.join(skipped_disconnected)}"
                )

    # ── Formation Geometry ───────────────────────────────────────────────
    # Local-frame layouts: list of (north_unit, east_unit) — they are scaled
    # by ``self._follow_distance`` (metres) and then converted to lat/lon.
    # The leader sits at the geometric origin (0, 0).
    _LETTER_R_OFFSETS = [
        # Vertical spine (top to bottom)
        (1.0, -0.6), (0.5, -0.6), (0.0, -0.6), (-0.5, -0.6), (-1.0, -0.6),
        # Top curve / horizontal of the bowl
        (1.0, -0.2), (1.0, 0.2),
        # Right edge of bowl
        (0.7, 0.4), (0.3, 0.4),
        # Bowl bottom (joins spine)
        (0.0, -0.2), (0.0, 0.2),
        # Diagonal leg
        (-0.5, 0.0), (-1.0, 0.4),
    ]
    _LETTER_Z_OFFSETS = [
        # Top horizontal (left to right)
        (1.0, -0.6), (1.0, -0.2), (1.0, 0.2), (1.0, 0.6),
        # Diagonal (top-right → bottom-left)
        (0.5, 0.3), (0.0, 0.0), (-0.5, -0.3),
        # Bottom horizontal
        (-1.0, -0.6), (-1.0, -0.2), (-1.0, 0.2), (-1.0, 0.6),
    ]

    def _formation_offsets(self, n_followers: int):
        """Return list of (north_m, east_m) offsets for ``n_followers`` drones
        based on the currently selected formation type.

        Formation type indices (must match the QML ComboBox model):
            0 = Line, 1 = V-Shape, 2 = Circle, 3 = Grid,
            4 = RZ (R+Z combined), 5 = R, 6 = Z
        """
        import math
        d = float(self._follow_distance)
        ftype = int(self._formation_type)

        if ftype == 1:  # V-shape
            offs = []
            for i in range(n_followers):
                rank = (i // 2) + 1
                side = -1 if (i % 2 == 0) else 1
                offs.append((-rank * d * 0.866, side * rank * d * 0.5))
            return offs

        if ftype == 2:  # Circle
            offs = []
            for i in range(n_followers):
                ang = 2 * math.pi * (i + 1) / max(n_followers, 1)
                offs.append((d * math.cos(ang), d * math.sin(ang)))
            return offs

        if ftype == 3:  # Grid
            cols = max(1, int(math.ceil(math.sqrt(n_followers + 1))))
            offs = []
            for i in range(n_followers):
                idx = i + 1  # leader at slot 0
                r = idx // cols
                c = idx % cols
                offs.append((-r * d, (c - cols / 2.0 + 0.5) * d))
            return offs

        if ftype in (4, 5, 6):
            # Letter formations — use the precomputed normalized templates.
            if ftype == 5:
                tmpl = self._LETTER_R_OFFSETS
            elif ftype == 6:
                tmpl = self._LETTER_Z_OFFSETS
            else:
                # "RZ" combined: place R to the west, Z to the east.
                rz = []
                for n, e in self._LETTER_R_OFFSETS:
                    rz.append((n, e - 1.6))
                for n, e in self._LETTER_Z_OFFSETS:
                    rz.append((n, e + 1.6))
                tmpl = rz
            # Scale by follow distance (letter spans ~2 units in N and ~1.6 in E)
            scale = d * 0.6
            return [(n * scale, e * scale) for (n, e) in tmpl[:n_followers]]

        # Default: Line (followers trail directly behind the leader)
        return [(-(i + 1) * d, 0.0) for i in range(n_followers)]

    def _calculate_formation_positions(self, leader_pos, drone_positions):
        """Calculate target lat/lon/alt for every drone in the formation."""
        import math
        positions = {self._leader_drone_id: leader_pos}

        # Eligible followers (deterministic ordering).
        # ``_formation_size`` semantics:
        #   <= 0  → no cap, every connected non-leader drone joins the formation
        #   > 0   → leader + (size-1) followers (legacy behaviour)
        followers = sorted(d for d in drone_positions.keys() if d != self._leader_drone_id)
        if int(self._formation_size) > 0:
            followers = followers[: max(0, int(self._formation_size) - 1)]
        if not followers:
            return positions

        offsets = self._formation_offsets(len(followers))

        lat0, lon0, alt0 = leader_pos
        m_per_deg_lat = 111_320.0
        m_per_deg_lon = 111_320.0 * max(0.1, math.cos(math.radians(lat0)))

        for drone_id, (north_m, east_m) in zip(followers, offsets):
            dlat = north_m / m_per_deg_lat
            dlon = east_m / m_per_deg_lon
            positions[drone_id] = (lat0 + dlat, lon0 + dlon, alt0)

        return positions

    # ── Direct backend access (for Python-side panels) ────────────────────

    @property
    def backend(self) -> SwarmBackend:
        return self._backend

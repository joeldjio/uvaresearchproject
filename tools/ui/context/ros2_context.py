"""
ROS2Context — QML bridge for PX4ROS2Bridge (uXRCE-DDS).

Exposed to QML as context property 'ros2'.

Features:
  - Toggle ROS2 bridge on/off per drone (not parallel to MAVLink)
  - Configure uXRCE-DDS namespace
  - Stream native PX4 uORB topics (VehicleOdometry, VehicleStatus, BatteryStatus)
  - Offboard-mode via TrajectorySetpoint (position/velocity)
  - ROS2 node status display

QML Signals:
  - bridgeStatusChanged(droneId, active)
  - telemetryReceived(droneId, snapshot)
  - ros2LogMessage(level, text)
  - nodeStatusChanged(status)        -- "ok" | "no_ros2" | "no_px4_msgs" | "error"

QML Slots:
  - startBridge(droneId, namespace)
  - stopBridge(droneId)
  - setOffboardPosition(droneId, north, east, down, yaw)
  - setOffboardVelocity(droneId, vn, ve, vd, yawRate)
  - stopOffboard(droneId)
  - armBridge(droneId)
  - disarmBridge(droneId)
  - takeoffBridge(droneId, altitude)
  - landBridge(droneId)
  - rtlBridge(droneId)
  - activateOffboardMode(droneId)
  - getBridgeTopics(droneId)         -> list of active topic names
"""
import threading
import importlib.util
from typing import Dict, Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer

# ── Detect ROS2 availability WITHOUT importing rclpy ──────────────────
# Importing rclpy is expensive (1-3s on cold start). We only check if
# it CAN be imported via importlib.util.find_spec, then defer the real
# import to first bridge start.
_ROS2_AVAILABLE   = importlib.util.find_spec("rclpy") is not None
_BRIDGE_AVAILABLE = importlib.util.find_spec("droneresearch.ros.px4_bridge") is not None
_PX4Bridge: Optional[type] = None  # populated on first start_bridge


def _ensure_bridge_loaded() -> bool:
    """Import PX4ROS2Bridge on first use. Returns True if available."""
    global _PX4Bridge
    if _PX4Bridge is not None:
        return True
    if not (_ROS2_AVAILABLE and _BRIDGE_AVAILABLE):
        return False
    try:
        from droneresearch.ros.px4_bridge import PX4ROS2Bridge as _B
        _PX4Bridge = _B
        return True
    except ImportError:
        return False


class ROS2Context(QObject):
    """QML-callable wrapper around PX4ROS2Bridge."""

    # ── Signals ───────────────────────────────────────────────────────────
    bridgeStatusChanged = pyqtSignal(str, bool,   arguments=["droneId", "active"])
    telemetryReceived   = pyqtSignal(str, "QVariant", arguments=["droneId", "snapshot"])
    ros2LogMessage      = pyqtSignal(str, str,    arguments=["level", "text"])
    nodeStatusChanged   = pyqtSignal(str,          arguments=["status"])
    missionStatusChanged = pyqtSignal(str, "QVariant", arguments=["droneId", "status"])

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bridges: Dict[str, object] = {}
        self._namespaces: Dict[str, str] = {}
        self._active_drone_ids: set = set()

        # Poll timer — forward bridge telemetry to QML at 5 Hz.
        # Started lazily on first bridge start, stopped when last bridge stops.
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(200)
        self._poll_timer.timeout.connect(self._poll)

        # SITL cluster management
        self._sitl_cluster = None
        self._sitl_config = {
            'px4_dir': '/home/iruz/PX4-Autopilot',
            'model': 'x500',
            'namespace': 'uav_1',
            'ros2_setups': [
                '/opt/ros/humble/setup.bash',
                '/home/iruz/ws_sensor_combined/install/setup.bash'
            ]
        }

        # Emit initial node status
        self._emit_node_status()

    def _gate_poll_timer(self) -> None:
        if self._active_drone_ids and not self._poll_timer.isActive():
            self._poll_timer.start()
        elif not self._active_drone_ids and self._poll_timer.isActive():
            self._poll_timer.stop()

    # ── Status ────────────────────────────────────────────────────────────

    def _emit_node_status(self):
        if not _ROS2_AVAILABLE:
            self.nodeStatusChanged.emit("no_ros2")
        elif not _BRIDGE_AVAILABLE:
            self.nodeStatusChanged.emit("no_px4_msgs")
        else:
            self.nodeStatusChanged.emit("ok")

    @pyqtSlot(result=str)
    def nodeStatus(self) -> str:
        if not _ROS2_AVAILABLE:
            return "no_ros2"
        if not _BRIDGE_AVAILABLE:
            return "no_px4_msgs"
        return "ok"

    @pyqtSlot(str, result=bool)
    def isBridgeActive(self, drone_id: str) -> bool:
        return drone_id in self._active_drone_ids

    @pyqtSlot(result="QVariant")
    def activeBridges(self) -> list:
        return list(self._active_drone_ids)

    # ── Bridge lifecycle ──────────────────────────────────────────────────

    @pyqtSlot(str, str)
    def startBridge(self, drone_id: str, namespace: str) -> None:
        """Start uXRCE-DDS bridge for a drone. Stops MAVLink if it was active."""
        if not _ROS2_AVAILABLE:
            self.ros2LogMessage.emit("ERROR", "[ROS2] rclpy not found — install ROS2 Humble+")
            return
        if not _BRIDGE_AVAILABLE:
            self.ros2LogMessage.emit("ERROR", "[ROS2] px4_msgs not found — build px4_msgs in your ROS2 workspace")
            return
        if drone_id in self._active_drone_ids:
            self.ros2LogMessage.emit("WARN", f"[ROS2] Bridge for {drone_id} already running")
            return

        ns = namespace.strip()
        self._namespaces[drone_id] = ns

        if not _ensure_bridge_loaded():
            self.ros2LogMessage.emit("ERROR", "[ROS2] PX4 bridge module unavailable")
            return

        def _start():
            try:
                bridge = _PX4Bridge(namespace=ns, publish_hz=10.0)
                bridge.on("telemetry", lambda data: self._on_bridge_telemetry(drone_id, data))
                bridge.start()
                self._bridges[drone_id] = bridge
                self._active_drone_ids.add(drone_id)
                self._gate_poll_timer()
                self.bridgeStatusChanged.emit(drone_id, True)
                self.ros2LogMessage.emit("INFO", f"[ROS2] Bridge started for {drone_id} ns='{ns or '/'}'")
                self.ros2LogMessage.emit("INFO", f"[ROS2] Listening on {ns or ''}/fmu/out/*")
            except Exception as e:
                self.ros2LogMessage.emit("ERROR", f"[ROS2] Bridge start failed: {e}")

        threading.Thread(target=_start, daemon=True).start()

    @pyqtSlot(str)
    def stopBridge(self, drone_id: str) -> None:
        bridge = self._bridges.pop(drone_id, None)
        self._active_drone_ids.discard(drone_id)
        self._gate_poll_timer()
        if bridge:
            try:
                bridge.stop()
            except Exception:
                pass
        self.bridgeStatusChanged.emit(drone_id, False)
        self.ros2LogMessage.emit("INFO", f"[ROS2] Bridge stopped for {drone_id}")

    # ── Offboard control ──────────────────────────────────────────────────

    @pyqtSlot(str)
    def activateOffboardMode(self, drone_id: str) -> None:
        b = self._bridges.get(drone_id)
        if b:
            b.set_offboard_mode()
            self.ros2LogMessage.emit("INFO", f"[ROS2] {drone_id} → OFFBOARD mode activated")
        else:
            self.ros2LogMessage.emit("WARN", f"[ROS2] No bridge for {drone_id}")

    @pyqtSlot(str, float, float, float, float)
    def setOffboardPosition(self, drone_id: str, north: float, east: float,
                            down: float, yaw: float) -> None:
        b = self._bridges.get(drone_id)
        if b:
            b.set_position_setpoint_ned(north, east, down, yaw)
            self.ros2LogMessage.emit("INFO",
                f"[ROS2] {drone_id} POSITION N={north:.1f} E={east:.1f} D={down:.1f} yaw={yaw:.1f}")

    @pyqtSlot(str, float, float, float, float)
    def setOffboardVelocity(self, drone_id: str, vn: float, ve: float,
                            vd: float, yaw_rate: float) -> None:
        b = self._bridges.get(drone_id)
        if b:
            b.set_velocity_setpoint_ned(vn, ve, vd, yaw_rate)
            self.ros2LogMessage.emit("INFO",
                f"[ROS2] {drone_id} VELOCITY vN={vn:.1f} vE={ve:.1f} vD={vd:.1f}")

    @pyqtSlot(str)
    def stopOffboard(self, drone_id: str) -> None:
        b = self._bridges.get(drone_id)
        if b:
            b.stop_offboard()
            self.ros2LogMessage.emit("INFO", f"[ROS2] {drone_id} offboard setpoints stopped")

    # ── Vehicle commands via bridge ───────────────────────────────────────

    @pyqtSlot(str)
    def armBridge(self, drone_id: str) -> None:
        b = self._bridges.get(drone_id)
        if b:
            b.arm()
            self.ros2LogMessage.emit("INFO", f"[ROS2] {drone_id} ARM sent via uXRCE-DDS")

    @pyqtSlot(str)
    def disarmBridge(self, drone_id: str) -> None:
        b = self._bridges.get(drone_id)
        if b:
            b.disarm()
            self.ros2LogMessage.emit("INFO", f"[ROS2] {drone_id} DISARM sent via uXRCE-DDS")

    @pyqtSlot(str, float)
    def takeoffBridge(self, drone_id: str, altitude: float) -> None:
        b = self._bridges.get(drone_id)
        if b:
            b.takeoff(altitude)
            self.ros2LogMessage.emit("INFO", f"[ROS2] {drone_id} TAKEOFF {altitude}m via uXRCE-DDS")

    @pyqtSlot(str)
    def landBridge(self, drone_id: str) -> None:
        b = self._bridges.get(drone_id)
        if b:
            b.land()
            self.ros2LogMessage.emit("INFO", f"[ROS2] {drone_id} LAND via uXRCE-DDS")

    @pyqtSlot(str)
    def rtlBridge(self, drone_id: str) -> None:
        b = self._bridges.get(drone_id)
        if b:
            b.rtl()
            self.ros2LogMessage.emit("INFO", f"[ROS2] {drone_id} RTL via uXRCE-DDS")

    # ── Topic snapshot ────────────────────────────────────────────────────

    @pyqtSlot(str, result="QVariant")
    def bridgeSnapshot(self, drone_id: str) -> dict:
        b = self._bridges.get(drone_id)
        return dict(b.telemetry) if b else {}

    @pyqtSlot(str, result="QVariant")
    def getBridgeTopics(self, drone_id: str) -> list:
        ns = self._namespaces.get(drone_id, "")
        prefix = f"{ns}/fmu" if ns else "/fmu"
        return [
            f"{prefix}/out/vehicle_global_position",
            f"{prefix}/out/vehicle_local_position",
            f"{prefix}/out/vehicle_attitude",
            f"{prefix}/out/vehicle_status",
            f"{prefix}/out/battery_status",
            f"{prefix}/out/vehicle_gps_position",
            f"{prefix}/in/vehicle_command",
            f"{prefix}/in/offboard_control_mode",
            f"{prefix}/in/trajectory_setpoint",
        ]

    # ── Internal ──────────────────────────────────────────────────────────

    def _on_bridge_telemetry(self, drone_id: str, data: dict) -> None:
        self.telemetryReceived.emit(drone_id, data)

    def _poll(self) -> None:
        for did, bridge in list(self._bridges.items()):
            snap = dict(bridge.telemetry)
            if snap:
                self.telemetryReceived.emit(did, snap)

    # ── PX4 SITL Control ──────────────────────────────────────────────────

    @pyqtSlot(result=bool)
    def isSitlRunning(self) -> bool:
        """Check if SITL cluster is running."""
        return self._sitl_cluster is not None and self._sitl_cluster.is_running()

    @pyqtSlot(result=str)
    def getSitlPx4Dir(self) -> str:
        """Get current PX4 directory."""
        return self._sitl_config.get('px4_dir', '')

    @pyqtSlot(str)
    def setSitlPx4Dir(self, path: str) -> None:
        """Set PX4 directory."""
        self._sitl_config['px4_dir'] = path

    @pyqtSlot(result=str)
    def getSitlModel(self) -> str:
        """Get current SITL model."""
        return self._sitl_config.get('model', 'x500')

    @pyqtSlot(str)
    def setSitlModel(self, model: str) -> None:
        """Set SITL model."""
        self._sitl_config['model'] = model

    @pyqtSlot(result=str)
    def getSitlNamespace(self) -> str:
        """Get current SITL namespace."""
        return self._sitl_config.get('namespace', 'uav_1')

    @pyqtSlot(str)
    def setSitlNamespace(self, namespace: str) -> None:
        """Set SITL namespace."""
        self._sitl_config['namespace'] = namespace

    @pyqtSlot(result="QVariant")
    def getSitlRos2Setups(self) -> list:
        """Get ROS2 setup files."""
        return self._sitl_config.get('ros2_setups', [])

    @pyqtSlot(str)
    def addSitlRos2Setup(self, path: str) -> None:
        """Add ROS2 setup file."""
        if path and path not in self._sitl_config['ros2_setups']:
            self._sitl_config['ros2_setups'].append(path)

    @pyqtSlot(str)
    def removeSitlRos2Setup(self, path: str) -> None:
        """Remove ROS2 setup file."""
        if path in self._sitl_config['ros2_setups']:
            self._sitl_config['ros2_setups'].remove(path)

    @pyqtSlot()
    def startSitl(self) -> None:
        """Start PX4 SITL + Gazebo + XRCE-DDS Agent."""
        
        if self._sitl_cluster is not None and self._sitl_cluster.is_running():
            self.ros2LogMessage.emit("WARN", "[SITL] Already running")
            return

        def _start():
            try:
                from droneresearch.simulation import PX4GazeboCluster
                
                self.ros2LogMessage.emit("INFO", "[SITL] Starting PX4 Gazebo cluster...")
                self.ros2LogMessage.emit("INFO", f"[SITL] PX4 Dir: {self._sitl_config['px4_dir']}")
                self.ros2LogMessage.emit("INFO", f"[SITL] Model: {self._sitl_config['model']}")
                self.ros2LogMessage.emit("INFO", f"[SITL] Namespace: {self._sitl_config['namespace']}")
                
                cluster = PX4GazeboCluster(
                    num_drones=1,
                    px4_dir=self._sitl_config['px4_dir'],
                    model=self._sitl_config['model'],
                    ros2_setups=self._sitl_config['ros2_setups'],
                    namespace_prefix=self._sitl_config['namespace'].rsplit('_', 1)[0]  # "uav_1" → "uav"
                )
                
                if cluster.start():
                    self._sitl_cluster = cluster
                    self.ros2LogMessage.emit("INFO", "[SITL] ✓ Cluster started successfully")
                    self.ros2LogMessage.emit("INFO", f"[SITL] Namespace: {self._sitl_config['namespace']}")
                    self.ros2LogMessage.emit("INFO", "[SITL] You can now start the ROS2 bridge")
                else:
                    self.ros2LogMessage.emit("ERROR", "[SITL] Failed to start cluster")
                    
            except FileNotFoundError as e:
                self.ros2LogMessage.emit("ERROR", f"[SITL] PX4 directory not found: {e}")
            except Exception as e:
                self.ros2LogMessage.emit("ERROR", f"[SITL] Start failed: {e}")

        threading.Thread(target=_start, daemon=True).start()

    @pyqtSlot()
    def stopSitl(self) -> None:
        """Stop PX4 SITL cluster."""
        if self._sitl_cluster is None:
            self.ros2LogMessage.emit("WARN", "[SITL] Not running")
            return

        def _stop():
            try:
                self.ros2LogMessage.emit("INFO", "[SITL] Stopping cluster...")
                self._sitl_cluster.stop()
                self._sitl_cluster = None
                self.ros2LogMessage.emit("INFO", "[SITL] ✓ Cluster stopped")
            except Exception as e:
                self.ros2LogMessage.emit("ERROR", f"[SITL] Stop failed: {e}")

        threading.Thread(target=_stop, daemon=True).start()
    
    # ── Mission Management ────────────────────────────────────────────────
    
    @pyqtSlot(str, "QVariant", result=bool)
    def uploadMission(self, drone_id: str, waypoints: list) -> bool:
        """
        Upload waypoint mission to PX4.
        
        Args:
            drone_id: Drone identifier
            waypoints: List of waypoint dicts with keys: lat, lon, alt
        
        Returns:
            True if upload successful
        """
        b = self._bridges.get(drone_id)
        if not b:
            self.ros2LogMessage.emit("WARN", f"[MISSION] No bridge for {drone_id}")
            return False
        
        try:
            # Convert QML list to Python list of dicts
            wp_list = []
            for wp in waypoints:
                wp_dict = {
                    "lat": float(wp.get("lat", 0)),
                    "lon": float(wp.get("lon", 0)),
                    "alt": float(wp.get("alt", 0)),
                }
                # Optional parameters
                if "hold_time" in wp:
                    wp_dict["hold_time"] = float(wp["hold_time"])
                if "accept_radius" in wp:
                    wp_dict["accept_radius"] = float(wp["accept_radius"])
                if "yaw" in wp:
                    wp_dict["yaw"] = float(wp["yaw"])
                wp_list.append(wp_dict)
            
            self.ros2LogMessage.emit("INFO", f"[MISSION] Uploading {len(wp_list)} waypoints to {drone_id}...")
            success = b.upload_mission(wp_list, timeout=10.0)
            
            if success:
                self.ros2LogMessage.emit("INFO", f"[MISSION] ✓ Mission uploaded to {drone_id}")
                # Register status callback
                b.on_mission_status(lambda status: self._on_mission_status(drone_id, status))
            else:
                self.ros2LogMessage.emit("ERROR", f"[MISSION] Upload failed for {drone_id}")
            
            return success
        except Exception as e:
            self.ros2LogMessage.emit("ERROR", f"[MISSION] Upload error: {e}")
            return False
    
    @pyqtSlot(str, result=bool)
    def clearMission(self, drone_id: str) -> bool:
        """Clear mission on PX4."""
        b = self._bridges.get(drone_id)
        if not b:
            self.ros2LogMessage.emit("WARN", f"[MISSION] No bridge for {drone_id}")
            return False
        
        try:
            success = b.clear_mission()
            if success:
                self.ros2LogMessage.emit("INFO", f"[MISSION] ✓ Mission cleared on {drone_id}")
            return success
        except Exception as e:
            self.ros2LogMessage.emit("ERROR", f"[MISSION] Clear error: {e}")
            return False
    
    @pyqtSlot(str)
    def startMission(self, drone_id: str) -> None:
        """Start mission execution (switch to AUTO.MISSION mode)."""
        b = self._bridges.get(drone_id)
        if not b:
            self.ros2LogMessage.emit("WARN", f"[MISSION] No bridge for {drone_id}")
            return
        
        try:
            b.start_mission()
            self.ros2LogMessage.emit("INFO", f"[MISSION] ✓ Mission started on {drone_id}")
        except Exception as e:
            self.ros2LogMessage.emit("ERROR", f"[MISSION] Start error: {e}")
    
    @pyqtSlot(str)
    def pauseMission(self, drone_id: str) -> None:
        """Pause mission execution (switch to AUTO.LOITER mode)."""
        b = self._bridges.get(drone_id)
        if not b:
            self.ros2LogMessage.emit("WARN", f"[MISSION] No bridge for {drone_id}")
            return
        
        try:
            b.pause_mission()
            self.ros2LogMessage.emit("INFO", f"[MISSION] ✓ Mission paused on {drone_id}")
        except Exception as e:
            self.ros2LogMessage.emit("ERROR", f"[MISSION] Pause error: {e}")
    
    @pyqtSlot(str, result="QVariant")
    def getMissionStatus(self, drone_id: str) -> dict:
        """Get current mission status."""
        b = self._bridges.get(drone_id)
        if not b:
            return {
                "active": False,
                "current_seq": 0,
                "total_count": 0,
                "reached": False,
                "finished": False,
                "failure": False,
            }
        
        try:
            return b.get_mission_status()
        except Exception as e:
            self.ros2LogMessage.emit("ERROR", f"[MISSION] Status error: {e}")
            return {}
    
    @pyqtSlot(str, result="QVariant")
    def getMissionWaypoints(self, drone_id: str) -> list:
        """Get uploaded mission waypoints."""
        b = self._bridges.get(drone_id)
        if not b:
            return []
        
        try:
            return b.get_mission_waypoints()
        except Exception as e:
            self.ros2LogMessage.emit("ERROR", f"[MISSION] Waypoints error: {e}")
            return []
    
    def _on_mission_status(self, drone_id: str, status: dict) -> None:
        """Handle mission status updates from bridge."""
        self.missionStatusChanged.emit(drone_id, status)
        
        # Log significant events
        if status.get("finished"):
            self.ros2LogMessage.emit("INFO", f"[MISSION] ✓ Mission completed on {drone_id}")
        elif status.get("failure"):
            self.ros2LogMessage.emit("ERROR", f"[MISSION] Mission failed on {drone_id}")

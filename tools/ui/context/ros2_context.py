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

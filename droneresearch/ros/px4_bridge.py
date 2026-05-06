"""
PX4ROS2Bridge — proper PX4 ↔ ROS2 integration via uXRCE-DDS.

PX4 v1.14+ uses uXRCE-DDS (NOT FastRTPS, NOT MAVLink-over-ROS).
Topics live under /fmu/out/* (PX4 → ROS2) and /fmu/in/* (ROS2 → PX4).

Reference:
    https://docs.px4.io/main/en/ros2/user_guide.html
    https://docs.px4.io/main/en/middleware/uxrce_dds

IMPORTANT — Frame conventions (PX4 uses FRD/NED, ROS2 uses FLU/ENU):
    PX4 position:   NED  (North-East-Down)
    ROS2 position:  ENU  (East-North-Up)
    PX4 body:       FRD  (Forward-Right-Down)
    ROS2 body:      FLU  (Forward-Left-Up)
    Conversion NED→ENU: [x,y,z]_enu = [y, x, -z]_ned
    Conversion ENU→NED: [x,y,z]_ned = [y, x, -z]_enu

Prerequisites:
    1. PX4 v1.14+ firmware on FC
    2. Micro XRCE-DDS Agent running on companion computer:
         pip3 install --user uxrce_dds_agent    (Python version)
         # or C++ version: https://micro.ros.org/docs/overview/xrce_dds
    3. On FC (via MAVLink shell):
         uxrce_dds_client start -t udp -h <companion_ip> -p 8888
         # or for multi-vehicle:
         uxrce_dds_client start -t udp -h <ip> -p 8888 -n uav_1
    4. px4_msgs installed in ROS2 workspace:
         cd ~/ros2_ws/src && git clone https://github.com/PX4/px4_msgs
         cd ~/ros2_ws && colcon build --packages-select px4_msgs
         source install/setup.bash

Usage (two modes):

    Mode 1 — Read from PX4 via uXRCE-DDS (no MAVLink needed):
        bridge = PX4ROS2Bridge(namespace="uav_1")
        bridge.start()
        # Access telemetry: bridge.telemetry

    Mode 2 — Bridge PX4 uXRCE-DDS ↔ DroneResearch Drone object:
        bridge = PX4ROS2Bridge(drone=drone, namespace="uav_1")
        bridge.start()
        bridge.arm()
        bridge.takeoff(altitude=10.0)
"""
import math
import threading
import time
from typing import Callable, Optional

try:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
    _ROS2_OK = True
except ImportError:
    _ROS2_OK = False

try:
    from px4_msgs.msg import (
        VehicleOdometry,
        VehicleStatus,
        BatteryStatus,
        SensorGps,
        VehicleAttitude,
        VehicleLocalPosition,
        VehicleGlobalPosition,
        VehicleCommand,
        OffboardControlMode,
        TrajectorySetpoint,
    )
    _PX4_MSGS_OK = True
except ImportError:
    _PX4_MSGS_OK = False


# ── Frame conversion utilities ─────────────────────────────────────────────────

def ned_to_enu(x: float, y: float, z: float) -> tuple:
    """NED → ENU: [N,E,D] → [E,N,-D]"""
    return (y, x, -z)

def enu_to_ned(x: float, y: float, z: float) -> tuple:
    """ENU → NED: [E,N,U] → [N,E,-U]"""
    return (y, x, -z)

def frd_to_flu(x: float, y: float, z: float) -> tuple:
    """FRD → FLU: pi rotation around X-axis: [F,R,D] → [F,-R,-D]"""
    return (x, -y, -z)

def quat_ned_to_enu(w: float, x: float, y: float, z: float) -> tuple:
    """Rotate quaternion from NED/FRD to ENU/FLU frame."""
    # Apply -pi/2 around Z then pi around X
    # Simplified: swap and negate specific components
    return (w, y, x, -z)


# ── PX4 vehicle command IDs ────────────────────────────────────────────────────

class VehicleCommandId:
    ARM_DISARM      = 400
    TAKEOFF         = 22
    LAND            = 21
    RTL             = 20
    SET_MODE        = 176


class PX4ROS2Bridge:
    """
    Bridges DroneResearch ↔ PX4 via uXRCE-DDS (the correct PX4 v1.14 way).

    Can operate in two modes:
    1. Standalone: reads PX4 uORB topics, fills internal telemetry dict
    2. Paired: syncs PX4 telemetry to a DroneResearch Drone object + sends commands

    Parameters
    ----------
    drone       : Optional Drone instance to sync telemetry to
    namespace   : PX4 uXRCE-DDS namespace (e.g. "uav_1" → /uav_1/fmu/*)
                  Leave empty for single-vehicle default (/fmu/*)
    publish_hz  : Control setpoint publish rate (must be >2Hz for offboard mode)
    """

    def __init__(
        self,
        drone=None,
        namespace:   str   = "",
        publish_hz:  float = 10.0,
    ):
        if not _ROS2_OK:
            raise ImportError("rclpy not found — install ROS2 Humble+")
        if not _PX4_MSGS_OK:
            raise ImportError(
                "px4_msgs not found.\n"
                "cd ~/ros2_ws/src && git clone https://github.com/PX4/px4_msgs\n"
                "cd ~/ros2_ws && colcon build --packages-select px4_msgs\n"
                "source install/setup.bash"
            )
        self._drone     = drone
        self._ns_prefix = f"/{namespace}" if namespace else ""
        self._hz        = publish_hz
        self._node: Optional[Node] = None
        self._thread: Optional[threading.Thread] = None
        self._running   = False

        # Internal telemetry (filled from uXRCE-DDS topics)
        self.telemetry: dict = {
            "armed":        False,
            "flight_mode":  0,
            "lat":          0.0,
            "lon":          0.0,
            "alt":          0.0,
            "alt_rel":      0.0,
            "vx":           0.0,
            "vy":           0.0,
            "vz":           0.0,
            "roll":         0.0,
            "pitch":        0.0,
            "yaw":          0.0,
            "battery_pct":  -1.0,
            "battery_v":    0.0,
            "gps_fix":      0,
            "satellites":   0,
        }
        self._offboard_active  = False
        self._setpoint: Optional[dict] = None
        self._callbacks: dict = {}

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._spin, daemon=True, name="px4-ros2-bridge"
        )
        self._thread.start()
        time.sleep(0.5)
        print(f"[px4-bridge] Started. Namespace: '{self._ns_prefix or '/'}'")
        print(f"[px4-bridge] Listening on {self._ns_prefix}/fmu/out/*")

    def stop(self):
        self._running = False
        if rclpy.ok():
            rclpy.shutdown()

    # ── Vehicle commands (PX4 VehicleCommand) ─────────────────────────────

    def arm(self):
        self._send_vehicle_command(VehicleCommandId.ARM_DISARM, param1=1.0)

    def disarm(self):
        self._send_vehicle_command(VehicleCommandId.ARM_DISARM, param1=0.0)

    def takeoff(self, altitude: float = 10.0):
        self._send_vehicle_command(VehicleCommandId.TAKEOFF, param7=altitude)

    def land(self):
        self._send_vehicle_command(VehicleCommandId.LAND)

    def rtl(self):
        self._send_vehicle_command(VehicleCommandId.RTL)

    def set_offboard_mode(self):
        """Switch to OFFBOARD mode (required before sending setpoints)."""
        self._send_vehicle_command(
            VehicleCommandId.SET_MODE,
            param1=1.0,    # MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
            param2=6.0,    # PX4 OFFBOARD mode
        )

    # ── Offboard setpoints ─────────────────────────────────────────────────

    def set_position_setpoint_ned(
        self, north: float, east: float, down: float, yaw: float = 0.0
    ):
        """
        Set position setpoint in NED frame (PX4 native).
        Call this at >2Hz while in OFFBOARD mode or PX4 will disengage.
        """
        self._offboard_active = True
        self._setpoint = {
            "type": "position",
            "x": north, "y": east, "z": down, "yaw": yaw,
        }

    def set_position_setpoint_enu(
        self, east: float, north: float, up: float, yaw: float = 0.0
    ):
        """Set position setpoint in ENU frame (auto-converts to NED)."""
        n, e, d = enu_to_ned(east, north, up)
        self.set_position_setpoint_ned(n, e, d, yaw)

    def set_velocity_setpoint_ned(
        self, vn: float, ve: float, vd: float, yaw_rate: float = 0.0
    ):
        """Set velocity setpoint in NED frame."""
        self._offboard_active = True
        self._setpoint = {
            "type": "velocity",
            "vx": vn, "vy": ve, "vz": vd, "yawspeed": yaw_rate,
        }

    def stop_offboard(self):
        self._offboard_active = False
        self._setpoint = None

    # ── Events ────────────────────────────────────────────────────────────

    def on(self, event: str, cb: Callable):
        """Register callback. Events: 'telemetry', 'armed', 'mode'"""
        self._callbacks.setdefault(event, []).append(cb)

    # ── Internal ──────────────────────────────────────────────────────────

    def _spin(self):
        rclpy.init()
        self._node = _PX4Node(
            ns_prefix       = self._ns_prefix,
            hz              = self._hz,
            on_telemetry    = self._on_telemetry,
            get_setpoint    = lambda: self._setpoint,
            offboard_active = lambda: self._offboard_active,
        )
        try:
            rclpy.spin(self._node)
        except Exception as e:
            print(f"[px4-bridge] ROS2 error: {e}")
        finally:
            self._node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()

    def _send_vehicle_command(self, cmd: int, **params):
        if self._node:
            self._node.send_vehicle_command(cmd, **params)
        else:
            print(f"[px4-bridge] Node not ready — command {cmd} dropped")

    def _on_telemetry(self, data: dict):
        self.telemetry.update(data)
        # Sync to DroneResearch Drone if paired
        if self._drone:
            t = self._drone._conn.telemetry
            t.lat         = data.get("lat",         t.lat)
            t.lon         = data.get("lon",         t.lon)
            t.alt         = data.get("alt",         t.alt)
            t.alt_rel     = data.get("alt_rel",     t.alt_rel)
            t.roll        = data.get("roll",        t.roll)
            t.pitch       = data.get("pitch",       t.pitch)
            t.yaw         = data.get("yaw",         t.yaw)
            t.battery_pct = data.get("battery_pct", t.battery_pct)
            t.battery_v   = data.get("battery_v",   t.battery_v)
            t.armed       = data.get("armed",       t.armed)
        # Fire callbacks
        for cb in self._callbacks.get("telemetry", []):
            try:
                cb(data)
            except Exception as e:
                print(f"[px4-bridge] callback error: {e}")


if _ROS2_OK and _PX4_MSGS_OK:
    class _PX4Node(Node):
        def __init__(self, ns_prefix, hz, on_telemetry, get_setpoint, offboard_active):
            super().__init__("droneresearch_px4_bridge")
            self._ns          = ns_prefix
            self._on_tel      = on_telemetry
            self._get_sp      = get_setpoint
            self._is_offboard = offboard_active

            # PX4 requires sensor_data QoS for subscriptions
            qos = QoSProfile(
                reliability=QoSReliabilityPolicy.BEST_EFFORT,
                history=QoSHistoryPolicy.KEEP_LAST,
                depth=5,
            )

            # ── Subscribers (PX4 → ROS2) ──────────────────────────────────
            self.create_subscription(
                VehicleGlobalPosition,
                f"{ns_prefix}/fmu/out/vehicle_global_position",
                self._cb_global_pos, qos,
            )
            self.create_subscription(
                VehicleLocalPosition,
                f"{ns_prefix}/fmu/out/vehicle_local_position",
                self._cb_local_pos, qos,
            )
            self.create_subscription(
                VehicleAttitude,
                f"{ns_prefix}/fmu/out/vehicle_attitude",
                self._cb_attitude, qos,
            )
            self.create_subscription(
                VehicleStatus,
                f"{ns_prefix}/fmu/out/vehicle_status",
                self._cb_status, qos,
            )
            self.create_subscription(
                BatteryStatus,
                f"{ns_prefix}/fmu/out/battery_status",
                self._cb_battery, qos,
            )
            self.create_subscription(
                SensorGps,
                f"{ns_prefix}/fmu/out/vehicle_gps_position",
                self._cb_gps, qos,
            )

            # ── Publishers (ROS2 → PX4) ───────────────────────────────────
            self._pub_cmd = self.create_publisher(
                VehicleCommand,
                f"{ns_prefix}/fmu/in/vehicle_command", 10,
            )
            self._pub_offboard = self.create_publisher(
                OffboardControlMode,
                f"{ns_prefix}/fmu/in/offboard_control_mode", 10,
            )
            self._pub_traj = self.create_publisher(
                TrajectorySetpoint,
                f"{ns_prefix}/fmu/in/trajectory_setpoint", 10,
            )

            # Publish setpoints at configured rate
            self.create_timer(1.0 / hz, self._publish_setpoints)

            self._arm_state   = False
            self._flight_mode = 0

        # ── Subscribers ───────────────────────────────────────────────────

        def _cb_global_pos(self, msg: VehicleGlobalPosition):
            self._on_tel({
                "lat": msg.lat,
                "lon": msg.lon,
                "alt": msg.alt,
                "alt_rel": msg.alt - msg.alt,   # TODO: home alt
            })

        def _cb_local_pos(self, msg: VehicleLocalPosition):
            # PX4 local pos is NED — convert to ENU for display
            e, n, u = ned_to_enu(msg.x, msg.y, msg.z)
            ve, vn, vu = ned_to_enu(msg.vx, msg.vy, msg.vz)
            self._on_tel({
                "alt_rel": u,
                "vx": vn, "vy": ve, "vz": vu,
            })

        def _cb_attitude(self, msg: VehicleAttitude):
            # PX4 quaternion is FRD/NED, convert to ENU roll/pitch/yaw
            q = msg.q
            # q = [w, x, y, z] in PX4
            w, x, y, z = q[0], q[1], q[2], q[3]
            # Convert FRD→FLU: rotate pi around X
            x_flu, y_flu, z_flu = frd_to_flu(x, y, z)
            # Euler from quaternion (FLU)
            roll  = math.degrees(math.atan2(2*(w*x_flu + y_flu*z_flu), 1 - 2*(x_flu**2 + y_flu**2)))
            pitch = math.degrees(math.asin(max(-1, min(1, 2*(w*y_flu - z_flu*x_flu)))))
            yaw   = math.degrees(math.atan2(2*(w*z_flu + x_flu*y_flu), 1 - 2*(y_flu**2 + z_flu**2))) % 360
            self._on_tel({"roll": roll, "pitch": pitch, "yaw": yaw})

        def _cb_status(self, msg: VehicleStatus):
            armed = msg.arming_state == 2   # ARMING_STATE_ARMED
            self._arm_state   = armed
            self._flight_mode = msg.nav_state
            self._on_tel({"armed": armed, "flight_mode": msg.nav_state})

        def _cb_battery(self, msg: BatteryStatus):
            self._on_tel({
                "battery_pct": msg.remaining * 100.0,
                "battery_v":   msg.voltage_v,
            })

        def _cb_gps(self, msg: SensorGps):
            self._on_tel({
                "gps_fix":    msg.fix_type,
                "satellites": msg.satellites_used,
            })

        # ── Publishers ────────────────────────────────────────────────────

        def _publish_setpoints(self):
            sp = self._get_sp()
            if not self._is_offboard() or sp is None:
                return
            now = self.get_clock().now().to_msg()

            # Offboard control mode (must be sent to keep PX4 in offboard)
            ocm = OffboardControlMode()
            ocm.timestamp  = self.get_clock().now().nanoseconds // 1000
            ocm.position   = sp["type"] == "position"
            ocm.velocity   = sp["type"] == "velocity"
            ocm.acceleration = False
            ocm.attitude   = False
            ocm.body_rate  = False
            self._pub_offboard.publish(ocm)

            # Trajectory setpoint (NED frame — PX4 native)
            ts = TrajectorySetpoint()
            ts.timestamp = ocm.timestamp
            if sp["type"] == "position":
                ts.position    = [sp["x"], sp["y"], sp["z"]]
                ts.yaw         = sp.get("yaw", float("nan"))
                ts.velocity    = [float("nan")] * 3
                ts.acceleration = [float("nan")] * 3
            elif sp["type"] == "velocity":
                ts.velocity    = [sp["vx"], sp["vy"], sp["vz"]]
                ts.yawspeed    = sp.get("yawspeed", float("nan"))
                ts.position    = [float("nan")] * 3
            self._pub_traj.publish(ts)

        def send_vehicle_command(self, command: int, **params):
            cmd = VehicleCommand()
            cmd.timestamp         = self.get_clock().now().nanoseconds // 1000
            cmd.command           = command
            cmd.param1            = float(params.get("param1", 0.0))
            cmd.param2            = float(params.get("param2", 0.0))
            cmd.param3            = float(params.get("param3", 0.0))
            cmd.param4            = float(params.get("param4", 0.0))
            cmd.param5            = float(params.get("param5", 0.0))
            cmd.param6            = float(params.get("param6", 0.0))
            cmd.param7            = float(params.get("param7", 0.0))
            cmd.target_system     = 1
            cmd.target_component  = 1
            cmd.source_system     = 255
            cmd.source_component  = 0
            cmd.from_external     = True
            self._pub_cmd.publish(cmd)

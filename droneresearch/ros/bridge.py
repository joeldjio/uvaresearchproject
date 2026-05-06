"""
ROS2Bridge — bidirectional MAVLink ↔ ROS2 bridge.

Graceful fallback: works without ROS2 installed (stub mode).

Topics published (MAVLink → ROS2):
    /droneresearch/{id}/attitude      geometry_msgs/Vector3
    /droneresearch/{id}/gps           sensor_msgs/NavSatFix
    /droneresearch/{id}/battery       sensor_msgs/BatteryState
    /droneresearch/{id}/mode          std_msgs/String
    /droneresearch/{id}/telemetry     std_msgs/String (JSON)

Topics subscribed (ROS2 → MAVLink):
    /droneresearch/{id}/cmd/mode      std_msgs/String
    /droneresearch/{id}/cmd/arm       std_msgs/Bool
    /droneresearch/{id}/cmd/goto      geometry_msgs/Point (x=lat,y=lon,z=alt)

Usage:
    bridge = ROS2Bridge(drone)
    bridge.start()
    # runs until bridge.stop()
"""
import json
import threading
import time
from typing import Optional

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String, Bool
    from geometry_msgs.msg import Vector3, Point
    from sensor_msgs.msg import NavSatFix, BatteryState
    _ROS2_AVAILABLE = True
except ImportError:
    _ROS2_AVAILABLE = False


class ROS2Bridge:
    def __init__(self, drone, node_name: str = None):
        self._drone     = drone
        self._node_name = node_name or f"droneresearch_{drone.id}"
        self._node      = None
        self._thread    = None
        self._running   = False
        self.available  = _ROS2_AVAILABLE

    def start(self):
        if not _ROS2_AVAILABLE:
            print("[ros2] rclpy not available — bridge running in stub mode")
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._run, daemon=True, name="ros2-bridge"
        )
        self._thread.start()

    def stop(self):
        self._running = False
        if _ROS2_AVAILABLE and rclpy.ok():
            rclpy.shutdown()

    def _run(self):
        rclpy.init()
        self._node = _DroneNode(self._node_name, self._drone)
        try:
            rclpy.spin(self._node)
        except Exception as e:
            print(f"[ros2] node error: {e}")
        finally:
            self._node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()


if _ROS2_AVAILABLE:
    class _DroneNode(Node):
        PUBLISH_HZ = 10

        def __init__(self, name: str, drone):
            super().__init__(name)
            self._drone  = drone
            did          = drone.id

            # Publishers
            self._pub_att  = self.create_publisher(Vector3,      f"/droneresearch/{did}/attitude",  10)
            self._pub_gps  = self.create_publisher(NavSatFix,    f"/droneresearch/{did}/gps",       10)
            self._pub_bat  = self.create_publisher(BatteryState, f"/droneresearch/{did}/battery",   10)
            self._pub_mode = self.create_publisher(String,       f"/droneresearch/{did}/mode",      10)
            self._pub_tel  = self.create_publisher(String,       f"/droneresearch/{did}/telemetry", 10)

            # Subscribers
            self.create_subscription(
                String, f"/droneresearch/{did}/cmd/mode",
                lambda msg: drone.set_mode(msg.data), 10
            )
            self.create_subscription(
                Bool, f"/droneresearch/{did}/cmd/arm",
                lambda msg: drone.arm() if msg.data else drone.disarm(), 10
            )
            self.create_subscription(
                Point, f"/droneresearch/{did}/cmd/goto",
                lambda msg: drone.goto(msg.x, msg.y, msg.z), 10
            )

            # Publish timer
            self.create_timer(1.0 / self.PUBLISH_HZ, self._publish)

        def _publish(self):
            t = self._drone.telemetry

            att = Vector3()
            att.x, att.y, att.z = t.roll, t.pitch, t.yaw
            self._pub_att.publish(att)

            gps = NavSatFix()
            gps.latitude, gps.longitude, gps.altitude = t.lat, t.lon, t.alt
            gps.status.status = 0 if t.gps_fix >= 3 else -1
            self._pub_gps.publish(gps)

            bat = BatteryState()
            bat.voltage    = t.battery_v
            bat.percentage = t.battery_pct / 100.0 if t.battery_pct >= 0 else -1.0
            self._pub_bat.publish(bat)

            self._pub_mode.publish(String(data=t.flight_mode))
            self._pub_tel.publish(String(data=json.dumps(t.snapshot())))

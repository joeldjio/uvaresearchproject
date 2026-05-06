"""
Example: Start ROS2 bridge — publish all telemetry as ROS topics.

Requires ROS2 + rclpy installed.

Run:
    python examples/ros2_bridge.py --port tcp:127.0.0.1:5760

Then in another terminal:
    ros2 topic list
    ros2 topic echo /droneresearch/drone/attitude
    ros2 topic echo /droneresearch/drone/gps
"""
import argparse
import time
from droneresearch import Drone
from droneresearch.ros import ROS2Bridge

parser = argparse.ArgumentParser()
parser.add_argument("--port", default="tcp:127.0.0.1:5760")
args = parser.parse_args()

drone = Drone(args.port)
print(f"Connecting ...")
drone.connect()

bridge = ROS2Bridge(drone)
if bridge.available:
    print("ROS2 bridge starting ...")
    bridge.start()
    print("Publishing. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    bridge.stop()
else:
    print("ROS2 not available. Install rclpy first.")

drone.disconnect()

"""
Example: Autonomous 3D Frontier Exploration

Uses the larics uav_frontier_exploration_3d ROS package as planner.
DroneResearch provides:
  - MAVLink telemetry → ROS2 Odometry
  - Point cloud forwarding (from depth cam topic)
  - Receives frontier goals → drone.goto()

Prerequisites:
    1. ROS2 Humble installed
    2. larics explorer built:
         cd ~/ros2_ws/src
         git clone https://github.com/larics/uav_frontier_exploration_3d
         cd ~/ros2_ws && colcon build
         source ~/ros2_ws/install/setup.bash
    3. Explorer node running:
         ros2 launch uav_frontier_exploration_3d frontier_server.launch.py
    4. Drone connected via MAVLink

Run:
    python examples/autonomous_exploration.py --port tcp:127.0.0.1:5760
"""
import argparse
import time
from droneresearch import Drone
from droneresearch.exploration import FrontierExplorationBridge

parser = argparse.ArgumentParser()
parser.add_argument("--port",    default="tcp:127.0.0.1:5760")
parser.add_argument("--alt",     type=float, default=5.0,  help="Exploration altitude (m)")
parser.add_argument("--cloud",   default=None,             help="ROS2 PointCloud2 topic from depth cam")
parser.add_argument("--timeout", type=float, default=600.0, help="Max exploration time (s)")
args = parser.parse_args()

# ── Connect drone ─────────────────────────────────────────────────────────────
drone = Drone(args.port, drone_id="explorer")
print(f"Connecting to {args.port} ...")
if not drone.connect():
    raise SystemExit("Connection failed.")

print(f"Autopilot: {drone.telemetry.autopilot}  |  Mode: {drone.mode}")

# ── Arm and take off ─────────────────────────────────────────────────────────
print("Arming ...")
drone.arm()
print(f"Taking off to {args.alt}m ...")
drone.takeoff(altitude=args.alt)
print("Airborne.")

# ── Start frontier exploration ────────────────────────────────────────────────
def on_goal_reached():
    print(f"[explorer] Frontier reached — pos: {drone.lat:.5f}, {drone.lon:.5f}, {drone.altitude:.1f}m")

def on_volume(vol):
    print(f"[explorer] Explored: {vol['explored_pct']:.1f}%  "
          f"(free={vol['free']:.1f}m³  unmapped={vol['unmapped']:.1f}m³)")

bridge = FrontierExplorationBridge(
    drone,
    point_cloud_topic=args.cloud,
    on_goal_reached=on_goal_reached,
    on_volume_update=on_volume,
)
bridge.start()
print("Frontier bridge started.")

bridge.exploration_start()
print("Exploration running. Waiting for completion or Ctrl+C ...")

try:
    done = bridge.wait_until_done(timeout=args.timeout)
    if done:
        print("Exploration complete!")
    else:
        print("Exploration timeout reached.")
except KeyboardInterrupt:
    print("\nStopped by user.")
finally:
    bridge.exploration_stop()
    bridge.save_octomap(filename="exploration_result", file_path="/tmp")
    print("Map saved to /tmp/exploration_result.ot")

    print("Returning to launch ...")
    drone.rtl()
    drone.wait_for_landing()
    drone.disconnect()
    bridge.stop()
    print("Done.")

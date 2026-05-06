"""
Example: Vision-based drone flocking with vswarm (EPFL LIS).

Each drone runs this script independently — no inter-drone communication.
The vswarm CNN detects neighbors from the camera and computes flocking commands.

Prerequisites:
    1. ROS (Melodic) + vswarm installed:
         cd ~/catkin_ws/src
         git clone https://github.com/lis-epfl/vswarm
         cd ~/catkin_ws && catkin_make
         source devel/setup.bash

    2. Download detection model:
         # see vswarm/docs/installation.md

    3. Launch vswarm nodes (per drone):
         roslaunch vswarm vswarm_onboard.launch

    4. Camera publishing on /camera/image_raw

Run (per drone):
    python examples/vswarm_flocking.py \
        --port tcp:127.0.0.1:5760 \
        --camera /camera/image_raw \
        --duration 120
"""
import argparse
import time
from droneresearch import Drone
from droneresearch.exploration import VSwarmBridge

parser = argparse.ArgumentParser()
parser.add_argument("--port",     default="tcp:127.0.0.1:5760")
parser.add_argument("--camera",   default="/camera/image_raw")
parser.add_argument("--caminfo",  default="/camera/camera_info")
parser.add_argument("--alt",      type=float, default=2.5,  help="Hover altitude (m)")
parser.add_argument("--duration", type=float, default=120.0, help="Flocking duration (s)")
parser.add_argument("--gain",     type=float, default=1.0,   help="Velocity→position gain")
args = parser.parse_args()

drone = Drone(args.port, drone_id="flock_agent")
print(f"Connecting to {args.port} ...")
if not drone.connect():
    raise SystemExit("Connection failed.")

# Status callback
@drone.on("statustext")
def on_status(text, sev):
    if sev <= 4:
        print(f"[FC] {text}")

# Start vswarm bridge
bridge = VSwarmBridge(
    drone,
    camera_topic    = args.camera,
    camera_info_topic = args.caminfo,
    cmd_vel_gain    = args.gain,
    on_cmd_vel      = lambda vx, vy, vz, yr: print(
        f"[vswarm] cmd_vel  vx={vx:.2f}  vy={vy:.2f}  vz={vz:.2f}  yaw_rate={yr:.2f}"
    ),
)
bridge.start()
print("vswarm bridge started.")

# Arm and take off
print("Arming ...")
drone.arm()
print(f"Taking off to {args.alt}m ...")
drone.takeoff(altitude=args.alt)
print("Hovering.")

# Start flocking
print("Starting flocking algorithm ...")
bridge.start_flocking()
print(f"Flocking for {args.duration}s. Ctrl+C to stop.")

try:
    time.sleep(args.duration)
except KeyboardInterrupt:
    print("\nStopped by user.")
finally:
    print("Stopping flocking ...")
    bridge.stop_flocking()
    print("Landing ...")
    drone.land()
    drone.disconnect()
    bridge.stop()
    print("Done.")

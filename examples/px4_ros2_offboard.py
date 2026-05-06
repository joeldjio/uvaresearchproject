"""
Example: PX4 offboard control via uXRCE-DDS + ROS2 (correct PX4 v1.14 way).

This uses the native PX4 ↔ ROS2 communication path:
    PX4 FC → uXRCE-DDS client → network → XRCE-DDS agent → /fmu/out/* topics

No MAVLink required for control — direct uORB access.

Prerequisites:
    1. PX4 v1.14+ on FC

    2. Micro XRCE-DDS Agent on companion (run once):
         pip3 install --user micro-xrce-dds-agent
         # or: sudo snap install micro-xrce-dds-agent
         MicroXRCEAgent udp4 -p 8888

    3. On FC (via MAVLink shell or at boot):
         uxrce_dds_client start -t udp -h 192.168.1.10 -p 8888

    4. px4_msgs in ROS2 workspace:
         cd ~/ros2_ws/src && git clone https://github.com/PX4/px4_msgs
         cd ~/ros2_ws && colcon build --packages-select px4_msgs
         source install/setup.bash

    5. For SITL testing:
         PX4_UXRCE_DDS_NS=uav_1 make px4_sitl gz_x500

Run:
    source ~/ros2_ws/install/setup.bash
    python3 examples/px4_ros2_offboard.py
"""
import math
import time
from droneresearch.ros.px4_bridge import PX4ROS2Bridge, ned_to_enu, enu_to_ned

# Single vehicle (default namespace)
bridge = PX4ROS2Bridge(namespace="uav_1")

@bridge.on("telemetry")
def on_tel(data):
    if data.get("armed") is not None:
        print(f"  armed={data.get('armed')}  mode={data.get('flight_mode')}  "
              f"alt={data.get('alt_rel', 0):.1f}m  bat={data.get('battery_pct', -1):.0f}%")

bridge.start()
print("Bridge started. Waiting for PX4...")
time.sleep(3)

print(f"Current telemetry: {bridge.telemetry}")

# Arm + takeoff via VehicleCommand (PX4 native)
print("Arming...")
bridge.arm()
time.sleep(2)

print("Taking off to 10m...")
bridge.takeoff(altitude=10.0)
time.sleep(5)

# Switch to OFFBOARD mode
print("Switching to OFFBOARD mode...")
bridge.set_offboard_mode()

# Send position setpoints in ENU (auto-converted to NED internally)
print("Flying 5m north...")
bridge.set_position_setpoint_enu(east=0.0, north=5.0, up=10.0)
time.sleep(5)

print("Flying circle...")
for i in range(36):
    angle = math.radians(i * 10)
    bridge.set_position_setpoint_enu(
        east=5.0 * math.sin(angle),
        north=5.0 * math.cos(angle),
        up=10.0,
        yaw=angle,
    )
    time.sleep(0.5)

print("Landing...")
bridge.stop_offboard()
bridge.land()
time.sleep(5)

bridge.stop()
print("Done.")

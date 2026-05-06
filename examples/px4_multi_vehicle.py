"""
Example: PX4 multi-vehicle swarm via uXRCE-DDS namespaces.

PX4 supports per-vehicle namespaces for multi-vehicle:
    uxrce_dds_client start -n uav_1 → /uav_1/fmu/out/*
    uxrce_dds_client start -n uav_2 → /uav_2/fmu/out/*
    uxrce_dds_client start -n uav_3 → /uav_3/fmu/out/*

SITL multi-vehicle:
    PX4_UXRCE_DDS_NS=uav_1 make px4_sitl gz_x500
    PX4_UXRCE_DDS_NS=uav_2 PX4_SIM_PORT_OFFSET=10 make px4_sitl gz_x500

Run:
    source ~/ros2_ws/install/setup.bash
    python3 examples/px4_multi_vehicle.py
"""
import time
import math
from droneresearch.ros.px4_bridge import PX4ROS2Bridge

VEHICLE_COUNT = 3
FORMATION_RADIUS = 5.0    # meters
CRUISE_ALT       = 10.0   # meters

bridges = [
    PX4ROS2Bridge(namespace=f"uav_{i+1}")
    for i in range(VEHICLE_COUNT)
]

# Start all bridges
for b in bridges:
    b.start()

print(f"Started {VEHICLE_COUNT} PX4 bridges.")
time.sleep(3)

# Print status
for i, b in enumerate(bridges):
    t = b.telemetry
    print(f"uav_{i+1}: armed={t['armed']}  lat={t['lat']:.6f}  bat={t['battery_pct']:.0f}%")

# Arm all
print("Arming all vehicles...")
for b in bridges:
    b.arm()
time.sleep(2)

# Takeoff staggered
print("Takeoff (staggered)...")
for b in bridges:
    b.takeoff(altitude=CRUISE_ALT)
    time.sleep(1.5)
time.sleep(5)

# Offboard circle formation
print("Starting circle formation in OFFBOARD mode...")
for b in bridges:
    b.set_offboard_mode()

for step in range(72):   # 360° in 5° steps
    t_now = time.time()
    for i, b in enumerate(bridges):
        # Each vehicle offset by 360/n degrees
        angle = math.radians(step * 5 + i * (360 / VEHICLE_COUNT))
        b.set_position_setpoint_enu(
            east  = FORMATION_RADIUS * math.sin(angle),
            north = FORMATION_RADIUS * math.cos(angle),
            up    = CRUISE_ALT,
            yaw   = angle + math.pi,   # face center
        )
    elapsed = time.time() - t_now
    time.sleep(max(0, 0.5 - elapsed))

# Land all
print("Landing all vehicles...")
for b in bridges:
    b.stop_offboard()
    b.land()
time.sleep(5)

for b in bridges:
    b.stop()

print("Done.")

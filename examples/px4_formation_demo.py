#!/usr/bin/env python3
"""
PX4 Formation Flight Demo

Demonstrates multi-vehicle formation control using PX4ROS2Bridge.
Requires:
- Multiple PX4 SITL instances with uXRCE-DDS
- ROS2 Humble+ with px4_msgs

Usage:
    # Start 3 PX4 SITL instances (in separate terminals):
    cd ~/PX4-Autopilot
    PX4_SYS_AUTOSTART=4001 PX4_GZ_MODEL=x500 ./build/px4_sitl_default/bin/px4 -i 1
    PX4_SYS_AUTOSTART=4001 PX4_GZ_MODEL=x500 ./build/px4_sitl_default/bin/px4 -i 2
    PX4_SYS_AUTOSTART=4001 PX4_GZ_MODEL=x500 ./build/px4_sitl_default/bin/px4 -i 3
    
    # Start uXRCE-DDS Agent:
    MicroXRCEAgent udp4 -p 8888
    
    # Run demo:
    python examples/px4_formation_demo.py
"""
import time
import math

try:
    from droneresearch.ros.px4_formation import PX4FormationController
except ImportError as e:
    print(f"Error: {e}")
    print("Install ROS2 Humble+ and px4_msgs package")
    exit(1)


def main():
    print("=== PX4 Formation Flight Demo ===\n")
    
    # Create formation controller
    print("Creating formation controller...")
    print("  Leader: uav_1")
    print("  Followers: uav_2, uav_3")
    print("  Shape: V-formation")
    print("  Spacing: 5 meters\n")
    
    controller = PX4FormationController(
        leader_ns="uav_1",
        follower_namespaces=["uav_2", "uav_3"],
        shape="v",
        spacing=5.0,
        update_rate_hz=20.0
    )
    
    # Start controller
    print("Starting controller...")
    if not controller.start():
        print("Failed to start controller!")
        return
    print("Controller started!\n")
    
    # Wait for offboard mode readiness (need 10+ setpoints)
    print("Waiting for offboard mode readiness...")
    time.sleep(1.0)
    
    all_ready = False
    for _ in range(30):  # 3 seconds max
        ready_count = sum(
            1 for ns in ["uav_1", "uav_2", "uav_3"]
            if controller.is_offboard_ready(ns)
        )
        if ready_count == 3:
            all_ready = True
            break
        time.sleep(0.1)
    
    if not all_ready:
        print("Warning: Not all vehicles ready for offboard mode")
    else:
        print("All vehicles ready!\n")
    
    # Set initial position (on ground)
    print("Setting initial position (ground)...")
    controller.set_leader_position(north=0, east=0, altitude=0, yaw=0)
    time.sleep(0.5)
    
    # Enable offboard mode
    print("Enabling offboard mode...")
    controller.enable_offboard_all()
    time.sleep(0.5)
    
    # Arm all vehicles
    print("Arming all vehicles...")
    controller.arm_all()
    time.sleep(1.0)
    
    # Takeoff to 10m
    print("\n=== Phase 1: Takeoff ===")
    print("Climbing to 10m altitude...")
    for alt in range(0, 11):
        controller.set_leader_position(north=0, east=0, altitude=alt, yaw=0)
        time.sleep(0.5)
    print("Reached 10m altitude\n")
    
    # Fly forward (North)
    print("=== Phase 2: Fly North ===")
    print("Flying 20m north...")
    for n in range(0, 21):
        controller.set_leader_position(north=n, east=0, altitude=10, yaw=0)
        time.sleep(0.2)
    print("Reached 20m north\n")
    
    # Turn East and fly
    print("=== Phase 3: Turn East ===")
    print("Turning and flying 15m east...")
    yaw = 0
    for e in range(0, 16):
        yaw = math.pi / 2 * (e / 15.0)  # Gradual turn
        controller.set_leader_position(north=20, east=e, altitude=10, yaw=yaw)
        time.sleep(0.2)
    print("Reached 15m east\n")
    
    # Circle maneuver
    print("=== Phase 4: Circle ===")
    print("Flying in circle (radius 10m)...")
    center_n, center_e = 20, 15
    radius = 10
    for i in range(72):  # 360 degrees in 5-degree steps
        angle = math.radians(i * 5)
        n = center_n + radius * math.cos(angle)
        e = center_e + radius * math.sin(angle)
        yaw = angle + math.pi / 2  # Tangent to circle
        controller.set_leader_position(north=n, east=e, altitude=10, yaw=yaw)
        time.sleep(0.1)
    print("Circle complete\n")
    
    # Return to start
    print("=== Phase 5: Return Home ===")
    print("Returning to start position...")
    for i in range(20):
        t = i / 19.0
        n = 20 * (1 - t)
        e = 15 * (1 - t)
        controller.set_leader_position(north=n, east=e, altitude=10, yaw=0)
        time.sleep(0.2)
    print("Back at start\n")
    
    # Land
    print("=== Phase 6: Landing ===")
    print("Landing...")
    for alt in range(10, -1, -1):
        controller.set_leader_position(north=0, east=0, altitude=alt, yaw=0)
        time.sleep(0.5)
    print("Landed\n")
    
    # Disarm
    print("Disarming all vehicles...")
    time.sleep(1.0)
    controller.disarm_all()
    time.sleep(1.0)
    
    # Stop controller
    print("Stopping controller...")
    controller.stop()
    
    print("\n=== Demo Complete ===")
    print("Formation positions:")
    leader_pos = controller.get_leader_position()
    follower_pos = controller.get_follower_positions()
    print(f"  Leader (uav_1): N={leader_pos['north']:.1f}, E={leader_pos['east']:.1f}, Alt={leader_pos['altitude']:.1f}")
    for ns, pos in follower_pos.items():
        print(f"  Follower ({ns}): N={pos['north']:.1f}, E={pos['east']:.1f}, Alt={pos['altitude']:.1f}")


if __name__ == "__main__":
    main()


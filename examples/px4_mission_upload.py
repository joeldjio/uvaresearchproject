#!/usr/bin/env python3
"""
PX4 Mission Upload Example

Demonstrates how to upload and execute waypoint missions on PX4 via uXRCE-DDS.

Requirements:
    - PX4 SITL running with uXRCE-DDS agent
    - ROS2 Humble installed
    - px4_msgs package built

Usage:
    python examples/px4_mission_upload.py
"""

import time
from droneresearch.ros.px4_bridge import PX4ROS2Bridge


def main():
    print("=" * 60)
    print("PX4 Mission Upload Example")
    print("=" * 60)
    
    # Create bridge (connects to /fmu/* topics by default)
    bridge = PX4ROS2Bridge(namespace="", publish_hz=10.0)
    
    try:
        # Start bridge
        print("\n[1/6] Starting PX4 ROS2 bridge...")
        bridge.start()
        time.sleep(2.0)
        
        # Wait for telemetry
        print("[2/6] Waiting for telemetry...")
        for i in range(10):
            if bridge.telemetry.get("armed") is not None:
                print(f"✓ Connected! Armed: {bridge.telemetry['armed']}")
                break
            time.sleep(0.5)
        else:
            print("✗ No telemetry received. Is PX4 SITL running?")
            return
        
        # Arm vehicle
        print("\n[3/6] Arming vehicle...")
        bridge.arm()
        time.sleep(2.0)
        
        if not bridge.telemetry.get("armed"):
            print("✗ Failed to arm. Check PX4 console for errors.")
            return
        print("✓ Armed")
        
        # Takeoff
        print("\n[4/6] Taking off to 10m...")
        bridge.takeoff(altitude=10.0)
        time.sleep(5.0)
        
        alt = bridge.telemetry.get("alt_rel", 0.0)
        print(f"✓ Altitude: {alt:.1f}m")
        
        # Define mission waypoints (around Zurich coordinates)
        waypoints = [
            {
                "lat": 47.397742,
                "lon": 8.545594,
                "alt": 15.0,
                "hold_time": 2.0,
                "accept_radius": 2.0,
            },
            {
                "lat": 47.397842,
                "lon": 8.545694,
                "alt": 20.0,
                "hold_time": 3.0,
                "accept_radius": 2.0,
            },
            {
                "lat": 47.397942,
                "lon": 8.545794,
                "alt": 15.0,
                "hold_time": 2.0,
                "accept_radius": 2.0,
            },
            {
                "lat": 47.397742,
                "lon": 8.545594,
                "alt": 10.0,
                "hold_time": 1.0,
                "accept_radius": 2.0,
            },
        ]
        
        # Upload mission
        print(f"\n[5/6] Uploading mission ({len(waypoints)} waypoints)...")
        success = bridge.upload_mission(waypoints, timeout=10.0)
        
        if not success:
            print("✗ Mission upload failed")
            return
        print("✓ Mission uploaded successfully")
        
        # Start mission
        print("\n[6/6] Starting mission execution...")
        bridge.start_mission()
        print("✓ Mission started (switched to AUTO.MISSION mode)")
        
        # Monitor mission progress
        print("\nMonitoring mission (press Ctrl+C to stop)...")
        print("-" * 60)
        
        try:
            while True:
                tel = bridge.telemetry
                print(
                    f"Alt: {tel.get('alt_rel', 0):.1f}m | "
                    f"Lat: {tel.get('lat', 0):.6f} | "
                    f"Lon: {tel.get('lon', 0):.6f} | "
                    f"Mode: {tel.get('flight_mode', 0)}",
                    end="\r"
                )
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n\nMission monitoring stopped")
        
        # Optional: Pause mission
        # print("\nPausing mission...")
        # bridge.pause_mission()
        # time.sleep(5.0)
        
        # Optional: Resume mission
        # print("Resuming mission...")
        # bridge.start_mission()
        
        # Optional: Clear mission
        # print("\nClearing mission...")
        # bridge.clear_mission()
        
        # Land
        print("\nLanding...")
        bridge.land()
        time.sleep(10.0)
        
        print("✓ Mission complete!")
        
    finally:
        # Cleanup
        print("\nStopping bridge...")
        bridge.stop()
        print("Done.")


if __name__ == "__main__":
    main()


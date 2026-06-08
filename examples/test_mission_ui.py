#!/usr/bin/env python3
"""
Test Mission Management UI with PX4 SITL
=========================================

This script tests the new Mission Management UI in ROS2Panel by:
1. Starting PX4 SITL with Gazebo
2. Launching the UI
3. Demonstrating mission upload, start, pause, clear workflow

Prerequisites:
- PX4-Autopilot installed at ~/PX4-Autopilot
- ROS2 Humble sourced
- px4_msgs installed

Usage:
    python examples/test_mission_ui.py
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from droneresearch.simulation.px4_gazebo import PX4GazeboCluster


def main():
    print("=" * 70)
    print("Mission Management UI Test")
    print("=" * 70)
    
    # Start PX4 SITL
    print("\n[1/3] Starting PX4 SITL with Gazebo...")
    cluster = PX4GazeboCluster(
        num_drones=1,
        px4_dir=str(Path.home() / "PX4-Autopilot"),
        model="x500"
    )
    
    if not cluster.start():
        print("❌ Failed to start SITL")
        return 1
    
    print("✅ SITL started successfully")
    print(f"   Vehicle: px4_1 on namespace /px4_1")
    
    # Wait for SITL to stabilize
    print("\n[2/3] Waiting for SITL to stabilize (5s)...")
    time.sleep(5)
    
    # Launch UI
    print("\n[3/3] Launching UI...")
    print("\n" + "=" * 70)
    print("UI TESTING INSTRUCTIONS:")
    print("=" * 70)
    print("1. Go to ROS2 Panel")
    print("2. Select drone 'px4_1' from dropdown")
    print("3. In Mission Management section:")
    print("   a. Click 'UPLOAD MISSION' → Upload Test Mission")
    print("   b. Click 'ARM' in Vehicle Commands")
    print("   c. Click 'TAKEOFF' (10m)")
    print("   d. Wait for takeoff to complete")
    print("   e. Click '▶ START' to start mission")
    print("   f. Watch progress bar and waypoint counter")
    print("   g. Try '⏸ PAUSE' and '▶ START' again")
    print("   h. Click '✕ CLEAR' to clear mission")
    print("\n4. Check status indicator:")
    print("   - Green pulsing = Mission Active")
    print("   - Green solid = Mission Complete")
    print("   - Red = Mission Failed")
    print("   - Gray = No Mission")
    print("\n5. Press Ctrl+C in terminal to stop SITL")
    print("=" * 70)
    
    # Import and launch UI
    try:
        from tools.ui.app import run as ui_run
        ui_run()
    except KeyboardInterrupt:
        print("\n\n[CLEANUP] Stopping SITL...")
    finally:
        cluster.stop()
        print("✅ SITL stopped")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob

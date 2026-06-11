#!/usr/bin/env python3
"""
PX4 Hardware Connection Test
=============================

Test script for connecting to real PX4 hardware via uXRCE-DDS.

Prerequisites:
    1. PX4 v1.14+ firmware on flight controller
    2. uXRCE-DDS Agent running on companion computer
    3. ROS2 Humble installed
    4. px4_msgs built in ROS2 workspace

Usage:
    # On companion computer (Raspberry Pi):
    MicroXRCEAgent serial --dev /dev/ttyACM0 -b 921600

    # On ground station:
    python examples/px4_hardware_test.py --namespace px4_0

Safety:
    - Remove propellers before testing
    - Have kill switch ready
    - Test in safe environment
"""
import sys
import time
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from droneresearch.ros import PX4ROS2Bridge


def test_connection(namespace: str = "px4_0"):
    """Test connection to PX4 hardware."""
    print(f"\n{'='*60}")
    print(f"  PX4 Hardware Connection Test")
    print(f"  Namespace: {namespace}")
    print(f"{'='*60}\n")
    
    # Create bridge
    print(f"[1/5] Creating PX4ROS2Bridge...")
    bridge = PX4ROS2Bridge(namespace=namespace)
    
    # Start bridge
    print(f"[2/5] Starting bridge...")
    bridge.start()
    
    # Wait for telemetry
    print(f"[3/5] Waiting for telemetry (5 seconds)...")
    time.sleep(5)
    
    # Check telemetry
    print(f"[4/5] Checking telemetry...")
    telem = bridge.telemetry
    
    if not telem:
        print("❌ No telemetry received!")
        print("\nTroubleshooting:")
        print("  1. Check uXRCE-DDS Agent is running")
        print("  2. Check ROS2 topics: ros2 topic list | grep fmu")
        print("  3. Check namespace matches")
        bridge.stop()
        return False
    
    print("✓ Telemetry received!")
    print(f"\n  Position: N={telem.get('ned_north', 0):.2f}m, "
          f"E={telem.get('ned_east', 0):.2f}m, "
          f"D={telem.get('ned_down', 0):.2f}m")
    print(f"  Attitude: Roll={telem.get('roll', 0):.1f}°, "
          f"Pitch={telem.get('pitch', 0):.1f}°, "
          f"Yaw={telem.get('yaw', 0):.1f}°")
    print(f"  Battery: {telem.get('battery_voltage', 0):.2f}V "
          f"({telem.get('battery_remaining', 0):.0f}%)")
    print(f"  Mode: {telem.get('mode', 'UNKNOWN')}")
    print(f"  Armed: {telem.get('armed', False)}")
    
    # Test commands (safe, no actual movement)
    print(f"\n[5/5] Testing command interface...")
    
    # Note: These commands are safe to test (won't move drone)
    # but you should still have propellers removed
    
    print("  Testing mode change (to OFFBOARD)...")
    success = bridge.set_offboard_mode()
    print(f"  {'✓' if success else '❌'} Offboard mode: {success}")
    
    print("  Testing position setpoint (no movement, just command)...")
    bridge.set_position_setpoint_ned(0, 0, -2, 0)  # 2m altitude
    print("  ✓ Position setpoint sent")
    
    time.sleep(1)
    
    # Stop bridge
    print(f"\nStopping bridge...")
    bridge.stop()
    
    print(f"\n{'='*60}")
    print(f"  Test Complete!")
    print(f"{'='*60}\n")
    
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test PX4 hardware connection")
    parser.add_argument(
        "--namespace",
        type=str,
        default="px4_0",
        help="PX4 namespace (default: px4_0)"
    )
    args = parser.parse_args()
    
    try:
        success = test_connection(args.namespace)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


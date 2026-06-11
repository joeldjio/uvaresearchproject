#!/usr/bin/env python3
"""
Frame Conversion Demo
=====================

Demonstrates NED ↔ ENU frame conversion for PX4 integration.

This example shows:
1. How PX4 uses NED (North-East-Down) frame
2. How ROS2 uses ENU (East-North-Up) frame
3. Conversion between the two coordinate systems
4. Practical examples with positions and velocities

Usage:
    python examples/frame_conversion_demo.py
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from droneresearch.ros.px4_bridge import ned_to_enu, enu_to_ned, frd_to_flu


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def demo_basic_conversion():
    """Demonstrate basic NED to ENU conversion."""
    print_section("Basic Frame Conversion")
    
    # Example 1: Position at origin
    print("Example 1: Origin")
    print("  NED: North=0, East=0, Down=0")
    e, n, u = ned_to_enu(0.0, 0.0, 0.0)
    print(f"  ENU: East={e:.1f}, North={n:.1f}, Up={u:.1f}")
    
    # Example 2: Position north and east
    print("\nExample 2: 10m North, 5m East, at ground level")
    print("  NED: North=10, East=5, Down=0")
    e, n, u = ned_to_enu(10.0, 5.0, 0.0)
    print(f"  ENU: East={e:.1f}, North={n:.1f}, Up={u:.1f}")
    
    # Example 3: Position with altitude
    print("\nExample 3: 10m North, 5m East, 20m altitude")
    print("  NED: North=10, East=5, Down=-20 (negative = up)")
    e, n, u = ned_to_enu(10.0, 5.0, -20.0)
    print(f"  ENU: East={e:.1f}, North={n:.1f}, Up={u:.1f} (positive = up)")


def demo_altitude_convention():
    """Demonstrate altitude sign convention."""
    print_section("Altitude Sign Convention")
    
    print("PX4 NED Frame:")
    print("  - Down is POSITIVE")
    print("  - Altitude is NEGATIVE")
    print("  - Ground level: Down=0")
    print("  - 10m altitude: Down=-10")
    
    print("\nROS2 ENU Frame:")
    print("  - Up is POSITIVE")
    print("  - Altitude is POSITIVE")
    print("  - Ground level: Up=0")
    print("  - 10m altitude: Up=10")
    
    print("\nConversion Examples:")
    altitudes = [0, 5, 10, 20, 50]
    for alt in altitudes:
        ned_down = -alt
        _, _, enu_up = ned_to_enu(0.0, 0.0, ned_down)
        print(f"  {alt}m altitude: NED Down={ned_down:6.1f} -> ENU Up={enu_up:6.1f}")


def demo_velocity_conversion():
    """Demonstrate velocity vector conversion."""
    print_section("Velocity Vector Conversion")
    
    # Example 1: Moving north
    print("Example 1: Moving 5 m/s North")
    print("  NED velocity: vN=5, vE=0, vD=0")
    ve, vn, vu = ned_to_enu(5.0, 0.0, 0.0)
    print(f"  ENU velocity: vE={ve:.1f}, vN={vn:.1f}, vU={vu:.1f}")
    
    # Example 2: Climbing
    print("\nExample 2: Climbing at 2 m/s")
    print("  NED velocity: vN=0, vE=0, vD=-2 (negative = up)")
    ve, vn, vu = ned_to_enu(0.0, 0.0, -2.0)
    print(f"  ENU velocity: vE={ve:.1f}, vN={vn:.1f}, vU={vu:.1f} (positive = up)")
    
    # Example 3: Combined motion
    print("\nExample 3: Moving NE while climbing")
    print("  NED velocity: vN=3, vE=4, vD=-1")
    ve, vn, vu = ned_to_enu(3.0, 4.0, -1.0)
    print(f"  ENU velocity: vE={ve:.1f}, vN={vn:.1f}, vU={vu:.1f}")
    speed = (ve**2 + vn**2 + vu**2)**0.5
    print(f"  Total speed: {speed:.2f} m/s")


def demo_body_frame():
    """Demonstrate body frame conversion (FRD ↔ FLU)."""
    print_section("Body Frame Conversion (FRD <-> FLU)")
    
    print("PX4 uses FRD (Forward-Right-Down):")
    print("  - X: Forward")
    print("  - Y: Right")
    print("  - Z: Down")
    
    print("\nROS2 uses FLU (Forward-Left-Up):")
    print("  - X: Forward")
    print("  - Y: Left")
    print("  - Z: Up")
    
    print("\nConversion Examples:")
    
    # Example 1: Forward motion
    print("\nExample 1: Moving forward at 5 m/s")
    print("  FRD: Forward=5, Right=0, Down=0")
    f, l, u = frd_to_flu(5.0, 0.0, 0.0)
    print(f"  FLU: Forward={f:.1f}, Left={l:.1f}, Up={u:.1f}")
    
    # Example 2: Banking right
    print("\nExample 2: Banking right (moving right at 2 m/s)")
    print("  FRD: Forward=0, Right=2, Down=0")
    f, l, u = frd_to_flu(0.0, 2.0, 0.0)
    print(f"  FLU: Forward={f:.1f}, Left={l:.1f} (negative = right), Up={u:.1f}")
    
    # Example 3: Descending
    print("\nExample 3: Descending at 1 m/s")
    print("  FRD: Forward=0, Right=0, Down=1")
    f, l, u = frd_to_flu(0.0, 0.0, 1.0)
    print(f"  FLU: Forward={f:.1f}, Left={l:.1f}, Up={u:.1f} (negative = down)")


def demo_roundtrip():
    """Demonstrate roundtrip conversion."""
    print_section("Roundtrip Conversion (NED -> ENU -> NED)")
    
    # Original NED position
    ned_n, ned_e, ned_d = 15.0, 25.0, -10.0
    print(f"Original NED: North={ned_n:.1f}, East={ned_e:.1f}, Down={ned_d:.1f}")
    
    # Convert to ENU
    enu_e, enu_n, enu_u = ned_to_enu(ned_n, ned_e, ned_d)
    print(f"Converted to ENU: East={enu_e:.1f}, North={enu_n:.1f}, Up={enu_u:.1f}")
    
    # Convert back to NED
    back_n, back_e, back_d = enu_to_ned(enu_e, enu_n, enu_u)
    print(f"Back to NED: North={back_n:.1f}, East={back_e:.1f}, Down={back_d:.1f}")
    
    # Check if values match
    match = (abs(back_n - ned_n) < 0.001 and 
             abs(back_e - ned_e) < 0.001 and 
             abs(back_d - ned_d) < 0.001)
    print(f"\nRoundtrip successful: {match}")


def demo_practical_scenario():
    """Demonstrate a practical flight scenario."""
    print_section("Practical Flight Scenario")
    
    print("Scenario: Drone takes off, moves to waypoint, and lands")
    print()
    
    # Takeoff
    print("1. Takeoff to 10m altitude")
    ned_pos = (0.0, 0.0, -10.0)
    enu_pos = ned_to_enu(*ned_pos)
    print(f"   NED: N={ned_pos[0]:.1f}, E={ned_pos[1]:.1f}, D={ned_pos[2]:.1f}")
    print(f"   ENU: E={enu_pos[0]:.1f}, N={enu_pos[1]:.1f}, U={enu_pos[2]:.1f}")
    
    # Move to waypoint
    print("\n2. Move to waypoint (20m North, 15m East, 10m altitude)")
    ned_pos = (20.0, 15.0, -10.0)
    enu_pos = ned_to_enu(*ned_pos)
    print(f"   NED: N={ned_pos[0]:.1f}, E={ned_pos[1]:.1f}, D={ned_pos[2]:.1f}")
    print(f"   ENU: E={enu_pos[0]:.1f}, N={enu_pos[1]:.1f}, U={enu_pos[2]:.1f}")
    
    # Descend
    print("\n3. Descend to 5m altitude")
    ned_pos = (20.0, 15.0, -5.0)
    enu_pos = ned_to_enu(*ned_pos)
    print(f"   NED: N={ned_pos[0]:.1f}, E={ned_pos[1]:.1f}, D={ned_pos[2]:.1f}")
    print(f"   ENU: E={enu_pos[0]:.1f}, N={enu_pos[1]:.1f}, U={enu_pos[2]:.1f}")
    
    # Land
    print("\n4. Land")
    ned_pos = (20.0, 15.0, 0.0)
    enu_pos = ned_to_enu(*ned_pos)
    print(f"   NED: N={ned_pos[0]:.1f}, E={ned_pos[1]:.1f}, D={ned_pos[2]:.1f}")
    print(f"   ENU: E={enu_pos[0]:.1f}, N={enu_pos[1]:.1f}, U={enu_pos[2]:.1f}")


def main():
    """Run all demonstrations."""
    print("\n" + "="*60)
    print("  PX4 Frame Conversion Demo")
    print("  NED (North-East-Down) <-> ENU (East-North-Up)")
    print("="*60)
    
    demo_basic_conversion()
    demo_altitude_convention()
    demo_velocity_conversion()
    demo_body_frame()
    demo_roundtrip()
    demo_practical_scenario()
    
    print("\n" + "="*60)
    print("  Demo Complete!")
    print("="*60 + "\n")
    
    print("Key Takeaways:")
    print("  1. PX4 uses NED frame (Down is positive)")
    print("  2. ROS2 uses ENU frame (Up is positive)")
    print("  3. Conversion: [E,N,U] = [E,N,-D] from NED")
    print("  4. Always check frame conventions when debugging!")
    print()


if __name__ == "__main__":
    main()


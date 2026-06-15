"""
Test APF Acceleration Limiting (Improvement 9).

Verifies that the APF filter limits acceleration to prevent jerky movements.
"""
import pytest
from droneresearch.safety.apf import APFSafetyFilter, Pose3D


def test_acceleration_limiting_prevents_sudden_changes():
    """Acceleration limiting should smooth out sudden velocity changes."""
    apf = APFSafetyFilter(
        max_speed=5.0,
        max_acceleration=2.0,  # 2 m/s²
        dt=0.05,  # 20 Hz
        repulsion_gain=0.0,  # disable repulsion for this test
        attraction_gain=1.0,
    )
    
    # Start at rest
    positions = {"D1": Pose3D(0, 0, 10)}
    
    # Sudden large desired displacement (would require high acceleration)
    desired = {"D1": Pose3D(10, 0, 10)}  # 10m away
    
    # First iteration: should not jump full distance
    safe1 = apf.filter(positions, desired)
    displacement1 = safe1["D1"].x - positions["D1"].x
    
    # With max_accel=2.0 m/s² and dt=0.05s:
    # max_delta_v = 2.0 * 0.05 = 0.1 m/s
    # max_displacement = 0.1 * 0.05 = 0.005 m
    # But attraction force will try to move faster, so we expect clamping
    assert displacement1 < 0.5, "Should not move too far in one step"
    
    # Second iteration: velocity should gradually increase
    positions2 = {"D1": safe1["D1"]}
    safe2 = apf.filter(positions2, desired)
    displacement2 = safe2["D1"].x - safe1["D1"].x
    
    # Displacement should increase (acceleration) but still be limited
    assert displacement2 > displacement1 * 0.5, "Should accelerate"
    assert displacement2 < 1.0, "Should still be limited"


def test_acceleration_limiting_with_direction_change():
    """Acceleration limiting should prevent instant direction reversals."""
    apf = APFSafetyFilter(
        max_speed=3.0,
        max_acceleration=1.5,  # 1.5 m/s²
        dt=0.05,
        repulsion_gain=0.0,
        attraction_gain=1.0,
    )
    
    # Start moving in +x direction
    pos1 = {"D1": Pose3D(0, 0, 10)}
    des1 = {"D1": Pose3D(5, 0, 10)}
    safe1 = apf.filter(pos1, des1)
    
    # Continue moving
    pos2 = {"D1": safe1["D1"]}
    safe2 = apf.filter(pos2, des1)
    
    # Now suddenly reverse direction
    pos3 = {"D1": safe2["D1"]}
    des3 = {"D1": Pose3D(-5, 0, 10)}  # opposite direction
    safe3 = apf.filter(pos3, des3)
    
    # Should not instantly reverse - should decelerate first
    # Check that we're still moving in original direction or slowing down
    delta_x = safe3["D1"].x - pos3["D1"].x
    prev_delta_x = pos3["D1"].x - pos2["D1"].x
    
    # If we were moving +x, we shouldn't suddenly jump to -x
    if prev_delta_x > 0:
        # Either still moving +x (slower) or stopped, but not large -x
        assert delta_x > -0.1, "Should not instantly reverse direction"


def test_smooth_approach_to_target():
    """Drone should smoothly approach target without oscillation."""
    apf = APFSafetyFilter(
        max_speed=2.0,
        max_acceleration=1.0,
        dt=0.05,
        repulsion_gain=0.0,
        attraction_gain=1.0,
        damping_coeff=0.3,  # damping helps prevent overshoot
    )
    
    positions = {"D1": Pose3D(0, 0, 10)}
    desired = {"D1": Pose3D(5, 0, 10)}
    
    # Simulate multiple iterations
    trajectory = [positions["D1"].x]
    current_pos = positions
    
    for _ in range(50):  # 2.5 seconds at 20 Hz
        safe = apf.filter(current_pos, desired)
        trajectory.append(safe["D1"].x)
        current_pos = {"D1": safe["D1"]}
        
        # Stop if close enough
        if abs(safe["D1"].x - desired["D1"].x) < 0.1:
            break
    
    # Check trajectory is monotonically increasing (no oscillation)
    for i in range(1, len(trajectory)):
        assert trajectory[i] >= trajectory[i-1] - 0.01, \
            f"Trajectory should not oscillate: {trajectory[i-1]:.3f} -> {trajectory[i]:.3f}"
    
    # Should make significant progress toward target (acceleration limiting slows approach)
    assert trajectory[-1] > 2.0, f"Should approach target, reached {trajectory[-1]:.2f}m"


def test_acceleration_limit_parameter_effect():
    """Higher max_acceleration should allow faster velocity changes."""
    # Low acceleration limit
    apf_slow = APFSafetyFilter(
        max_speed=5.0,
        max_acceleration=0.5,  # very conservative
        dt=0.05,
        repulsion_gain=0.0,
        attraction_gain=1.0,
    )
    
    # High acceleration limit
    apf_fast = APFSafetyFilter(
        max_speed=5.0,
        max_acceleration=5.0,  # aggressive
        dt=0.05,
        repulsion_gain=0.0,
        attraction_gain=1.0,
    )
    
    positions = {"D1": Pose3D(0, 0, 10)}
    desired = {"D1": Pose3D(10, 0, 10)}
    
    # First step
    safe_slow = apf_slow.filter(positions, desired)
    safe_fast = apf_fast.filter(positions, desired)
    
    # Fast should move further in first step
    assert safe_fast["D1"].x > safe_slow["D1"].x, \
        "Higher acceleration limit should allow faster initial movement"


def test_acceleration_limiting_with_multiple_drones():
    """Acceleration limiting should work correctly with multiple drones."""
    apf = APFSafetyFilter(
        max_speed=3.0,
        max_acceleration=2.0,
        dt=0.05,
        min_separation=2.0,
        repulsion_gain=1.0,
        attraction_gain=1.0,
    )
    
    # Two drones starting close together
    positions = {
        "D1": Pose3D(0, 0, 10),
        "D2": Pose3D(1, 0, 10),  # 1m apart (violates min_separation)
    }
    
    # Both want to move in same direction
    desired = {
        "D1": Pose3D(5, 0, 10),
        "D2": Pose3D(5, 0, 10),
    }
    
    # Run multiple iterations
    current_pos = positions
    for _ in range(20):
        safe = apf.filter(current_pos, desired)
        current_pos = safe
    
    # Should maintain reasonable separation (acceleration limiting affects repulsion response)
    final_dist = current_pos["D1"].dist(current_pos["D2"])
    assert final_dist >= 1.0, f"Should maintain separation, got {final_dist:.2f}m"
    
    # Both should have moved forward (not stuck)
    assert current_pos["D1"].x > 0.5, "D1 should have moved"
    assert current_pos["D2"].x > 0.5, "D2 should have moved"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob

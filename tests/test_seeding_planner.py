"""
Tests for SeedingMissionPlanner.

Tests seeding mission generation with servo commands for seed drops.
"""

import pytest
from droneresearch.control.seeding_planner import (
    SeedingMissionPlanner,
    SeedingConfig,
    MAV_CMD_NAV_WAYPOINT,
    MAV_CMD_DO_SET_SERVO,
    MAV_CMD_NAV_DELAY
)
from droneresearch.control.field_coverage import FieldBoundary


def test_seeding_config_validation():
    """Test SeedingConfig parameter validation."""
    # Valid config
    config = SeedingConfig(
        seed_spacing=2.0,
        row_spacing=5.0,
        altitude=10.0,
        speed=3.0,
        servo_channel=9,
        servo_open_pwm=1900,
        servo_close_pwm=1100,
        drop_duration=0.5
    )
    assert config.seed_spacing == 2.0
    assert config.servo_channel == 9
    
    # Invalid seed spacing
    with pytest.raises(ValueError, match="Seed spacing must be positive"):
        SeedingConfig(seed_spacing=-1.0)
    
    # Invalid servo channel
    with pytest.raises(ValueError, match="Servo channel must be between 1 and 16"):
        SeedingConfig(servo_channel=0)
    
    with pytest.raises(ValueError, match="Servo channel must be between 1 and 16"):
        SeedingConfig(servo_channel=17)
    
    # Invalid PWM values
    with pytest.raises(ValueError, match="Servo open PWM must be between 900 and 2100"):
        SeedingConfig(servo_open_pwm=800)
    
    with pytest.raises(ValueError, match="Servo close PWM must be between 900 and 2100"):
        SeedingConfig(servo_close_pwm=2200)


def test_seeding_planner_initialization():
    """Test SeedingMissionPlanner initialization."""
    planner = SeedingMissionPlanner()
    assert planner._home_position is None
    assert planner._coverage_planner is not None


def test_set_home_position():
    """Test setting home position."""
    planner = SeedingMissionPlanner()
    planner.set_home_position(48.137, 11.575)
    assert planner._home_position == (48.137, 11.575)


def test_plan_seeding_mission_requires_home():
    """Test that planning requires home position to be set."""
    planner = SeedingMissionPlanner()
    boundary = FieldBoundary(corners=[
        (48.137, 11.575),
        (48.138, 11.575),
        (48.138, 11.576),
        (48.137, 11.576)
    ])
    
    with pytest.raises(ValueError, match="Home position must be set"):
        planner.plan_seeding_mission(boundary)


def test_plan_seeding_mission_basic():
    """Test basic seeding mission generation."""
    planner = SeedingMissionPlanner()
    planner.set_home_position(48.137, 11.575)
    
    boundary = FieldBoundary(corners=[
        (48.137, 11.575),
        (48.138, 11.575),
        (48.138, 11.576),
        (48.137, 11.576)
    ])
    
    waypoints = planner.plan_seeding_mission(
        boundary=boundary,
        seed_spacing=2.0,
        row_spacing=5.0,
        altitude=10.0,
        add_rtl=False
    )
    
    # Should have waypoints
    assert len(waypoints) > 0
    
    # First waypoint should be navigation
    assert waypoints[0].cmd == MAV_CMD_NAV_WAYPOINT
    assert waypoints[0].alt == 10.0
    
    # Should contain servo commands
    servo_commands = [wp for wp in waypoints if wp.cmd == MAV_CMD_DO_SET_SERVO]
    assert len(servo_commands) > 0
    
    # Should contain delay commands
    delay_commands = [wp for wp in waypoints if wp.cmd == MAV_CMD_NAV_DELAY]
    assert len(delay_commands) > 0
    
    # Servo commands should come in pairs (open/close)
    assert len(servo_commands) % 2 == 0


def test_plan_seeding_mission_with_rtl():
    """Test seeding mission with RTL waypoint."""
    planner = SeedingMissionPlanner()
    planner.set_home_position(48.137, 11.575)
    
    boundary = FieldBoundary(corners=[
        (48.137, 11.575),
        (48.138, 11.575),
        (48.138, 11.576),
        (48.137, 11.576)
    ])
    
    waypoints = planner.plan_seeding_mission(
        boundary=boundary,
        add_rtl=True
    )
    
    # Last waypoint should be RTL (home position)
    last_wp = waypoints[-1]
    assert last_wp.lat == 48.137
    assert last_wp.lon == 11.575
    assert last_wp.cmd == MAV_CMD_NAV_WAYPOINT


def test_servo_command_parameters():
    """Test that servo commands have correct parameters."""
    planner = SeedingMissionPlanner()
    planner.set_home_position(48.137, 11.575)
    
    boundary = FieldBoundary(corners=[
        (48.137, 11.575),
        (48.138, 11.575),
        (48.138, 11.576),
        (48.137, 11.576)
    ])
    
    waypoints = planner.plan_seeding_mission(
        boundary=boundary,
        servo_channel=9,
        servo_open_pwm=1900,
        servo_close_pwm=1100,
        add_rtl=False
    )
    
    # Find servo commands
    servo_commands = [wp for wp in waypoints if wp.cmd == MAV_CMD_DO_SET_SERVO]
    
    # Check that servo commands have correct channel and PWM values
    for i, wp in enumerate(servo_commands):
        assert wp.hold == 9.0  # Servo channel
        if i % 2 == 0:  # Open command
            assert wp.radius == 1900.0  # Open PWM
        else:  # Close command
            assert wp.radius == 1100.0  # Close PWM


def test_delay_command_duration():
    """Test that delay commands have correct duration."""
    planner = SeedingMissionPlanner()
    planner.set_home_position(48.137, 11.575)
    
    boundary = FieldBoundary(corners=[
        (48.137, 11.575),
        (48.138, 11.575),
        (48.138, 11.576),
        (48.137, 11.576)
    ])
    
    drop_duration = 0.75
    waypoints = planner.plan_seeding_mission(
        boundary=boundary,
        drop_duration=drop_duration,
        add_rtl=False
    )
    
    # Find delay commands
    delay_commands = [wp for wp in waypoints if wp.cmd == MAV_CMD_NAV_DELAY]
    
    # Check that delay commands have correct duration
    for wp in delay_commands:
        assert wp.hold == drop_duration


def test_estimate_mission_stats():
    """Test mission statistics estimation."""
    planner = SeedingMissionPlanner()
    planner.set_home_position(48.137, 11.575)
    
    boundary = FieldBoundary(corners=[
        (48.137, 11.575),
        (48.138, 11.575),
        (48.138, 11.576),
        (48.137, 11.576)
    ])
    
    config = SeedingConfig(
        seed_spacing=2.0,
        row_spacing=5.0,
        altitude=10.0,
        speed=3.0
    )
    
    stats = planner.estimate_mission_stats(boundary, config)
    
    # Check that stats are returned
    assert "total_distance" in stats
    assert "estimated_time" in stats
    assert "seed_count" in stats
    assert "row_count" in stats
    assert "field_area" in stats
    
    # Check that values are reasonable
    assert stats["total_distance"] > 0
    assert stats["estimated_time"] > 0
    assert stats["seed_count"] > 0
    assert stats["row_count"] > 0
    assert stats["field_area"] > 0


def test_calculate_distance():
    """Test GPS distance calculation."""
    planner = SeedingMissionPlanner()
    
    # Test known distance (approximately 1 degree latitude = 111km)
    pos1 = (48.0, 11.0)
    pos2 = (49.0, 11.0)
    distance = planner._calculate_distance(pos1, pos2)
    
    # Should be approximately 111km (111000m)
    assert 110000 < distance < 112000
    
    # Test zero distance
    distance = planner._calculate_distance(pos1, pos1)
    assert distance == 0.0


def test_different_seed_spacings():
    """Test mission generation with different seed spacings."""
    planner = SeedingMissionPlanner()
    planner.set_home_position(48.137, 11.575)
    
    boundary = FieldBoundary(corners=[
        (48.137, 11.575),
        (48.138, 11.575),
        (48.138, 11.576),
        (48.137, 11.576)
    ])
    
    # Test with small spacing (more seeds)
    waypoints_small = planner.plan_seeding_mission(
        boundary=boundary,
        seed_spacing=1.0,
        add_rtl=False
    )
    
    # Test with large spacing (fewer seeds)
    waypoints_large = planner.plan_seeding_mission(
        boundary=boundary,
        seed_spacing=5.0,
        add_rtl=False
    )
    
    # Smaller spacing should result in more servo commands
    servo_small = len([wp for wp in waypoints_small if wp.cmd == MAV_CMD_DO_SET_SERVO])
    servo_large = len([wp for wp in waypoints_large if wp.cmd == MAV_CMD_DO_SET_SERVO])
    
    assert servo_small >= servo_large


def test_waypoint_sequence():
    """Test that waypoints follow correct sequence."""
    planner = SeedingMissionPlanner()
    planner.set_home_position(48.137, 11.575)
    
    boundary = FieldBoundary(corners=[
        (48.137, 11.575),
        (48.138, 11.575),
        (48.138, 11.576),
        (48.137, 11.576)
    ])
    
    waypoints = planner.plan_seeding_mission(
        boundary=boundary,
        add_rtl=False
    )
    
    # Find first seed drop sequence
    # New sequence: NAV (with hold) -> SERVO_OPEN -> SERVO_CLOSE
    for i, wp in enumerate(waypoints):
        if wp.cmd == MAV_CMD_NAV_WAYPOINT and wp.hold > 0:
            # This is a seed drop waypoint
            assert waypoints[i].cmd == MAV_CMD_NAV_WAYPOINT
            assert waypoints[i].hold > 0  # Has hold time for seed drop
            assert waypoints[i+1].cmd == MAV_CMD_DO_SET_SERVO  # Open
            assert waypoints[i+2].cmd == MAV_CMD_DO_SET_SERVO  # Close
            break


def test_custom_servo_channel():
    """Test using different servo channels."""
    planner = SeedingMissionPlanner()
    planner.set_home_position(48.137, 11.575)
    
    boundary = FieldBoundary(corners=[
        (48.137, 11.575),
        (48.138, 11.575),
        (48.138, 11.576),
        (48.137, 11.576)
    ])
    
    # Test with channel 10
    waypoints = planner.plan_seeding_mission(
        boundary=boundary,
        servo_channel=10,
        add_rtl=False
    )
    
    servo_commands = [wp for wp in waypoints if wp.cmd == MAV_CMD_DO_SET_SERVO]
    for wp in servo_commands:
        assert wp.hold == 10.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob

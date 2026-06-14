"""
Tests for Smart Battery Monitor.

Tests cover:
- Battery monitoring start/stop
- Power consumption tracking
- RTL trigger conditions
- Distance calculations
- Power rate calculations
- Predictive RTL logic
"""

import pytest
import time
from droneresearch.safety.battery_monitor import BatteryMonitor, BatteryStatus, PowerSample


@pytest.fixture
def monitor():
    """Create battery monitor with test settings."""
    return BatteryMonitor(
        critical_threshold=20.0,
        warning_threshold=30.0,
        safety_margin=1.2,
        min_samples_for_prediction=5
    )


@pytest.fixture
def home_position():
    """Home position for testing."""
    return (48.137, 11.575, 0.0)  # Munich coordinates


def test_monitor_initialization(monitor):
    """Test monitor initializes with correct settings."""
    assert monitor.critical_threshold == 20.0
    assert monitor.warning_threshold == 30.0
    assert monitor.safety_margin == 1.2


def test_start_stop_monitoring(monitor):
    """Test starting and stopping monitoring."""
    monitor.start_monitoring("D1")
    assert "D1" in monitor._monitoring
    assert monitor._monitoring["D1"] is True
    
    monitor.stop_monitoring("D1")
    assert "D1" not in monitor._monitoring


def test_update_telemetry(monitor):
    """Test updating telemetry data."""
    monitor.start_monitoring("D1")
    
    telemetry = {
        "battery_pct": 80.0,
        "battery_v": 12.6,
        "lat": 48.137,
        "lon": 11.575,
        "alt_rel": 10.0
    }
    
    monitor.update("D1", telemetry)
    
    assert "D1" in monitor._last_sample
    sample = monitor._last_sample["D1"]
    assert sample.battery_pct == 80.0
    assert sample.position == (48.137, 11.575, 10.0)


def test_critical_battery_triggers_rtl(monitor, home_position):
    """Test RTL triggers when battery drops below critical threshold."""
    monitor.start_monitoring("D1")
    
    # Update with critical battery
    telemetry = {
        "battery_pct": 15.0,  # Below 20% threshold
        "lat": 48.137,
        "lon": 11.575,
        "alt_rel": 10.0
    }
    
    monitor.update("D1", telemetry)
    
    should_rtl, reason = monitor.should_trigger_rtl("D1", home_position)
    assert should_rtl is True
    assert "Critical battery" in reason


def test_sufficient_battery_no_rtl(monitor, home_position):
    """Test RTL does not trigger with sufficient battery."""
    monitor.start_monitoring("D1")
    
    # Update with good battery
    telemetry = {
        "battery_pct": 80.0,
        "lat": 48.137,
        "lon": 11.575,
        "alt_rel": 10.0
    }
    
    monitor.update("D1", telemetry)
    
    should_rtl, reason = monitor.should_trigger_rtl("D1", home_position)
    assert should_rtl is False


def test_distance_calculation(monitor):
    """Test GPS distance calculation."""
    # Munich to ~1km north
    pos1 = (48.137, 11.575)
    pos2 = (48.146, 11.575)
    
    distance = monitor._calculate_distance(pos1, pos2)
    
    # Should be approximately 1000 meters
    assert 900 < distance < 1100


def test_power_consumption_tracking(monitor):
    """Test power consumption rate calculation."""
    monitor.start_monitoring("D1")
    
    # Simulate battery drain over time
    positions = [
        (48.137, 11.575, 10.0),
        (48.138, 11.576, 10.0),
        (48.139, 11.577, 10.0),
    ]
    
    batteries = [80.0, 78.0, 76.0]
    
    for i, (pos, batt) in enumerate(zip(positions, batteries)):
        telemetry = {
            "battery_pct": batt,
            "lat": pos[0],
            "lon": pos[1],
            "alt_rel": pos[2]
        }
        monitor.update("D1", telemetry)
        time.sleep(0.1)  # Small delay to simulate time passing
    
    history = monitor._power_history["D1"]
    assert len(history) == 3
    
    # Check power consumption rate
    rate = monitor._calculate_power_consumption_rate(history)
    assert rate > 0  # Should have positive consumption rate


def test_average_speed_calculation(monitor):
    """Test average speed calculation from history."""
    monitor.start_monitoring("D1")
    
    # Simulate movement
    positions = [
        (48.137, 11.575, 10.0),
        (48.138, 11.575, 10.0),  # ~111m north
        (48.139, 11.575, 10.0),  # ~222m north total
    ]
    
    for pos in positions:
        telemetry = {
            "battery_pct": 80.0,
            "lat": pos[0],
            "lon": pos[1],
            "alt_rel": pos[2]
        }
        monitor.update("D1", telemetry)
        time.sleep(0.1)
    
    history = monitor._power_history["D1"]
    avg_speed = monitor._calculate_average_speed(history)
    
    assert avg_speed > 0  # Should have positive speed


def test_rtl_requirements_calculation(monitor, home_position):
    """Test RTL time and battery requirements calculation."""
    monitor.start_monitoring("D1")
    
    # Build up history with movement
    positions = [
        (48.137, 11.575, 10.0),
        (48.138, 11.576, 10.0),
        (48.139, 11.577, 10.0),
        (48.140, 11.578, 10.0),
        (48.141, 11.579, 10.0),
    ]
    
    batteries = [80.0, 78.0, 76.0, 74.0, 72.0]
    
    for pos, batt in zip(positions, batteries):
        telemetry = {
            "battery_pct": batt,
            "lat": pos[0],
            "lon": pos[1],
            "alt_rel": pos[2]
        }
        monitor.update("D1", telemetry)
        time.sleep(0.05)
    
    history = monitor._power_history["D1"]
    current_pos = positions[-1]
    
    rtl_time, battery_required = monitor._calculate_rtl_requirements(
        "D1", current_pos, home_position, history
    )
    
    assert rtl_time > 0
    assert battery_required >= monitor.critical_threshold


def test_battery_status_object(monitor, home_position):
    """Test BatteryStatus object creation."""
    monitor.start_monitoring("D1")
    
    # Add some samples
    for i in range(10):
        telemetry = {
            "battery_pct": 80.0 - i,
            "lat": 48.137 + i * 0.001,
            "lon": 11.575 + i * 0.001,
            "alt_rel": 10.0
        }
        monitor.update("D1", telemetry)
        time.sleep(0.05)
    
    status = monitor.get_battery_status("D1", home_position)
    
    assert status is not None
    assert isinstance(status, BatteryStatus)
    assert status.battery_pct > 0
    assert status.estimated_time_remaining >= 0
    assert status.rtl_time_required >= 0
    assert status.rtl_battery_required >= 0


def test_predictive_rtl_trigger(monitor, home_position):
    """Test predictive RTL triggers before critical threshold."""
    monitor.start_monitoring("D1")
    
    # Simulate drone far from home with declining battery
    # Start at 40% battery, 5km from home
    far_position = (48.182, 11.575, 10.0)  # ~5km north
    
    # Build history showing rapid battery drain
    for i in range(10):
        telemetry = {
            "battery_pct": 40.0 - i * 2,  # Rapid drain: 40% -> 22%
            "lat": far_position[0] - i * 0.001,
            "lon": far_position[1],
            "alt_rel": 10.0
        }
        monitor.update("D1", telemetry)
        time.sleep(0.05)
    
    # Check if predictive RTL triggers
    should_rtl, reason = monitor.should_trigger_rtl("D1", home_position)
    
    # Should trigger either due to critical battery or insufficient battery for RTL
    assert should_rtl is True
    assert reason != ""


def test_rtl_trigger_reset(monitor, home_position):
    """Test RTL trigger can be reset."""
    monitor.start_monitoring("D1")
    
    # Trigger RTL
    telemetry = {
        "battery_pct": 15.0,
        "lat": 48.137,
        "lon": 11.575,
        "alt_rel": 10.0
    }
    monitor.update("D1", telemetry)
    
    should_rtl, _ = monitor.should_trigger_rtl("D1", home_position)
    assert should_rtl is True
    
    # Reset trigger
    monitor.reset_rtl_trigger("D1")
    
    # Flag should be cleared after reset
    assert monitor._rtl_triggered.get("D1") is False
    
    # Should trigger again when checked (battery still critical)
    should_rtl, _ = monitor.should_trigger_rtl("D1", home_position)
    assert should_rtl is True
    # And flag is set again
    assert monitor._rtl_triggered.get("D1") is True


def test_multiple_drones(monitor, home_position):
    """Test monitoring multiple drones independently."""
    monitor.start_monitoring("D1")
    monitor.start_monitoring("D2")
    
    # D1 has critical battery
    telemetry_d1 = {
        "battery_pct": 15.0,
        "lat": 48.137,
        "lon": 11.575,
        "alt_rel": 10.0
    }
    monitor.update("D1", telemetry_d1)
    
    # D2 has good battery
    telemetry_d2 = {
        "battery_pct": 80.0,
        "lat": 48.138,
        "lon": 11.576,
        "alt_rel": 10.0
    }
    monitor.update("D2", telemetry_d2)
    
    # D1 should trigger RTL
    should_rtl_d1, _ = monitor.should_trigger_rtl("D1", home_position)
    assert should_rtl_d1 is True
    
    # D2 should not trigger RTL
    should_rtl_d2, _ = monitor.should_trigger_rtl("D2", home_position)
    assert should_rtl_d2 is False


def test_invalid_telemetry_ignored(monitor):
    """Test invalid telemetry is ignored."""
    monitor.start_monitoring("D1")
    
    # Invalid telemetry (zero battery)
    telemetry = {
        "battery_pct": 0.0,
        "lat": 48.137,
        "lon": 11.575,
        "alt_rel": 10.0
    }
    monitor.update("D1", telemetry)
    
    assert "D1" not in monitor._last_sample
    
    # Invalid telemetry (zero position)
    telemetry = {
        "battery_pct": 80.0,
        "lat": 0.0,
        "lon": 0.0,
        "alt_rel": 10.0
    }
    monitor.update("D1", telemetry)
    
    assert "D1" not in monitor._last_sample


def test_safety_margin_applied(monitor, home_position):
    """Test safety margin is applied to RTL calculations."""
    monitor.start_monitoring("D1")
    
    # Build history
    for i in range(10):
        telemetry = {
            "battery_pct": 50.0 - i,
            "lat": 48.137 + i * 0.001,
            "lon": 11.575,
            "alt_rel": 10.0
        }
        monitor.update("D1", telemetry)
        time.sleep(0.05)
    
    history = monitor._power_history["D1"]
    current_pos = (48.147, 11.575, 10.0)
    
    rtl_time, _ = monitor._calculate_rtl_requirements(
        "D1", current_pos, home_position, history
    )
    
    # Calculate time without safety margin
    distance = monitor._calculate_distance(
        (current_pos[0], current_pos[1]),
        (home_position[0], home_position[1])
    )
    avg_speed = monitor._calculate_average_speed(history) or 5.0
    base_time = distance / avg_speed
    
    # RTL time should be greater due to safety margin
    assert rtl_time > base_time


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob

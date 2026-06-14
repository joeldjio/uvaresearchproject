# Smart Battery Monitoring

## Overview

The Smart Battery Monitor provides predictive battery management for UAVs, triggering Return-to-Launch (RTL) before critical battery levels are reached. It analyzes power consumption patterns and calculates whether the drone has sufficient battery to return home safely.

## Features

- **Real-time Battery Tracking**: Monitors battery percentage continuously
- **Power Consumption Analysis**: Tracks battery drain rate over time
- **Predictive RTL**: Calculates required battery for safe return home
- **Distance-based Calculations**: Uses GPS position to determine RTL requirements
- **Safety Margin**: Configurable safety buffer (default 20%) for RTL calculations
- **Multi-drone Support**: Monitors multiple drones independently
- **Autopilot Agnostic**: Works with ArduPilot, PX4, and other MAVLink-compatible systems

## Architecture

### Core Components

```
droneresearch/safety/battery_monitor.py
├── BatteryMonitor          # Main monitoring class
├── BatteryStatus           # Status dataclass
└── PowerSample             # Historical sample dataclass
```

### Key Classes

#### BatteryMonitor

Main class for battery monitoring with predictive RTL capabilities.

**Configuration:**
- `critical_threshold`: Battery percentage to trigger immediate RTL (default: 20%)
- `safety_margin`: Multiplier for RTL time calculations (default: 1.2 = 20% buffer)
- `min_samples`: Minimum samples needed for predictions (default: 5)
- `max_history`: Maximum samples to keep in history (default: 100)

**Methods:**
- `start_monitoring(drone_id)`: Begin monitoring a drone
- `stop_monitoring(drone_id)`: Stop monitoring a drone
- `update(drone_id, telemetry)`: Update with new telemetry data
- `should_trigger_rtl(drone_id, home_position)`: Check if RTL should trigger
- `get_battery_status(drone_id, home_position)`: Get comprehensive battery status
- `reset_rtl_trigger(drone_id)`: Reset RTL trigger flag

#### BatteryStatus

Dataclass containing comprehensive battery status information.

**Fields:**
- `battery_pct`: Current battery percentage
- `voltage`: Battery voltage (V)
- `current`: Current draw (A)
- `estimated_time_remaining`: Estimated flight time remaining (seconds)
- `rtl_time_required`: Time required for RTL (seconds)
- `rtl_battery_required`: Battery percentage required for RTL
- `should_rtl`: Whether RTL should be triggered
- `rtl_reason`: Reason for RTL trigger

#### PowerSample

Historical power consumption sample.

**Fields:**
- `timestamp`: Sample timestamp
- `battery_pct`: Battery percentage at sample time
- `position`: GPS position (lat, lon, alt)

## Usage

### Basic Usage

```python
from droneresearch.safety.battery_monitor import BatteryMonitor

# Create monitor with default settings
monitor = BatteryMonitor()

# Start monitoring a drone
monitor.start_monitoring("UAV_1")

# Update with telemetry (called periodically)
telemetry = {
    "battery_pct": 75.0,
    "lat": 48.137,
    "lon": 11.575,
    "alt_rel": 10.0
}
monitor.update("UAV_1", telemetry)

# Check if RTL should trigger
home_position = (48.137, 11.575, 0.0)
should_rtl, reason = monitor.should_trigger_rtl("UAV_1", home_position)
if should_rtl:
    print(f"RTL triggered: {reason}")
    # Trigger RTL command...

# Get comprehensive status
status = monitor.get_battery_status("UAV_1", home_position)
print(f"Battery: {status.battery_pct:.1f}%")
print(f"Time remaining: {status.estimated_time_remaining:.0f}s")
print(f"RTL requires: {status.rtl_battery_required:.1f}%")
```

### Custom Configuration

```python
# Create monitor with custom settings
monitor = BatteryMonitor(
    critical_threshold=15.0,  # Trigger at 15% battery
    safety_margin=1.3,        # 30% safety buffer
    min_samples=10            # Need 10 samples for predictions
)
```

### Multi-drone Monitoring

```python
# Monitor multiple drones
monitor = BatteryMonitor()

for drone_id in ["UAV_1", "UAV_2", "UAV_3"]:
    monitor.start_monitoring(drone_id)

# Update each drone independently
for drone_id, telemetry in drone_telemetry.items():
    monitor.update(drone_id, telemetry)
    
    # Check each drone's status
    status = monitor.get_battery_status(drone_id, home_position)
    if status.should_rtl:
        trigger_rtl(drone_id, status.rtl_reason)
```

## Algorithm Details

### Power Consumption Rate

The monitor calculates power consumption rate (% per minute) by analyzing historical samples:

```python
rate = (battery_change / time_elapsed) * 60
```

This rate is averaged over recent samples to smooth out variations.

### RTL Requirements Calculation

1. **Calculate distance to home** using Haversine formula
2. **Estimate average speed** from recent position changes
3. **Calculate RTL time**: `distance / speed`
4. **Apply safety margin**: `rtl_time * safety_margin`
5. **Calculate required battery**: `power_rate * rtl_time_with_margin`

### Predictive RTL Trigger

RTL is triggered when:
1. Battery drops below critical threshold (immediate trigger), OR
2. Current battery < required battery for safe RTL (predictive trigger)

The predictive trigger ensures the drone returns home before it's too late, accounting for:
- Current distance from home
- Historical power consumption patterns
- Average flight speed
- Configurable safety margin

## Integration with Autopilots

### ArduPilot

The monitor uses standard MAVLink telemetry messages:
- `BATTERY_STATUS`: Battery percentage, voltage, current
- `GLOBAL_POSITION_INT`: GPS position

```python
# ArduPilot telemetry format
telemetry = {
    "battery_pct": msg.battery_remaining,
    "lat": msg.lat / 1e7,
    "lon": msg.lon / 1e7,
    "alt_rel": msg.relative_alt / 1000.0
}
```

### PX4

PX4 provides battery data through:
- `battery_status` topic (ROS2)
- `BATTERY_STATUS` MAVLink message

```python
# PX4 telemetry format (same as ArduPilot)
telemetry = {
    "battery_pct": battery_msg.remaining * 100,
    "lat": position_msg.lat,
    "lon": position_msg.lon,
    "alt_rel": position_msg.alt
}
```

## Testing

Comprehensive test suite with 15 test cases:

```bash
pytest tests/test_battery_monitor.py -v
```

**Test Coverage:**
- Initialization and configuration
- Start/stop monitoring
- Telemetry updates
- Critical battery RTL trigger
- Predictive RTL logic
- Distance calculations (Haversine)
- Power consumption tracking
- Average speed calculations
- RTL requirements calculation
- Multiple drone monitoring
- Safety margin application
- RTL trigger reset
- Invalid telemetry handling

## Performance

- **Memory**: ~1KB per drone (100 samples × 10 bytes)
- **CPU**: Minimal overhead, O(n) calculations where n = history size
- **Thread-safe**: Uses threading.Lock for concurrent access
- **Scalable**: Tested with 10+ drones simultaneously

## Limitations

- Requires minimum 5 samples for predictive RTL (configurable)
- Assumes relatively constant flight speed
- Does not account for wind conditions
- GPS-based distance calculations (not obstacle-aware)

## Future Enhancements

- [ ] Wind compensation in RTL calculations
- [ ] Voltage and current tracking (currently placeholders)
- [ ] Battery health estimation
- [ ] Mission-aware RTL (return to nearest safe point)
- [ ] Integration with path planning for obstacle avoidance
- [ ] Battery temperature monitoring
- [ ] Multiple battery support (parallel/series configurations)

## References

- [MAVLink Battery Status](https://mavlink.io/en/messages/common.html#BATTERY_STATUS)
- [ArduPilot Battery Monitoring](https://ardupilot.org/copter/docs/common-powermodule-landingpage.html)
- [PX4 Battery Estimation](https://docs.px4.io/main/en/config/battery.html)
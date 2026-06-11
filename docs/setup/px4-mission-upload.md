# PX4 Mission Upload via uXRCE-DDS

This guide explains how to upload and execute waypoint missions on PX4 using the native uXRCE-DDS protocol (NOT MAVLink).

## Overview

The `PX4MissionUploader` class provides mission management functionality:
- Upload waypoint missions to PX4
- Clear missions
- Start/pause mission execution
- Monitor mission acknowledgments

## Architecture

```
┌─────────────────────┐
│  DroneResearch App  │
│  (Python)           │
└──────────┬──────────┘
           │
           │ ROS2 Topics
           │
┌──────────▼──────────┐
│  PX4MissionUploader │
│  (uXRCE-DDS)        │
└──────────┬──────────┘
           │
           │ /fmu/in/vehicle_mission_item_count
           │ /fmu/in/vehicle_mission_item
           │ /fmu/out/vehicle_mission_ack
           │
┌──────────▼──────────┐
│  PX4 Autopilot      │
│  (SITL/Hardware)    │
└─────────────────────┘
```

## Prerequisites

1. **ROS2 Humble** installed and sourced
2. **px4_msgs** package built:
   ```bash
   cd ~/ros2_ws/src
   git clone https://github.com/PX4/px4_msgs
   cd ~/ros2_ws
   colcon build --packages-select px4_msgs
   source install/setup.bash
   ```
3. **PX4 SITL** running with uXRCE-DDS agent (see [px4-sitl-automation.md](px4-sitl-automation.md))

## Quick Start

### 1. Basic Mission Upload

```python
from droneresearch.ros.px4_bridge import PX4ROS2Bridge

# Create bridge
bridge = PX4ROS2Bridge(namespace="", publish_hz=10.0)
bridge.start()

# Define waypoints (lat/lon in degrees, alt in meters)
waypoints = [
    {"lat": 47.397742, "lon": 8.545594, "alt": 15.0},
    {"lat": 47.397842, "lon": 8.545694, "alt": 20.0},
    {"lat": 47.397942, "lon": 8.545794, "alt": 15.0},
]

# Upload mission
success = bridge.upload_mission(waypoints, timeout=10.0)
if success:
    print("✓ Mission uploaded")
else:
    print("✗ Mission upload failed")

# Start mission execution
bridge.start_mission()
```

### 2. Waypoint Parameters

Waypoints support optional parameters:

```python
waypoint = {
    "lat": 47.397742,           # Latitude (degrees) - REQUIRED
    "lon": 8.545594,            # Longitude (degrees) - REQUIRED
    "alt": 15.0,                # Altitude (meters MSL) - REQUIRED
    "hold_time": 5.0,           # Hold time at waypoint (seconds)
    "accept_radius": 2.0,       # Acceptance radius (meters)
    "pass_radius": 0.0,         # Pass-through radius (meters)
    "yaw": 90.0,                # Yaw angle (degrees)
}
```

### 3. Mission Control

```python
# Start mission (switch to AUTO.MISSION mode)
bridge.start_mission()

# Pause mission (switch to AUTO.LOITER mode)
bridge.pause_mission()

# Clear mission
bridge.clear_mission()
```

## Complete Example

See [`examples/px4_mission_upload.py`](../../examples/px4_mission_upload.py) for a complete working example.

```bash
# Terminal 1: Start PX4 SITL with Gazebo
cd ~/PX4-Autopilot
make px4_sitl gz_x500

# Terminal 2: Start uXRCE-DDS agent
MicroXRCEAgent udp4 -p 8888

# Terminal 3: Run example
python examples/px4_mission_upload.py
```

## API Reference

### PX4ROS2Bridge

#### `upload_mission(waypoints, timeout=10.0) -> bool`

Upload waypoint mission to PX4.

**Parameters:**
- `waypoints` (List[Dict]): List of waypoint dictionaries
- `timeout` (float): Timeout in seconds for ACK

**Returns:**
- `bool`: True if upload successful

**Example:**
```python
waypoints = [
    {"lat": 47.397742, "lon": 8.545594, "alt": 15.0},
    {"lat": 47.397842, "lon": 8.545694, "alt": 20.0},
]
success = bridge.upload_mission(waypoints)
```

#### `clear_mission() -> bool`

Clear mission on PX4.

**Returns:**
- `bool`: True if successful

**Example:**
```python
bridge.clear_mission()
```

#### `start_mission()`

Start mission execution (switch to AUTO.MISSION mode).

**Example:**
```python
bridge.start_mission()
```

#### `pause_mission()`

Pause mission execution (switch to AUTO.LOITER mode).

**Example:**
```python
bridge.pause_mission()
```

### PX4MissionUploader

Low-level mission uploader (used internally by `PX4ROS2Bridge`).

#### `__init__(node, namespace="")`

Initialize mission uploader.

**Parameters:**
- `node` (rclpy.node.Node): ROS2 node instance
- `namespace` (str): PX4 namespace (e.g., "uav_1")

#### `upload(waypoints, timeout=10.0) -> bool`

Upload waypoints to PX4.

#### `clear() -> bool`

Clear mission on PX4.

## Frame Convention

- **Coordinates**: WGS84 (latitude/longitude in degrees)
- **Altitude**: MSL (Mean Sea Level) in meters
- **Frame**: `MAV_FRAME_GLOBAL_RELATIVE_ALT` (altitude relative to home)

## Mission Protocol

The uploader uses the PX4 mission protocol over uXRCE-DDS:

1. **Send Count**: Publish `VehicleMissionItemCount` with total waypoint count
2. **Send Items**: Publish `VehicleMissionItem` for each waypoint
3. **Wait for ACK**: Subscribe to `VehicleMissionAck` for confirmation

### Topics Used

- `/fmu/in/vehicle_mission_item_count` - Mission count (ROS2 → PX4)
- `/fmu/in/vehicle_mission_item` - Mission items (ROS2 → PX4)
- `/fmu/out/vehicle_mission_ack` - Mission acknowledgment (PX4 → ROS2)

## Troubleshooting

### Mission Upload Fails

**Symptom**: `upload_mission()` returns `False`

**Solutions:**
1. Check PX4 SITL is running: `ps aux | grep px4`
2. Check uXRCE-DDS agent is running: `ps aux | grep MicroXRCEAgent`
3. Verify ROS2 topics: `ros2 topic list | grep fmu`
4. Check PX4 console for errors: Look for mission-related messages

### No ACK Received

**Symptom**: "No ACK received within timeout" warning

**Solutions:**
1. Increase timeout: `bridge.upload_mission(waypoints, timeout=20.0)`
2. Check if `px4_msgs` includes `VehicleMissionAck` message
3. Verify PX4 firmware version (v1.14+ recommended)

### Mission Doesn't Start

**Symptom**: `start_mission()` called but vehicle doesn't move

**Solutions:**
1. Ensure vehicle is armed: `bridge.arm()`
2. Ensure vehicle has taken off: `bridge.takeoff(10.0)`
3. Check GPS fix: `bridge.telemetry['gps_fix'] >= 3`
4. Verify mission was uploaded successfully
5. Check PX4 mode: Should be in AUTO.MISSION (mode 4)

### Invalid Waypoints

**Symptom**: Mission upload rejected by PX4

**Solutions:**
1. Verify coordinates are valid (lat: -90 to 90, lon: -180 to 180)
2. Check altitude is positive and reasonable (< 120m for safety)
3. Ensure accept_radius is positive
4. Verify waypoints are not too close together (> 1m apart)

## Multi-Vehicle Missions

For multi-vehicle setups, use namespaces:

```python
# Vehicle 1
bridge1 = PX4ROS2Bridge(namespace="uav_1")
bridge1.start()
bridge1.upload_mission(waypoints1)
bridge1.start_mission()

# Vehicle 2
bridge2 = PX4ROS2Bridge(namespace="uav_2")
bridge2.start()
bridge2.upload_mission(waypoints2)
bridge2.start_mission()
```

## Testing

Run the test suite:

```bash
pytest tests/test_px4_mission.py -v
```

All 16 tests should pass:
- Uploader initialization
- Mission upload (single/multiple waypoints)
- Optional parameters
- ACK handling (success/timeout/rejection)
- Mission clear
- Bridge integration

## References

- [PX4 ROS2 User Guide](https://docs.px4.io/main/en/ros2/user_guide.html)
- [MAVLink Mission Protocol](https://mavlink.io/en/services/mission.html)
- [PX4 Flight Modes](https://docs.px4.io/main/en/flight_modes/)
- [uXRCE-DDS Documentation](https://micro-xrce-dds.docs.eprosima.com/)

## See Also

- [PX4 SITL Automation](px4-sitl-automation.md) - Automated SITL setup
- [Installation Guide](installation.md) - Setup instructions
- [Project Overview](../project/overview.md) - Architecture overview
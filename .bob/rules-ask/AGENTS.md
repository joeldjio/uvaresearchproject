# Ask Mode Rules (Non-Obvious Only)

## Documentation Context

### Project Structure Quirks
- `droneresearch/` is the main package, NOT `src/`
- `tools/ui/` contains QML-based GCS (on `ui-dashboard` branch only)
- `pi/` is standalone server, separate from main package
- `examples/` are runnable scripts, NOT unit tests

### Default Port Confusion
- Documentation may reference port 5760, but default is actually **5762**
- 5762 = raw ArduCopter SITL (default)
- 5760 = MAVProxy-aggregated SITL
- 14550 = PX4 SITL (UDP)

### Test Suite Philosophy
- Tests are **intentionally hardware-free** - no real MAVLink/ROS2/SITL
- All external dependencies mocked in [`tests/conftest.py`](../../tests/conftest.py)
- Full suite runs in ~1 second
- This is a design decision, not a limitation

### Frame Convention Documentation
- PX4 ROS2 integration uses **uXRCE-DDS**, NOT MAVLink-over-ROS or FastRTPS
- Frame conversions in [`droneresearch/ros/px4_bridge.py`](../../droneresearch/ros/px4_bridge.py) are critical
- NED (PX4) ↔ ENU (ROS2) conversion: `[x,y,z]_enu = [y, x, -z]_ned`
- Topics: `/fmu/out/*` (PX4→ROS2), `/fmu/in/*` (ROS2→PX4)

### APF Filter Coordinate System
- Despite using "NED" terminology, APF filter expects **positive z_up** for altitude
- Filter handles inversion internally
- [`Pose3D`](../../droneresearch/safety/apf.py): `x=North, y=East, z=altitude_above_ground`

### Optional Dependencies
- ROS2 (`rclpy`, `px4_msgs`) is optional - package works without it
- UI (`PyQt6`) is optional - core is headless
- Lazy imports in [`droneresearch/__init__.py`](../../droneresearch/__init__.py) prevent hard dependencies
- Use factory functions: `get_backend()`, `get_sitl()`, `get_coordinator()`

### Raspberry Pi Server
- [`pi/server.py`](../../pi/server.py) is optimized for Pi 1 (700MHz, 512MB RAM)
- Uses ONLY stdlib + pymavlink + pyserial (no numpy, pandas, Qt)
- ~20MB RAM, <5% CPU
- Separate from main package by design

### Mission Upload Blocking Behavior
- [`MissionEngine.upload()`](../../droneresearch/control/mission.py) is **blocking** (~50ms per waypoint)
- This is intentional - uses hybrid protocol with 250ms timeout
- Documentation should warn against calling from UI thread

### ROS2 Context Sharing
- Multiple bridges share single `rclpy` context via reference counting
- [`acquire_ros()`](../../droneresearch/ros/context.py) / [`release_ros()`](../../droneresearch/ros/context.py) pattern is mandatory
- Second `rclpy.init()` raises `RCLError` - this is why the pattern exists

## Common Misconceptions

### "Why is the default port 5762 not 5760?"
- 5762 is raw ArduCopter SITL (direct connection)
- 5760 is MAVProxy-aggregated (adds proxy layer)
- Direct connection is preferred for research/testing

### "Why are tests so fast?"
- Hardware-free by design - all external deps mocked
- Enables rapid iteration without SITL/ROS2 setup
- See [`tests/conftest.py`](../../tests/conftest.py) for mock implementations

### "Why separate pi/ directory?"
- Pi 1 has severe resource constraints (512MB RAM)
- Main package has heavy optional deps (ROS2, Qt)
- Separate server keeps Pi deployment minimal
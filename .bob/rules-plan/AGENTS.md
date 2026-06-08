# Plan Mode Rules (Non-Obvious Only)

## Architectural Constraints

### Hardware-Free Test Philosophy
- Test suite is **intentionally** hardware-free (no MAVLink, ROS2, SITL)
- All external dependencies mocked in [`tests/conftest.py`](../../tests/conftest.py)
- This is a design decision for rapid iteration, not a limitation
- When planning test additions, MUST use existing mock fixtures

### ROS2 Context Lifecycle
- Multiple bridges (PX4, VSwarm, Frontier) share single `rclpy` context
- Reference counting in [`droneresearch/ros/context.py`](../../droneresearch/ros/context.py) prevents conflicts
- Second `rclpy.init()` raises `RCLError` - this is why pattern exists
- When planning ROS2 features, MUST use `acquire_ros()` / `release_ros()`

### Mission Upload Blocking Constraint
- [`MissionEngine.upload()`](../../droneresearch/control/mission.py) is **blocking** (~50ms per waypoint)
- Uses hybrid protocol with 250ms timeout for handshake
- NEVER plan to call from UI/Qt main thread - requires worker thread
- This is protocol limitation, not implementation bug

### Frame Convention Complexity (PX4 ROS2)
- PX4 native: NED (North-East-Down) + FRD (Forward-Right-Down)
- ROS2 standard: ENU (East-North-Up) + FLU (Forward-Left-Up)
- Conversion functions in [`droneresearch/ros/px4_bridge.py`](../../droneresearch/ros/px4_bridge.py)
- Topics: `/fmu/out/*` (PX4→ROS2), `/fmu/in/*` (ROS2→PX4)
- Uses **uXRCE-DDS**, NOT MAVLink-over-ROS or FastRTPS

### APF Filter Coordinate System
- Despite "NED" terminology, expects **positive z_up** for altitude input
- Filter handles inversion internally for NED calculations
- [`Pose3D`](../../droneresearch/safety/apf.py): `x=North, y=East, z=altitude_above_ground`
- When planning APF integration, remember this quirk

### Optional Dependency Architecture
- ROS2 (`rclpy`, `px4_msgs`) is optional - core works without it
- UI (`PyQt6`) is optional - core is headless
- Lazy imports in [`droneresearch/__init__.py`](../../droneresearch/__init__.py) prevent hard dependencies
- When planning features, consider which dependencies are truly required

### Raspberry Pi Constraints
- [`pi/server.py`](../../pi/server.py) targets Pi 1 (700MHz, 512MB RAM)
- ONLY stdlib + pymavlink + pyserial allowed
- NO numpy, pandas, Qt, or heavy dependencies
- ~20MB RAM, <5% CPU budget
- When planning Pi features, respect these constraints

### Default Port Convention
- Default is `tcp:127.0.0.1:5762` (raw ArduCopter SITL), NOT 5760
- 5760 is MAVProxy-aggregated SITL (adds proxy layer)
- CLI resolution: `--port` flag > `$DRONE_PORT` env > default 5762
- When planning CLI features, maintain this precedence

## Planning Guidelines

### Test Planning
- New tests MUST use fixtures from [`tests/conftest.py`](../../tests/conftest.py)
- NO real MAVLink connections, ROS2 nodes, or SITL spawning
- Target: <2 seconds for full suite
- Use `FakeConnection`, `FakeTelemetry`, `FakeMav`, `snap_factory()`

### ROS2 Feature Planning
- ALWAYS plan for `acquire_ros()` / `release_ros()` lifecycle
- Consider multi-bridge scenarios (PX4 + VSwarm + Frontier)
- Frame conversions required for PX4 integration
- Check if `rclpy` and `px4_msgs` are available before planning features

### Threading Considerations
- Mission upload is blocking - plan for worker threads
- Logger uses queue with backpressure tracking
- FSM is thread-safe with lock
- APF filter runs at 20Hz in separate thread

### Dependency Planning
- Core package: pymavlink + pyserial only
- ROS2 features: optional, lazy-loaded
- UI features: optional, separate branch (`ui-dashboard`)
- Pi deployment: stdlib + pymavlink + pyserial only

## File Restrictions
- This mode can only edit markdown files (`.md`)
- Use code mode for implementation after planning
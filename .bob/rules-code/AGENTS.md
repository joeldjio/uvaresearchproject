# Code Mode Rules (Non-Obvious Only)

## Critical Patterns Discovered

### Connection String Resolution
- MUST respect precedence: explicit `--port` > `$DRONE_PORT` env > default `tcp:127.0.0.1:5762`
- Default is 5762 (raw SITL), NOT 5760 (MAVProxy-aggregated)
- See [`droneresearch/cli/main.py`](../../droneresearch/cli/main.py) for implementation

### Test Fixture Usage
- NEVER import real MAVLink/ROS2 in tests - use fixtures from [`tests/conftest.py`](../../tests/conftest.py)
- `FakeConnection` provides `.on()`, `.set_mode()`, `.rtl()`, `.emit_message()` for testing
- `FakeMav` captures `mav.mav.*_send()` calls for inspection
- `snap_factory()` builds telemetry dicts with sensible defaults

### ROS2 Bridge Lifecycle
- ALWAYS use `acquire_ros()` before creating ROS2 nodes
- ALWAYS call `release_ros()` in finally block
- NEVER call `rclpy.init()` or `rclpy.shutdown()` directly
- Multiple bridges share one context via reference counting in [`droneresearch/ros/context.py`](../../droneresearch/ros/context.py)

### Frame Conversions (PX4 ROS2)
- PX4 publishes in NED/FRD, ROS2 expects ENU/FLU
- Use `ned_to_enu()`, `enu_to_ned()`, `frd_to_flu()` from [`droneresearch/ros/px4_bridge.py`](../../droneresearch/ros/px4_bridge.py)
- Conversion: `[x,y,z]_enu = [y, x, -z]_ned`
- Topics: `/fmu/out/*` (PX4→ROS2), `/fmu/in/*` (ROS2→PX4)

### APF Filter Coordinate System
- Input positions: local NED meters with **positive z_up** (altitude above ground)
- Filter inverts z internally for NED calculations
- [`Pose3D`](../../droneresearch/safety/apf.py): `x=North, y=East, z=altitude_above_ground`

### Mission Upload Threading
- [`MissionEngine.upload()`](../../droneresearch/control/mission.py) is BLOCKING (~50ms per waypoint)
- Uses hybrid protocol with 250ms timeout for `MISSION_REQUEST(0)`
- NEVER call from UI/Qt main thread - always use worker thread

### Optional Dependency Pattern
- Wrap imports in try/except with `_OK` flag: `_ROS2_OK`, `_PX4_MSGS_OK`, `_MAV_OK`
- Check flag before using: `if not _ROS2_OK: return False`
- See [`droneresearch/__init__.py`](../../droneresearch/__init__.py) for lazy import pattern

### Logger Queue Backpressure
- Queue size: 10000 items (see [`droneresearch/data/logger.py`](../../droneresearch/data/logger.py))
- Tracks `_dropped` count when full
- Warns every 5 seconds if dropping messages

### Pi Server Constraints
- [`pi/server.py`](../../pi/server.py) uses ONLY stdlib + pymavlink + pyserial
- NO numpy, pandas, Qt, or other heavy dependencies
- Plain dict for state (no dataclass overhead)
- Ring buffer with `deque(maxlen=200)` for logs

## File Restrictions
- This mode can edit any file type
# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Critical Non-Obvious Patterns

### Default Port Convention
- Default connection is `tcp:127.0.0.1:5762` (raw ArduCopter SITL), NOT 5760
- Port 5760 is for MAVProxy-aggregated SITL
- CLI resolution: `--port` flag > `$DRONE_PORT` env var > default 5762

### Test Suite Architecture
- Tests are **hardware-free** by design - no MAVLink, no ROS2, no SITL spawning
- All external dependencies mocked via [`tests/conftest.py`](tests/conftest.py)
- Use `FakeConnection`, `FakeTelemetry`, `FakeMav` fixtures instead of real connections
- Full suite runs in ~1 second

### Frame Convention Hell (PX4 ROS2)
- PX4 native: NED (North-East-Down) + FRD (Forward-Right-Down)
- ROS2 standard: ENU (East-North-Up) + FLU (Forward-Left-Up)
- Conversion functions in [`droneresearch/ros/px4_bridge.py`](droneresearch/ros/px4_bridge.py): `ned_to_enu()`, `enu_to_ned()`, `frd_to_flu()`
- PX4 topics: `/fmu/out/*` (PX4→ROS2), `/fmu/in/*` (ROS2→PX4)
- **NOT** MAVLink-over-ROS, **NOT** FastRTPS - uses uXRCE-DDS

### ROS2 Context Management
- Multiple bridges share single `rclpy` context via reference counting
- MUST use [`acquire_ros()`](droneresearch/ros/context.py) / [`release_ros()`](droneresearch/ros/context.py) - never call `rclpy.init()` directly
- Second `rclpy.init()` raises `RCLError`; premature `shutdown()` kills all bridges

### Mission Upload Protocol
- [`MissionEngine.upload()`](droneresearch/control/mission.py) is **blocking** (~50ms per waypoint)
- Uses hybrid protocol: sends `MISSION_COUNT`, waits for `MISSION_REQUEST(0)` with 250ms timeout
- Never call from UI/Qt main thread

### APF Safety Filter
- Runs at 20Hz by default (configurable)
- Positions in local NED meters but uses **positive z_up** for altitude (filter inverts internally)
- [`Pose3D`](droneresearch/safety/apf.py): `x=North, y=East, z=altitude_above_ground`

### Raspberry Pi Server
- Pi 1 optimized: stdlib-only HTTP server, ~20MB RAM, <5% CPU
- Dependencies: ONLY `pymavlink` + `pyserial` (no numpy, no pandas, no Qt)
- Located in [`pi/server.py`](pi/server.py), separate from main package

### Lazy Imports Pattern
- Top-level [`droneresearch/__init__.py`](droneresearch/__init__.py) uses lazy imports to avoid hard dependencies
- ROS2 (`rclpy`, `px4_msgs`) and UI (`PyQt6`) are optional
- Use `get_backend()`, `get_sitl()`, `get_coordinator()` factory functions

## Build/Test Commands

```bash
# Install
pip install -e .                    # Core only
pip install -e ".[ros]"             # With ROS2 support
pip install -e ".[test]"            # With test dependencies

# Test
pytest tests/                       # Full suite (~1s, hardware-free)
pytest tests/test_apf.py -v         # Single module
pytest tests/ -k "not slow"         # Skip slow markers

# Run examples (needs SITL on tcp:127.0.0.1:5762)
python examples/hover.py --port tcp:127.0.0.1:5762
python examples/llm_swarm_control.py --backend mock --interactive

# CLI
droneresearch connect               # Default: tcp:127.0.0.1:5762
droneresearch status --port tcp:127.0.0.1:5760
DRONE_PORT=udp:127.0.0.1:14550 droneresearch arm
```

## Code Style

### Import Order
1. Standard library (`import threading`, `import time`)
2. Third-party (`import pytest`, `from pymavlink import mavutil`)
3. Local absolute (`from droneresearch.core.fsm import StateMachine`)
4. Use `from __future__ import annotations` for forward references

### Type Hints
- Use type hints for public APIs
- Optional dependencies wrapped in try/except with `_OK` flag pattern
- Example: `_ROS2_OK`, `_PX4_MSGS_OK`, `_MAV_OK`

### Error Handling
- Connection failures return `bool` (True/False), not exceptions
- FSM invalid transitions return `False` and increment `rejected_count`
- Logger queue full: tracks `_dropped` count, warns every 5s

### Naming Conventions
- Private methods: `_on_message`, `_handle_event`
- Constants: `AIRBORNE_STATES`, `SAFE_STATES`, `_TRANSITIONS`
- Fixtures: `fake_conn`, `make_msg`, `snap_factory`
- Drone IDs: `"D1"`, `"UAV_1"`, `"uav_1"` (context-dependent)
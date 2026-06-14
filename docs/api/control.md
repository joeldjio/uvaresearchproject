# Control API Reference

The control layer provides mission planning, execution, and monitoring capabilities.

## MissionEngine

Upload, run, and monitor MAVLink missions with waypoint-based navigation.

### Constructor

```python
MissionEngine(connection: MAVLinkConnection)
```

**Parameters:**
- `connection` (MAVLinkConnection): Active MAVLink connection

**Example:**
```python
from droneresearch.core.connection import MAVLinkConnection
from droneresearch.control.mission import MissionEngine

conn = MAVLinkConnection("tcp:127.0.0.1:5762")
conn.connect()
mission = MissionEngine(conn)
```

---

## Waypoint

Dataclass representing a mission waypoint.

### Constructor

```python
@dataclass
class Waypoint:
    lat: float                      # Latitude in degrees
    lon: float                      # Longitude in degrees
    alt: float = 10.0              # Altitude in meters (relative to home)
    speed: Optional[float] = None  # Speed in m/s (None = keep current)
    hold: float = 0.0              # Loiter time in seconds
    cmd: int = 16                  # MAV_CMD (16 = NAV_WAYPOINT)
    radius: float = 2.0            # Acceptance radius in meters
```

**Example:**
```python
from droneresearch.control.mission import Waypoint

# Simple waypoint
wp1 = Waypoint(lat=48.137, lon=11.575, alt=20)

# Waypoint with speed and loiter
wp2 = Waypoint(
    lat=48.138, 
    lon=11.576, 
    alt=25,
    speed=5.0,    # Fly at 5 m/s
    hold=10.0,    # Loiter for 10 seconds
    radius=3.0    # Accept within 3m
)
```

---

## MissionEngine Methods

### Building Missions

#### clear()

```python
def clear()
```

Clear all queued waypoints.

**Example:**
```python
mission.clear()
```

#### add()

```python
def add(wp: Waypoint)
```

Add a waypoint to the mission queue.

**Parameters:**
- `wp` (Waypoint): Waypoint to add

**Example:**
```python
mission.add(Waypoint(lat=48.137, lon=11.575, alt=20))
mission.add(Waypoint(lat=48.138, lon=11.576, alt=20))
```

#### from_list()

```python
def from_list(points: List[dict])
```

Build mission from list of dictionaries.

**Parameters:**
- `points` (List[dict]): List of waypoint dicts with "lat", "lon", "alt" keys

**Example:**
```python
waypoints = [
    {"lat": 48.137, "lon": 11.575, "alt": 20},
    {"lat": 48.138, "lon": 11.576, "alt": 20},
    {"lat": 48.139, "lon": 11.577, "alt": 20},
]
mission.from_list(waypoints)
```

---

### Mission Execution

#### upload()

```python
def upload() -> bool
```

Upload all queued waypoints to the autopilot.

**⚠️ WARNING:** This is **BLOCKING** for ~50ms per waypoint (push-all path) or until the autopilot completes the handshake (request-based path). **Always call from a worker thread**, never from the UI/Qt main thread.

**Protocol:**
Uses a **hybrid protocol**:
1. Sends `MISSION_COUNT` and waits up to 250ms for `MISSION_REQUEST(0)`
2. If request arrives → full request/response handshake (correct MAVLink behavior)
3. Otherwise → legacy push-all with 50ms inter-item pacing (ArduPilot-compatible fallback)

**Returns:**
- `bool`: True if upload successful, False otherwise

**Example:**
```python
# Build mission
mission.clear()
mission.add(Waypoint(lat=48.137, lon=11.575, alt=20))
mission.add(Waypoint(lat=48.138, lon=11.576, alt=20))

# Upload (blocking!)
if mission.upload():
    print("Mission uploaded successfully")
else:
    print("Upload failed")
```

**Worker Thread Pattern:**
```python
import threading

def upload_worker():
    if mission.upload():
        print("Upload complete")
    else:
        print("Upload failed")

thread = threading.Thread(target=upload_worker, daemon=True)
thread.start()
```

#### start()

```python
def start() -> bool
```

Start mission execution by switching to AUTO mode.

**Returns:**
- `bool`: True if mode change successful

**Example:**
```python
mission.upload()
mission.start()
```

#### pause()

```python
def pause() -> bool
```

Pause mission by switching to LOITER mode.

**Returns:**
- `bool`: True if mode change successful

**Example:**
```python
mission.pause()  # Drone will hold position
```

#### resume()

```python
def resume() -> bool
```

Resume mission by switching back to AUTO mode.

**Returns:**
- `bool`: True if mode change successful

**Example:**
```python
mission.resume()  # Continue mission
```

#### abort()

```python
def abort() -> bool
```

Abort mission and return to launch (RTL).

**Returns:**
- `bool`: True if RTL command successful

**Side Effects:**
- Sets `_running = False`
- Triggers `_abort_event` (interrupts any in-flight `upload()`)
- Unblocks `wait_done()`

**Example:**
```python
mission.abort()  # Emergency abort
```

#### wait_done()

```python
def wait_done(timeout: float = 600.0) -> bool
```

Block until mission completes or timeout.

**Parameters:**
- `timeout` (float): Maximum time to wait in seconds (default: 10 minutes)

**Returns:**
- `bool`: True if mission completed, False if timeout

**Example:**
```python
mission.start()
if mission.wait_done(timeout=300):
    print("Mission completed!")
else:
    print("Mission timeout")
```

---

### Callbacks

#### on_waypoint_reached()

```python
def on_waypoint_reached(cb: Callable)
```

Register callback for waypoint reached events.

**Parameters:**
- `cb` (Callable): Callback function receiving `seq: int` (waypoint sequence number)

**Example:**
```python
def on_waypoint(seq: int):
    print(f"Reached waypoint {seq}")

mission.on_waypoint_reached(on_waypoint)
```

#### on_mission_done()

```python
def on_mission_done(cb: Callable)
```

Register callback for mission completion.

**Parameters:**
- `cb` (Callable): Callback function (no parameters)

**Example:**
```python
def on_done():
    print("Mission complete!")

mission.on_mission_done(on_done)
```

---

## Complete Mission Example

```python
from droneresearch.core.connection import MAVLinkConnection
from droneresearch.control.mission import MissionEngine, Waypoint
import threading

# Connect
conn = MAVLinkConnection("tcp:127.0.0.1:5762")
conn.connect()

# Create mission
mission = MissionEngine(conn)
mission.clear()

# Add waypoints
mission.add(Waypoint(lat=48.137, lon=11.575, alt=20))
mission.add(Waypoint(lat=48.138, lon=11.576, alt=20))
mission.add(Waypoint(lat=48.139, lon=11.577, alt=20))

# Register callbacks
mission.on_waypoint_reached(lambda seq: print(f"Waypoint {seq} reached"))
mission.on_mission_done(lambda: print("Mission complete!"))

# Upload in worker thread
def upload_worker():
    if mission.upload():
        print("Upload successful, starting mission...")
        mission.start()
    else:
        print("Upload failed!")

thread = threading.Thread(target=upload_worker, daemon=True)
thread.start()

# Wait for completion
if mission.wait_done(timeout=600):
    print("Mission finished successfully")
else:
    print("Mission timeout or aborted")

conn.disconnect()
```

---

## Mission Monitoring

The `MissionEngine` automatically monitors mission progress via MAVLink messages:

**MISSION_CURRENT:**
- Updates `_current` sequence number
- Fires `on_waypoint_reached` callback

**MISSION_ITEM_REACHED:**
- Updates `_last_seq` sequence number
- Fires `on_waypoint_reached` callback
- Marks mission done when last waypoint reached

**HEARTBEAT:**
- Monitors flight mode
- Marks mission done if mode changes from AUTO/GUIDED during execution

---

## Advanced Usage

### Abort During Upload

The `abort()` method can interrupt an in-flight `upload()`:

```python
import threading

def upload_worker():
    print("Starting upload...")
    if mission.upload():
        print("Upload complete")
    else:
        print("Upload aborted")

thread = threading.Thread(target=upload_worker, daemon=True)
thread.start()

# Abort after 2 seconds
import time
time.sleep(2.0)
mission.abort()  # Interrupts upload
```

### Custom Waypoint Commands

Use different MAV_CMD values for special waypoints:

```python
# Takeoff waypoint
wp_takeoff = Waypoint(
    lat=48.137, 
    lon=11.575, 
    alt=10,
    cmd=22  # MAV_CMD_NAV_TAKEOFF
)

# Land waypoint
wp_land = Waypoint(
    lat=48.140, 
    lon=11.578, 
    alt=0,
    cmd=21  # MAV_CMD_NAV_LAND
)

mission.add(wp_takeoff)
mission.add(Waypoint(lat=48.138, lon=11.576, alt=20))
mission.add(wp_land)
```

### Speed Changes Mid-Mission

```python
# Slow approach
wp1 = Waypoint(lat=48.137, lon=11.575, alt=20, speed=3.0)

# Fast transit
wp2 = Waypoint(lat=48.138, lon=11.576, alt=20, speed=10.0)

# Slow landing approach
wp3 = Waypoint(lat=48.139, lon=11.577, alt=10, speed=2.0)

mission.add(wp1)
mission.add(wp2)
mission.add(wp3)
```

### Loiter Waypoints

```python
# Survey point: loiter for 30 seconds
survey_point = Waypoint(
    lat=48.137, 
    lon=11.575, 
    alt=50,
    hold=30.0,      # Loiter for 30 seconds
    radius=5.0      # Within 5m radius
)

mission.add(survey_point)
```

---

## Mission Protocol Details

### Handshake Path (Preferred)

1. GCS sends `MISSION_COUNT(n)`
2. Autopilot sends `MISSION_REQUEST(0)`
3. GCS sends `MISSION_ITEM_INT(0)` (home)
4. Autopilot sends `MISSION_REQUEST(1)`
5. GCS sends `MISSION_ITEM_INT(1)` (first waypoint)
6. ... repeat for all waypoints ...
7. Autopilot sends `MISSION_ACK(MAV_MISSION_ACCEPTED)`

**Timeout:** 3 seconds per `MISSION_REQUEST`

### Push-All Path (Fallback)

1. GCS sends `MISSION_COUNT(n)`
2. Wait 250ms for `MISSION_REQUEST(0)` (timeout)
3. GCS sends all `MISSION_ITEM_INT` messages with 50ms pacing
4. No explicit ACK expected

**Used when:** Autopilot doesn't respond with `MISSION_REQUEST(0)` within 250ms (some ArduPilot configurations)

---

## Error Handling

### Upload Failures

```python
if not mission.upload():
    # Check connection
    if not conn.connected:
        print("Connection lost")
    
    # Check last NACK
    if conn.last_nack:
        cmd, result = conn.last_nack
        print(f"Last NACK: {cmd} → {result}")
    
    # Retry
    print("Retrying upload...")
    mission.upload()
```

### Mission Interruption

```python
# Monitor for mode changes
def on_mode(mode: str):
    if mode != "AUTO" and mission._running:
        print(f"Mission interrupted: mode changed to {mode}")

conn.on("mode", on_mode)
```

### Timeout Handling

```python
mission.start()

# Wait with timeout
if not mission.wait_done(timeout=300):
    print("Mission timeout - aborting")
    mission.abort()
    
    # Wait for RTL to complete
    time.sleep(30)
```

---

## Performance Considerations

### Upload Time

- **Handshake path:** ~100-200ms per waypoint (depends on link latency)
- **Push-all path:** ~50ms per waypoint (fixed pacing)
- **10 waypoints:** ~0.5-2 seconds total

### Thread Safety

- `upload()` is **NOT** thread-safe - only call from one thread at a time
- `start()`, `pause()`, `resume()`, `abort()` are thread-safe
- Callbacks are invoked from the MAVLink receive thread

### Memory Usage

- Each waypoint: ~100 bytes
- Mission history: Last 500 state transitions kept
- No memory leaks on repeated upload/clear cycles

---

## Integration with High-Level API

The `Drone` class provides a simplified mission interface:

```python
from droneresearch import Drone

drone = Drone("tcp:127.0.0.1:5762")
drone.connect()

# Simple mission execution
waypoints = [
    {"lat": 48.137, "lon": 11.575, "alt": 20},
    {"lat": 48.138, "lon": 11.576, "alt": 20},
]

drone.run_mission(waypoints, wait=True, timeout=600)
```

Internally, this uses `MissionEngine`:
```python
def run_mission(self, waypoints, wait=True, timeout=600):
    self._mission.clear()
    for wp in waypoints:
        self._mission.add(Waypoint(**wp))
    self._mission.upload()
    self._mission.start()
    if wait:
        return self._mission.wait_done(timeout=timeout)
    return True

---

## FieldCoveragePlanner

Generate waypoint patterns for efficient field coverage in agricultural operations.

### Constructor

```python
FieldCoveragePlanner()
```

**Example:**
```python
from droneresearch.control.field_coverage import FieldCoveragePlanner

planner = FieldCoveragePlanner()
planner.set_home_position(47.3977, 8.5456)
```

---

### set_home_position()

Set home position for GPS coordinate conversions.

```python
set_home_position(lat: float, lon: float) -> None
```

**Parameters:**
- `lat` (float): Home latitude in degrees
- `lon` (float): Home longitude in degrees

**Example:**
```python
planner.set_home_position(47.3977, 8.5456)  # Zurich
```

---

### generate_coverage_waypoints()

Generate waypoints for field coverage based on boundary and configuration.

```python
generate_coverage_waypoints(
    boundary: FieldBoundary,
    config: CoverageConfig
) -> List[Tuple[float, float, float]]
```

**Parameters:**
- `boundary` (FieldBoundary): Field boundary definition
- `config` (CoverageConfig): Coverage configuration

**Returns:**
- List of waypoints as `(lat, lon, alt)` tuples

**Raises:**
- `ValueError`: If home position not set or invalid configuration

**Example:**
```python
from droneresearch.control.field_coverage import (
    FieldBoundary,
    CoverageConfig,
    CoveragePattern
)

boundary = FieldBoundary(corners=[
    (47.3977, 8.5456),
    (47.3987, 8.5456),
    (47.3987, 8.5466),
    (47.3977, 8.5466),
])

config = CoverageConfig(
    pattern=CoveragePattern.PARALLEL_LINES,
    altitude=20.0,
    line_spacing=10.0,
    overlap=0.2
)

waypoints = planner.generate_coverage_waypoints(boundary, config)
```

---

### estimate_coverage_time()

Estimate time to complete coverage mission.

```python
estimate_coverage_time(
    waypoints: List[Tuple[float, float, float]],
    speed: float
) -> float
```

**Parameters:**
- `waypoints` (List): List of `(lat, lon, alt)` waypoints
- `speed` (float): Flight speed in m/s

**Returns:**
- Estimated time in seconds

**Example:**
```python
waypoints = planner.generate_coverage_waypoints(boundary, config)
time_seconds = planner.estimate_coverage_time(waypoints, speed=5.0)
print(f"Mission time: {time_seconds / 60:.1f} minutes")
```

---

## FieldBoundary

Field boundary definition using GPS coordinates.

### Constructor

```python
@dataclass
class FieldBoundary:
    corners: List[Tuple[float, float]]  # [(lat, lon), ...]
```

**Parameters:**
- `corners` (List): List of GPS coordinates defining field boundary (minimum 3 corners)

**Example:**
```python
from droneresearch.control.field_coverage import FieldBoundary

# Rectangular field
boundary = FieldBoundary(corners=[
    (47.3977, 8.5456),  # SW corner
    (47.3987, 8.5456),  # NW corner
    (47.3987, 8.5466),  # NE corner
    (47.3977, 8.5466),  # SE corner
])
```

---

## CoverageConfig

Configuration for field coverage planning.

### Constructor

```python
@dataclass
class CoverageConfig:
    pattern: CoveragePattern = CoveragePattern.PARALLEL_LINES
    altitude: float = 20.0        # meters AGL
    overlap: float = 0.2          # 20% overlap (0-1)
    line_spacing: float = 10.0    # meters between lines
    speed: float = 5.0            # m/s
    heading: float = 0.0          # degrees (0=North, 90=East)
```

**Parameters:**
- `pattern` (CoveragePattern): Coverage pattern type
- `altitude` (float): Flight altitude in meters AGL (must be positive)
- `overlap` (float): Overlap between passes (0-1, default 0.2)
- `line_spacing` (float): Distance between parallel lines in meters (must be positive)
- `speed` (float): Flight speed in m/s (must be positive)
- `heading` (float): Pattern orientation in degrees (0=North, 90=East)

**Example:**
```python
from droneresearch.control.field_coverage import CoverageConfig, CoveragePattern

config = CoverageConfig(
    pattern=CoveragePattern.PARALLEL_LINES,
    altitude=25.0,
    line_spacing=15.0,
    overlap=0.3,
    speed=8.0,
    heading=45.0
)
```

---

## CoveragePattern

Enum defining coverage pattern types.

```python
class CoveragePattern(Enum):
    PARALLEL_LINES = 0  # Parallel lines with alternating direction
    SPIRAL = 1          # Spiral from outside to inside
    GRID = 2            # Grid pattern (both directions)
    ZIGZAG = 3          # Zigzag pattern (no turns at ends)
```

**Example:**
```python
from droneresearch.control.field_coverage import CoveragePattern

# Use in configuration
config = CoverageConfig(pattern=CoveragePattern.SPIRAL)
```

---
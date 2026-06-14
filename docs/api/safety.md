# Safety API Reference

The safety layer provides collision avoidance and geofencing using Artificial Potential Fields (APF).

## Overview

The APF Safety Filter prevents collisions between drones and enforces operational boundaries by:
- Applying **repulsive forces** between drones (and obstacles)
- Applying **attractive forces** toward desired waypoints
- Enforcing **kinematic limits** (max speed)
- Clipping positions to **geofence boundaries**

**Based on:** SkySim (Shibu et al., 2025) - "SkySim: A ROS2-based Simulation Environment for Natural Language Control of Drone Swarms using Large Language Models" (arXiv:2602.01226)

---

## Pose3D

3D position representation in local NED coordinates.

### Constructor

```python
@dataclass
class Pose3D:
    x: float = 0.0  # North in meters
    y: float = 0.0  # East in meters
    z: float = 0.0  # Altitude above ground (positive = UP)
```

**Coordinate System:**
- `x` = North (meters)
- `y` = East (meters)
- `z` = Altitude above ground (meters, **positive = UP**)

**Note:** The APF filter internally inverts `z` for NED calculations, but the API uses positive-up for intuitive altitude handling.

**Example:**
```python
from droneresearch.safety.apf import Pose3D

# Drone at 10m north, 5m east, 15m altitude
pos = Pose3D(x=10.0, y=5.0, z=15.0)
```

### Methods

#### dist()

```python
def dist(other: Pose3D) -> float
```

Calculate 3D Euclidean distance to another position.

**Parameters:**
- `other` (Pose3D): Target position

**Returns:**
- `float`: Distance in meters

**Example:**
```python
pos1 = Pose3D(0, 0, 10)
pos2 = Pose3D(3, 4, 10)
distance = pos1.dist(pos2)  # 5.0 meters
```

#### dist_2d()

```python
def dist_2d(other: Pose3D) -> float
```

Calculate 2D horizontal distance (ignoring altitude).

**Parameters:**
- `other` (Pose3D): Target position

**Returns:**
- `float`: Horizontal distance in meters

**Example:**
```python
pos1 = Pose3D(0, 0, 10)
pos2 = Pose3D(3, 4, 20)
distance = pos1.dist_2d(pos2)  # 5.0 meters (altitude ignored)
```

#### norm()

```python
def norm() -> float
```

Calculate vector magnitude (distance from origin).

**Returns:**
- `float`: Magnitude in meters

#### normalized()

```python
def normalized() -> Pose3D
```

Return unit vector in same direction.

**Returns:**
- `Pose3D`: Normalized vector (magnitude = 1.0)

**Example:**
```python
vec = Pose3D(3, 4, 0)
unit = vec.normalized()  # Pose3D(0.6, 0.8, 0.0)
```

#### clamp()

```python
def clamp(max_norm: float) -> Pose3D
```

Limit vector magnitude to maximum value.

**Parameters:**
- `max_norm` (float): Maximum allowed magnitude

**Returns:**
- `Pose3D`: Clamped vector

**Example:**
```python
vec = Pose3D(10, 0, 0)
clamped = vec.clamp(5.0)  # Pose3D(5.0, 0.0, 0.0)
```

### Operators

```python
# Addition
pos1 + pos2  # Component-wise addition

# Scalar multiplication
pos * 2.0    # Scale all components

# String representation
str(pos)     # "Pose3D(10.00, 5.00, 15.00)"
```

---

## Geofence

Cylindrical geofence with horizontal radius and altitude band.

### Constructor

```python
@dataclass
class Geofence:
    origin_x: float = 0.0    # Origin north coordinate (meters)
    origin_y: float = 0.0    # Origin east coordinate (meters)
    radius: float = 50.0     # Horizontal radius (meters)
    alt_min: float = 1.0     # Minimum altitude (meters)
    alt_max: float = 30.0    # Maximum altitude (meters)
```

**Example:**
```python
from droneresearch.safety.apf import Geofence

# 100m radius, 2-50m altitude
fence = Geofence(
    origin_x=0.0,
    origin_y=0.0,
    radius=100.0,
    alt_min=2.0,
    alt_max=50.0
)
```

### Methods

#### contains()

```python
def contains(p: Pose3D) -> bool
```

Check if position is within geofence.

**Parameters:**
- `p` (Pose3D): Position to check

**Returns:**
- `bool`: True if inside geofence

**Example:**
```python
fence = Geofence(radius=50.0, alt_min=1.0, alt_max=30.0)
pos = Pose3D(10, 10, 15)
if fence.contains(pos):
    print("Inside geofence")
```

#### clip()

```python
def clip(p: Pose3D) -> Pose3D
```

Clip position to geofence boundary.

**Parameters:**
- `p` (Pose3D): Position to clip

**Returns:**
- `Pose3D`: Clipped position (guaranteed inside geofence)

**Example:**
```python
fence = Geofence(radius=50.0, alt_min=1.0, alt_max=30.0)
pos = Pose3D(60, 0, 35)  # Outside fence
safe = fence.clip(pos)    # Pose3D(50.0, 0.0, 30.0)
```

---

## APFSafetyFilter

Artificial Potential Field collision avoidance filter.

### Constructor

```python
APFSafetyFilter(
    min_separation: float = 2.0,
    max_speed: float = 3.0,
    geofence_radius: float = 50.0,
    geofence_alt: Tuple[float, float] = (1.0, 30.0),
    repulsion_gain: float = 2.0,
    attraction_gain: float = 1.0,
    obstacle_radius: float = 4.0,
    dt: float = 0.05  # 20 Hz
)
```

**Parameters:**
- `min_separation` (float): Minimum safe distance between drones (meters)
- `max_speed` (float): Maximum velocity step per update (m/s)
- `geofence_radius` (float): Horizontal geofence radius from origin (meters)
- `geofence_alt` (Tuple[float, float]): (min_alt, max_alt) altitude band (meters)
- `repulsion_gain` (float): Strength of repulsive force between drones
- `attraction_gain` (float): Strength of attractive force toward waypoints
- `obstacle_radius` (float): Safety margin - repulsion activates within this range (meters)
- `dt` (float): Time step for velocity integration (seconds)

**Example:**
```python
from droneresearch.safety.apf import APFSafetyFilter

apf = APFSafetyFilter(
    min_separation=2.0,      # Keep 2m apart
    max_speed=3.0,           # Max 3 m/s movement per step
    geofence_radius=50.0,    # 50m radius fence
    geofence_alt=(1.0, 30.0),# 1-30m altitude
    repulsion_gain=2.0,      # Strong repulsion
    attraction_gain=1.0,     # Moderate attraction
    obstacle_radius=4.0,     # Activate repulsion at 4m
    dt=0.05                  # 20 Hz update rate
)
```

### Methods

#### filter()

```python
def filter(
    positions: Dict[str, Pose3D],
    desired: Dict[str, Pose3D]
) -> Dict[str, Pose3D]
```

Apply APF to compute safe waypoints for all drones.

**Parameters:**
- `positions` (Dict[str, Pose3D]): Current positions of all drones
- `desired` (Dict[str, Pose3D]): Desired target positions

**Returns:**
- `Dict[str, Pose3D]`: Safe waypoints after APF filtering

**Algorithm:**
1. For each drone:
   - Calculate **attractive force** toward desired position
   - Calculate **repulsive forces** from other drones
   - Calculate **repulsive forces** from static obstacles
   - Sum forces and clamp to max_speed
   - Apply geofence clipping

**Example:**
```python
# Current positions
positions = {
    "D1": Pose3D(0, 0, 10),
    "D2": Pose3D(3, 0, 10),
    "D3": Pose3D(6, 0, 10),
}

# Desired positions (from mission planner / LLM)
desired = {
    "D1": Pose3D(0, 5, 10),
    "D2": Pose3D(5, 5, 10),
    "D3": Pose3D(10, 5, 10),
}

# Apply APF filter
safe = apf.filter(positions, desired)

# Send safe waypoints to drones
for drone_id, pos in safe.items():
    drone = swarm.get(drone_id)
    drone.goto(pos.x, pos.y, pos.z)
```

#### check_separation()

```python
def check_separation(
    positions: Dict[str, Pose3D]
) -> List[Tuple[str, str, float]]
```

Check for minimum separation violations.

**Parameters:**
- `positions` (Dict[str, Pose3D]): Current positions of all drones

**Returns:**
- `List[Tuple[str, str, float]]`: List of (drone_a, drone_b, distance) for violations

**Example:**
```python
positions = {
    "D1": Pose3D(0, 0, 10),
    "D2": Pose3D(1, 0, 10),  # Only 1m apart!
}

violations = apf.check_separation(positions)
for drone_a, drone_b, dist in violations:
    print(f"WARNING: {drone_a} and {drone_b} are {dist:.2f}m apart")
```

#### add_obstacle()

```python
def add_obstacle(x: float, y: float, z: float = 0.0)
```

Add a static obstacle (e.g., building, tree).

**Parameters:**
- `x` (float): North coordinate (meters)
- `y` (float): East coordinate (meters)
- `z` (float): Altitude (meters, default: 0.0)

**Example:**
```python
# Add building at (20, 30) with 25m height
apf.add_obstacle(x=20.0, y=30.0, z=25.0)

# Add tree at (10, 15) with 10m height
apf.add_obstacle(x=10.0, y=15.0, z=10.0)
```

#### clear_obstacles()

```python
def clear_obstacles()
```

Remove all static obstacles.

**Example:**
```python
apf.clear_obstacles()
```

---

## APFFilterLoop

Background thread running APF filter at configurable rate.

### Constructor

```python
APFFilterLoop(
    apf: APFSafetyFilter,
    get_positions: Callable[[], Dict[str, Pose3D]],
    get_desired: Callable[[], Dict[str, Pose3D]],
    on_safe: Callable[[Dict[str, Pose3D]], None],
    hz: float = 20.0,
    on_violation: Optional[Callable[[List], None]] = None
)
```

**Parameters:**
- `apf` (APFSafetyFilter): Configured APF filter
- `get_positions` (Callable): Function returning current drone positions
- `get_desired` (Callable): Function returning desired target positions
- `on_safe` (Callable): Callback receiving safe waypoints
- `hz` (float): Update rate in Hz (default: 20.0)
- `on_violation` (Callable): Optional callback for separation violations

**Example:**
```python
from droneresearch.safety.apf import APFSafetyFilter, APFFilterLoop

apf = APFSafetyFilter()

# Data sources
def get_positions():
    return {
        "D1": Pose3D(swarm.get("D1").telemetry.x, ...),
        "D2": Pose3D(swarm.get("D2").telemetry.x, ...),
    }

def get_desired():
    return mission_planner.get_targets()

# Callback to send safe waypoints
def on_safe(safe_waypoints):
    for drone_id, pos in safe_waypoints.items():
        swarm.get(drone_id).goto(pos.x, pos.y, pos.z)

# Violation handler
def on_violation(violations):
    for drone_a, drone_b, dist in violations:
        print(f"COLLISION RISK: {drone_a}-{drone_b} at {dist:.2f}m")

# Start filter loop
loop = APFFilterLoop(
    apf=apf,
    get_positions=get_positions,
    get_desired=get_desired,
    on_safe=on_safe,
    hz=20.0,
    on_violation=on_violation
)
loop.start()

# ... run mission ...

loop.stop()
```

### Methods

#### start()

```python
def start()
```

Start the filter loop in a background thread.

#### stop()

```python
def stop()
```

Stop the filter loop.

---

## Complete Usage Example

```python
from droneresearch import Swarm
from droneresearch.safety.apf import APFSafetyFilter, Pose3D

# Create swarm
swarm = Swarm()
swarm.add("D1", "tcp:127.0.0.1:5762")
swarm.add("D2", "tcp:127.0.0.1:5763")
swarm.add("D3", "tcp:127.0.0.1:5764")
swarm.connect_all()

# Configure APF filter
apf = APFSafetyFilter(
    min_separation=3.0,
    max_speed=2.0,
    geofence_radius=100.0,
    geofence_alt=(2.0, 50.0)
)

# Add obstacles
apf.add_obstacle(x=20.0, y=20.0, z=15.0)  # Building

# Takeoff
swarm.arm_all()
swarm.takeoff_all(altitude=10.0)

# Mission waypoints (potentially unsafe)
desired = {
    "D1": Pose3D(10, 10, 15),
    "D2": Pose3D(10, 10, 15),  # Same as D1 - collision!
    "D3": Pose3D(10, 10, 15),  # Same as D1 - collision!
}

# Get current positions
positions = {
    "D1": Pose3D(0, 0, 10),
    "D2": Pose3D(5, 0, 10),
    "D3": Pose3D(10, 0, 10),
}

# Apply APF filter
safe = apf.filter(positions, desired)

# Safe waypoints will be spread out to maintain separation
for drone_id, pos in safe.items():
    print(f"{drone_id}: {pos}")
    drone = swarm.get(drone_id)
    # Convert to GPS if needed, or use local NED
    drone.goto(home_lat + pos.x/111320, home_lon + pos.y/111320, pos.z)

# Check for violations
violations = apf.check_separation(safe)
if violations:
    print("WARNING: Separation violations detected!")
    for drone_a, drone_b, dist in violations:
        print(f"  {drone_a} - {drone_b}: {dist:.2f}m")
```

---

## APF Algorithm Details

### Attractive Force

Pulls drone toward desired position:

```
F_attr = (desired - current) * attraction_gain
F_attr = clamp(F_attr, max_speed * dt)
```

### Repulsive Force

Pushes drone away from obstacles/drones:

```
For each obstacle within obstacle_radius:
    distance = ||current - obstacle||
    if distance < obstacle_radius:
        magnitude = repulsion_gain * (1/d - 1/r) / d²
        direction = normalize(current - obstacle)
        F_rep += direction * magnitude * dt
```

### Total Force

```
F_total = F_attr + F_rep
F_total = clamp(F_total, max_speed * dt)
new_position = current + F_total
```

### Geofence Clipping

```
if new_position outside geofence:
    new_position = clip_to_boundary(new_position)
```

---

## Tuning Guidelines

### min_separation

- **Too small:** Risk of collisions
- **Too large:** Drones spread too far, formations break
- **Recommended:** 2-3 meters for outdoor, 1-2 meters for indoor

### max_speed

- **Too small:** Slow response, drones lag behind
- **Too large:** Jerky motion, overshooting
- **Recommended:** 2-5 m/s depending on drone capabilities

### repulsion_gain

- **Too small:** Weak avoidance, collisions possible
- **Too large:** Drones repel too strongly, formations unstable
- **Recommended:** 1.5-3.0

### attraction_gain

- **Too small:** Slow convergence to target
- **Too large:** Overshooting, oscillation
- **Recommended:** 0.5-1.5

### obstacle_radius

- **Too small:** Late avoidance, near-misses
- **Too large:** Drones avoid too early, inefficient paths
- **Recommended:** 2× min_separation (4-6 meters)

---

## Performance Considerations

### Computational Complexity

- **O(n²)** for n drones (all-pairs repulsion)
- **O(n×m)** for m static obstacles
- **20 Hz:** ~50ms budget per cycle
- **Practical limit:** ~20 drones at 20 Hz on modern CPU

### Optimization Tips

1. **Reduce update rate** for large swarms (10 Hz instead of 20 Hz)
2. **Spatial partitioning** for >20 drones (only check nearby pairs)
3. **Async filtering** in separate thread (use `APFFilterLoop`)

### Memory Usage

- **Per drone:** ~100 bytes
- **10 drones:** ~1 KB
- **100 drones:** ~10 KB
- Negligible compared to telemetry/logging

---

## Integration with Mission Planning

```python
from droneresearch.control.mission import MissionEngine, Waypoint
from droneresearch.safety.apf import APFSafetyFilter, Pose3D

# Mission waypoints
mission_waypoints = [
    Waypoint(lat=48.137, lon=11.575, alt=20),
    Waypoint(lat=48.138, lon=11.576, alt=20),
]

# Convert to local NED
def gps_to_ned(lat, lon, alt, home_lat, home_lon):
    x = (lat - home_lat) * 111320  # meters north
    y = (lon - home_lon) * 111320 * cos(radians(home_lat))  # meters east
    z = alt  # meters altitude
    return Pose3D(x, y, z)

# Apply APF before sending to drones
apf = APFSafetyFilter()
for wp in mission_waypoints:
    ned = gps_to_ned(wp.lat, wp.lon, wp.alt, home_lat, home_lon)
    desired = {"D1": ned}
    positions = {"D1": get_current_position()}
    safe = apf.filter(positions, desired)
    # Send safe waypoint
    drone.goto(safe["D1"].x, safe["D1"].y, safe["D1"].z)
```

---

## Safety Guarantees

### What APF Guarantees

✅ Collision avoidance between drones (if properly tuned)  
✅ Geofence enforcement (hard boundary)  
✅ Kinematic limits (max speed)  
✅ Smooth trajectories (no sudden jumps)

### What APF Does NOT Guarantee

❌ Optimal paths (greedy local optimization)  
❌ Deadlock-free (drones can get stuck in local minima)  
❌ Real-time guarantees (depends on CPU load)  
❌ Obstacle detection (only pre-defined obstacles)

### Recommended Additional Safety

1. **Pre-flight checks:** GPS fix, battery, geofence
2. **Failsafe modes:** RTL on low battery, loss of GPS
3. **Manual override:** Always have RC control available
4. **Redundant sensors:** Use onboard collision avoidance if available
5. **Conservative tuning:** Start with large separations, slow speeds
---

## CollisionPredictor

**New in v0.4.0**

Predicts future collisions based on current drone trajectories or planned waypoints.

### Constructor

```python
from droneresearch.safety.collision_predictor import CollisionPredictor

predictor = CollisionPredictor(
    time_horizon=10.0,        # seconds to look ahead
    min_separation=2.0,       # minimum safe distance (meters)
    sample_rate=0.5,          # prediction sample interval (seconds)
    critical_threshold=1.0,   # critical collision distance (meters)
    warning_threshold=1.5     # warning collision distance (meters)
)
```

**Parameters:**
- `time_horizon` (float): How far into the future to predict (seconds). Default: 10.0
- `min_separation` (float): Minimum safe distance between drones (meters). Default: 2.0
- `sample_rate` (float): Time interval for trajectory sampling (seconds). Default: 0.5
- `critical_threshold` (float): Distance threshold for critical severity (meters). Default: 1.0
- `warning_threshold` (float): Distance threshold for warning severity (meters). Default: 1.5

### Methods

#### predict()

```python
def predict(states: Dict[str, DroneState]) -> List[CollisionPrediction]
```

Predict collisions based on current velocities (velocity-based prediction).

**Parameters:**
- `states` (Dict[str, DroneState]): Current state of each drone

**Returns:**
- `List[CollisionPrediction]`: List of predicted collisions, sorted by time_to_collision

**Example:**
```python
from droneresearch.safety.collision_predictor import DroneState

states = {
    "D1": DroneState(x=0, y=0, z=10, vx=2, vy=0, vz=0, armed=True),
    "D2": DroneState(x=20, y=0, z=10, vx=-2, vy=0, vz=0, armed=True),
}

predictions = predictor.predict(states)
for pred in predictions:
    print(f"Collision: {pred.drone_a} ↔ {pred.drone_b} in {pred.time_to_collision:.1f}s")
```

#### predict_with_waypoints()

```python
def predict_with_waypoints(
    states: Dict[str, DroneState],
    waypoints: Dict[str, List[Tuple[float, float, float]]],
    cruise_speed: float = 5.0
) -> List[CollisionPrediction]
```

Predict collisions based on planned waypoints (waypoint-aware prediction).

**Parameters:**
- `states` (Dict[str, DroneState]): Current state of each drone
- `waypoints` (Dict[str, List[Tuple[float, float, float]]]): Planned waypoints for each drone in local NED coordinates [(x, y, z), ...]
- `cruise_speed` (float): Expected cruise speed between waypoints (m/s). Default: 5.0

**Returns:**
- `List[CollisionPrediction]`: List of predicted collisions along planned routes

**Example:**
```python
waypoints = {
    "D1": [(100, 0, 10), (100, 100, 10), (0, 100, 10)],  # Square pattern
    "D2": [(0, 100, 10), (100, 0, 10)],  # Diagonal crossing
}

predictions = predictor.predict_with_waypoints(states, waypoints, cruise_speed=5.0)
```

**Algorithm:**
1. Builds time-stamped trajectory from waypoints: `[(time, x, y, z), ...]`
2. Interpolates positions at regular intervals (sample_rate)
3. Finds minimum distance between all drone pairs
4. Reports collisions where distance < min_separation

---

## DroneState

**New in v0.4.0**

Current state of a drone for collision prediction.

### Constructor

```python
@dataclass
class DroneState:
    x: float = 0.0      # North (meters)
    y: float = 0.0      # East (meters)
    z: float = 0.0      # Altitude above ground (meters, positive up)
    vx: float = 0.0     # Velocity North (m/s)
    vy: float = 0.0     # Velocity East (m/s)
    vz: float = 0.0     # Velocity Up (m/s)
    armed: bool = False # Armed status
```

### Methods

#### position_at()

```python
def position_at(dt: float) -> Tuple[float, float, float]
```

Predict position after `dt` seconds assuming constant velocity.

**Parameters:**
- `dt` (float): Time delta in seconds

**Returns:**
- `Tuple[float, float, float]`: Predicted (x, y, z) position

#### distance_to()

```python
def distance_to(other: DroneState) -> float
```

Calculate 3D Euclidean distance to another drone.

**Parameters:**
- `other` (DroneState): Target drone state

**Returns:**
- `float`: Distance in meters

---

## CollisionPrediction

**New in v0.4.0**

Predicted collision between two drones.

### Attributes

```python
@dataclass
class CollisionPrediction:
    drone_a: str                                    # First drone ID
    drone_b: str                                    # Second drone ID
    time_to_collision: float                        # Seconds until collision
    min_distance: float                             # Closest approach distance (meters)
    collision_point: Tuple[float, float, float]     # (x, y, z) in NED
    severity: str                                   # "critical" | "warning" | "caution"
```

**Severity Levels:**
- `"critical"`: distance < critical_threshold (default: 1.0m)
- `"warning"`: distance < warning_threshold (default: 1.5m)
- `"caution"`: distance < min_separation (default: 2.0m)

### Methods

#### to_dict()

```python
def to_dict() -> dict
```

Convert to QML-friendly dictionary format.

**Returns:**
```python
{
    "droneA": "D1",
    "droneB": "D2",
    "timeToCollision": 5.2,
    "minDistance": 0.8,
    "collisionPoint": {"x": 50.0, "y": 0.0, "z": 10.0},
    "severity": "critical"
}
```

---

## UI Integration

### SafetyContext (QML)

**New Methods in v0.4.0:**

#### enableCollisionPrediction()

```qml
safety.enableCollisionPrediction(true)  // Enable
safety.enableCollisionPrediction(false) // Disable
```

#### configureCollisionPredictor()

```qml
safety.configureCollisionPredictor({
    timeHorizon: 15.0,
    minSeparation: 3.0,
    sampleRate: 0.3,
    criticalThreshold: 1.0,
    warningThreshold: 2.0
})
```

#### enableWaypointAwarePrediction()

```qml
safety.enableWaypointAwarePrediction(true)  // Use waypoints
safety.enableWaypointAwarePrediction(false) // Use velocity
```

#### updateDroneWaypoints()

```qml
safety.updateDroneWaypoints({
    "D1": [{lat: 48.137, lon: 11.575, alt: 10}, ...],
    "D2": [{lat: 48.138, lon: 11.576, alt: 10}, ...]
})
```

**Signals:**

```qml
Connections {
    target: safety
    function onCollisionPredicted(predictions) {
        // predictions: List of collision prediction dicts
        for (var i = 0; i < predictions.length; i++) {
            var pred = predictions[i]
            console.log("Collision:", pred.droneA, "↔", pred.droneB,
                       "in", pred.timeToCollision, "s")
        }
    }
}
```

### AppState (QML)

**New in v0.4.0:** Per-drone waypoint storage

#### Waypoint Management

```qml
// Get waypoints for a drone
var wps = Cmp.AppState.getWaypoints("D1")

// Set waypoints for a drone
Cmp.AppState.setWaypoints("D1", [
    {lat: 48.137, lon: 11.575, alt: 10},
    {lat: 48.138, lon: 11.576, alt: 15}
])

// Add single waypoint
Cmp.AppState.addWaypoint("D1", 48.139, 11.577, 20)

// Clear waypoints
Cmp.AppState.clearWaypoints("D1")

// Clear all waypoints
Cmp.AppState.clearAllWaypoints()
```

#### Multi-Drone Operations

```qml
// Set same waypoints for multiple drones
var droneIds = ["D1", "D2", "D3"]
var waypoints = [{lat: 48.137, lon: 11.575, alt: 10}, ...]
Cmp.AppState.setWaypointsForMultiple(droneIds, waypoints)

// Add waypoint to multiple drones
Cmp.AppState.addWaypointForMultiple(droneIds, 48.138, 11.576, 15)
```

**Signals:**

```qml
Connections {
    target: Cmp.AppState
    function onWaypointsChanged(droneId) {
        console.log("Waypoints changed for", droneId)
        var wps = Cmp.AppState.getWaypoints(droneId)
        console.log("New waypoint count:", wps.length)
    }
}
```

---


## BatteryMonitor

Smart battery monitoring with predictive Return-to-Launch (RTL) capabilities.

### Constructor

```python
from droneresearch.safety.battery_monitor import BatteryMonitor

monitor = BatteryMonitor(
    critical_threshold=20.0,  # Battery % to trigger immediate RTL
    safety_margin=1.2,        # Safety multiplier for RTL calculations
    min_samples=5,            # Minimum samples for predictions
    max_history=100           # Maximum samples to keep
)
```

**Parameters:**
- `critical_threshold` (float): Battery percentage below which RTL is immediately triggered. Default: 20.0
- `safety_margin` (float): Multiplier for RTL time calculations to add safety buffer. Default: 1.2 (20% buffer)
- `min_samples` (int): Minimum number of samples required for predictive RTL. Default: 5
- `max_history` (int): Maximum number of historical samples to keep per drone. Default: 100

### Methods

#### start_monitoring()

Begin monitoring a drone's battery status.

```python
monitor.start_monitoring("UAV_1")
```

**Parameters:**
- `drone_id` (str): Unique identifier for the drone

**Returns:** None

#### stop_monitoring()

Stop monitoring a drone's battery status.

```python
monitor.stop_monitoring("UAV_1")
```

**Parameters:**
- `drone_id` (str): Unique identifier for the drone

**Returns:** None

#### update()

Update battery monitor with new telemetry data.

```python
telemetry = {
    "battery_pct": 75.0,
    "lat": 48.137,
    "lon": 11.575,
    "alt_rel": 10.0
}
monitor.update("UAV_1", telemetry)
```

**Parameters:**
- `drone_id` (str): Unique identifier for the drone
- `telemetry` (dict): Telemetry data containing:
  - `battery_pct` (float): Battery percentage (0-100)
  - `lat` (float): Latitude in degrees
  - `lon` (float): Longitude in degrees
  - `alt_rel` (float): Relative altitude in meters

**Returns:** None

**Note:** This method should be called periodically (e.g., every 1-2 seconds) with updated telemetry.

#### should_trigger_rtl()

Check if RTL should be triggered for a drone.

```python
home_position = (48.137, 11.575, 0.0)  # (lat, lon, alt)
should_rtl, reason = monitor.should_trigger_rtl("UAV_1", home_position)

if should_rtl:
    print(f"RTL triggered: {reason}")
    # Trigger RTL command...
```

**Parameters:**
- `drone_id` (str): Unique identifier for the drone
- `home_position` (tuple): Home position as (latitude, longitude, altitude)

**Returns:** 
- `tuple[bool, str]`: (should_trigger, reason)
  - `should_trigger`: True if RTL should be triggered
  - `reason`: Human-readable reason for RTL trigger

**Trigger Conditions:**
1. Battery below critical threshold (immediate)
2. Insufficient battery for safe RTL (predictive)
3. Already triggered (returns False with "RTL already triggered")

#### get_battery_status()

Get comprehensive battery status for a drone.

```python
status = monitor.get_battery_status("UAV_1", home_position)

print(f"Battery: {status.battery_pct:.1f}%")
print(f"Time remaining: {status.estimated_time_remaining:.0f}s")
print(f"RTL requires: {status.rtl_battery_required:.1f}%")
print(f"Should RTL: {status.should_rtl}")
```

**Parameters:**
- `drone_id` (str): Unique identifier for the drone
- `home_position` (tuple): Home position as (latitude, longitude, altitude)

**Returns:**
- `BatteryStatus | None`: Battery status object or None if not monitoring

#### reset_rtl_trigger()

Reset the RTL trigger flag for a drone.

```python
monitor.reset_rtl_trigger("UAV_1")
```

**Parameters:**
- `drone_id` (str): Unique identifier for the drone

**Returns:** None

**Use Case:** Call this after successfully executing RTL to allow re-triggering if needed.

## BatteryStatus

Dataclass containing comprehensive battery status information.

### Attributes

```python
@dataclass
class BatteryStatus:
    battery_pct: float              # Current battery percentage
    voltage: float                  # Battery voltage (V)
    current: float                  # Current draw (A)
    estimated_time_remaining: float # Estimated flight time (seconds)
    rtl_time_required: float        # Time required for RTL (seconds)
    rtl_battery_required: float     # Battery % required for RTL
    should_rtl: bool                # Whether RTL should trigger
    rtl_reason: str                 # Reason for RTL trigger
```

**Example:**

```python
status = monitor.get_battery_status("UAV_1", home_position)

if status:
    print(f"Battery: {status.battery_pct:.1f}%")
    print(f"Voltage: {status.voltage:.2f}V")
    print(f"Current: {status.current:.2f}A")
    print(f"Time remaining: {status.estimated_time_remaining:.0f}s")
    print(f"RTL time: {status.rtl_time_required:.0f}s")
    print(f"RTL battery needed: {status.rtl_battery_required:.1f}%")
    
    if status.should_rtl:
        print(f"⚠️ RTL REQUIRED: {status.rtl_reason}")
```

## PowerSample

Historical power consumption sample (internal use).

### Attributes

```python
@dataclass
class PowerSample:
    timestamp: float                    # Sample timestamp
    battery_pct: float                  # Battery percentage
    position: Tuple[float, float, float] # GPS position (lat, lon, alt)
```

## Battery Monitor Algorithm

### Power Consumption Rate

Calculates average power consumption rate (% per minute):

```
rate = (battery_change / time_elapsed) * 60
```

Averaged over recent samples to smooth variations.

### RTL Requirements

1. **Distance Calculation**: Haversine formula for GPS distance to home
2. **Speed Estimation**: Average speed from recent position changes
3. **RTL Time**: `distance / average_speed`
4. **Safety Buffer**: `rtl_time * safety_margin`
5. **Battery Required**: `power_rate * rtl_time_with_margin`

### Predictive RTL Logic

```
IF battery_pct < critical_threshold:
    TRIGGER RTL (immediate)
ELSE IF battery_pct < rtl_battery_required:
    TRIGGER RTL (predictive)
ELSE:
    CONTINUE MISSION
```

## Complete Usage Example

```python
from droneresearch.safety.battery_monitor import BatteryMonitor
import time

# Initialize monitor
monitor = BatteryMonitor(
    critical_threshold=15.0,  # Trigger at 15%
    safety_margin=1.3,        # 30% safety buffer
    min_samples=10            # Need 10 samples
)

# Start monitoring
monitor.start_monitoring("UAV_1")

# Home position
home = (48.137, 11.575, 0.0)

# Monitoring loop
while mission_active:
    # Get telemetry from drone
    telemetry = get_drone_telemetry("UAV_1")
    
    # Update monitor
    monitor.update("UAV_1", telemetry)
    
    # Check RTL status
    should_rtl, reason = monitor.should_trigger_rtl("UAV_1", home)
    
    if should_rtl:
        print(f"⚠️ Triggering RTL: {reason}")
        drone.rtl()
        break
    
    # Get detailed status
    status = monitor.get_battery_status("UAV_1", home)
    if status:
        print(f"Battery: {status.battery_pct:.1f}% | "
              f"Time left: {status.estimated_time_remaining:.0f}s | "
              f"RTL needs: {status.rtl_battery_required:.1f}%")
    
    time.sleep(1.0)

# Stop monitoring
monitor.stop_monitoring("UAV_1")
```

## Multi-Drone Example

```python
# Monitor multiple drones
monitor = BatteryMonitor()

drone_ids = ["UAV_1", "UAV_2", "UAV_3"]
home_positions = {
    "UAV_1": (48.137, 11.575, 0.0),
    "UAV_2": (48.138, 11.576, 0.0),
    "UAV_3": (48.139, 11.577, 0.0)
}

# Start monitoring all drones
for drone_id in drone_ids:
    monitor.start_monitoring(drone_id)

# Monitoring loop
while any_mission_active:
    for drone_id in drone_ids:
        # Update telemetry
        telemetry = get_drone_telemetry(drone_id)
        monitor.update(drone_id, telemetry)
        
        # Check RTL
        home = home_positions[drone_id]
        should_rtl, reason = monitor.should_trigger_rtl(drone_id, home)
        
        if should_rtl:
            print(f"⚠️ {drone_id} RTL: {reason}")
            trigger_rtl(drone_id)
    
    time.sleep(1.0)
```

## Autopilot Integration

### ArduPilot

```python
from pymavlink import mavutil

# Connect to ArduPilot
conn = mavutil.mavlink_connection('tcp:127.0.0.1:5762')
conn.wait_heartbeat()

monitor = BatteryMonitor()
monitor.start_monitoring("UAV_1")

while True:
    msg = conn.recv_match(type=['BATTERY_STATUS', 'GLOBAL_POSITION_INT'], blocking=True)
    
    if msg.get_type() == 'BATTERY_STATUS':
        battery_pct = msg.battery_remaining
    
    if msg.get_type() == 'GLOBAL_POSITION_INT':
        telemetry = {
            "battery_pct": battery_pct,
            "lat": msg.lat / 1e7,
            "lon": msg.lon / 1e7,
            "alt_rel": msg.relative_alt / 1000.0
        }
        monitor.update("UAV_1", telemetry)
        
        should_rtl, reason = monitor.should_trigger_rtl("UAV_1", home)
        if should_rtl:
            # Send RTL command
            conn.mav.command_long_send(
                conn.target_system,
                conn.target_component,
                mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
                0, 0, 0, 0, 0, 0, 0, 0
            )
            break
```

### PX4

```python
import rclpy
from rclpy.node import Node
from px4_msgs.msg import BatteryStatus, VehicleLocalPosition

class BatteryMonitorNode(Node):
    def __init__(self):
        super().__init__('battery_monitor_node')
        self.monitor = BatteryMonitor()
        self.monitor.start_monitoring("UAV_1")
        
        self.battery_sub = self.create_subscription(
            BatteryStatus, '/fmu/out/battery_status',
            self.battery_callback, 10
        )
        self.position_sub = self.create_subscription(
            VehicleLocalPosition, '/fmu/out/vehicle_local_position',
            self.position_callback, 10
        )
        
        self.battery_pct = 100.0
        self.home = (48.137, 11.575, 0.0)
    
    def battery_callback(self, msg):
        self.battery_pct = msg.remaining * 100
    
    def position_callback(self, msg):
        telemetry = {
            "battery_pct": self.battery_pct,
            "lat": msg.lat,
            "lon": msg.lon,
            "alt_rel": -msg.z  # NED to altitude
        }
        self.monitor.update("UAV_1", telemetry)
        
        should_rtl, reason = self.monitor.should_trigger_rtl("UAV_1", self.home)
        if should_rtl:
            self.get_logger().warn(f'RTL triggered: {reason}')
            # Trigger RTL via PX4 command
```

## Performance Characteristics

- **Memory**: ~1KB per drone (100 samples × ~10 bytes/sample)
- **CPU**: O(n) where n = history size (typically 5-100)
- **Thread-safe**: Uses `threading.Lock` for concurrent access
- **Latency**: <1ms for status checks
- **Scalability**: Tested with 10+ drones simultaneously

## Best Practices

1. **Update Frequency**: Call `update()` every 1-2 seconds for accurate predictions
2. **Minimum Samples**: Wait for at least `min_samples` before relying on predictive RTL
3. **Safety Margin**: Use 1.2-1.5 for safety margin (20-50% buffer)
4. **Critical Threshold**: Set to 15-20% to ensure safe landing after RTL
5. **Home Position**: Update home position if it changes during mission
6. **Reset Trigger**: Call `reset_rtl_trigger()` after successful RTL if continuing mission

## Limitations

- Requires GPS position data (not suitable for indoor flights)
- Assumes relatively constant flight speed
- Does not account for wind conditions
- Distance calculations are straight-line (not obstacle-aware)
- Requires minimum sample count for predictions

## See Also

- [Battery Monitoring Feature Documentation](../features/battery-monitoring.md)
- [APFSafetyFilter](#apfsafetyfilter) - Collision avoidance
- [CollisionPredictor](#collisionpredictor) - Collision prediction

---

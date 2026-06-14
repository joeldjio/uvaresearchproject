# Field Coverage Planning

Automated waypoint generation for efficient field coverage in agricultural UAV operations.

## Overview

The Field Coverage Planning module generates optimized waypoint patterns for covering rectangular or irregular fields. It supports multiple coverage patterns and is designed for agricultural applications like crop monitoring, spraying, or mapping.

## Features

- **Multiple Coverage Patterns**: Parallel lines, spiral, grid, zigzag
- **Configurable Parameters**: Altitude, line spacing, overlap, speed
- **GPS Coordinate Handling**: Automatic conversion between GPS and local NED coordinates
- **Time Estimation**: Calculate mission duration based on coverage area and speed
- **Complex Boundaries**: Support for non-rectangular field shapes

## Coverage Patterns

### Parallel Lines (Default)
Generates parallel lines across the field with alternating direction for efficiency.

```python
from droneresearch.control.field_coverage import (
    FieldCoveragePlanner,
    FieldBoundary,
    CoverageConfig,
    CoveragePattern
)

planner = FieldCoveragePlanner()
planner.set_home_position(47.3977, 8.5456)  # Zurich

# Define field boundary (GPS coordinates)
boundary = FieldBoundary(corners=[
    (47.3977, 8.5456),  # SW corner
    (47.3987, 8.5456),  # NW corner
    (47.3987, 8.5466),  # NE corner
    (47.3977, 8.5466),  # SE corner
])

# Configure coverage
config = CoverageConfig(
    pattern=CoveragePattern.PARALLEL_LINES,
    altitude=20.0,        # meters AGL
    line_spacing=10.0,    # meters between lines
    overlap=0.2,          # 20% overlap
    speed=5.0,            # m/s
    heading=0.0           # 0=North, 90=East
)

# Generate waypoints
waypoints = planner.generate_coverage_waypoints(boundary, config)
# Returns: [(lat, lon, alt), ...]
```

### Spiral Pattern
Spirals from outside to inside, useful for perimeter-first coverage.

```python
config = CoverageConfig(
    pattern=CoveragePattern.SPIRAL,
    altitude=15.0,
    line_spacing=30.0
)
waypoints = planner.generate_coverage_waypoints(boundary, config)
```

### Grid Pattern
Covers field in both horizontal and vertical directions for maximum coverage.

```python
config = CoverageConfig(
    pattern=CoveragePattern.GRID,
    altitude=25.0,
    line_spacing=40.0
)
waypoints = planner.generate_coverage_waypoints(boundary, config)
```

### Zigzag Pattern
Similar to parallel lines but with diagonal connections (no turns at ends).

```python
config = CoverageConfig(
    pattern=CoveragePattern.ZIGZAG,
    altitude=18.0,
    line_spacing=35.0
)
waypoints = planner.generate_coverage_waypoints(boundary, config)
```

## Configuration Parameters

### CoverageConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pattern` | CoveragePattern | PARALLEL_LINES | Coverage pattern type |
| `altitude` | float | 20.0 | Flight altitude in meters AGL |
| `overlap` | float | 0.2 | Overlap between passes (0-1) |
| `line_spacing` | float | 10.0 | Distance between parallel lines (m) |
| `speed` | float | 5.0 | Flight speed in m/s |
| `heading` | float | 0.0 | Pattern orientation (degrees, 0=North) |

### FieldBoundary

Define field boundaries using GPS coordinates:

```python
# Rectangular field
boundary = FieldBoundary(corners=[
    (lat1, lon1),
    (lat2, lon2),
    (lat3, lon3),
    (lat4, lon4),
])

# Complex (non-rectangular) field
boundary = FieldBoundary(corners=[
    (47.3977, 8.5456),
    (47.3987, 8.5450),
    (47.3992, 8.5461),
    (47.3985, 8.5470),
    (47.3975, 8.5465),
])
```

**Requirements:**
- Minimum 3 corners
- Corners should be ordered (clockwise or counter-clockwise)
- GPS coordinates in decimal degrees

## Mission Time Estimation

Calculate estimated mission duration:

```python
waypoints = planner.generate_coverage_waypoints(boundary, config)
time_seconds = planner.estimate_coverage_time(waypoints, speed=5.0)

print(f"Estimated mission time: {time_seconds / 60:.1f} minutes")
```

## Coordinate Conversion

The planner automatically handles GPS ↔ Local NED conversions:

```python
# Set home position (required before generating waypoints)
planner.set_home_position(47.3977, 8.5456)

# Internal conversions happen automatically
# GPS → Local NED → Pattern Generation → GPS
waypoints = planner.generate_coverage_waypoints(boundary, config)
```

## Integration with Mission System

Use with `MissionEngine` for execution:

```python
from droneresearch.control.mission import MissionEngine, Waypoint

# Generate coverage waypoints
coverage_waypoints = planner.generate_coverage_waypoints(boundary, config)

# Convert to mission waypoints
mission_waypoints = [
    Waypoint(lat=lat, lon=lon, alt=alt, speed=config.speed)
    for lat, lon, alt in coverage_waypoints
]

# Upload to drone
mission_engine = MissionEngine(connection)
success = mission_engine.upload(mission_waypoints)
```

## Best Practices

### Line Spacing
- **Crop Monitoring**: 10-20m spacing with 20% overlap
- **Spraying**: 5-10m spacing with 30% overlap
- **Mapping**: 15-30m spacing with 10% overlap

### Altitude Selection
- **Low altitude (10-15m)**: High resolution, slower coverage
- **Medium altitude (20-30m)**: Balanced resolution and speed
- **High altitude (40-50m)**: Fast coverage, lower resolution

### Pattern Selection
- **Parallel Lines**: Most efficient for rectangular fields
- **Spiral**: Good for perimeter inspection first
- **Grid**: Maximum coverage assurance (slower)
- **Zigzag**: Fastest pattern (less precise turns)

### Overlap Considerations
- **10-20%**: Sufficient for most applications
- **30-40%**: High-precision mapping or spraying
- **0%**: Maximum speed (risk of gaps)

## Example: Complete Agricultural Mission

```python
from droneresearch.control.field_coverage import (
    FieldCoveragePlanner,
    FieldBoundary,
    CoverageConfig,
    CoveragePattern
)

# Initialize planner
planner = FieldCoveragePlanner()
planner.set_home_position(47.3977, 8.5456)

# Define 1-hectare field (100m x 100m)
boundary = FieldBoundary(corners=[
    (47.3977, 8.5456),
    (47.3986, 8.5456),
    (47.3986, 8.5470),
    (47.3977, 8.5470),
])

# Configure for crop monitoring
config = CoverageConfig(
    pattern=CoveragePattern.PARALLEL_LINES,
    altitude=25.0,        # 25m AGL
    line_spacing=15.0,    # 15m between lines
    overlap=0.2,          # 20% overlap
    speed=8.0,            # 8 m/s
    heading=0.0           # North-South lines
)

# Generate waypoints
waypoints = planner.generate_coverage_waypoints(boundary, config)

# Estimate mission time
time_seconds = planner.estimate_coverage_time(waypoints, config.speed)
print(f"Mission will take approximately {time_seconds / 60:.1f} minutes")
print(f"Generated {len(waypoints)} waypoints")

# Execute mission (integrate with your drone control system)
# mission_engine.upload(waypoints)
# mission_engine.start()
```

## Limitations

- **Flat Earth Approximation**: Uses simplified GPS conversion (accurate for areas < 10km²)
- **No Obstacle Avoidance**: Generated waypoints don't account for obstacles
- **Fixed Altitude**: All waypoints at same altitude (no terrain following)
- **Simple Boundaries**: Complex concave shapes may have coverage gaps

## Future Enhancements

- Terrain-following altitude adjustment
- Obstacle-aware path planning
- Variable line spacing based on field zones
- Integration with real-time wind compensation
- Support for 3D coverage patterns

## See Also

- [Mission Control API](../api/control.md)
- [Safety Features](../api/safety.md)
- [Swarm Coordination](swarm-coordination.md)
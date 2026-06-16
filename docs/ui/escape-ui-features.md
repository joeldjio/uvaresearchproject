# ESCAPE Framework UI Integration

This document describes the UI integration for the ESCAPE (Enhanced Swarm Coordination and Perception Environment) framework features.

## Overview

The ESCAPE framework provides four key capabilities for autonomous swarm operations:

1. **Perception-Based Collision Avoidance** - Real-time obstacle detection and avoidance
2. **Distributed Task Allocation** - Decentralized task assignment across swarm
3. **Adaptive Safety Margins** - Dynamic safety distance adjustment based on environmental conditions
4. **Distributed Mapping Consensus** - Collaborative 3D environment mapping

All ESCAPE features are integrated into existing UI panels (SafetyPanel and SwarmPanel) rather than requiring a separate panel.

## Architecture

### ESCAPEContext (`tools/ui/context/escape_context.py`)

Qt/QML context providing:

**Properties:**
- `obstacles` - List of detected obstacles (position, velocity, radius)
- `obstacleCount` - Number of active obstacles
- `tasks` - List of announced tasks (ID, position, status, assigned drone)
- `taskCount` - Number of active tasks
- `windSpeed` - Current wind speed (m/s)
- `gpsUncertainty` - GPS position uncertainty (m)
- `droneMargins` - Safety margins for each drone (ID, margin distance)
- `occupiedVoxels` - List of occupied voxels in 3D map (x, y, z, occupancy)
- `voxelCount` - Number of occupied voxels

**Enable/Disable Flags:**
- `perceptionEnabled` - Toggle perception-based collision avoidance
- `taskAllocationEnabled` - Toggle distributed task allocation
- `adaptiveMarginsEnabled` - Toggle adaptive safety margins
- `mappingEnabled` - Toggle distributed mapping consensus

**Signals:**
- `obstaclesChanged()` - Emitted when obstacle list changes
- `tasksChanged()` - Emitted when task list changes
- `marginsChanged()` - Emitted when safety margins change
- `mapChanged()` - Emitted when voxel map changes
- `windSpeedChanged()` - Emitted when wind speed changes
- `gpsUncertaintyChanged()` - Emitted when GPS uncertainty changes
- `logMessage(level, text)` - Emitted for logging (connected to SwarmContext)

**Methods:**
- `initialize()` - Initialize ESCAPE components
- `clearObstacles()` - Remove all obstacles
- `updateObstacles(obstacles)` - Update obstacle list
- `announceTask(taskId, x, y, z)` - Announce new task
- `setWindSpeed(speed)` - Update wind speed
- `setGpsUncertainty(uncertainty)` - Update GPS uncertainty
- `cleanupMap()` - Remove stale voxels from map

## UI Integration

### SafetyPanel Integration

Three ESCAPE sections added to SafetyPanel (`tools/ui/qml/panels/SafetyPanel.qml`):

#### 1. Perception-Based Collision Avoidance (Lines 965-1088)

```qml
GroupBox {
    title: "Perception-Based Collision Avoidance"
    
    ColumnLayout {
        // Enable/disable toggle
        Switch {
            text: "Enable Perception-Based Avoidance"
            checked: escapeCtx.perceptionEnabled
            onCheckedChanged: escapeCtx.perceptionEnabled = checked
        }
        
        // Obstacle list
        ListView {
            model: escapeCtx.obstacles
            delegate: Rectangle {
                // Shows: ID, position, velocity, radius
            }
        }
        
        // Clear all button
        Button {
            text: "Clear All Obstacles"
            onClicked: escapeCtx.clearObstacles()
        }
    }
}
```

**Features:**
- Real-time obstacle list with position, velocity, radius
- Enable/disable toggle with logging
- Clear all obstacles button
- Automatic updates via `obstaclesChanged` signal

#### 2. Adaptive Safety Margins (Lines 1090-1213)

```qml
GroupBox {
    title: "Adaptive Safety Margins"
    
    ColumnLayout {
        // Enable/disable toggle
        Switch {
            text: "Enable Adaptive Margins"
            checked: escapeCtx.adaptiveMarginsEnabled
            onCheckedChanged: escapeCtx.adaptiveMarginsEnabled = checked
        }
        
        // Wind speed slider (0-15 m/s)
        Slider {
            from: 0
            to: 15
            stepSize: 0.5
            value: escapeCtx.windSpeed
            onMoved: escapeCtx.setWindSpeed(value)
        }
        
        // GPS uncertainty slider (0-5 m)
        Slider {
            from: 0
            to: 5
            stepSize: 0.1
            Component.onCompleted: value = escapeCtx.gpsUncertainty
            onMoved: escapeCtx.setGpsUncertainty(value)
        }
        
        // Drone margins list
        ListView {
            model: escapeCtx.droneMargins
            delegate: Rectangle {
                // Shows: Drone ID, margin distance
            }
        }
    }
}
```

**Features:**
- Wind speed adjustment (0-15 m/s, 0.5 m/s steps)
- GPS uncertainty adjustment (0-5 m, 0.1 m steps)
- Real-time margin calculation per drone
- Enable/disable toggle with logging

#### 3. Distributed Mapping Consensus (Lines 1215-1364)

```qml
GroupBox {
    title: "Distributed Mapping Consensus"
    
    ColumnLayout {
        // Enable/disable toggle
        Switch {
            text: "Enable Distributed Mapping"
            checked: escapeCtx.mappingEnabled
            onCheckedChanged: escapeCtx.mappingEnabled = checked
        }
        
        // Voxel statistics
        Label {
            text: "Occupied Voxels: " + escapeCtx.voxelCount
        }
        
        // Voxel list
        ListView {
            model: escapeCtx.occupiedVoxels
            delegate: Rectangle {
                // Shows: Position (x,y,z), occupancy probability
            }
        }
        
        // Cleanup button
        Button {
            text: "Cleanup Map"
            onClicked: escapeCtx.cleanupMap()
        }
    }
}
```

**Features:**
- Voxel count display
- Voxel list with position and occupancy
- Cleanup stale voxels button
- Enable/disable toggle with logging

### SwarmPanel Integration

#### Distributed Task Allocation (Lines 1022-1329)

```qml
GroupBox {
    title: "Distributed Task Allocation"
    
    ColumnLayout {
        // Enable/disable toggle
        Switch {
            text: "Enable Task Allocation"
            checked: escapeCtx.taskAllocationEnabled
            onCheckedChanged: escapeCtx.taskAllocationEnabled = checked
        }
        
        // Task announcement form
        GroupBox {
            title: "Announce New Task"
            
            GridLayout {
                columns: 2
                
                Label { text: "Task ID:" }
                TextField { id: taskIdField }
                
                Label { text: "Position X (m):" }
                TextField { id: posXField }
                
                Label { text: "Position Y (m):" }
                TextField { id: posYField }
                
                Label { text: "Position Z (m):" }
                TextField { id: posZField }
                
                Button {
                    text: "Announce Task"
                    onClicked: {
                        escapeCtx.announceTask(
                            taskIdField.text,
                            parseFloat(posXField.text),
                            parseFloat(posYField.text),
                            parseFloat(posZField.text)
                        )
                    }
                }
            }
        }
        
        // Task status list
        ListView {
            model: escapeCtx.tasks
            delegate: Rectangle {
                // Shows: Task ID, position, status, assigned drone
            }
        }
    }
}
```

**Features:**
- Task announcement form (ID + 3D position)
- Task status list with assignment info
- Enable/disable toggle with logging
- Real-time updates via `tasksChanged` signal

### MapView Integration

3D visualization overlays added to MapView (`tools/ui/qml/MapView.qml`):

#### Obstacle Visualization (Lines 176-218)

```qml
Repeater {
    model: escapeCtx.obstacles
    
    delegate: Entity {
        components: [
            SphereMesh { radius: modelData.radius },
            PhongMaterial { diffuse: "red", ambient: "darkred" },
            Transform {
                translation: Qt.vector3d(
                    modelData.position.x,
                    modelData.position.y,
                    modelData.position.z
                )
            }
        ]
        
        // Tooltip on hover
        ToolTip.text: "Obstacle " + modelData.id + 
                      "\nPos: " + modelData.position.x.toFixed(1) + ", " +
                      modelData.position.y.toFixed(1) + ", " +
                      modelData.position.z.toFixed(1) +
                      "\nRadius: " + modelData.radius.toFixed(1) + "m"
    }
}
```

**Features:**
- Red spheres for obstacles
- Size matches obstacle radius
- Tooltip shows ID, position, radius
- Real-time updates

#### Voxel Visualization (Lines 221-268)

```qml
Repeater {
    model: escapeCtx.occupiedVoxels
    
    delegate: Entity {
        components: [
            CuboidMesh { 
                xExtent: 0.5
                yExtent: 0.5
                zExtent: 0.5
            },
            PhongMaterial { 
                diffuse: Qt.rgba(1, 0, 0, modelData.occupancy)
                ambient: "darkred"
            },
            Transform {
                translation: Qt.vector3d(
                    modelData.x,
                    modelData.y,
                    modelData.z
                )
            }
        ]
        
        // Tooltip on hover
        ToolTip.text: "Voxel\nPos: " + 
                      modelData.x.toFixed(1) + ", " +
                      modelData.y.toFixed(1) + ", " +
                      modelData.z.toFixed(1) +
                      "\nOccupancy: " + (modelData.occupancy * 100).toFixed(0) + "%"
    }
}
```

**Features:**
- Red cubes for occupied voxels (0.5m size)
- Transparency based on occupancy probability
- Tooltip shows position and occupancy
- Real-time updates

## Service Locator Integration

ESCAPEContext registered in `tools/ui/service_locator.py`:

```python
def _escape() -> "ESCAPEContext":
    """Create ESCAPE context."""
    from tools.ui.context.escape_context import ESCAPEContext
    return ESCAPEContext()

# Register contexts
locator.register("escape", _escape)

# Wire logging
escape = locator["escape"]
escape.logMessage.connect(swarm.logMessage)
```

**Logging Integration:**
- All ESCAPE log messages routed to SwarmContext
- Appear in Safety Log with `[ESCAPE]` prefix
- Log levels: INFO, WARN, ERROR
- Logged events:
  - Feature enable/disable
  - Obstacle updates
  - Task announcements
  - Wind speed changes
  - GPS uncertainty changes
  - Map cleanup operations

## Coordinate Systems

### Local NED Frame
- **Obstacles**: Position in local NED meters (North, East, Down)
- **Tasks**: Position in local NED meters
- **Drone Positions**: Local NED meters

### Voxel Grid
- **Voxels**: Discrete 3D grid cells (typically 0.5m resolution)
- **Coordinates**: Grid indices (x, y, z)
- **Occupancy**: Probability 0.0-1.0

## Usage Examples

### Example 1: Enable Perception-Based Avoidance

1. Navigate to Safety Panel
2. Scroll to "Perception-Based Collision Avoidance" section
3. Toggle "Enable Perception-Based Avoidance" switch
4. Check Safety Log for confirmation: `[ESCAPE] Perception-based collision avoidance enabled`
5. Obstacles will appear in list and on 3D map as red spheres

### Example 2: Announce Task

1. Navigate to Swarm Panel
2. Scroll to "Distributed Task Allocation" section
3. Toggle "Enable Task Allocation" switch
4. Fill in task form:
   - Task ID: "SURVEY_AREA_1"
   - Position X: 50.0
   - Position Y: 30.0
   - Position Z: -10.0
5. Click "Announce Task"
6. Check Safety Log: `[ESCAPE] Task announced: SURVEY_AREA_1 at (50.0, 30.0, -10.0)`
7. Task appears in status list with assignment info

### Example 3: Adjust Safety Margins

1. Navigate to Safety Panel
2. Scroll to "Adaptive Safety Margins" section
3. Toggle "Enable Adaptive Margins" switch
4. Adjust wind speed slider (e.g., 8.5 m/s)
5. Check Safety Log: `[ESCAPE] Wind speed updated: 8.5 m/s`
6. Adjust GPS uncertainty slider (e.g., 2.3 m)
7. Check Safety Log: `[ESCAPE] GPS uncertainty updated: 2.3 m`
8. Observe updated margins in drone list

### Example 4: View 3D Map

1. Navigate to Map View
2. Enable "Distributed Mapping Consensus" in Safety Panel
3. Red cubes appear for occupied voxels
4. Hover over cube to see tooltip with position and occupancy
5. Use "Cleanup Map" button to remove stale voxels
6. Check Safety Log: `[ESCAPE] Cleaned up N stale voxel(s)`

## Testing

### Manual Testing Checklist

- [ ] UI starts without errors
- [ ] All four ESCAPE sections visible in correct panels
- [ ] Enable/disable toggles work and log messages appear
- [ ] Obstacle list updates and displays correctly
- [ ] Task announcement form works and logs correctly
- [ ] Wind speed slider updates margins
- [ ] GPS uncertainty slider updates margins
- [ ] Voxel list displays correctly
- [ ] 3D obstacles render as red spheres
- [ ] 3D voxels render as red cubes
- [ ] Tooltips show correct information
- [ ] Clear/cleanup buttons work
- [ ] All log messages appear in Safety Log with `[ESCAPE]` prefix

### Automated Testing

Currently no automated UI tests for ESCAPE features. Future work:
- Add QML test cases for ESCAPEContext
- Add integration tests for panel interactions
- Add visual regression tests for 3D rendering

## Future Enhancements

### Sensor Configuration UI
- Add sensor configuration to GimbalPanel
- Support depth camera and LiDAR settings
- Configure detection ranges and FOV

### Advanced Visualization
- Color-code obstacles by threat level
- Show velocity vectors for moving obstacles
- Animate task assignment process
- Show communication links between drones

### Performance Monitoring
- Add ESCAPE performance metrics panel
- Track obstacle detection latency
- Monitor task allocation efficiency
- Display map consensus convergence

## Related Documentation

- [ESCAPE Framework Overview](../features/escape-framework.md)
- [Perception-Based Collision Avoidance](../features/perception-collision-avoidance.md)
- [Distributed Task Allocation](../features/distributed-task-allocation.md)
- [Adaptive Safety Margins](../features/adaptive-safety-margins.md)
- [Distributed Mapping Consensus](../features/distributed-mapping-consensus.md)
- [UI Documentation](ui-documentation.md)
- [Safety Panel](../api/safety.md)
- [Swarm Panel](../api/swarm.md)

## Troubleshooting

### Issue: ESCAPE sections not visible
**Solution:** Check that ESCAPEContext is registered in service_locator.py and imported correctly.

### Issue: No log messages appearing
**Solution:** Verify that `escape.logMessage.connect(swarm.logMessage)` is called in service_locator.py.

### Issue: 3D objects not rendering
**Solution:** Check that Qt3D is properly initialized and MapView has correct camera setup.

### Issue: Sliders not updating values
**Solution:** Ensure slider `onMoved` handlers call ESCAPEContext methods, not direct property assignment.

### Issue: Type checker errors on properties
**Solution:** These are known PyQt6/basedpyright compatibility issues. Functionality is correct despite warnings.
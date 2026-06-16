# ESCAPE Framework UI Integration Guide

**Version:** 0.4.0
**Target Panels:** SafetyPanel, SwarmPanel
**Language:** English

## Overview

This guide describes how to integrate ESCAPE framework features into existing UI panels without creating a separate ESCAPE panel. Features are distributed across relevant panels based on their functionality.

**Integration Points:**
- **SafetyPanel:** Perception-Based Avoidance + Adaptive Safety Margins + Distributed Mapping
- **SwarmPanel:** Distributed Task Allocation
- **MapView:** 3D Visualization (obstacles + occupancy map)

---

## 1. SafetyPanel Integration

**File:** `tools/ui/qml/panels/SafetyPanel.qml`

### 1.1 Perception-Based Collision Avoidance

**Location:** Add new section after existing APF controls

```qml
// ── PERCEPTION-BASED AVOIDANCE ────────────────────────────────
Rectangle {
    width: parent.width
    height: perceptionColumn.height + 24
    color: "#1e293b"
    radius: 8
    border.color: "#334155"
    border.width: 1

    Column {
        id: perceptionColumn
        width: parent.width - 24
        anchors.centerIn: parent
        spacing: 12

        // Header
        Row {
            width: parent.width
            spacing: 8

            Rectangle {
                width: 4
                height: 20
                color: "#8b5cf6"
                radius: 2
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "PERCEPTION-BASED AVOIDANCE"
                color: "#8b5cf6"
                font.pixelSize: 12
                font.weight: Font.Bold
                font.letterSpacing: 1
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Text {
            text: "Uses depth sensors to detect obstacles in 3D space"
            color: "#64748b"
            font.pixelSize: 9
            font.italic: true
            wrapMode: Text.WordWrap
            width: parent.width
        }

        Rectangle { width: parent.width; height: 1; color: "#2d3748" }

        // Obstacle Statistics
        Grid {
            width: parent.width
            columns: 3
            columnSpacing: 12
            rowSpacing: 6

            Column {
                spacing: 2
                Text {
                    text: "Detected Obstacles"
                    color: "#64748b"
                    font.pixelSize: 8
                }
                Text {
                    text: safetyContext ? safetyContext.obstacleCount : "0"
                    color: safetyContext && safetyContext.obstacleCount > 0 ? "#ef4444" : "#22c55e"
                    font.pixelSize: 14
                    font.weight: Font.Bold
                    font.family: "Consolas"
                }
            }

            Column {
                spacing: 2
                Text {
                    text: "Perception Radius"
                    color: "#64748b"
                    font.pixelSize: 8
                }
                Text {
                    text: "10.0 m"
                    color: "#e2e8f0"
                    font.pixelSize: 14
                    font.weight: Font.Bold
                    font.family: "Consolas"
                }
            }

            Column {
                spacing: 2
                Text {
                    text: "Voxel Resolution"
                    color: "#64748b"
                    font.pixelSize: 8
                }
                Text {
                    text: "0.5 m"
                    color: "#e2e8f0"
                    font.pixelSize: 14
                    font.weight: Font.Bold
                    font.family: "Consolas"
                }
            }
        }

        // Clear obstacles button
        Rectangle {
            width: parent.width
            height: 32
            radius: 6
            color: clearObstaclesM.containsMouse ? "#991b1b" : "#7f1d1d"
            border.color: "#ef4444"
            border.width: 1
            opacity: safetyContext && safetyContext.obstacleCount > 0 ? 1 : 0.4

            Row {
                anchors.centerIn: parent
                spacing: 6

                Icon {
                    name: "x"
                    size: 12
                    color: "#fecaca"
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: "CLEAR OBSTACLES"
                    color: "#fecaca"
                    font.pixelSize: 9
                    font.weight: Font.Bold
                    font.letterSpacing: 0.5
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            MouseArea {
                id: clearObstaclesM
                anchors.fill: parent
                hoverEnabled: true
                enabled: safetyContext && safetyContext.obstacleCount > 0
                onClicked: {
                    if (safetyContext) {
                        safetyContext.clearObstacles()
                    }
                }
            }
        }

        Text {
            text: "Note: Obstacles auto-expire after 5 seconds of no detection"
            color: "#64748b"
            font.pixelSize: 8
            font.italic: true
            wrapMode: Text.WordWrap
            width: parent.width
        }
    }
}
```

### 1.2 Adaptive Safety Margins

**Location:** Add new section after APF parameters

```qml
// ── ADAPTIVE SAFETY MARGINS ───────────────────────────────────
Rectangle {
    width: parent.width
    height: adaptiveColumn.height + 24
    color: "#1e293b"
    radius: 8
    border.color: "#334155"
    border.width: 1

    Column {
        id: adaptiveColumn
        width: parent.width - 24
        anchors.centerIn: parent
        spacing: 12

        // Header
        Row {
            width: parent.width
            spacing: 8

            Rectangle {
                width: 4
                height: 20
                color: "#f59e0b"
                radius: 2
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "ADAPTIVE SAFETY MARGINS"
                color: "#f59e0b"
                font.pixelSize: 12
                font.weight: Font.Bold
                font.letterSpacing: 1
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Text {
            text: "Dynamically adjusts separation based on velocity, GPS accuracy, and wind"
            color: "#64748b"
            font.pixelSize: 9
            font.italic: true
            wrapMode: Text.WordWrap
            width: parent.width
        }

        Rectangle { width: parent.width; height: 1; color: "#2d3748" }

        // Wind Speed Control
        Column {
            width: parent.width
            spacing: 6

            Row {
                width: parent.width
                spacing: 8

                Text {
                    text: "Wind Speed"
                    color: "#94a3b8"
                    font.pixelSize: 10
                    font.weight: Font.Bold
                    width: 120
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: safetyContext ? safetyContext.windSpeed.toFixed(1) + " m/s" : "0.0 m/s"
                    color: "#3b82f6"
                    font.pixelSize: 12
                    font.weight: Font.Bold
                    font.family: "Consolas"
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Slider {
                width: parent.width
                from: 0
                to: 10
                stepSize: 0.5
                value: safetyContext ? safetyContext.windSpeed : 0
                onMoved: {
                    if (safetyContext) {
                        safetyContext.setWindSpeed(value)
                    }
                }
            }

            Text {
                text: {
                    var v = safetyContext ? safetyContext.windSpeed : 0;
                    if (v < 3) return "Calm conditions - minimal margin increase";
                    if (v < 6) return "Moderate wind - standard margin adjustment";
                    return "Strong wind - increased safety margins";
                }
                color: "#64748b"
                font.pixelSize: 8
                font.italic: true
                wrapMode: Text.WordWrap
                width: parent.width
            }
        }

        Rectangle { width: parent.width; height: 1; color: "#2d3748" }

        // GPS Uncertainty Control
        Column {
            width: parent.width
            spacing: 6

            Row {
                width: parent.width
                spacing: 8

                Text {
                    text: "GPS Uncertainty"
                    color: "#94a3b8"
                    font.pixelSize: 10
                    font.weight: Font.Bold
                    width: 120
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: safetyContext ? safetyContext.gpsUncertainty.toFixed(2) + " m" : "0.30 m"
                    color: "#3b82f6"
                    font.pixelSize: 12
                    font.weight: Font.Bold
                    font.family: "Consolas"
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Slider {
                width: parent.width
                from: 0
                to: 1.0
                stepSize: 0.05
                value: safetyContext ? safetyContext.gpsUncertainty : 0.3
                onMoved: {
                    if (safetyContext) {
                        safetyContext.setGpsUncertainty(value)
                    }
                }
            }

            Text {
                text: {
                    var v = safetyContext ? safetyContext.gpsUncertainty : 0.3;
                    if (v < 0.2) return "High GPS accuracy - tight formations possible";
                    if (v < 0.5) return "Normal GPS accuracy - standard margins";
                    return "Poor GPS accuracy - increased safety buffer (2-sigma)";
                }
                color: "#64748b"
                font.pixelSize: 8
                font.italic: true
                wrapMode: Text.WordWrap
                width: parent.width
            }
        }

        Rectangle { width: parent.width; height: 1; color: "#2d3748" }

        // Current Margins Display
        Column {
            width: parent.width
            spacing: 6

            Text {
                text: "Current Safety Margins"
                color: "#94a3b8"
                font.pixelSize: 10
                font.weight: Font.Bold
            }

            Rectangle {
                width: parent.width
                height: 120
                color: "#0f172a"
                border.color: "#334155"
                border.width: 1
                radius: 4

                ListView {
                    id: marginsListView
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true
                    spacing: 4

                    model: safetyContext ? safetyContext.droneMargins : []

                    delegate: Row {
                        width: marginsListView.width
                        spacing: 10

                        Text {
                            text: modelData.pair
                            color: "#e2e8f0"
                            font.pixelSize: 10
                            font.family: "Consolas"
                            width: 80
                        }

                        Text {
                            text: modelData.margin.toFixed(2) + " m"
                            color: modelData.safe ? "#22c55e" : "#ef4444"
                            font.pixelSize: 10
                            font.weight: Font.Bold
                            font.family: "Consolas"
                            width: 60
                        }

                        Rectangle {
                            width: 50
                            height: 18
                            color: modelData.safe ? "#22c55e" : "#ef4444"
                            radius: 3

                            Text {
                                anchors.centerIn: parent
                                text: modelData.safe ? "SAFE" : "WARN"
                                color: "#000000"
                                font.pixelSize: 8
                                font.weight: Font.Bold
                            }
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        text: "No drone pairs detected"
                        visible: marginsListView.count === 0
                        color: "#64748b"
                        font.pixelSize: 9
                        font.italic: true
                    }
                }
            }

            Text {
                text: "Margins adapt based on relative velocity, GPS accuracy, and wind conditions"
                color: "#64748b"
                font.pixelSize: 8
                font.italic: true
                wrapMode: Text.WordWrap
                width: parent.width
            }
        }
    }
}
```

---

## 2. SwarmPanel Integration

**File:** `tools/ui/qml/panels/SwarmPanel.qml`

### 2.1 Distributed Task Allocation

**Location:** Add new section after formation controls

```qml
// ── DISTRIBUTED TASK ALLOCATION ───────────────────────────────
Rectangle {
    width: parent.width
    height: taskColumn.height + 24
    color: "#1e293b"
    radius: 8
    border.color: "#334155"
    border.width: 1

    Column {
        id: taskColumn
        width: parent.width - 24
        anchors.centerIn: parent
        spacing: 12

        // Header
        Row {
            width: parent.width
            spacing: 8

            Rectangle {
                width: 4
                height: 20
                color: "#06b6d4"
                radius: 2
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "DISTRIBUTED TASK ALLOCATION"
                color: "#06b6d4"
                font.pixelSize: 12
                font.weight: Font.Bold
                font.letterSpacing: 1
                anchors.verticalCenter: parent.verticalCenter
            }

            Item { width: parent.width - 300; height: 1 }

            Text {
                text: swarmContext ? swarmContext.taskCount + " TASKS" : "0 TASKS"
                color: "#64748b"
                font.pixelSize: 9
                font.weight: Font.Bold
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Text {
            text: "Auction-based task assignment without central coordinator (UDP broadcast)"
            color: "#64748b"
            font.pixelSize: 9
            font.italic: true
            wrapMode: Text.WordWrap
            width: parent.width
        }

        Rectangle { width: parent.width; height: 1; color: "#2d3748" }

        // Task List
        Rectangle {
            width: parent.width
            height: 200
            color: "#0f172a"
            border.color: "#334155"
            border.width: 1
            radius: 4

            ListView {
                id: taskListView
                anchors.fill: parent
                anchors.margins: 8
                clip: true
                spacing: 6

                model: swarmContext ? swarmContext.tasks : []

                delegate: Rectangle {
                    width: taskListView.width
                    height: 60
                    color: "#1e293b"
                    border.color: "#334155"
                    border.width: 1
                    radius: 4

                    Column {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 4

                        Row {
                            width: parent.width
                            spacing: 10

                            Text {
                                text: modelData.task_id
                                color: "#e2e8f0"
                                font.pixelSize: 10
                                font.weight: Font.Bold
                                font.family: "Consolas"
                                width: 80
                            }

                            Text {
                                text: modelData.task_type.toUpperCase()
                                color: "#94a3b8"
                                font.pixelSize: 9
                                width: 80
                            }

                            Rectangle {
                                width: 80
                                height: 20
                                color: modelData.assigned_to ? "#22c55e" : "#f59e0b"
                                radius: 3

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.assigned_to || "BIDDING"
                                    color: "#000000"
                                    font.pixelSize: 8
                                    font.weight: Font.Bold
                                }
                            }
                        }

                        Row {
                            width: parent.width
                            spacing: 10

                            Text {
                                text: "Priority: " + modelData.priority.toFixed(2)
                                color: "#64748b"
                                font.pixelSize: 8
                            }

                            Text {
                                text: "Pos: (" + modelData.position[0].toFixed(1) + ", " + 
                                      modelData.position[1].toFixed(1) + ", " + 
                                      modelData.position[2].toFixed(1) + ")"
                                color: "#64748b"
                                font.pixelSize: 8
                                font.family: "Consolas"
                            }
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    text: "No active tasks"
                    visible: taskListView.count === 0
                    color: "#64748b"
                    font.pixelSize: 9
                    font.italic: true
                }
            }
        }

        Rectangle { width: parent.width; height: 1; color: "#2d3748" }

        // Announce Task Controls
        Column {
            width: parent.width
            spacing: 8

            Text {
                text: "Announce New Task"
                color: "#94a3b8"
                font.pixelSize: 10
                font.weight: Font.Bold
            }

            Grid {
                width: parent.width
                columns: 2
                columnSpacing: 12
                rowSpacing: 8

                Text {
                    text: "Task Type:"
                    color: "#64748b"
                    font.pixelSize: 9
                    anchors.verticalCenter: parent.verticalCenter
                }

                ComboBox {
                    id: taskTypeCombo
                    model: ["survey", "patrol", "inspect", "transport", "search"]
                    width: 150
                }

                Text {
                    text: "Position X:"
                    color: "#64748b"
                    font.pixelSize: 9
                }

                SpinBox {
                    id: taskXSpin
                    from: -50
                    to: 50
                    value: 10
                    width: 150
                }

                Text {
                    text: "Position Y:"
                    color: "#64748b"
                    font.pixelSize: 9
                }

                SpinBox {
                    id: taskYSpin
                    from: -50
                    to: 50
                    value: 20
                    width: 150
                }

                Text {
                    text: "Position Z:"
                    color: "#64748b"
                    font.pixelSize: 9
                }

                SpinBox {
                    id: taskZSpin
                    from: 0
                    to: 30
                    value: 15
                    width: 150
                }

                Text {
                    text: "Priority:"
                    color: "#64748b"
                    font.pixelSize: 9
                }

                Slider {
                    id: taskPrioritySlider
                    from: 0.0
                    to: 1.0
                    value: 0.5
                    stepSize: 0.1
                    width: 150
                }
            }

            Rectangle {
                width: parent.width
                height: 36
                radius: 6
                color: announceM.containsMouse ? "#0e7490" : "#0891b2"
                border.color: "#06b6d4"
                border.width: 1

                Row {
                    anchors.centerIn: parent
                    spacing: 6

                    Icon {
                        name: "send"
                        size: 14
                        color: "#cffafe"
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        text: "ANNOUNCE TASK"
                        color: "#cffafe"
                        font.pixelSize: 10
                        font.weight: Font.Bold
                        font.letterSpacing: 0.5
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                MouseArea {
                    id: announceM
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        if (swarmContext) {
                            swarmContext.announceTask(
                                taskTypeCombo.currentText,
                                taskXSpin.value,
                                taskYSpin.value,
                                taskZSpin.value,
                                taskPrioritySlider.value
                            )
                        }
                    }
                }
            }

            Text {
                text: "Tasks are automatically assigned via auction (lowest cost wins)"
                color: "#64748b"
                font.pixelSize: 8
                font.italic: true
                wrapMode: Text.WordWrap
                width: parent.width
            }
        }
    }
}
```

---

## 3. SafetyPanel Integration (continued)

### 1.3 Distributed Mapping Consensus

**Location:** Add new section after Adaptive Safety Margins in SafetyPanel

```qml
// ── DISTRIBUTED MAPPING ───────────────────────────────────────
Rectangle {
    width: parent.width
    height: mappingColumn.height + 24
    color: "#1e293b"
    radius: 8
    border.color: "#334155"
    border.width: 1

    Column {
        id: mappingColumn
        width: parent.width - 24
        anchors.centerIn: parent
        spacing: 12

        // Header
        Row {
            width: parent.width
            spacing: 8

            Rectangle {
                width: 4
                height: 20
                color: "#ec4899"
                radius: 2
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "DISTRIBUTED MAPPING"
                color: "#ec4899"
                font.pixelSize: 12
                font.weight: Font.Bold
                font.letterSpacing: 1
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Text {
            text: "Collaborative 3D occupancy mapping with consensus-based merging"
            color: "#64748b"
            font.pixelSize: 9
            font.italic: true
            wrapMode: Text.WordWrap
            width: parent.width
        }

        Rectangle { width: parent.width; height: 1; color: "#2d3748" }

        // Map Statistics
        Grid {
            width: parent.width
            columns: 3
            columnSpacing: 12
            rowSpacing: 6

            Column {
                spacing: 2
                Text {
                    text: "Voxels"
                    color: "#64748b"
                    font.pixelSize: 8
                }
                Text {
                    text: mappingContext ? mappingContext.voxelCount : "0"
                    color: "#e2e8f0"
                    font.pixelSize: 14
                    font.weight: Font.Bold
                    font.family: "Consolas"
                }
            }

            Column {
                spacing: 2
                Text {
                    text: "Map Merges"
                    color: "#64748b"
                    font.pixelSize: 8
                }
                Text {
                    text: mappingContext ? mappingContext.mergeCount : "0"
                    color: "#e2e8f0"
                    font.pixelSize: 14
                    font.weight: Font.Bold
                    font.family: "Consolas"
                }
            }

            Column {
                spacing: 2
                Text {
                    text: "Consensus Ops"
                    color: "#64748b"
                    font.pixelSize: 8
                }
                Text {
                    text: mappingContext ? mappingContext.consensusCount : "0"
                    color: "#e2e8f0"
                    font.pixelSize: 14
                    font.weight: Font.Bold
                    font.family: "Consolas"
                }
            }
        }

        Rectangle { width: parent.width; height: 1; color: "#2d3748" }

        // Map Configuration
        Column {
            width: parent.width
            spacing: 6

            Text {
                text: "Map Configuration"
                color: "#94a3b8"
                font.pixelSize: 10
                font.weight: Font.Bold
            }

            Grid {
                width: parent.width
                columns: 2
                columnSpacing: 12
                rowSpacing: 4

                Text {
                    text: "Voxel Size:"
                    color: "#64748b"
                    font.pixelSize: 9
                }
                Text {
                    text: "0.5 m"
                    color: "#e2e8f0"
                    font.pixelSize: 9
                    font.family: "Consolas"
                }

                Text {
                    text: "Decay Rate:"
                    color: "#64748b"
                    font.pixelSize: 9
                }
                Text {
                    text: "0.1 /s"
                    color: "#e2e8f0"
                    font.pixelSize: 9
                    font.family: "Consolas"
                }

                Text {
                    text: "Max Age:"
                    color: "#64748b"
                    font.pixelSize: 9
                }
                Text {
                    text: "30 s"
                    color: "#e2e8f0"
                    font.pixelSize: 9
                    font.family: "Consolas"
                }

                Text {
                    text: "Min Confidence:"
                    color: "#64748b"
                    font.pixelSize: 9
                }
                Text {
                    text: "0.3"
                    color: "#e2e8f0"
                    font.pixelSize: 9
                    font.family: "Consolas"
                }
            }
        }

        Rectangle { width: parent.width; height: 1; color: "#2d3748" }

        // Map Actions
        Row {
            width: parent.width
            spacing: 6

            Rectangle {
                width: (parent.width - 6) / 2
                height: 32
                radius: 6
                color: cleanupM.containsMouse ? "#713f12" : "#78350f"
                border.color: "#f59e0b"
                border.width: 1

                Row {
                    anchors.centerIn: parent
                    spacing: 6

                    Icon {
                        name: "trash-2"
                        size: 12
                        color: "#fde68a"
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        text: "CLEANUP"
                        color: "#fde68a"
                        font.pixelSize: 9
                        font.weight: Font.Bold
                        font.letterSpacing: 0.5
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                MouseArea {
                    id: cleanupM
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        if (mappingContext) {
                            mappingContext.cleanupMap()
                        }
                    }
                }
            }

            Rectangle {
                width: (parent.width - 6) / 2
                height: 32
                radius: 6
                color: clearMapM.containsMouse ? "#991b1b" : "#7f1d1d"
                border.color: "#ef4444"
                border.width: 1

                Row {
                    anchors.centerIn: parent
                    spacing: 6

                    Icon {
                        name: "x-circle"
                        size: 12
                        color: "#fecaca"
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        text: "CLEAR MAP"
                        color: "#fecaca"
                        font.pixelSize: 9
                        font.weight: Font.Bold
                        font.letterSpacing: 0.5
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                MouseArea {
                    id: clearMapM
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        if (mappingContext) {
                            mappingContext.clearMap()
                        }
                    }
                }
            }
        }

        Text {
            text: "Map visualization available in 3D view (occupied voxels shown as red cubes)"
            color: "#64748b"
            font.pixelSize: 8
            font.italic: true
            wrapMode: Text.WordWrap
            width: parent.width
        }

        Text {
            text: "Consensus merging: confidence-weighted averaging when multiple drones observe same voxel"
            color: "#64748b"
            font.pixelSize: 8
            font.italic: true
            wrapMode: Text.WordWrap
            width: parent.width
        }
    }
}
```

---

## 3. Context Integration

### 4.1 Update `tools/ui/context/__init__.py`

```python
from tools.ui.context.escape_context import ESCAPEContext

__all__ = [
    # ... existing exports ...
    "ESCAPEContext",
]
```

### 4.2 Update `tools/ui/app.py` or `main_window.py`

```python
from tools.ui.context.escape_context import ESCAPEContext

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # ... existing context initialization ...
        
        # Initialize ESCAPE context
        self.escape_context = ESCAPEContext(self)
        self.escape_context.initialize("D1")  # or dynamic drone ID
        
        # Expose to QML
        self.engine.rootContext().setContextProperty("escapeContext", self.escape_context)
```

---

## 4. 3D Visualization (MapView.qml)

### 5.1 Obstacle Visualization

Add to `MapView.qml` 3D scene:

```qml
// Perception obstacles
Repeater {
    model: safetyContext ? safetyContext.obstacles : []
    
    delegate: Model {
        source: "#Sphere"
        position: Qt.vector3d(modelData.x, modelData.y, modelData.z)
        scale: Qt.vector3d(0.5, 0.5, 0.5)
        
        materials: PrincipledMaterial {
            baseColor: "#ef4444"
            opacity: 0.6
            alphaMode: PrincipledMaterial.Blend
        }
    }
}
```

### 5.2 Occupancy Map Visualization

```qml
// Distributed map voxels
Repeater {
    model: mappingContext ? mappingContext.occupiedVoxels : []
    
    delegate: Model {
        source: "#Cube"
        position: Qt.vector3d(modelData.x, modelData.y, modelData.z)
        scale: Qt.vector3d(0.5, 0.5, 0.5)
        
        materials: PrincipledMaterial {
            baseColor: Qt.rgba(1, 0, 0, modelData.confidence)
            opacity: modelData.confidence
            alphaMode: PrincipledMaterial.Blend
        }
    }
}
```

---

## 5. Testing

### 5.1 Manual Testing Checklist

**Perception:**
- [ ] Obstacles appear when point cloud data received
- [ ] Obstacle count updates in SafetyPanel
- [ ] Clear button removes all obstacles
- [ ] Obstacles auto-expire after 5 seconds

**Adaptive Safety:**
- [ ] Wind speed slider updates margins
- [ ] GPS uncertainty slider updates margins
- [ ] Margin list shows all drone pairs
- [ ] Warning indicators appear when margin < 3m

**Task Allocation:**
- [ ] Tasks can be announced via SwarmPanel
- [ ] Task list updates with bidding status
- [ ] Tasks show assigned drone after auction
- [ ] Complete button removes task

**Distributed Mapping:**
- [ ] Voxel count increases with observations
- [ ] Merge count increases when maps shared
- [ ] Cleanup removes old voxels
- [ ] Clear button empties map

### 5.2 Integration Test

```python
# tests/test_escape_ui_integration.py
def test_escape_context_initialization():
    """Test ESCAPE context can be initialized."""
    context = ESCAPEContext()
    context.initialize("D1")
    assert context.available == True  # if dependencies installed

def test_adaptive_margins_update():
    """Test adaptive margins respond to wind/GPS changes."""
    context = ESCAPEContext()
    context.initialize("D1")
    
    context.setWindSpeed(5.0)
    assert context.windSpeed == 5.0
    
    context.setGpsUncertainty(0.5)
    assert context.gpsUncertainty == 0.5
```

---

## 6. Documentation Updates

### 6.1 User Guide

Add section to `docs/ui/ui-documentation.md`:

```markdown
## ESCAPE Framework Features

### Perception-Based Avoidance (SafetyPanel)
- Real-time obstacle detection from depth sensors
- 3D voxel grid with 0.5m resolution
- Automatic obstacle expiration (5s timeout)

### Adaptive Safety Margins (SafetyPanel)
- Dynamic separation based on:
  - Wind speed (0-10 m/s)
  - GPS uncertainty (0-1.0 m)
  - Relative velocity between drones
- Real-time margin display for all drone pairs

### Distributed Task Allocation (SwarmPanel)
- Auction-based task assignment
- No central coordinator required
- UDP broadcast communication
- Cost function: distance + battery + workload + risk

### Distributed Mapping (ExperimentPanel)
- Collaborative 3D occupancy mapping
- Consensus-based map merging
- Confidence-weighted averaging
- Automatic cleanup of stale data
```

---

## 7. Summary

**Integration Points:**
- **SafetyPanel:** Perception + Adaptive Margins + Distributed Mapping
- **SwarmPanel:** Task Allocation
- **MapView:** 3D visualization (obstacles + occupancy map)

**Context Requirements:**
- ESCAPEContext with all ESCAPE features
- Exposed to QML via `escapeContext` property
- Optional dependencies handled gracefully

**UI Language:** All descriptions in English
**Design:** Consistent with existing panel style (dark theme, modern buttons)
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components" as Cmp

Rectangle {
    id: root
    color: "#0f172a"

    property var mission: null

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        Column {
            width: parent.width
            spacing: 12
            padding: 16

            // ── HEADER ────────────────────────────────────────────────────
            Row {
                width: parent.width
                spacing: 12

                Cmp.Icon {
                    name: "map"
                    size: 24
                    color: "#3b82f6"
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: "MISSION PLANNING"
                    color: "#e2e8f0"
                    font.pixelSize: 18
                    font.weight: Font.Bold
                    font.letterSpacing: 1
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Rectangle { width: parent.width; height: 1; color: "#1e293b" }

            // ── FIELD COVERAGE PLANNING ───────────────────────────────────
            Rectangle {
                width: parent.width
                height: coverageColumn.height + 24
                color: "#1e293b"
                radius: 8
                border.color: "#334155"
                border.width: 1

                Column {
                    id: coverageColumn
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
                            color: "#22c55e"
                            radius: 2
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: "FIELD COVERAGE"
                            color: "#22c55e"
                            font.pixelSize: 12
                            font.weight: Font.Bold
                            font.letterSpacing: 1
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Item { width: parent.width - 200; height: 1 }

                        Text {
                            text: mission && mission.fieldCoverageActive ? "ACTIVE" : "INACTIVE"
                            color: mission && mission.fieldCoverageActive ? "#22c55e" : "#64748b"
                            font.pixelSize: 9
                            font.weight: Font.Bold
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    Rectangle { width: parent.width; height: 1; color: "#2d3748" }

                    // Pattern Selection
                    Column {
                        width: parent.width
                        spacing: 6
                        opacity: mission && mission.missionLocked ? 0.4 : 1.0

                        Text {
                            text: "Coverage Pattern"
                            color: "#94a3b8"
                            font.pixelSize: 10
                            font.weight: Font.Bold
                        }

                        Row {
                            width: parent.width
                            spacing: 6

                            Repeater {
                                model: [
                                    { name: "Parallel Lines", icon: "grid", value: 0 },
                                    { name: "Spiral", icon: "rotate-cw", value: 1 },
                                    { name: "Grid", icon: "grid", value: 2 },
                                    { name: "Zigzag", icon: "trending-up", value: 3 }
                                ]

                                Rectangle {
                                    width: (parent.width - 18) / 4
                                    height: 60
                                    radius: 6
                                    color: mission && mission.coveragePattern === modelData.value ? "#22c55e" : "#0f172a"
                                    border.color: mission && mission.coveragePattern === modelData.value ? "#22c55e" : "#334155"
                                    border.width: 1

                                    Column {
                                        anchors.centerIn: parent
                                        spacing: 4

                                        Cmp.Icon {
                                            name: modelData.icon
                                            size: 20
                                            color: mission && mission.coveragePattern === modelData.value ? "#0f172a" : "#94a3b8"
                                            anchors.horizontalCenter: parent.horizontalCenter
                                        }

                                        Text {
                                            text: modelData.name
                                            color: mission && mission.coveragePattern === modelData.value ? "#0f172a" : "#cbd5e1"
                                            font.pixelSize: 8
                                            font.weight: Font.Bold
                                            anchors.horizontalCenter: parent.horizontalCenter
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        enabled: !(mission && mission.missionLocked)
                                        onClicked: {
                                            if (!mission) return
                                            mission.coveragePattern = modelData.value
                                            // Auto-regenerate if boundary exists
                                            if (mission.fieldBoundaryPoints >= 3) {
                                                mission.generateFieldCoverage()
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Parameters
                    Grid {
                        width: parent.width
                        columns: 2
                        columnSpacing: 12
                        rowSpacing: 12
                        opacity: mission && mission.missionLocked ? 0.4 : 1.0
                        enabled: !(mission && mission.missionLocked)

                        // Altitude
                        Column {
                            width: (parent.width - 12) / 2
                            spacing: 2

                            Text {
                                text: "Altitude (m)"
                                color: "#64748b"
                                font.pixelSize: 9
                            }

                            Row {
                                width: parent.width
                                spacing: 4

                                Slider {
                                    id: altSlider
                                    width: parent.width - 50
                                    height: 18
                                    from: 10
                                    to: 100
                                    stepSize: 5
                                    value: mission ? mission.coverageAltitude : 20
                                    onMoved: if (mission) mission.coverageAltitude = value
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: Math.round(altSlider.value) + " m"
                                    color: "#e2e8f0"
                                    font.pixelSize: 9
                                    font.family: "Consolas"
                                    width: 42
                                    horizontalAlignment: Text.AlignRight
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            Text {
                                text: {
                                    var v = altSlider.value;
                                    if (v < 20) return "Low (high resolution)";
                                    if (v < 40) return "Normal";
                                    return "High (fast coverage)";
                                }
                                color: "#94a3b8"
                                font.pixelSize: 8
                                font.italic: true
                            }
                        }

                        // Line Spacing
                        Column {
                            width: (parent.width - 12) / 2
                            spacing: 2

                            Text {
                                text: "Line Spacing (m)"
                                color: "#64748b"
                                font.pixelSize: 9
                            }

                            Row {
                                width: parent.width
                                spacing: 4

                                Slider {
                                    id: spacingSlider
                                    width: parent.width - 50
                                    height: 18
                                    from: 5
                                    to: 50
                                    stepSize: 5
                                    value: mission ? mission.coverageLineSpacing : 10
                                    onMoved: if (mission) mission.coverageLineSpacing = value
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: Math.round(spacingSlider.value) + " m"
                                    color: "#e2e8f0"
                                    font.pixelSize: 9
                                    font.family: "Consolas"
                                    width: 42
                                    horizontalAlignment: Text.AlignRight
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            Text {
                                text: {
                                    var v = spacingSlider.value;
                                    if (v < 15) return "Tight (high coverage)";
                                    if (v < 30) return "Normal";
                                    return "Wide (fast)";
                                }
                                color: "#94a3b8"
                                font.pixelSize: 8
                                font.italic: true
                            }
                        }

                        // Overlap
                        Column {
                            width: (parent.width - 12) / 2
                            spacing: 2

                            Text {
                                text: "Overlap (%)"
                                color: "#64748b"
                                font.pixelSize: 9
                            }

                            Row {
                                width: parent.width
                                spacing: 4

                                Slider {
                                    id: overlapSlider
                                    width: parent.width - 50
                                    height: 18
                                    from: 0
                                    to: 50
                                    stepSize: 5
                                    value: mission ? mission.coverageOverlap * 100 : 20
                                    onMoved: if (mission) mission.coverageOverlap = value / 100
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: Math.round(overlapSlider.value) + " %"
                                    color: "#e2e8f0"
                                    font.pixelSize: 9
                                    font.family: "Consolas"
                                    width: 42
                                    horizontalAlignment: Text.AlignRight
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            Text {
                                text: {
                                    var v = overlapSlider.value;
                                    if (v < 15) return "Minimal (risk of gaps)";
                                    if (v < 30) return "Standard";
                                    return "High (precision)";
                                }
                                color: "#94a3b8"
                                font.pixelSize: 8
                                font.italic: true
                            }
                        }

                        // Speed
                        Column {
                            width: (parent.width - 12) / 2
                            spacing: 2

                            Text {
                                text: "Flight Speed (m/s)"
                                color: "#64748b"
                                font.pixelSize: 9
                            }

                            Row {
                                width: parent.width
                                spacing: 4

                                Slider {
                                    id: speedSlider
                                    width: parent.width - 50
                                    height: 18
                                    from: 2
                                    to: 15
                                    stepSize: 1
                                    value: mission ? mission.coverageSpeed : 5
                                    onMoved: if (mission) mission.coverageSpeed = value
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: Math.round(speedSlider.value) + " m/s"
                                    color: "#e2e8f0"
                                    font.pixelSize: 9
                                    font.family: "Consolas"
                                    width: 42
                                    horizontalAlignment: Text.AlignRight
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            Text {
                                text: {
                                    var v = speedSlider.value;
                                    if (v < 5) return "Slow (stable)";
                                    if (v < 10) return "Normal";
                                    return "Fast";
                                }
                                color: "#94a3b8"
                                font.pixelSize: 8
                                font.italic: true
                            }
                        }
                    }


                    // Multi-Drone Strategy
                    Column {
                        width: parent.width
                        spacing: 6
                        opacity: mission && mission.missionLocked ? 0.4 : 1.0

                        Row {
                            width: parent.width
                            spacing: 8

                            Rectangle {
                                width: 4
                                height: 16
                                color: "#f59e0b"
                                radius: 2
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                text: "Multi-Drone Strategy"
                                color: "#f59e0b"
                                font.pixelSize: 10
                                font.weight: Font.Bold
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        Text {
                            text: "Select how waypoints are distributed among multiple drones"
                            color: "#64748b"
                            font.pixelSize: 8
                            font.italic: true
                            wrapMode: Text.WordWrap
                            width: parent.width
                        }

                        // Strategy buttons
                        Column {
                            width: parent.width
                            spacing: 4

                            Repeater {
                                model: [
                                    { name: "Single Drone", value: 0, desc: "One drone covers entire field" },
                                    { name: "Offset Pattern", value: 1, desc: "Distribute lines among drones (D1: lines 1,4,7... D2: lines 2,5,8...)" },
                                    { name: "Field Splitting", value: 2, desc: "Divide field into vertical zones (one zone per drone)" },
                                    { name: "Sequential + APF", value: 3, desc: "All drones fly same path with time delay and collision avoidance" },
                                    { name: "Formation Flight", value: 4, desc: "Leader flies coverage pattern, followers maintain offset formation" }
                                ]

                                Rectangle {
                                    width: parent.width
                                    height: 48
                                    radius: 6
                                    color: {
                                        if (mission && mission.multiDroneStrategy === modelData.value)
                                            return "#1e40af";
                                        return strategyMouseArea.containsMouse ? "#1e3a8a" : "#0f172a";
                                    }
                                    border.color: mission && mission.multiDroneStrategy === modelData.value ? "#3b82f6" : "#334155"
                                    border.width: mission && mission.multiDroneStrategy === modelData.value ? 2 : 1

                                    Column {
                                        anchors.left: parent.left
                                        anchors.leftMargin: 12
                                        anchors.verticalCenter: parent.verticalCenter
                                        spacing: 2

                                        Text {
                                            text: modelData.name
                                            color: mission && mission.multiDroneStrategy === modelData.value ? "#60a5fa" : "#e2e8f0"
                                            font.pixelSize: 10
                                            font.weight: Font.Bold
                                        }

                                        Text {
                                            text: modelData.desc
                                            color: "#94a3b8"
                                            font.pixelSize: 8
                                            font.italic: true
                                        }
                                    }

                                    MouseArea {
                                        id: strategyMouseArea
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        enabled: !(mission && mission.missionLocked)
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (mission) {
                                                mission.multiDroneStrategy = modelData.value;
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // Formation offset (only for Formation Flight)
                        Column {
                            width: parent.width
                            spacing: 2
                            visible: mission && mission.multiDroneStrategy === 4

                            Text {
                                text: "Formation Offset (m)"
                                color: "#64748b"
                                font.pixelSize: 9
                            }

                            Row {
                                width: parent.width
                                spacing: 4

                                Slider {
                                    id: formationSlider
                                    width: parent.width - 50
                                    height: 18
                                    from: 3
                                    to: 20
                                    stepSize: 1
                                    value: mission ? mission.formationOffset : 5
                                    onMoved: if (mission) mission.formationOffset = value
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: Math.round(formationSlider.value) + " m"
                                    color: "#e2e8f0"
                                    font.pixelSize: 9
                                    font.family: "Consolas"
                                    width: 42
                                    horizontalAlignment: Text.AlignRight
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                        }

                        // Sequential delay (only for Sequential + APF)
                        Column {
                            width: parent.width
                            spacing: 2
                            visible: mission && mission.multiDroneStrategy === 3

                            Text {
                                text: "Start Delay (seconds)"
                                color: "#64748b"
                                font.pixelSize: 9
                            }

                            Row {
                                width: parent.width
                                spacing: 4

                                Slider {
                                    id: delaySlider
                                    width: parent.width - 50
                                    height: 18
                                    from: 5
                                    to: 60
                                    stepSize: 5
                                    value: mission ? mission.sequentialDelay : 10
                                    onMoved: if (mission) mission.sequentialDelay = value
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: Math.round(delaySlider.value) + " s"
                                    color: "#e2e8f0"
                                    font.pixelSize: 9
                                    font.family: "Consolas"
                                    width: 42
                                    horizontalAlignment: Text.AlignRight
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                        }
                    }

                    Rectangle { width: parent.width; height: 1; color: "#2d3748" }
                    Rectangle { width: parent.width; height: 1; color: "#2d3748" }

                    // Field Boundary
                    Column {
                        width: parent.width
                        spacing: 6

                        Row {
                            width: parent.width
                            spacing: 8

                            Text {
                                text: "Field Boundary"
                                color: "#94a3b8"
                                font.pixelSize: 10
                                font.weight: Font.Bold
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                text: mission ? mission.fieldBoundaryPoints + " points" : "0 points"
                                color: "#64748b"
                                font.pixelSize: 9
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        Row {
                            width: parent.width
                            spacing: 6

                            Rectangle {
                                width: (parent.width - 6) / 2
                                height: 32
                                radius: 6
                                color: drawBoundaryM.containsMouse ? "#1e40af" : "#1e3a8a"
                                border.color: "#3b82f6"
                                border.width: 1
                                opacity: mission && mission.missionLocked ? 0.4 : 1.0

                                Row {
                                    anchors.centerIn: parent
                                    spacing: 6

                                    Cmp.Icon {
                                        name: mission && mission.missionLocked ? "lock" : "edit"
                                        size: 12
                                        color: "#93c5fd"
                                        anchors.verticalCenter: parent.verticalCenter
                                    }

                                    Text {
                                        text: mission && mission.missionLocked ? "LOCKED" : "DRAW ON MAP"
                                        color: "#93c5fd"
                                        font.pixelSize: 9
                                        font.weight: Font.Bold
                                        font.letterSpacing: 0.5
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }

                                MouseArea {
                                    id: drawBoundaryM
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    enabled: !(mission && mission.missionLocked)
                                    onClicked: {
                                        if (mission) {
                                            mission.startDrawingBoundary()
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                width: (parent.width - 6) / 2
                                height: 32
                                radius: 6
                                color: mission && mission.drawingMode
                                    ? (finishM.containsMouse ? "#15803d" : "#166534")
                                    : (clearBoundaryM.containsMouse ? "#991b1b" : "#7f1d1d")
                                border.color: mission && mission.drawingMode ? "#22c55e" : "#ef4444"
                                border.width: 1
                                opacity: (mission && mission.drawingMode) || (mission && mission.fieldBoundaryPoints > 0) ? 1 : 0.5

                                Row {
                                    anchors.centerIn: parent
                                    spacing: 6

                                    Cmp.Icon {
                                        name: mission && mission.drawingMode ? "check" : "x"
                                        size: 12
                                        color: mission && mission.drawingMode ? "#bbf7d0" : "#fecaca"
                                        anchors.verticalCenter: parent.verticalCenter
                                    }

                                    Text {
                                        text: mission && mission.drawingMode ? "FINISH" : "CLEAR"
                                        color: mission && mission.drawingMode ? "#bbf7d0" : "#fecaca"
                                        font.pixelSize: 9
                                        font.weight: Font.Bold
                                        font.letterSpacing: 0.5
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }

                                MouseArea {
                                    id: finishM
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    visible: mission && mission.drawingMode
                                    onClicked: if (mission) mission.finishDrawingBoundary()
                                }

                                MouseArea {
                                    id: clearBoundaryM
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    visible: !(mission && mission.drawingMode)
                                    enabled: mission && mission.fieldBoundaryPoints > 0
                                    onClicked: if (mission) mission.clearFieldBoundary()
                                }
                            }
                        }
                    }

                    Rectangle { width: parent.width; height: 1; color: "#2d3748" }

                    // Mission Info
                    Column {
                        width: parent.width
                        spacing: 6
                        visible: mission && mission.coverageWaypointCount > 0

                        Text {
                            text: "Mission Preview"
                            color: "#94a3b8"
                            font.pixelSize: 10
                            font.weight: Font.Bold
                        }

                        Grid {
                            width: parent.width
                            columns: 3
                            columnSpacing: 12
                            rowSpacing: 6

                            Column {
                                spacing: 2
                                Text {
                                    text: "Waypoints"
                                    color: "#64748b"
                                    font.pixelSize: 8
                                }
                                Text {
                                    text: mission ? mission.coverageWaypointCount.toString() : "0"
                                    color: "#e2e8f0"
                                    font.pixelSize: 14
                                    font.weight: Font.Bold
                                    font.family: "Consolas"
                                }
                            }

                            Column {
                                spacing: 2
                                Text {
                                    text: "Distance"
                                    color: "#64748b"
                                    font.pixelSize: 8
                                }
                                Text {
                                    text: mission ? (mission.coverageDistance / 1000).toFixed(2) + " km" : "0 km"
                                    color: "#e2e8f0"
                                    font.pixelSize: 14
                                    font.weight: Font.Bold
                                    font.family: "Consolas"
                                }
                            }

                            Column {
                                spacing: 2
                                Text {
                                    text: "Est. Time"
                                    color: "#64748b"
                                    font.pixelSize: 8
                                }
                                Text {
                                    text: mission ? (mission.coverageTime / 60).toFixed(1) + " min" : "0 min"
                                    color: "#e2e8f0"
                                    font.pixelSize: 14
                                    font.weight: Font.Bold
                                    font.family: "Consolas"
                                }
                            }
                        }
                    }

                    Rectangle { width: parent.width; height: 1; color: "#2d3748" }

                    // Action Buttons
                    Row {
                        width: parent.width
                        spacing: 6

                        Rectangle {
                            width: (parent.width - 12) / 3
                            height: 36
                            radius: 6
                            color: generateM.containsMouse ? "#15803d" : "#166534"
                            border.color: "#22c55e"
                            border.width: 1
                            opacity: (mission && mission.fieldBoundaryPoints >= 3 && !(mission && mission.missionLocked)) ? 1 : 0.4

                            Row {
                                anchors.centerIn: parent
                                spacing: 6

                                Cmp.Icon {
                                    name: "zap"
                                    size: 14
                                    color: "#bbf7d0"
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: "GENERATE"
                                    color: "#bbf7d0"
                                    font.pixelSize: 10
                                    font.weight: Font.Bold
                                    font.letterSpacing: 0.5
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            MouseArea {
                                id: generateM
                                anchors.fill: parent
                                hoverEnabled: true
                                enabled: mission && mission.fieldBoundaryPoints >= 3 && !(mission && mission.missionLocked)
                                onClicked: if (mission) mission.generateFieldCoverage()
                            }
                        }

                        Rectangle {
                            width: (parent.width - 12) / 3
                            height: 36
                            radius: 6
                            color: uploadM.containsMouse ? "#1e40af" : "#1e3a8a"
                            border.color: "#3b82f6"
                            border.width: 1
                            opacity: mission && mission.coverageWaypointCount > 0 ? 1 : 0.5

                            Row {
                                anchors.centerIn: parent
                                spacing: 6

                                Cmp.Icon {
                                    name: "upload"
                                    size: 14
                                    color: "#93c5fd"
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: "UPLOAD"
                                    color: "#93c5fd"
                                    font.pixelSize: 10
                                    font.weight: Font.Bold
                                    font.letterSpacing: 0.5
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            MouseArea {
                                id: uploadM
                                anchors.fill: parent
                                hoverEnabled: true
                                enabled: mission && mission.coverageWaypointCount > 0
                                onClicked: if (mission) mission.uploadCoverageMission()
                            }
                        }

                        Rectangle {
                            width: (parent.width - 12) / 3
                            height: 36
                            radius: 6
                            color: previewM.containsMouse ? "#713f12" : "#78350f"
                            border.color: "#f59e0b"
                            border.width: 1
                            opacity: mission && mission.coverageWaypointCount > 0 ? 1 : 0.5

                            Row {
                                anchors.centerIn: parent
                                spacing: 6

                                Cmp.Icon {
                                    name: "eye"
                                    size: 14
                                    color: "#fde68a"
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: "PREVIEW"
                                    color: "#fde68a"
                                    font.pixelSize: 10
                                    font.weight: Font.Bold
                                    font.letterSpacing: 0.5
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            MouseArea {
                                id: previewM
                                anchors.fill: parent
                                hoverEnabled: true
                                enabled: mission && mission.coverageWaypointCount > 0
                                onClicked: if (mission) mission.toggleCoveragePreview()
                            }
                        }
                    }
                }
            }

            // Spacer
            Item { width: 1; height: 20 }
        }
    }
}
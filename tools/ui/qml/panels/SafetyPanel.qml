import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    anchors.fill: parent

    // ── State ─────────────────────────────────────────────────────────────
    property var apfParams: ({ minSeparation: 3.0, maxSpeed: 5.0, repulsionGain: 3.0, attractionGain: 1.0, geofenceRadius: 50.0, geofenceAltMin: 1.0, geofenceAltMax: 30.0, obstacleRadius: 4.0, maxAcceleration: 2.0 })
    property var predParams: ({ timeHorizon: 10.0, minSeparation: 2.0, sampleRate: 0.5, criticalThreshold: 1.0, warningThreshold: 1.5 })
    property var batteryParams: ({ criticalThreshold: 20.0, warningThreshold: 30.0, safetyMargin: 1.2, historySize: 100, minSamplesForPrediction: 10 })

    function getApfValue(key, defaultVal) {
        return apfParams && apfParams[key] !== undefined ? apfParams[key] : defaultVal
    }

    function getPredValue(key, defaultVal) {
        return predParams && predParams[key] !== undefined ? predParams[key] : defaultVal
    }

    property var violations: []
    property bool apfActive: safety ? safety.apfActive : false
    property int violationCount: safety ? safety.violationCount : 0

    // Debounce timer for collision prediction config updates
    Timer {
        id: predConfigTimer
        interval: 500  // 500ms delay
        repeat: false
        onTriggered: {
            if (safety && safety.predictionEnabled) {
                safety.configureCollisionPredictor(predParams)
                safetyLogModel.append({
                    txt: "[CONFIG] Collision Prediction: horizon=" + predParams.timeHorizon.toFixed(1) + "s, minSep=" + predParams.minSeparation.toFixed(1) + "m"
                })
            }
        }
    }

    ScrollView {
        id: safetyScroll
        anchors { fill: parent; margins: 12 }
        clip: true
        contentWidth: availableWidth
        contentHeight: col.implicitHeight
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        Column {
            id: col
            width: safetyScroll.availableWidth
            spacing: 12

            // ── APF Configuration ───────────────────────────────────────────
            Text { text: "APF CONFIGURATION"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

            Rectangle {
                width: parent.width
                height: apfConfigCol.implicitHeight + 20
                radius: 8
                color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                Column {
                    id: apfConfigCol
                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                    spacing: 8

                    // Parameter Grid
                    GridLayout {
                        width: parent.width
                        columns: 2
                        columnSpacing: 12
                        rowSpacing: 6

                        // Min Separation
                        Column {
                            spacing: 2
                            Text {
                                text: "Min Separation"
                                color: "#94a3b8"
                                font.pixelSize: 10
                            }
                            Text {
                                text: "Minimum safe distance between drones"
                                color: "#64748b"
                                font.pixelSize: 8
                                font.italic: true
                                wrapMode: Text.WordWrap
                                width: 200
                            }
                        }
                        Row {
                            spacing: 4
                            Slider {
                                id: sepSlider
                                from: 0.5; to: 10.0; value: root.getApfValue("minSeparation", 3.0)
                                width: 120
                                onValueChanged: if (apfParams) apfParams.minSeparation = value
                            }
                            Column {
                                spacing: 2
                                anchors.verticalCenter: parent.verticalCenter
                                
                                Text {
                                    text: sepSlider.value.toFixed(1) + " m"
                                    color: "#e2e8f0"
                                    font.pixelSize: 10
                                }
                                
                                Text {
                                    text: {
                                        var val = sepSlider.value;
                                        if (val < 1.5) return "Very tight";
                                        if (val < 3.0) return "Tight";
                                        if (val < 5.0) return "Normal";
                                        return "Safe";
                                    }
                                    color: {
                                        var val = sepSlider.value;
                                        if (val < 1.5) return "#ef4444";
                                        if (val < 3.0) return "#f59e0b";
                                        if (val < 5.0) return "#22c55e";
                                        return "#3b82f6";
                                    }
                                    font.pixelSize: 8
                                    font.italic: true
                                }
                            }
                        }

                        // Max Speed
                        Column {
                            spacing: 2
                            Text {
                                text: "Max Speed Step"
                                color: "#94a3b8"
                                font.pixelSize: 10
                            }
                            Text {
                                text: "Maximum velocity change per update cycle"
                                color: "#64748b"
                                font.pixelSize: 8
                                font.italic: true
                                wrapMode: Text.WordWrap
                                width: 200
                            }
                        }
                        Row {
                            spacing: 4
                            Slider {
                                id: spdSlider
                                from: 0.5; to: 10.0; value: root.getApfValue("maxSpeed", 5.0)
                                width: 120
                                onValueChanged: if (apfParams) apfParams.maxSpeed = value
                            }
                            Text {
                                text: spdSlider.value.toFixed(1) + " m/s"
                                color: "#e2e8f0"; font.pixelSize: 10
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        // Max Acceleration (Improvement 9)
                        Column {
                            spacing: 2
                            Text {
                                text: "Max Acceleration"
                                color: "#94a3b8"
                                font.pixelSize: 10
                            }
                            Text {
                                text: "Limits rate of velocity change to prevent jerky movements"
                                color: "#64748b"
                                font.pixelSize: 8
                                font.italic: true
                                wrapMode: Text.WordWrap
                                width: 200
                            }
                        }
                        Row {
                            spacing: 4
                            Slider {
                                id: accelSlider
                                from: 0.5; to: 5.0; value: root.getApfValue("maxAcceleration", 2.0)
                                width: 120
                                onValueChanged: if (apfParams) apfParams.maxAcceleration = value
                            }
                            Column {
                                spacing: 2
                                anchors.verticalCenter: parent.verticalCenter
                                
                                Text {
                                    text: accelSlider.value.toFixed(1) + " m/s²"
                                    color: "#e2e8f0"
                                    font.pixelSize: 10
                                }
                                
                                Text {
                                    text: {
                                        var val = accelSlider.value;
                                        if (val < 1.0) return "Smooth";
                                        if (val < 2.5) return "Normal";
                                        if (val < 4.0) return "Responsive";
                                        return "Aggressive";
                                    }
                                    color: {
                                        var val = accelSlider.value;
                                        if (val < 1.0) return "#22c55e";
                                        if (val < 2.5) return "#3b82f6";
                                        if (val < 4.0) return "#f59e0b";
                                        return "#ef4444";
                                    }
                                    font.pixelSize: 8
                                    font.italic: true
                                }
                            }
                        }

                        // Repulsion Gain
                        Column {
                            spacing: 2
                            Text {
                                text: "Repulsion Gain"
                                color: "#94a3b8"
                                font.pixelSize: 10
                            }
                            Text {
                                text: "Strength of repulsive force between drones"
                                color: "#64748b"
                                font.pixelSize: 8
                                font.italic: true
                                wrapMode: Text.WordWrap
                                width: 200
                            }
                        }
                        Row {
                            spacing: 4
                            Slider {
                                id: repSlider
                                from: 0.1; to: 10.0; value: root.getApfValue("repulsionGain", 3.0)
                                width: 120
                                onValueChanged: if (apfParams) apfParams.repulsionGain = value
                            }
                            Column {
                                spacing: 2
                                anchors.verticalCenter: parent.verticalCenter
                                
                                Text {
                                    text: repSlider.value.toFixed(1)
                                    color: "#e2e8f0"
                                    font.pixelSize: 10
                                }
                                
                                Text {
                                    text: {
                                        var val = repSlider.value;
                                        if (val < 1.0) return "Weak";
                                        if (val < 3.0) return "Normal";
                                        if (val < 6.0) return "Strong";
                                        return "Very strong";
                                    }
                                    color: {
                                        var val = repSlider.value;
                                        if (val < 1.0) return "#ef4444";
                                        if (val < 3.0) return "#22c55e";
                                        if (val < 6.0) return "#f59e0b";
                                        return "#3b82f6";
                                    }
                                    font.pixelSize: 8
                                    font.italic: true
                                }
                            }
                        }

                        // Geofence Radius
                        Column {
                            spacing: 2
                            Text {
                                text: "Geofence Radius"
                                color: "#94a3b8"
                                font.pixelSize: 10
                            }
                            Text {
                                text: "Horizontal boundary limit from origin"
                                color: "#64748b"
                                font.pixelSize: 8
                                font.italic: true
                                wrapMode: Text.WordWrap
                                width: 200
                            }
                        }
                        Row {
                            spacing: 4
                            Slider {
                                id: gfSlider
                                from: 10.0; to: 200.0; value: root.getApfValue("geofenceRadius", 50.0)
                                width: 120
                                onValueChanged: if (apfParams) apfParams.geofenceRadius = value
                            }
                            Text {
                                text: gfSlider.value.toFixed(0) + " m"
                                color: "#e2e8f0"; font.pixelSize: 10
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        // Altitude Limits
                        Column {
                            spacing: 2
                            Text {
                                text: "Altitude Range"
                                color: "#94a3b8"
                                font.pixelSize: 10
                            }
                            Text {
                                text: "Minimum and maximum flight altitude above ground"
                                color: "#64748b"
                                font.pixelSize: 8
                                font.italic: true
                                wrapMode: Text.WordWrap
                                width: 200
                            }
                        }
                        Row {
                            spacing: 4
                            TextField {
                                width: 50; height: 24
                                text: root.getApfValue("geofenceAltMin", 1.0).toFixed(0)
                                background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" }
                                color: "#e2e8f0"; font.pixelSize: 10
                                onTextChanged: if (apfParams) apfParams.geofenceAltMin = parseFloat(text) || 1.0
                            }
                            Text { text: "-"; color: "#64748b"; anchors.verticalCenter: parent.verticalCenter }
                            TextField {
                                width: 50; height: 24
                                text: root.getApfValue("geofenceAltMax", 30.0).toFixed(0)
                                background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" }
                                color: "#e2e8f0"; font.pixelSize: 10
                                onTextChanged: if (apfParams) apfParams.geofenceAltMax = parseFloat(text) || 30.0
                            }
                            Text { text: "m"; color: "#64748b"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter }
                        }
                    }

                    // Action Buttons
                    Row {
                        width: parent.width
                        spacing: 8

                        Rectangle {
                            width: 140; height: 32; radius: 6
                            color: enableM.containsMouse ? (apfActive ? "#dc2626" : "#15803d") : (apfActive ? "#b91c1c" : "#22c55e")
                            Text {
                                anchors.centerIn: parent
                                text: apfActive ? "DISABLE APF" : "ENABLE APF"
                                color: "white"; font.pixelSize: 11; font.weight: Font.Bold
                            }
                            MouseArea {
                                id: enableM
                                anchors.fill: parent; hoverEnabled: true
                                onClicked: {
                                    if (apfActive) {
                                        safety.disableAPF()
                                    } else {
                                        safety.configureAPF(apfParams)
                                    }
                                }
                            }
                        }

                        Rectangle {
                            width: 120; height: 32; radius: 6
                            color: checkM.containsMouse ? "#2563eb" : "#1e2535"
                            Text {
                                anchors.centerIn: parent
                                text: "CHECK NOW"
                                color: "#e2e8f0"; font.pixelSize: 11; font.weight: Font.Bold
                            }
                            MouseArea {
                                id: checkM
                                anchors.fill: parent; hoverEnabled: true
                                onClicked: if (safety) safety.checkSeparations()
                            }
                        }

                        Item { width: parent.width - 280; height: parent.height }

                        Rectangle {
                            width: 100; height: 32; radius: 6
                            color: obsM.containsMouse ? "#f59e0b" : "#1e2535"
                            Text {
                                anchors.centerIn: parent
                                text: "OBSTACLE"
                                color: "#f59e0b"; font.pixelSize: 11; font.weight: Font.Bold
                            }
                            MouseArea {
                                id: obsM
                                anchors.fill: parent; hoverEnabled: true
                                onClicked: {
                                    // Add test obstacle at origin
                                    if (safety) safety.addObstacle(0, 0, 0)
                                }
                            }
                        }

                        Rectangle {
                            width: 80; height: 32; radius: 6
                            color: clearM.containsMouse ? "#ef4444" : "#1e2535"
                            Text {
                                anchors.centerIn: parent
                                text: "Clear"
                                color: "#ef4444"; font.pixelSize: 11
                            }
                            MouseArea {
                                id: clearM
                                anchors.fill: parent; hoverEnabled: true
                                onClicked: if (safety) safety.clearObstacles()
                            }
                        }
                    }
                }
            }

            // ── Collision Prediction ────────────────────────────────────────
            Text { text: "COLLISION PREDICTION"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

            Rectangle {
                width: parent.width
                height: predCol.implicitHeight + 20
                radius: 8
                color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                Column {
                    id: predCol
                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                    spacing: 10

                    // Enable/Disable Toggle
                    Row {
                        spacing: 12
                        width: parent.width

                        Rectangle {
                            width: 140; height: 36; radius: 6
                            color: safety && safety.predictionEnabled ? "#15803d" : (predToggleM.containsMouse ? "#1e3a5f" : "#1e2535")
                            border.color: safety && safety.predictionEnabled ? "#22c55e" : "#2563eb"
                            border.width: 1

                            Row {
                                anchors.centerIn: parent
                                spacing: 6

                                Rectangle {
                                    width: 8; height: 8; radius: 4
                                    color: safety && safety.predictionEnabled ? "#22c55e" : "#64748b"
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: safety && safety.predictionEnabled ? "ENABLED" : "DISABLED"
                                    color: "#e2e8f0"
                                    font.pixelSize: 11
                                    font.weight: Font.Bold
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            MouseArea {
                                id: predToggleM
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: {
                                    if (safety) {
                                        var enabled = safety.predictionEnabled
                                        safety.enableCollisionPrediction(!enabled)
                                    }
                                }
                            }
                        }

                        Text {
                            text: safety && safety.predictionCount > 0
                                  ? safety.predictionCount + " collision(s) predicted"
                                  : "No collisions predicted"
                            color: safety && safety.predictionCount > 0 ? "#ef4444" : "#64748b"
                            font.pixelSize: 10
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    // Info Text
                    Text {
                        text: "Predicts collisions based on current trajectories.\nWorks with PX4, ArduPilot, and Mock backends."
                        color: "#64748b"
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                        width: parent.width
                    }

                    // Parameter Grid
                    GridLayout {
                        width: parent.width
                        columns: 2
                        columnSpacing: 12
                        rowSpacing: 6
                        visible: safety && safety.predictionEnabled

                        // Time Horizon
                        Text { text: "Time Horizon"; color: "#94a3b8"; font.pixelSize: 10 }
                        Row {
                            spacing: 4
                            Slider {
                                id: horizonSlider
                                from: 5.0; to: 30.0; value: root.getPredValue("timeHorizon", 10.0)
                                width: 120
                                onValueChanged: {
                                    if (predParams) predParams.timeHorizon = value
                                    predConfigTimer.restart()
                                }
                            }
                            Column {
                                spacing: 2
                                anchors.verticalCenter: parent.verticalCenter
                                
                                Text {
                                    text: horizonSlider.value.toFixed(1) + " s"
                                    color: "#e2e8f0"
                                    font.pixelSize: 10
                                }
                                
                                Text {
                                    text: {
                                        var val = horizonSlider.value;
                                        if (val < 8.0) return "Short";
                                        if (val < 15.0) return "Normal";
                                        if (val < 22.0) return "Long";
                                        return "Very long";
                                    }
                                    color: {
                                        var val = horizonSlider.value;
                                        if (val < 8.0) return "#ef4444";
                                        if (val < 15.0) return "#22c55e";
                                        if (val < 22.0) return "#f59e0b";
                                        return "#3b82f6";
                                    }
                                    font.pixelSize: 8
                                    font.italic: true
                                }
                            }
                        }

                        // Min Separation
                        Text { text: "Min Separation"; color: "#94a3b8"; font.pixelSize: 10 }
                        Row {
                            spacing: 4
                            Slider {
                                id: predSepSlider
                                from: 0.5; to: 5.0; value: root.getPredValue("minSeparation", 2.0)
                                width: 120
                                onValueChanged: {
                                    if (predParams) predParams.minSeparation = value
                                    predConfigTimer.restart()
                                }
                            }
                            Text {
                                text: predSepSlider.value.toFixed(1) + " m"
                                color: "#e2e8f0"; font.pixelSize: 10
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        // Sample Rate
                        Text { text: "Sample Rate"; color: "#94a3b8"; font.pixelSize: 10 }
                        Row {
                            spacing: 4
                            Slider {
                                id: sampleSlider
                                from: 0.1; to: 2.0; value: root.getPredValue("sampleRate", 0.5)
                                width: 120
                                onValueChanged: {
                                    if (predParams) predParams.sampleRate = value
                                    predConfigTimer.restart()
                                }
                            }
                            Text {
                                text: sampleSlider.value.toFixed(1) + " s"
                                color: "#e2e8f0"; font.pixelSize: 10
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        // Critical Threshold
                        Text { text: "Critical Threshold"; color: "#94a3b8"; font.pixelSize: 10 }
                        Row {
                            spacing: 4
                            Slider {
                                id: critSlider
                                from: 0.5; to: 2.0; value: root.getPredValue("criticalThreshold", 1.0)
                                width: 120
                                onValueChanged: {
                                    if (predParams) predParams.criticalThreshold = value
                                    predConfigTimer.restart()
                                }
                            }
                            Text {
                                text: critSlider.value.toFixed(1) + " m"
                                color: "#ef4444"; font.pixelSize: 10
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        // Warning Threshold
                        Text { text: "Warning Threshold"; color: "#94a3b8"; font.pixelSize: 10 }
                        Row {
                            spacing: 4
                            Slider {
                                id: warnSlider
                                from: 1.0; to: 3.0; value: root.getPredValue("warningThreshold", 1.5)
                                width: 120
                                onValueChanged: {
                                    if (predParams) predParams.warningThreshold = value
                                    if (safety && safety.predictionEnabled) {
                                        safety.configureCollisionPredictor(predParams)
                                    }
                                }
                            }
                            Text {
                                text: warnSlider.value.toFixed(1) + " m"
                                color: "#f59e0b"; font.pixelSize: 10
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                    }
                    
                    // Waypoint-Aware Prediction Toggle
                    Rectangle {
                        width: parent.width
                        height: wpAwareCol.implicitHeight + 16
                        radius: 6
                        color: "#1a2035"
                        border.color: "#2d3748"
                        border.width: 1
                        
                        Column {
                            id: wpAwareCol
                            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 8 }
                            spacing: 6
                            
                            Row {
                                width: parent.width
                                spacing: 8
                                
                                Rectangle {
                                    width: 24; height: 24; radius: 4
                                    color: wpAwareCheck.checked ? "#15803d" : "#1e2535"
                                    border.color: wpAwareCheck.checked ? "#22c55e" : "#334155"
                                    border.width: 1
                                    
                                    Text {
                                        anchors.centerIn: parent
                                        text: wpAwareCheck.checked ? "✓" : ""
                                        color: "#22c55e"
                                        font.pixelSize: 14
                                        font.weight: Font.Bold
                                    }
                                    
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: wpAwareCheck.checked = !wpAwareCheck.checked
                                    }
                                    
                                    CheckBox {
                                        id: wpAwareCheck
                                        visible: false
                                        checked: false
                                        onCheckedChanged: {
                                            if (safety) {
                                                safety.enableWaypointAwarePrediction(checked)
                                            }
                                        }
                                    }
                                }
                                
                                Column {
                                    width: parent.width - 32
                                    spacing: 2
                                    
                                    Text {
                                        text: "Waypoint-Aware Prediction"
                                        color: "#e2e8f0"
                                        font.pixelSize: 11
                                        font.weight: Font.Bold
                                    }
                                    
                                    Text {
                                        text: wpAwareCheck.checked
                                              ? "Using planned waypoints for collision prediction"
                                              : "Using current velocity for collision prediction"
                                        color: "#64748b"
                                        font.pixelSize: 9
                                        wrapMode: Text.WordWrap
                                        width: parent.width
                                    }
                                }
                            }
                            
                            Text {
                                text: "⚠ Requires waypoints to be set in Swarm Panel"
                                color: "#f59e0b"
                                font.pixelSize: 8
                                visible: wpAwareCheck.checked
                                width: parent.width
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }

            // ── Battery Monitor ──────────────────────────────────────────────
            Text { text: "BATTERY MONITOR"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

            Rectangle {
                width: parent.width
                height: batteryCol.implicitHeight + 20
                radius: 8
                color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                Column {
                    id: batteryCol
                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                    spacing: 10

                    // Enable/Disable Toggle
                    Row {
                        spacing: 12
                        width: parent.width

                        Rectangle {
                            width: 140; height: 36; radius: 6
                            color: safety && safety.batteryMonitorEnabled ? "#15803d" : (battToggleM.containsMouse ? "#1e3a5f" : "#1e2535")
                            border.color: safety && safety.batteryMonitorEnabled ? "#22c55e" : "#2563eb"
                            border.width: 1

                            Row {
                                anchors.centerIn: parent
                                spacing: 6

                                Rectangle {
                                    width: 8; height: 8; radius: 4
                                    color: safety && safety.batteryMonitorEnabled ? "#22c55e" : "#64748b"
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: safety && safety.batteryMonitorEnabled ? "ENABLED" : "DISABLED"
                                    color: "#e2e8f0"
                                    font.pixelSize: 11
                                    font.weight: Font.Bold
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            MouseArea {
                                id: battToggleM
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: {
                                    if (safety) {
                                        var enabled = safety.batteryMonitorEnabled
                                        if (enabled) {
                                            safety.disableBatteryMonitor()
                                        } else {
                                            safety.configureBatteryMonitor(batteryParams)
                                        }
                                    }
                                }
                            }
                        }

                        Text {
                            text: "Predictive RTL based on battery drain & distance"
                            color: "#64748b"
                            font.pixelSize: 10
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    // Info Text
                    Text {
                        text: "Monitors battery levels and triggers RTL before critical threshold.\nWorks with all autopilot types (ArduPilot, PX4, etc.).\nHistory saved to logs/batterylogs/battery_history.json for better predictions."
                        color: "#64748b"
                        font.pixelSize: 9
                        font.italic: true
                        wrapMode: Text.WordWrap
                        width: parent.width
                    }

                    // Parameter Grid
                    GridLayout {
                        width: parent.width
                        columns: 2
                        columnSpacing: 12
                        rowSpacing: 6
                        visible: safety && safety.batteryMonitorEnabled

                        // Critical Threshold
                        Text { text: "Critical Threshold"; color: "#94a3b8"; font.pixelSize: 10 }
                        Row {
                            spacing: 4
                            Slider {
                                id: battCritSlider
                                from: 10.0; to: 30.0; value: 20.0
                                width: 120
                                onValueChanged: {
                                    if (batteryParams) batteryParams.criticalThreshold = value
                                    battConfigTimer.restart()
                                }
                            }
                            Text {
                                text: battCritSlider.value.toFixed(1) + " %"
                                color: "#ef4444"; font.pixelSize: 10
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        // Warning Threshold
                        Text { text: "Warning Threshold"; color: "#94a3b8"; font.pixelSize: 10 }
                        Row {
                            spacing: 4
                            Slider {
                                id: battWarnSlider
                                from: 20.0; to: 50.0; value: 30.0
                                width: 120
                                onValueChanged: {
                                    if (batteryParams) batteryParams.warningThreshold = value
                                    battConfigTimer.restart()
                                }
                            }
                            Text {
                                text: battWarnSlider.value.toFixed(1) + " %"
                                color: "#f59e0b"; font.pixelSize: 10
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        // Safety Margin
                        Text { text: "Safety Margin"; color: "#94a3b8"; font.pixelSize: 10 }
                        Row {
                            spacing: 4
                            Slider {
                                id: safetyMarginSlider
                                from: 1.0; to: 2.0; value: 1.2
                                stepSize: 0.1
                                width: 120
                                onValueChanged: {
                                    if (batteryParams) batteryParams.safetyMargin = value
                                    battConfigTimer.restart()
                                }
                            }
                            Column {
                                spacing: 2
                                anchors.verticalCenter: parent.verticalCenter
                                
                                Text {
                                    text: safetyMarginSlider.value.toFixed(1) + "x (" + ((safetyMarginSlider.value - 1.0) * 100).toFixed(0) + "% buffer)"
                                    color: "#22c55e"
                                    font.pixelSize: 10
                                }
                                
                                Text {
                                    text: {
                                        var val = safetyMarginSlider.value;
                                        if (val < 1.15) return "Aggressive";
                                        if (val < 1.35) return "Standard";
                                        if (val < 1.75) return "Conservative";
                                        return "Very safe";
                                    }
                                    color: {
                                        var val = safetyMarginSlider.value;
                                        if (val < 1.15) return "#ef4444";  // red
                                        if (val < 1.35) return "#22c55e";  // green
                                        if (val < 1.75) return "#f59e0b";  // orange
                                        return "#3b82f6";  // blue
                                    }
                                    font.pixelSize: 8
                                    font.italic: true
                                }
                            }
                        }

                        // Min Samples
                        Text { text: "Min Samples"; color: "#94a3b8"; font.pixelSize: 10 }
                        Row {
                            spacing: 4
                            Slider {
                                id: minSamplesSlider
                                from: 5; to: 20; value: 10
                                stepSize: 1
                                width: 120
                                onValueChanged: {
                                    if (batteryParams) batteryParams.minSamplesForPrediction = value
                                    battConfigTimer.restart()
                                }
                            }
                            Text {
                                text: minSamplesSlider.value.toFixed(0) + " samples"
                                color: "#e2e8f0"; font.pixelSize: 10
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                    }

                    // Safety Margin Explanation
                    Rectangle {
                        width: parent.width
                        height: marginExplainCol.implicitHeight + 12
                        radius: 6
                        color: "#0d1117"
                        border.color: "#334155"
                        border.width: 1
                        visible: safety && safety.batteryMonitorEnabled

                        Column {
                            id: marginExplainCol
                            anchors { left: parent.left; right: parent.right; top: parent.top; margins: 6 }
                            spacing: 4

                            Text {
                                text: "Safety Margin Explanation:"
                                color: "#94a3b8"
                                font.pixelSize: 9
                                font.weight: Font.Bold
                            }

                            Text {
                                text: "• 1.1x (10%) - Ideal conditions, experienced pilots\n" +
                                      "• 1.2x (20%) - Normal conditions (default)\n" +
                                      "• 1.5x (50%) - Windy/difficult conditions\n" +
                                      "• 2.0x (100%) - Extreme safety, long distances"
                                color: "#64748b"
                                font.pixelSize: 8
                                lineHeight: 1.3
                                width: parent.width
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }

            // Debounce timer for battery config updates
            Timer {
                id: battConfigTimer
                interval: 500
                repeat: false
                onTriggered: {
                    if (safety && safety.batteryMonitorEnabled) {
                        safety.configureBatteryMonitor(batteryParams)
                    }
                }
            }
            // ── Perception-Based Collision Avoidance ────────────────────────
            Text { text: "PERCEPTION-BASED COLLISION AVOIDANCE"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

            Rectangle {
                width: parent.width
                height: perceptionCol.implicitHeight + 20
                radius: 8
                color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                Column {
                    id: perceptionCol
                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                    spacing: 10

                    // Enable/Disable Toggle
                    Row {
                        spacing: 12
                        width: parent.width

                        Rectangle {
                            width: 140; height: 36; radius: 6
                            color: escape && escape.perceptionEnabled ? "#15803d" : (perceptionToggleM.containsMouse ? "#1e3a5f" : "#1e2535")
                            border.color: escape && escape.perceptionEnabled ? "#22c55e" : "#2563eb"
                            border.width: 1

                            Row {
                                anchors.centerIn: parent
                                spacing: 6

                                Rectangle {
                                    width: 8; height: 8; radius: 4
                                    color: escape && escape.perceptionEnabled ? "#22c55e" : "#64748b"
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: escape && escape.perceptionEnabled ? "ENABLED" : "DISABLED"
                                    color: "#e2e8f0"
                                    font.pixelSize: 11
                                    font.weight: Font.Bold
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            MouseArea {
                                id: perceptionToggleM
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: {
                                    if (escape) {
                                        escape.perceptionEnabled = !escape.perceptionEnabled
                                    }
                                }
                            }
                        }

                        Text {
                            text: escape && escape.obstacleCount > 0
                                  ? escape.obstacleCount + " obstacle(s) detected"
                                  : "No obstacles detected"
                            color: escape && escape.obstacleCount > 0 ? "#f59e0b" : "#64748b"
                            font.pixelSize: 10
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    // Info Text
                    Text {
                        text: "Uses depth camera data to detect and avoid obstacles in real-time.\nIntegrates with APF for dynamic collision avoidance."
                        color: "#64748b"
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                        width: parent.width
                    }

                    // Obstacle List
                    Rectangle {
                        width: parent.width
                        height: 120
                        radius: 6
                        color: "#0d1117"
                        border.color: "#2d3748"
                        border.width: 1
                        visible: escape && escape.perceptionEnabled

                        ListView {
                            id: obstacleList
                            anchors { fill: parent; margins: 8 }
                            model: escape ? escape.obstacles : []
                            clip: true
                            delegate: Row {
                                spacing: 8
                                width: obstacleList.width

                                Rectangle {
                                    width: 6; height: 6; radius: 3
                                    color: "#ef4444"
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: "Obstacle at (" + modelData.x.toFixed(1) + ", " + 
                                          modelData.y.toFixed(1) + ", " + modelData.z.toFixed(1) + ") m"
                                    color: "#e2e8f0"
                                    font.pixelSize: 10
                                    font.family: "Consolas"
                                }
                            }

                            Text {
                                anchors.centerIn: parent
                                text: "No obstacles detected"
                                color: "#64748b"
                                font.pixelSize: 10
                                visible: obstacleList.count === 0
                            }
                        }
                    }

                    // Action Buttons
                    Row {
                        spacing: 8
                        visible: escape && escape.perceptionEnabled

                        Rectangle {
                            width: 100; height: 32; radius: 6
                            color: clearObstaclesM.containsMouse ? "#ef4444" : "#1e2535"
                            border.color: "#ef4444"
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "Clear All"
                                color: "#ef4444"
                                font.pixelSize: 11
                            }

                            MouseArea {
                                id: clearObstaclesM
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: {
                                    if (escape) escape.clearObstacles()
                                }
                            }
                        }
                    }
                }
            }

            // ── Adaptive Safety Margins ─────────────────────────────────────
            Text { text: "ADAPTIVE SAFETY MARGINS"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

            Rectangle {
                width: parent.width
                height: adaptiveCol.implicitHeight + 20
                radius: 8
                color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                Column {
                    id: adaptiveCol
                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                    spacing: 10

                    // Enable/Disable Toggle
                    Row {
                        spacing: 12
                        width: parent.width

                        Rectangle {
                            width: 140; height: 36; radius: 6
                            color: escape && escape.adaptiveMarginsEnabled ? "#15803d" : (adaptiveToggleM.containsMouse ? "#1e3a5f" : "#1e2535")
                            border.color: escape && escape.adaptiveMarginsEnabled ? "#22c55e" : "#2563eb"
                            border.width: 1

                            Row {
                                anchors.centerIn: parent
                                spacing: 6

                                Rectangle {
                                    width: 8; height: 8; radius: 4
                                    color: escape && escape.adaptiveMarginsEnabled ? "#22c55e" : "#64748b"
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: escape && escape.adaptiveMarginsEnabled ? "ENABLED" : "DISABLED"
                                    color: "#e2e8f0"
                                    font.pixelSize: 11
                                    font.weight: Font.Bold
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            MouseArea {
                                id: adaptiveToggleM
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: {
                                    if (escape) {
                                        escape.adaptiveMarginsEnabled = !escape.adaptiveMarginsEnabled
                                    }
                                }
                            }
                        }
                    }

                    // Info Text
                    Text {
                        text: "Dynamically adjusts safety margins based on environmental conditions.\nAdapts to wind speed, GPS uncertainty, and drone velocity."
                        color: "#64748b"
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                        width: parent.width
                    }

                    // Environmental Conditions
                    GridLayout {
                        width: parent.width
                        columns: 2
                        columnSpacing: 12
                        rowSpacing: 8
                        visible: escape && escape.adaptiveMarginsEnabled

                        // Wind Speed
                        Text { text: "Wind Speed"; color: "#94a3b8"; font.pixelSize: 10 }
                        Row {
                            spacing: 4
                            Slider {
                                id: windSlider
                                from: 0.0; to: 15.0
                                value: escape ? escape.windSpeed : 0.0
                                width: 120
                                onValueChanged: {
                                    if (escape) escape.setWindSpeed(value)
                                }
                            }
                            Text {
                                text: windSlider.value.toFixed(1) + " m/s"
                                color: windSlider.value > 10.0 ? "#ef4444" : 
                                       windSlider.value > 5.0 ? "#f59e0b" : "#22c55e"
                                font.pixelSize: 10
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        // GPS Uncertainty
                        Text { text: "GPS Uncertainty"; color: "#94a3b8"; font.pixelSize: 10 }
                        Row {
                            spacing: 4
                            Slider {
                                id: gpsSlider
                                from: 0.0; to: 5.0
                                value: 0.0
                                width: 120
                                Component.onCompleted: {
                                    if (escape) value = escape.gpsUncertainty
                                }
                                onValueChanged: {
                                    if (escape) escape.setGpsUncertainty(value)
                                }
                            }
                            Text {
                                text: gpsSlider.value.toFixed(2) + " m"
                                color: gpsSlider.value > 2.0 ? "#ef4444" : 
                                       gpsSlider.value > 1.0 ? "#f59e0b" : "#22c55e"
                                font.pixelSize: 10
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }
                    }

                    // Drone Margins Display
                    Rectangle {
                        width: parent.width
                        height: 100
                        radius: 6
                        color: "#0d1117"
                        border.color: "#2d3748"
                        border.width: 1
                        visible: escape && escape.adaptiveMarginsEnabled

                        ListView {
                            id: marginsList
                            anchors { fill: parent; margins: 8 }
                            model: escape ? escape.droneMargins : []
                            clip: true
                            delegate: Row {
                                spacing: 12
                                width: marginsList.width

                                Text {
                                    text: modelData.droneId
                                    color: "#3b82f6"
                                    font.pixelSize: 10
                                    font.weight: Font.Bold
                                    width: 60
                                }

                                Text {
                                    text: "Margin: " + modelData.margin.toFixed(2) + " m"
                                    color: "#e2e8f0"
                                    font.pixelSize: 10
                                    font.family: "Consolas"
                                }

                                Text {
                                    text: "Velocity: " + modelData.velocity.toFixed(1) + " m/s"
                                    color: "#94a3b8"
                                    font.pixelSize: 9
                                }
                            }

                            Text {
                                anchors.centerIn: parent
                                text: "No active drones"
                                color: "#64748b"
                                font.pixelSize: 10
                                visible: marginsList.count === 0
                            }
                        }
                    }
                }
            }

            // ── Distributed Mapping Consensus ───────────────────────────────
            Text { text: "DISTRIBUTED MAPPING CONSENSUS"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

            Rectangle {
                width: parent.width
                height: mappingCol.implicitHeight + 20
                radius: 8
                color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                Column {
                    id: mappingCol
                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                    spacing: 10

                    // Enable/Disable Toggle
                    Row {
                        spacing: 12
                        width: parent.width

                        Rectangle {
                            width: 140; height: 36; radius: 6
                            color: escape && escape.mappingEnabled ? "#15803d" : (mappingToggleM.containsMouse ? "#1e3a5f" : "#1e2535")
                            border.color: escape && escape.mappingEnabled ? "#22c55e" : "#2563eb"
                            border.width: 1

                            Row {
                                anchors.centerIn: parent
                                spacing: 6

                                Rectangle {
                                    width: 8; height: 8; radius: 4
                                    color: escape && escape.mappingEnabled ? "#22c55e" : "#64748b"
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: escape && escape.mappingEnabled ? "ENABLED" : "DISABLED"
                                    color: "#e2e8f0"
                                    font.pixelSize: 11
                                    font.weight: Font.Bold
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            MouseArea {
                                id: mappingToggleM
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: {
                                    if (escape) {
                                        escape.mappingEnabled = !escape.mappingEnabled
                                    }
                                }
                            }
                        }

                        Text {
                            text: escape && escape.voxelCount > 0
                                  ? escape.voxelCount + " voxel(s) mapped"
                                  : "No voxels mapped"
                            color: escape && escape.voxelCount > 0 ? "#22c55e" : "#64748b"
                            font.pixelSize: 10
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    // Info Text
                    Text {
                        text: "Builds a shared 3D occupancy map through swarm consensus.\nEach drone contributes observations, merged via distributed voting."
                        color: "#64748b"
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                        width: parent.width
                    }

                    // Map Statistics
                    GridLayout {
                        width: parent.width
                        columns: 2
                        columnSpacing: 12
                        rowSpacing: 6
                        visible: escape && escape.mappingEnabled

                        Text { text: "Voxel Size"; color: "#94a3b8"; font.pixelSize: 10 }
                        Text {
                            text: "0.5 m"
                            color: "#e2e8f0"
                            font.pixelSize: 10
                        }

                        Text { text: "Consensus Threshold"; color: "#94a3b8"; font.pixelSize: 10 }
                        Text {
                            text: "2 votes"
                            color: "#e2e8f0"
                            font.pixelSize: 10
                        }

                        Text { text: "Occupied Voxels"; color: "#94a3b8"; font.pixelSize: 10 }
                        Text {
                            text: escape ? escape.voxelCount.toString() : "0"
                            color: "#22c55e"
                            font.pixelSize: 10
                            font.weight: Font.Bold
                        }
                    }

                    // Voxel List (scrollable)
                    Rectangle {
                        width: parent.width
                        height: 100
                        radius: 6
                        color: "#0d1117"
                        border.color: "#2d3748"
                        border.width: 1
                        visible: escape && escape.mappingEnabled

                        ListView {
                            id: voxelList
                            anchors { fill: parent; margins: 8 }
                            model: escape ? escape.occupiedVoxels : []
                            clip: true
                            delegate: Row {
                                spacing: 8
                                width: voxelList.width

                                Rectangle {
                                    width: 6; height: 6; radius: 3
                                    color: "#22c55e"
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: "Voxel (" + modelData.x + ", " + modelData.y + ", " + modelData.z + 
                                          ") - " + modelData.votes + " vote(s)"
                                    color: "#e2e8f0"
                                    font.pixelSize: 10
                                    font.family: "Consolas"
                                }
                            }

                            Text {
                                anchors.centerIn: parent
                                text: "No voxels mapped yet"
                                color: "#64748b"
                                font.pixelSize: 10
                                visible: voxelList.count === 0
                            }
                        }
                    }

                    // Action Buttons
                    Row {
                        spacing: 8
                        visible: escape && escape.mappingEnabled

                        Rectangle {
                            width: 120; height: 32; radius: 6
                            color: cleanupMapM.containsMouse ? "#3b82f6" : "#1e2535"
                            border.color: "#3b82f6"
                            border.width: 1

                            Text {
                                anchors.centerIn: parent
                                text: "Cleanup Map"
                                color: "#3b82f6"
                                font.pixelSize: 11
                            }

                            MouseArea {
                                id: cleanupMapM
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: {
                                    if (escape) escape.cleanupMap()
                                }
                            }
                        }
                    }
                }
            }


            // ── Safety Log ──────────────────────────────────────────────────
            Text { text: "SAFETY LOG"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

            Rectangle {
                width: parent.width
                height: 140
                radius: 8
                color: "#0d1117"; border.color: "#2d3748"; border.width: 1

                ListView {
                    id: safetyLog
                    anchors { fill: parent; margins: 8 }
                    model: ListModel { id: safetyLogModel }
                    clip: true
                    delegate: Text {
                        text: model.txt
                        color: model.txt.startsWith("[APF]") ? "#22c55e" :
                               model.txt.includes("VIOLATION") ? "#ef4444" :
                               model.txt.includes("Geofence") ? "#f59e0b" : "#8be9fd"
                        font.pixelSize: 10; font.family: "Consolas"
                        width: safetyLog.width; wrapMode: Text.WordWrap
                    }
                    onCountChanged: positionViewAtEnd()
                }
            }
        }
    }

    // ── Connections ─────────────────────────────────────────────────────────
    Connections {
        target: safety

        function onViolationsChanged(violations) {
            root.violations = violations
        }

        function onApfLogMessage(text) {
            safetyLogModel.append({ txt: text })
        }

        function onCollisionPredicted(predictions) {
            // Predictions are automatically visualized on map
            // Log critical predictions
            for (var i = 0; i < predictions.length; i++) {
                var pred = predictions[i]
                if (pred.severity === "critical") {
                    safetyLogModel.append({
                        txt: "[PREDICTION] 🚨 " + pred.droneA + " ↔ " + pred.droneB +
                             " collision in " + pred.timeToCollision + "s"
                    })
                }
            }
        }

        function onGeofenceBreached(droneId, reason) {
            safetyLogModel.append({ txt: "[GEOFENCE] " + droneId + ": " + reason })
        }

        function onRtlTriggered(droneId, reason) {
            safetyLogModel.append({
                txt: "[BATTERY] RTL TRIGGERED: " + droneId + " - " + reason
            })
        }

        function onBatteryStatusChanged(status) {
            // Log warnings when battery is getting low
            if (status.shouldRtl && !status.rtlReason.includes("already triggered")) {
                safetyLogModel.append({
                    txt: "[BATTERY] " + status.droneId + ": " + status.batteryPct.toFixed(1) + "% - " + status.rtlReason
                })
            }
        }
    }

    Connections {
        target: swarm
        function onLogMessage(level, text) {
            if (level === "WARN" || level === "ERROR" || text.includes("safety") || text.includes("collision")) {
                safetyLogModel.append({ txt: "[" + level + "] " + text })
            }
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "../components" as Cmp

Item {
    id: root
    anchors.fill: parent

    // Multi-drone mission state lives in the AppState QML singleton — both
    // SwarmPanel and main.qml share the same instance, so toggling here is
    // immediately reflected on the Map-toolbar MISSION button (and vice-versa).

    // External (shared) waypoints model — injected from main.qml
    property var globalWaypoints: null
    property string selectedDroneId: Cmp.AppState.selectedDroneId
    // Local fallback used only when no global model is injected
    ListModel { id: localWaypoints }
    // Effective model
    readonly property var wps: globalWaypoints ? globalWaypoints : localWaypoints
    property var selectedSnap: ({})

    function refreshSelectedSnap() {
        selectedSnap = (selectedDroneId && typeof swarm !== "undefined" && swarm) ? swarm.droneSnapshot(selectedDroneId) : ({})
    }

    Timer {
        interval: 500
        running: true
        repeat: true
        onTriggered: root.refreshSelectedSnap()
    }

    onSelectedDroneIdChanged: refreshSelectedSnap()

    // ── Helper functions ──────────────────────────────────────────────────
    function _updateDistancePreview() {
        if (!selectedDroneId || !swarm) { distPreview.text = ""; return }
        var snap = swarm.droneSnapshot(selectedDroneId)
        if (!snap || !latField.text || !lonField.text) { distPreview.text = ""; return }
        var lat1 = snap.lat || 0, lon1 = snap.lon || 0
        var lat2 = parseFloat(latField.text), lon2 = parseFloat(lonField.text)
        if (lat1 === 0 || lat2 === 0 || isNaN(lat2) || isNaN(lon2)) { distPreview.text = ""; return }
        var R = 6371e3
        var φ1 = lat1 * Math.PI / 180, φ2 = lat2 * Math.PI / 180
        var Δφ = (lat2 - lat1) * Math.PI / 180, Δλ = (lon2 - lon1) * Math.PI / 180
        var a = Math.sin(Δφ/2)*Math.sin(Δφ/2) + Math.cos(φ1)*Math.cos(φ2)*Math.sin(Δλ/2)*Math.sin(Δλ/2)
        distPreview.text = qsTr("Distance: ") + (R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))).toFixed(0) + " m"
    }

    function setWaypointFromMap(lat, lon) {
        if (lat === 0 && lon === 0) return
        latField.text = lat.toFixed(6)
        lonField.text = lon.toFixed(6)
    }

    // ── Two-column horizontal layout ─────────────────────────────────────

        // ════════════════ LEFT COLUMN ════════════════
        ScrollView {
            id: leftScroll
            anchors { top: parent.top; left: parent.left; bottom: parent.bottom; margins: 12 }
            width: (parent.width - 34) * 0.38
            clip: true
            contentWidth: availableWidth
            contentHeight: leftCol.implicitHeight
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical.policy: ScrollBar.AsNeeded

            Column {
                id: leftCol
                width: leftScroll.availableWidth
                spacing: 8

                // ── DRONE AUSWAHL ─────────────────────────────────────────
                Text { text: qsTr("DRONE SELECTION"); color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width; height: selCol.implicitHeight + 20; radius: 8
                    color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                    Column {
                        id: selCol
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                        spacing: 8

                        // Drone selector ComboBox
                        ComboBox {
                            id: droneSelCombo; width: parent.width; height: 30
                            model: (typeof swarm !== "undefined" && swarm) ? swarm.droneIds() : []
                            background: Rectangle { color: "#1e2535"; radius: 5; border.color: "#2d3748"; border.width: 1 }
                            contentItem: Text {
                                text: droneSelCombo.displayText; color: "#e2e8f0"
                                font.pixelSize: 12; verticalAlignment: Text.AlignVCenter; leftPadding: 8
                            }
                            Connections {
                                target: swarm
                                function onDroneAdded()   { droneSelCombo.model = swarm.droneIds() }
                                function onDroneRemoved() { droneSelCombo.model = swarm.droneIds() }
                            }
                            onCurrentTextChanged: {
                                Cmp.AppState.selectedDroneId = currentText
                                root.refreshSelectedSnap()
                                if (currentText && typeof swarm !== "undefined" && swarm) {
                                    var snap = swarm.droneSnapshot(currentText)
                                    typeRow.currentType = (snap && snap.droneType) ? snap.droneType : "generic"
                                }
                            }
                        }

                        // Type buttons
                        Text { text: "TYP"; color: "#475569"; font.pixelSize: 8; font.weight: Font.Bold; font.letterSpacing: 1 }
                        Row {
                            id: typeRow
                            width: parent.width; spacing: 6
                            property string currentType: "generic"

                            Rectangle {
                                width: (parent.width - 6) / 2; height: 36; radius: 5
                                color: typeRow.currentType === "generic" ? "#1e3a5f" : "#1e2535"
                                border.color: typeRow.currentType === "generic" ? "#2563eb" : "#2d3748"; border.width: 1
                                Column {
                                    anchors.centerIn: parent; spacing: 1
                                    Row { anchors.horizontalCenter: parent.horizontalCenter; spacing: 4
                                            Cmp.Icon { name: "gear"; size: 11; color: typeRow.currentType === "generic" ? "#93c5fd" : "#64748b"; anchors.verticalCenter: parent.verticalCenter }
                                            Text { text: "Generic"; color: typeRow.currentType === "generic" ? "#93c5fd" : "#64748b"; font.pixelSize: 10; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                                        }
                                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: "FSM · Mission"; color: "#475569"; font.pixelSize: 7 }
                                }
                                MouseArea { anchors.fill: parent; onClicked: { typeRow.currentType = "generic"; if (droneSelCombo.currentText && typeof swarm !== "undefined") swarm.setDroneType(droneSelCombo.currentText, "generic") } }
                            }

                            Rectangle {
                                width: (parent.width - 6) / 2; height: 36; radius: 5
                                color: typeRow.currentType === "observation" ? "#1e3a5f" : "#1e2535"
                                border.color: typeRow.currentType === "observation" ? "#8b5cf6" : "#2d3748"; border.width: 1
                                Column {
                                    anchors.centerIn: parent; spacing: 1
                                    Row { anchors.horizontalCenter: parent.horizontalCenter; spacing: 4
                                            Cmp.Icon { name: "camera"; size: 11; color: typeRow.currentType === "observation" ? "#c4b5fd" : "#64748b"; anchors.verticalCenter: parent.verticalCenter }
                                            Text { text: "Obs."; color: typeRow.currentType === "observation" ? "#c4b5fd" : "#64748b"; font.pixelSize: 10; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                                        }
                                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Gimbal · ROS2"; color: "#475569"; font.pixelSize: 7 }
                                }
                                MouseArea { anchors.fill: parent; onClicked: { typeRow.currentType = "observation"; if (droneSelCombo.currentText && typeof swarm !== "undefined") swarm.setDroneType(droneSelCombo.currentText, "observation") } }
                            }
                        }
                    }
                }

                // ── CONNECTED DRONES ──────────────────────────────────────
                Row {
                    width: parent.width; spacing: 6
                    Text {
                        text: "CONNECTED DRONES"
                        color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Item { width: parent.width - 290; height: 1 }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: (Cmp.AppState.missionTargetCount > 0)
                              ? (Cmp.AppState.missionTargetCount + " selected for mission")
                              : "Checkbox = Multi-Mission Target"
                        color: Cmp.AppState.missionTargetCount > 0 ? "#22c55e" : "#475569"
                        font.pixelSize: 9; font.italic: true
                    }
                    Rectangle {
                        width: 70; height: 20; radius: 4
                        color: missClrM.containsMouse ? "#7f1d1d" : "#1e2535"
                        border.color: "#475569"; border.width: 1
                        anchors.verticalCenter: parent.verticalCenter
                        visible: Cmp.AppState.missionTargetCount > 0
                        Text { anchors.centerIn: parent; text: "CLEAR"; color: "#94a3b8"; font.pixelSize: 8; font.weight: Font.Bold }
                        MouseArea {
                            id: missClrM; anchors.fill: parent; hoverEnabled: true
                            onClicked: Cmp.AppState.clearMissionTargets()
                        }
                    }
                }

                ListView {
                    id: droneList
                    width: parent.width
                    height: Math.max(60, Math.min((telemetryModel ? telemetryModel.count : 0) * 56, 400))
                    model: telemetryModel ? telemetryModel : null
                    spacing: 5; clip: true

                    delegate: Rectangle {
                        id: droneRow
                        width: droneList.width; height: 50; radius: 8
                        property string _dtype: (typeof swarm !== "undefined" && swarm) ? swarm.droneType(model.droneId) : "generic"
                        property color _tcol: _dtype === "observation" ? "#8b5cf6" : "#2563eb"
                        // Re-evaluated on every missionTargetsChanged via the Connections below.
                        property bool _missionSel: Cmp.AppState.isMissionTarget(model.droneId)
                        Connections {
                            target: Cmp.AppState
                            function onMissionTargetsChanged() {
                                droneRow._missionSel = Cmp.AppState.isMissionTarget(model.droneId)
                            }
                        }
                        color: model.droneId === selectedDroneId
                            ? Qt.rgba(Qt.color(_tcol).r, Qt.color(_tcol).g, Qt.color(_tcol).b, 0.13)
                            : (_missionSel ? "#0c2818" : "#1a2035")
                        border.color: model.droneId === selectedDroneId ? _tcol : (_missionSel ? "#22c55e" : "#2d3748")
                        border.width: (model.droneId === selectedDroneId || _missionSel) ? 2 : 1

                        // ── Mission-target checkbox (left edge) ──
                        Rectangle {
                            id: missCb
                            width: 20; height: 20; radius: 4
                            anchors { left: parent.left; leftMargin: 8; verticalCenter: parent.verticalCenter }
                            color: parent._missionSel ? "#16a34a" : "#0d1117"
                            border.color: parent._missionSel ? "#22c55e" : "#475569"; border.width: 1
                            Cmp.Icon {
                                anchors.centerIn: parent
                                name: "check"; size: 14; color: "white"
                                visible: missCb.parent._missionSel
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: Cmp.AppState.toggleMissionTarget(model.droneId)
                            }
                        }

                        // ── Row click area (excluding checkbox) → selectDrone ──
                        MouseArea {
                            anchors { left: missCb.right; leftMargin: 4; top: parent.top; right: parent.right; bottom: parent.bottom }
                            onClicked: {
                                Cmp.AppState.selectedDroneId = model.droneId
                                droneSelCombo.currentIndex = droneSelCombo.model.indexOf(model.droneId)
                                root.refreshSelectedSnap()
                            }
                        }

                        Column {
                            anchors { left: missCb.right; right: parent.right; leftMargin: 8; rightMargin: 8; verticalCenter: parent.verticalCenter }
                            spacing: 3

                            Row {
                                spacing: 6
                                Rectangle { width: 8; height: 8; radius: 4; color: parent.parent.parent._tcol; anchors.verticalCenter: parent.verticalCenter }
                                Row { spacing: 4; anchors.verticalCenter: parent.verticalCenter
                                                Cmp.Icon { name: parent.parent.parent.parent._dtype === "observation" ? "camera" : "gear"; size: 10; color: "#94a3b8"; anchors.verticalCenter: parent.verticalCenter }
                                                Text { text: model.droneId + (model.droneId === selectedDroneId ? " ✓" : ""); color: "#e2e8f0"; font.pixelSize: 11; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                                            }
                            }

                            Text {
                                width: parent.width
                                text: (model.connected ? "" : "⚠ OFFLINE  ") + (model.armed ? "ARM · " : "") + model.flightMode + " | " + model.altRel.toFixed(1) + "m"
                                color: model.connected ? "#64748b" : "#ef4444"; font.pixelSize: 9
                                elide: Text.ElideRight
                            }

                            Row {
                                spacing: 4
                                Rectangle {
                                    width: 56; height: 20; radius: 3
                                    color: dcM.containsMouse ? (model.connected ? "#7f1d1d" : "#14532d") : "#0d1117"
                                    border.color: model.connected ? "#66ef4444" : "#6622c55e"; border.width: 1
                                    Text { anchors.centerIn: parent; text: model.connected ? "⏏ Disc" : "⟳ Conn"; color: model.connected ? "#ef4444" : "#22c55e"; font.pixelSize: 8; font.weight: Font.Bold }
                                    MouseArea { id: dcM; anchors.fill: parent; hoverEnabled: true; onClicked: model.connected ? swarm.disconnectDrone(model.droneId) : swarm.reconnectDrone(model.droneId) }
                                }
                                Rectangle {
                                    width: 20; height: 20; radius: 3
                                    color: rmM.containsMouse ? "#7f1d1d" : "#0d1117"
                                    Text { anchors.centerIn: parent; text: "✕"; color: "#64748b"; font.pixelSize: 9 }
                                    MouseArea { id: rmM; anchors.fill: parent; hoverEnabled: true; onClicked: swarm.removeDrone(model.droneId) }
                                }
                            }
                        }
                    }

                    Text { anchors.centerIn: parent; text: qsTr("No drones connected"); color: "#374151"; font.pixelSize: 10; visible: !telemetryModel || telemetryModel.count === 0 }
                }

                Text { text: "SYSTEM INFO"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width
                    height: sysInfoCol.implicitHeight + 24
                    radius: 8
                    color: "#1a2035"
                    border.color: "#2d3748"
                    border.width: 1

                    Column {
                        id: sysInfoCol
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
                        spacing: 12

                        // Header with drone name and status
                        Rectangle {
                            width: parent.width
                            height: 44
                            radius: 6
                            color: (root.selectedSnap && root.selectedSnap.connected) ? "#0f2d1a" : "#2d1a1a"
                            border.color: (root.selectedSnap && root.selectedSnap.connected) ? "#22c55e" : "#ef4444"
                            border.width: 1

                            Row {
                                anchors { fill: parent; margins: 10 }
                                spacing: 10

                                Rectangle {
                                    width: 24; height: 24; radius: 12
                                    color: (root.selectedSnap && root.selectedSnap.connected) ? "#22c55e" : "#ef4444"
                                    anchors.verticalCenter: parent.verticalCenter

                                    Text {
                                        anchors.centerIn: parent
                                        text: (root.selectedSnap && root.selectedSnap.connected) ? "✓" : "✕"
                                        color: "white"
                                        font.pixelSize: 14
                                        font.weight: Font.Bold
                                    }
                                }

                                Column {
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 2

                                    Text {
                                        text: selectedDroneId || "No drone selected"
                                        color: selectedDroneId ? "#e2e8f0" : "#64748b"
                                        font.pixelSize: 13
                                        font.weight: Font.Bold
                                    }

                                    Text {
                                        text: (root.selectedSnap && root.selectedSnap.connected) ? "Connected" : "Disconnected"
                                        color: (root.selectedSnap && root.selectedSnap.connected) ? "#22c55e" : "#ef4444"
                                        font.pixelSize: 9
                                    }
                                }
                            }
                        }

                        // Autopilot Section
                        Column {
                            width: parent.width
                            spacing: 8

                            Text {
                                text: "AUTOPILOT"
                                color: "#64748b"
                                font.pixelSize: 8
                                font.weight: Font.Bold
                                font.letterSpacing: 1
                            }

                            Rectangle {
                                width: parent.width
                                height: autopilotGrid.implicitHeight + 16
                                radius: 6
                                color: "#0d1117"
                                border.color: "#1e2535"
                                border.width: 1

                                GridLayout {
                                    id: autopilotGrid
                                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: 8 }
                                    columns: 2
                                    columnSpacing: 12
                                    rowSpacing: 8

                                    Repeater {
                                        model: [
                                            ["Autopilot", root.selectedSnap.autopilot || "—", "#2563eb"],
                                            ["Vehicle", root.selectedSnap.vehicle_type || "—", "#8b5cf6"],
                                            ["Firmware", root.selectedSnap.firmware_version || "—", "#06b6d4"],
                                            ["Board", root.selectedSnap.board_version || "—", "#10b981"]
                                        ]
                                        delegate: Column {
                                            Layout.fillWidth: true
                                            spacing: 3

                                            Text {
                                                text: modelData[0]
                                                color: "#64748b"
                                                font.pixelSize: 8
                                                font.weight: Font.Bold
                                            }

                                            Text {
                                                width: parent.width
                                                text: modelData[1]
                                                color: modelData[1] === "—" ? "#475569" : "#e2e8f0"
                                                font.pixelSize: 10
                                                elide: Text.ElideRight
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // Status Section
                        Column {
                            width: parent.width
                            spacing: 8

                            Text {
                                text: "STATUS"
                                color: "#64748b"
                                font.pixelSize: 8
                                font.weight: Font.Bold
                                font.letterSpacing: 1
                            }

                            Rectangle {
                                width: parent.width
                                height: statusGrid.implicitHeight + 16
                                radius: 6
                                color: "#0d1117"
                                border.color: "#1e2535"
                                border.width: 1

                                GridLayout {
                                    id: statusGrid
                                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: 8 }
                                    columns: 2
                                    columnSpacing: 12
                                    rowSpacing: 8

                                    Repeater {
                                        model: [
                                            ["System", root.selectedSnap.system_status !== undefined ? root.selectedSnap.system_status : "—"],
                                            ["Flight Mode", root.selectedSnap.flight_mode || "—"],
                                            ["FSM State", root.selectedSnap.fsmState || "—"],
                                            ["Drone Type", root.selectedSnap.droneType || "generic"]
                                        ]
                                        delegate: Column {
                                            Layout.fillWidth: true
                                            spacing: 3

                                            Text {
                                                text: modelData[0]
                                                color: "#64748b"
                                                font.pixelSize: 8
                                                font.weight: Font.Bold
                                            }

                                            Text {
                                                width: parent.width
                                                text: modelData[1]
                                                color: "#e2e8f0"
                                                font.pixelSize: 10
                                                elide: Text.ElideRight
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // Connection Section
                        Column {
                            width: parent.width
                            spacing: 8

                            Text {
                                text: "CONNECTION"
                                color: "#64748b"
                                font.pixelSize: 8
                                font.weight: Font.Bold
                                font.letterSpacing: 1
                            }

                            Rectangle {
                                width: parent.width
                                height: connCol.implicitHeight + 16
                                radius: 6
                                color: "#0d1117"
                                border.color: "#1e2535"
                                border.width: 1

                                Column {
                                    id: connCol
                                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: 8 }
                                    spacing: 6

                                    Column {
                                        width: parent.width
                                        spacing: 3

                                        Text {
                                            text: "Connection String"
                                            color: "#64748b"
                                            font.pixelSize: 8
                                            font.weight: Font.Bold
                                        }

                                        Text {
                                            width: parent.width
                                            text: root.selectedSnap.connectionString || "—"
                                            color: "#e2e8f0"
                                            font.pixelSize: 9
                                            font.family: "Consolas"
                                            wrapMode: Text.WrapAnywhere
                                        }
                                    }

                                    Row {
                                        width: parent.width
                                        spacing: 12

                                        Column {
                                            width: (parent.width - 12) / 2
                                            spacing: 3

                                            Text {
                                                text: "Vendor ID"
                                                color: "#64748b"
                                                font.pixelSize: 8
                                                font.weight: Font.Bold
                                            }

                                            Text {
                                                text: String(root.selectedSnap.vendor_id || 0)
                                                color: "#e2e8f0"
                                                font.pixelSize: 10
                                            }
                                        }

                                        Column {
                                            width: (parent.width - 12) / 2
                                            spacing: 3

                                            Text {
                                                text: "Product ID"
                                                color: "#64748b"
                                                font.pixelSize: 8
                                                font.weight: Font.Bold
                                            }

                                            Text {
                                                text: String(root.selectedSnap.product_id || 0)
                                                color: "#e2e8f0"
                                                font.pixelSize: 10
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // Info Note
                        Rectangle {
                            width: parent.width
                            height: noteText.implicitHeight + 12
                            radius: 4
                            color: "#1e3a5f"
                            border.color: "#2563eb"
                            border.width: 1

                            Text {
                                id: noteText
                                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 6 }
                                text: "ℹ Firmware/Board info appears after AUTOPILOT_VERSION response"
                                color: "#93c5fd"
                                font.pixelSize: 8
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
        }

        // ════════════════ RIGHT COLUMN ════════════════
        ScrollView {
            id: rightScroll
            anchors { top: parent.top; left: leftScroll.right; right: parent.right; bottom: parent.bottom; topMargin: 12; leftMargin: 10; rightMargin: 12; bottomMargin: 12 }
            clip: true
            contentWidth: availableWidth
            contentHeight: rightCol.implicitHeight
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical.policy: ScrollBar.AsNeeded

            Column {
                id: rightCol
                width: rightScroll.availableWidth
                spacing: 8

                // ── SWARM BEFEHLE ─────────────────────────────────────────
                Text { text: "SWARM BEFEHLE"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width; height: swarmCmdCol.implicitHeight + 20; radius: 8
                    color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                    Column {
                        id: swarmCmdCol
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                        spacing: 8

                        // ARM / DISARM ALL
                        Row {
                            width: parent.width; spacing: 6
                            Rectangle {
                                width: (parent.width - 6) / 2; height: 34; radius: 6
                                color: armAllM.containsMouse ? "#15803d" : "#166534"
                                border.color: "#22c55e"; border.width: 1
                                Row { anchors.centerIn: parent; spacing: 5
                                    Text { text: "▶"; color: "#22c55e"; font.pixelSize: 13 }
                                    Text { text: "ARM ALL"; color: "#22c55e"; font.pixelSize: 10; font.weight: Font.Bold }
                                }
                                MouseArea { id: armAllM; anchors.fill: parent; hoverEnabled: true; onClicked: if (swarm) swarm.armAll() }
                            }
                            Rectangle {
                                width: (parent.width - 6) / 2; height: 34; radius: 6
                                color: disarmAllM.containsMouse ? "#7f1d1d" : "#450a0a"
                                border.color: "#ef4444"; border.width: 1
                                Row { anchors.centerIn: parent; spacing: 5
                                    Text { text: "■"; color: "#ef4444"; font.pixelSize: 13 }
                                    Text { text: "DISARM ALL"; color: "#ef4444"; font.pixelSize: 10; font.weight: Font.Bold }
                                }
                                MouseArea { id: disarmAllM; anchors.fill: parent; hoverEnabled: true; onClicked: if (swarm) swarm.disarmAll() }
                            }
                        }

                        // TAKEOFF ALL
                        Row {
                            width: parent.width; spacing: 6
                            Column {
                                width: parent.width - 90 - 6; spacing: 2
                                Text { text: qsTr("Takeoff Alt (m)"); color: "#64748b"; font.pixelSize: 9 }
                                TextField {
                                    id: swarmTakeoffAlt; width: parent.width; height: 28; text: "10"
                                    background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748"; border.width: 1 }
                                    color: "#e2e8f0"; font.pixelSize: 11; font.family: "Consolas"; leftPadding: 8
                                }
                            }
                            Rectangle {
                                width: 90; height: 44; radius: 6; anchors.bottom: parent.bottom
                                color: takeoffAllM.containsMouse ? "#1d4ed8" : "#1e3a5f"
                                border.color: "#2563eb"; border.width: 1
                                Column { anchors.centerIn: parent; spacing: 2
                                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: "⬆"; color: "#93c5fd"; font.pixelSize: 14 }
                                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: "TAKEOFF ALL"; color: "#93c5fd"; font.pixelSize: 8; font.weight: Font.Bold }
                                }
                                MouseArea { id: takeoffAllM; anchors.fill: parent; hoverEnabled: true; onClicked: if (swarm) swarm.takeoffAll(parseFloat(swarmTakeoffAlt.text) || 10) }
                            }
                        }

                        // LAND / RTL ALL
                        Row {
                            width: parent.width; spacing: 6
                            Rectangle {
                                width: (parent.width - 6) / 2; height: 34; radius: 6
                                color: landAllM.containsMouse ? "#78350f" : "#431407"
                                border.color: "#f97316"; border.width: 1
                                Row { anchors.centerIn: parent; spacing: 5
                                    Text { text: "⬇"; color: "#f97316"; font.pixelSize: 13 }
                                    Text { text: "LAND ALL"; color: "#f97316"; font.pixelSize: 10; font.weight: Font.Bold }
                                }
                                MouseArea { id: landAllM; anchors.fill: parent; hoverEnabled: true; onClicked: if (swarm) swarm.landAll() }
                            }
                            Rectangle {
                                width: (parent.width - 6) / 2; height: 34; radius: 6
                                color: rtlAllM.containsMouse ? "#4c1d95" : "#2e1065"
                                border.color: "#a78bfa"; border.width: 1
                                Row { anchors.centerIn: parent; spacing: 5
                                    Cmp.Icon { name: "home"; size: 13; color: "#94a3b8" }
                                    Text { text: "RTL ALL"; color: "#a78bfa"; font.pixelSize: 10; font.weight: Font.Bold }
                                }
                                MouseArea { id: rtlAllM; anchors.fill: parent; hoverEnabled: true; onClicked: if (swarm) swarm.rtlAll() }
                            }
                        }

                        // MODE ALL
                        Text { text: qsTr("FLIGHT MODE (ALL)"); color: "#475569"; font.pixelSize: 8; font.weight: Font.Bold; font.letterSpacing: 1 }
                        Flow {
                            width: parent.width; spacing: 4
                            Repeater {
                                model: ["STABILIZE", "ALT_HOLD", "LOITER", "AUTO", "GUIDED", "POSCTL", "OFFBOARD", "HOLD"]
                                delegate: Rectangle {
                                    height: 26; radius: 4
                                    width: modeLabel.implicitWidth + 16
                                    color: modeAllMA.containsMouse ? "#1e3a5f" : "#1a2035"
                                    border.color: "#2563eb"; border.width: 1
                                    Text {
                                        id: modeLabel
                                        anchors.centerIn: parent
                                        text: modelData; color: "#93c5fd"; font.pixelSize: 9; font.weight: Font.Bold
                                    }
                                    MouseArea { id: modeAllMA; anchors.fill: parent; hoverEnabled: true; onClicked: if (swarm) swarm.setModeAll(modelData) }
                                }
                            }
                        }
                    }
                }

                // ── WAYPOINT / GOTO ───────────────────────────────────────
                Text { text: qsTr("WAYPOINT / GOTO"); color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width; height: gotoCol.implicitHeight + 20; radius: 8
                    color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                    Column {
                        id: gotoCol
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                        spacing: 6

                        // Target drone indicator with mode selector
                        Rectangle {
                            width: parent.width; height: wpModeCol.implicitHeight + 12; radius: 5
                            color: "#1e2535"
                            border.color: "#334155"; border.width: 1
                            
                            Column {
                                id: wpModeCol
                                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 6 }
                                spacing: 6
                                
                                // Mode selector
                                Row {
                                    width: parent.width; spacing: 4
                                    
                                    Rectangle {
                                        width: (parent.width - 4) / 2; height: 28; radius: 4
                                        color: !wpMultiMode.checked ? "#1e3a5f" : "#1e2535"
                                        border.color: !wpMultiMode.checked ? "#2563eb" : "#334155"; border.width: 1
                                        Row {
                                            anchors.centerIn: parent; spacing: 4
                                            Cmp.Icon { name: "user"; size: 10; color: !wpMultiMode.checked ? "#93c5fd" : "#64748b" }
                                            Text {
                                                text: "Single Drone"
                                                color: !wpMultiMode.checked ? "#93c5fd" : "#64748b"
                                                font.pixelSize: 9; font.weight: Font.Bold
                                            }
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            onClicked: wpMultiMode.checked = false
                                        }
                                    }
                                    
                                    Rectangle {
                                        width: (parent.width - 4) / 2; height: 28; radius: 4
                                        color: wpMultiMode.checked ? "#1e3a5f" : "#1e2535"
                                        border.color: wpMultiMode.checked ? "#2563eb" : "#334155"; border.width: 1
                                        Row {
                                            anchors.centerIn: parent; spacing: 4
                                            Cmp.Icon { name: "users"; size: 10; color: wpMultiMode.checked ? "#93c5fd" : "#64748b" }
                                            Text {
                                                text: "Multi-Drone"
                                                color: wpMultiMode.checked ? "#93c5fd" : "#64748b"
                                                font.pixelSize: 9; font.weight: Font.Bold
                                            }
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            onClicked: wpMultiMode.checked = true
                                        }
                                    }
                                    
                                    CheckBox {
                                        id: wpMultiMode
                                        visible: false
                                        checked: false
                                    }
                                }
                                
                                // Target indicator
                                Rectangle {
                                    width: parent.width; height: 24; radius: 4
                                    property var _targets: wpMultiMode.checked ? Cmp.AppState.effectiveMissionTargets() : (selectedDroneId ? [selectedDroneId] : [])
                                    property bool _hasTarget: _targets.length > 0
                                    color: _hasTarget ? "#0f2d1a" : "#1a1a1a"
                                    border.color: _hasTarget ? "#22c55e" : "#374151"; border.width: 1
                                    Row {
                                        anchors { fill: parent; leftMargin: 8 }
                                        spacing: 6
                                        Cmp.Icon {
                                            name: parent.parent._targets.length > 1 ? "users" : "target"
                                            size: 10
                                            color: parent.parent._hasTarget ? "#22c55e" : "#475569"
                                            anchors.verticalCenter: parent.verticalCenter
                                        }
                                        Text {
                                            text: {
                                                var t = parent.parent._targets
                                                if (t.length === 0) return "No target selected"
                                                if (t.length === 1) return t[0]
                                                return t.length + " drones selected"
                                            }
                                            color: parent.parent._hasTarget ? "#22c55e" : "#475569"
                                            font.pixelSize: 10; font.weight: Font.Bold
                                            anchors.verticalCenter: parent.verticalCenter
                                        }
                                    }
                                }
                            }
                        }

                        // Lat / Lon / Alt in one row
                        Row {
                            width: parent.width; spacing: 4

                            Column {
                                width: (parent.width - 8) / 3; spacing: 2
                                Text { text: "Lat"; color: "#64748b"; font.pixelSize: 9 }
                                TextField {
                                    id: latField; width: parent.width; height: 26; text: ""
                                    placeholderText: "52.5200"
                                    background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748"; border.width: 1 }
                                    color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"
                                    onTextChanged: root._updateDistancePreview()
                                }
                            }
                            Column {
                                width: (parent.width - 8) / 3; spacing: 2
                                Text { text: "Lon"; color: "#64748b"; font.pixelSize: 9 }
                                TextField {
                                    id: lonField; width: parent.width; height: 26; text: ""
                                    placeholderText: "13.4050"
                                    background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748"; border.width: 1 }
                                    color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"
                                    onTextChanged: root._updateDistancePreview()
                                }
                            }
                            Column {
                                width: (parent.width - 8) / 3; spacing: 2
                                Text { text: "Alt (m)"; color: "#64748b"; font.pixelSize: 9 }
                                TextField {
                                    id: altGotoField; width: parent.width; height: 26; text: "10"
                                    background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748"; border.width: 1 }
                                    color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"
                                }
                            }
                        }

                        Text { id: distPreview; text: ""; color: "#94a3b8"; font.pixelSize: 9; visible: text !== "" }

                        // Buttons row
                        Flow {
                            width: parent.width; spacing: 4

                            // Add WP Button - Opens map in waypoint mode
                            Rectangle {
                                width: 100; height: 28; radius: 5
                                property var _targets: wpMultiMode.checked ? Cmp.AppState.effectiveMissionTargets() : (selectedDroneId ? [selectedDroneId] : [])
                                property bool _hasTarget: _targets.length > 0
                                color: !_hasTarget ? "#0d1117" : (addWpM.containsMouse ? "#1e3a5f" : "#1e2535")
                                border.color: _hasTarget ? "#2563eb" : "#374151"; border.width: 1
                                Row {
                                    anchors.centerIn: parent; spacing: 4
                                    Cmp.Icon {
                                        name: "plus"
                                        size: 11
                                        color: parent.parent._hasTarget ? "#2563eb" : "#374151"
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                    Text {
                                        text: parent.parent._targets.length > 1 ? ("Add WP (" + parent.parent._targets.length + ")") : "Add WP"
                                        color: parent.parent._hasTarget ? "#2563eb" : "#374151"
                                        font.pixelSize: 9
                                        font.weight: Font.Bold
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }
                                MouseArea {
                                    id: addWpM
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    enabled: parent._hasTarget
                                    onClicked: {
                                        // Switch to map and enable waypoint mode
                                        if (root.mainWindow) {
                                            root.mainWindow.mapWaypointMode = true
                                            root.mainWindow.selectTab(0)  // Switch to Map tab
                                            if (root.mainWindow.mapLoader.item) {
                                                root.mainWindow.mapLoader.item.setPickMode(true)
                                            }
                                        }
                                    }
                                }
                            }
                            
                            // GOTO Button - Flies to coordinates
                            Rectangle {
                                width: 90; height: 28; radius: 5
                                property var _targets: Cmp.AppState.effectiveMissionTargets()
                                property bool _hasTarget: _targets.length > 0
                                color: !_hasTarget ? "#0d1117" : gotoBtnM.containsMouse ? "#15803d" : "#22c55e"
                                Row { anchors.centerIn: parent; spacing: 4
                                        Cmp.Icon { name: "target"; size: 11; color: parent.parent._hasTarget ? "white" : "#374151"; anchors.verticalCenter: parent.verticalCenter }
                                        Text {
                                            text: parent.parent._targets.length > 1
                                                  ? "GOTO (" + parent.parent._targets.length + ")"
                                                  : "GOTO"
                                            color: parent.parent._hasTarget ? "white" : "#374151"
                                            font.pixelSize: 9; font.weight: Font.Bold
                                            anchors.verticalCenter: parent.verticalCenter
                                        }
                                    }
                                MouseArea {
                                    id: gotoBtnM; anchors.fill: parent; hoverEnabled: true
                                    enabled: parent._hasTarget
                                    onClicked: {
                                        if (!latField.text || !lonField.text) return
                                        var lat = parseFloat(latField.text)
                                        var lon = parseFloat(lonField.text)
                                        var alt = parseFloat(altGotoField.text) || 10
                                        var ids = parent._targets
                                        for (var i = 0; i < ids.length; i++) {
                                            var did = ids[i]
                                            var snap = swarm.droneSnapshot(did)
                                            var armed = snap ? (snap.armed || false) : false
                                            if (armed)
                                                swarm.gotoDrone(did, lat, lon, alt)
                                            else
                                                swarm.smartGotoDrone(did, lat, lon, alt)
                                        }
                                    }
                                }
                            }
                            Rectangle {
                                width: 60; height: 28; radius: 5
                                property var _targets: wpMultiMode.checked ? Cmp.AppState.effectiveMissionTargets() : (selectedDroneId ? [selectedDroneId] : [])
                                color: clearWpM.containsMouse ? "#7f1d1d" : "#1e2535"
                                Row { anchors.centerIn: parent; spacing: 4
                                        Cmp.Icon { name: "trash"; size: 11; color: "#ef4444"; anchors.verticalCenter: parent.verticalCenter }
                                        Text { text: "Clear"; color: "#ef4444"; font.pixelSize: 9; anchors.verticalCenter: parent.verticalCenter }
                                    }
                                MouseArea {
                                    id: clearWpM
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onClicked: {
                                        root.wps.clear()
                                        var targets = parent._targets
                                        for (var i = 0; i < targets.length; i++) {
                                            Cmp.AppState.clearWaypoints(targets[i])
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // ── MISSION WAYPOINTS ─────────────────────────────────────
                Text { text: qsTr("MISSION WAYPOINTS"); color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width
                    height: Math.max(64, Math.min(root.wps.count * 32 + 16, 200))
                    radius: 8; color: "#0d1117"; border.color: "#2d3748"; border.width: 1

                    ListView {
                        id: waypointList
                        anchors { fill: parent; margins: 8 }
                        model: root.wps
                        spacing: 3; clip: true

                        delegate: Rectangle {
                            width: ListView.view.width; height: 28; radius: 4
                            color: "#1e2535"; border.color: "#2d3748"; border.width: 1
                            Row {
                                anchors { fill: parent; leftMargin: 6; rightMargin: 6 }
                                spacing: 6
                                Text { text: (index+1)+"."; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter; width: 16 }
                                Text { text: model.lat.toFixed(5)+", "+model.lon.toFixed(5)+" @"+model.alt+"m"; color: "#e2e8f0"; font.pixelSize: 9; font.family: "Consolas"; anchors.verticalCenter: parent.verticalCenter }
                                Item { width: parent.width - 180; height: 1 }
                                Rectangle { width: 20; height: 20; radius: 3; visible: index > 0; color: upM.containsMouse ? "#2563eb" : "#1a2035"
                                    Text { anchors.centerIn: parent; text: "↑"; color: "#2563eb"; font.pixelSize: 10 }
                                    MouseArea { id: upM; anchors.fill: parent; hoverEnabled: true; onClicked: if (index > 0) root.wps.move(index, index-1, 1) }
                                }
                                Rectangle { width: 20; height: 20; radius: 3; visible: index < root.wps.count-1; color: downM.containsMouse ? "#2563eb" : "#1a2035"
                                    Text { anchors.centerIn: parent; text: "↓"; color: "#2563eb"; font.pixelSize: 10 }
                                    MouseArea { id: downM; anchors.fill: parent; hoverEnabled: true; onClicked: if (index < root.wps.count-1) root.wps.move(index, index+1, 1) }
                                }
                                Rectangle { width: 20; height: 20; radius: 3; color: rmWpM.containsMouse ? "#dc2626" : "#1a2035"
                                    Text { anchors.centerIn: parent; text: "×"; color: "#ef4444"; font.pixelSize: 12 }
                                    MouseArea { id: rmWpM; anchors.fill: parent; hoverEnabled: true; onClicked: root.wps.remove(index) }
                                }
                            }
                        }
                    }
                    Text { anchors.centerIn: parent; text: qsTr("No waypoints"); color: "#374151"; font.pixelSize: 10; visible: root.wps.count === 0 }
                }

                // Start Mission button — supports multi-drone target
                Rectangle {
                    width: parent.width; height: 32; radius: 6
                    visible: root.wps.count > 0
                    property int _nTargets: Cmp.AppState.missionTargetCount > 0
                                            ? Cmp.AppState.missionTargetCount
                                            : (selectedDroneId ? 1 : 0)
                    property bool _enabled: _nTargets > 0
                    color: !_enabled ? "#0d1117" : startMissionM.containsMouse ? "#15803d" : "#22c55e"
                    Row {
                        anchors.centerIn: parent; spacing: 6
                        Cmp.Icon { name: "play"; size: 12; color: parent.parent._enabled ? "white" : "#374151"; anchors.verticalCenter: parent.verticalCenter }
                        Text {
                            text: qsTr("Start Mission") + " (" + root.wps.count + " WP" + (parent.parent._nTargets > 1 ? " · " + parent.parent._nTargets + qsTr(" drones") : "") + ")"
                            color: parent.parent._enabled ? "white" : "#374151"
                            font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 0.5
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                    MouseArea {
                        id: startMissionM; anchors.fill: parent; hoverEnabled: true
                        enabled: parent._enabled
                        onClicked: {
                            if (!swarm || root.wps.count === 0) return
                            var arr = []
                            for (var i = 0; i < root.wps.count; i++) { var wp = root.wps.get(i); arr.push({lat: wp.lat, lon: wp.lon, alt: wp.alt}) }
                            var ids = Cmp.AppState.effectiveMissionTargets()
                            if (ids.length === 0) return
                            swarm.runMissionMulti(JSON.stringify(ids), JSON.stringify(arr))
                            Cmp.AppState.clearMissionTargets()
                        }
                    }
                }
                // ── DISTRIBUTED TASK ALLOCATION ───────────────────────────
                Text { text: "DISTRIBUTED TASK ALLOCATION"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width; height: taskAllocCol.implicitHeight + 20; radius: 8
                    color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                    Column {
                        id: taskAllocCol
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                        spacing: 10

                        // Enable/Disable Toggle
                        Row {
                            spacing: 12
                            width: parent.width

                            Rectangle {
                                width: 140; height: 36; radius: 6
                                color: escape && escape.taskAllocationEnabled ? "#15803d" : (taskAllocToggleM.containsMouse ? "#1e3a5f" : "#1e2535")
                                border.color: escape && escape.taskAllocationEnabled ? "#22c55e" : "#2563eb"
                                border.width: 1

                                Row {
                                    anchors.centerIn: parent
                                    spacing: 6

                                    Rectangle {
                                        width: 8; height: 8; radius: 4
                                        color: escape && escape.taskAllocationEnabled ? "#22c55e" : "#64748b"
                                        anchors.verticalCenter: parent.verticalCenter
                                    }

                                    Text {
                                        text: escape && escape.taskAllocationEnabled ? "ENABLED" : "DISABLED"
                                        color: "#e2e8f0"
                                        font.pixelSize: 11
                                        font.weight: Font.Bold
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }

                                MouseArea {
                                    id: taskAllocToggleM
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onClicked: {
                                        if (escape) {
                                            escape.taskAllocationEnabled = !escape.taskAllocationEnabled
                                        }
                                    }
                                }
                            }

                            Text {
                                text: escape && escape.taskCount > 0
                                      ? escape.taskCount + " task(s) allocated"
                                      : "No tasks allocated"
                                color: escape && escape.taskCount > 0 ? "#22c55e" : "#64748b"
                                font.pixelSize: 10
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        // Info Text
                        Text {
                            text: "Auction-based task allocation for swarm coordination.\nDrones bid on tasks based on distance, battery, and workload."
                            color: "#64748b"
                            font.pixelSize: 9
                            wrapMode: Text.WordWrap
                            width: parent.width
                        }

                        // Task Announcement
                        Rectangle {
                            width: parent.width
                            height: announceCol.implicitHeight + 16
                            radius: 6
                            color: "#0d1117"
                            border.color: "#2d3748"
                            border.width: 1
                            visible: escape && escape.taskAllocationEnabled

                            Column {
                                id: announceCol
                                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 8 }
                                spacing: 8

                                Text {
                                    text: "Announce New Task"
                                    color: "#94a3b8"
                                    font.pixelSize: 10
                                    font.weight: Font.Bold
                                }

                                GridLayout {
                                    width: parent.width
                                    columns: 2
                                    columnSpacing: 8
                                    rowSpacing: 6

                                    Text { text: "Task ID"; color: "#94a3b8"; font.pixelSize: 9 }
                                    TextField {
                                        id: taskIdField
                                        Layout.fillWidth: true
                                        height: 28
                                        placeholderText: "e.g., TASK_001"
                                        color: "#e2e8f0"
                                        font.pixelSize: 10
                                        background: Rectangle {
                                            color: "#1e2535"
                                            radius: 4
                                            border.color: "#2d3748"
                                            border.width: 1
                                        }
                                    }

                                    Text { text: "Position X"; color: "#94a3b8"; font.pixelSize: 9 }
                                    TextField {
                                        id: taskXField
                                        Layout.fillWidth: true
                                        height: 28
                                        placeholderText: "meters"
                                        color: "#e2e8f0"
                                        font.pixelSize: 10
                                        background: Rectangle {
                                            color: "#1e2535"
                                            radius: 4
                                            border.color: "#2d3748"
                                            border.width: 1
                                        }
                                    }

                                    Text { text: "Position Y"; color: "#94a3b8"; font.pixelSize: 9 }
                                    TextField {
                                        id: taskYField
                                        Layout.fillWidth: true
                                        height: 28
                                        placeholderText: "meters"
                                        color: "#e2e8f0"
                                        font.pixelSize: 10
                                        background: Rectangle {
                                            color: "#1e2535"
                                            radius: 4
                                            border.color: "#2d3748"
                                            border.width: 1
                                        }
                                    }

                                    Text { text: "Position Z"; color: "#94a3b8"; font.pixelSize: 9 }
                                    TextField {
                                        id: taskZField
                                        Layout.fillWidth: true
                                        height: 28
                                        placeholderText: "meters"
                                        color: "#e2e8f0"
                                        font.pixelSize: 10
                                        background: Rectangle {
                                            color: "#1e2535"
                                            radius: 4
                                            border.color: "#2d3748"
                                            border.width: 1
                                        }
                                    }
                                }

                                Rectangle {
                                    width: 120; height: 32; radius: 6
                                    color: announceTaskM.containsMouse ? "#3b82f6" : "#1e2535"
                                    border.color: "#3b82f6"
                                    border.width: 1

                                    Text {
                                        anchors.centerIn: parent
                                        text: "Announce Task"
                                        color: "#3b82f6"
                                        font.pixelSize: 11
                                    }

                                    MouseArea {
                                        id: announceTaskM
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: {
                                            if (escape && taskIdField.text && taskXField.text && taskYField.text && taskZField.text) {
                                                escape.announceTask(
                                                    taskIdField.text,
                                                    parseFloat(taskXField.text),
                                                    parseFloat(taskYField.text),
                                                    parseFloat(taskZField.text)
                                                )
                                                taskIdField.text = ""
                                                taskXField.text = ""
                                                taskYField.text = ""
                                                taskZField.text = ""
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // Allocated Tasks List
                        Rectangle {
                            width: parent.width
                            height: 120
                            radius: 6
                            color: "#0d1117"
                            border.color: "#2d3748"
                            border.width: 1
                            visible: escape && escape.taskAllocationEnabled

                            ListView {
                                id: tasksList
                                anchors { fill: parent; margins: 8 }
                                model: escape ? escape.tasks : []
                                clip: true
                                delegate: Column {
                                    spacing: 4
                                    width: tasksList.width

                                    Row {
                                        spacing: 12
                                        width: parent.width

                                        Rectangle {
                                            width: 6; height: 6; radius: 3
                                            color: modelData.status === "allocated" ? "#22c55e" : 
                                                   modelData.status === "bidding" ? "#f59e0b" : "#64748b"
                                            anchors.verticalCenter: parent.verticalCenter
                                        }

                                        Text {
                                            text: modelData.taskId
                                            color: "#3b82f6"
                                            font.pixelSize: 10
                                            font.weight: Font.Bold
                                            width: 80
                                        }

                                        Text {
                                            text: "→ " + (modelData.assignedDrone || "Unassigned")
                                            color: modelData.assignedDrone ? "#22c55e" : "#64748b"
                                            font.pixelSize: 10
                                            width: 100
                                        }

                                        Text {
                                            text: "(" + modelData.x.toFixed(1) + ", " + 
                                                  modelData.y.toFixed(1) + ", " + 
                                                  modelData.z.toFixed(1) + ")"
                                            color: "#94a3b8"
                                            font.pixelSize: 9
                                            font.family: "Consolas"
                                        }
                                    }

                                    Rectangle {
                                        width: parent.width
                                        height: 1
                                        color: "#2d3748"
                                    }
                                }

                                Text {
                                    anchors.centerIn: parent
                                    text: "No tasks announced yet"
                                    color: "#64748b"
                                    font.pixelSize: 10
                                    visible: tasksList.count === 0
                                }
                            }
                        }
                    }
                }


                // ── SWARM ROLLE & FORMATION ───────────────────────────────
                Text { text: qsTr("SWARM ROLE & FORMATION"); color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width; height: roleCol.implicitHeight + 20; radius: 8
                    color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                    Column {
                        id: roleCol
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                        spacing: 6

                        Row {
                            width: parent.width; spacing: 5
                            property int sel: 0
                            id: roleSelRow

                            Repeater {
                                model: [
                                    { label: "None",   color: "#64748b", desc: "Standalone" },
                                    { label: "Leader", color: "#22c55e", desc: "Führt Formation" },
                                    { label: "Follow", color: "#2563eb", desc: "Folgt Leader" },
                                    { label: "Coord",  color: "#f59e0b", desc: "Verwaltet Swarm" },
                                ]
                                delegate: Rectangle {
                                    width: (parent.width - 15) / 4; height: 36; radius: 5
                                    color: roleSelRow.sel === index ? Qt.rgba(Qt.color(modelData.color).r, Qt.color(modelData.color).g, Qt.color(modelData.color).b, 0.13) : "#1e2535"
                                    border.color: roleSelRow.sel === index ? modelData.color : "#334155"; border.width: 1
                                    Column {
                                        anchors.centerIn: parent; spacing: 1
                                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.label; color: roleSelRow.sel === index ? modelData.color : "#64748b"; font.pixelSize: 9; font.weight: Font.Bold }
                                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.desc; color: "#374151"; font.pixelSize: 6 }
                                    }
                                    MouseArea { anchors.fill: parent; onClicked: roleSelRow.sel = index }
                                }
                            }
                        }

                        Row { width: parent.width; spacing: 8; visible: roleSelRow.sel === 2
                            Text { text: "Leader ID:"; color: "#64748b"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter; width: 60 }
                            TextField {
                                id: leaderIdField; width: parent.width - 68; height: 24
                                placeholderText: "D1"
                                background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" }
                                color: "#e2e8f0"; font.pixelSize: 11; font.family: "Consolas"; leftPadding: 6
                            }
                        }

                        Row {
                            width: parent.width; spacing: 4; visible: roleSelRow.sel > 0
                            Column { width: (parent.width - 8) / 3; spacing: 2
                                Text { text: "North (m)"; color: "#64748b"; font.pixelSize: 8 }
                                TextField { id: offsetNorth; width: parent.width; height: 24; text: "0.0"; color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; leftPadding: 6; background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" } }
                            }
                            Column { width: (parent.width - 8) / 3; spacing: 2
                                Text { text: "East (m)"; color: "#64748b"; font.pixelSize: 8 }
                                TextField { id: offsetEast; width: parent.width; height: 24; text: "0.0"; color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; leftPadding: 6; background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" } }
                            }
                            Column { width: (parent.width - 8) / 3; spacing: 2
                                Text { text: "Alt (m)"; color: "#64748b"; font.pixelSize: 8 }
                                TextField { id: offsetAlt; width: parent.width; height: 24; text: "0.0"; color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; leftPadding: 6; background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" } }
                            }
                        }

                        Rectangle {
                            width: parent.width; height: 28; radius: 5
                            color: roleApplyM.containsMouse ? "#1d4ed8" : "#1e3a5f"
                            border.color: "#2563eb"; border.width: 1
                            Text { anchors.centerIn: parent; text: "✓  Rolle & Offset setzen"; color: "#93c5fd"; font.pixelSize: 10; font.weight: Font.Bold }
                            MouseArea {
                                id: roleApplyM; anchors.fill: parent; hoverEnabled: true
                                onClicked: {
                                    var did = droneSelCombo.currentText
                                    if (!did || typeof swarm === "undefined") return
                                    var roles = ["none", "leader", "follower", "coordinator"]
                                    var role = roles[roleSelRow.sel]
                                    swarm.setDroneRole(did, role, role === "follower" ? leaderIdField.text.trim() : "")
                                    if (roleSelRow.sel > 0) swarm.setFormationOffset(did, parseFloat(offsetNorth.text)||0, parseFloat(offsetEast.text)||0, parseFloat(offsetAlt.text)||0)
                                }
                            }
                        }
                    }
                }

                // ── SWARM AI ALGORITHMS ───────────────────────────────────
                Text { text: "SWARM AI ALGORITHMS"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width; height: algorithmsCol.implicitHeight + 20; radius: 8
                    color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                    Column {
                        id: algorithmsCol
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                        spacing: 10

                        // Status indicator
                        Row {
                            width: parent.width; spacing: 8
                            Rectangle {
                                width: 10; height: 10; radius: 5
                                anchors.verticalCenter: parent.verticalCenter
                                color: swarm && swarm.swarmAlgorithmsActive ? "#22c55e" : "#64748b"
                            }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: swarm && swarm.swarmAlgorithmsActive ? "AI ACTIVE" : "AI INACTIVE"
                                color: swarm && swarm.swarmAlgorithmsActive ? "#22c55e" : "#64748b"
                                font.pixelSize: 10; font.weight: Font.Bold
                            }
                        }

                        Column { width: parent.width; spacing: 2
                            Text { text: "Update Rate"; color: "#64748b"; font.pixelSize: 9 }
                            Row { width: parent.width; spacing: 4
                                Slider {
                                    id: rateSlider
                                    width: parent.width - 50; height: 18
                                    from: 50; to: 1000; stepSize: 50
                                    value: swarm ? swarm.algorithmsUpdateRate : 100
                                    onMoved: if (swarm) swarm.algorithmsUpdateRate = value
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                                Text {
                                    text: Math.round(rateSlider.value) + " ms";
                                    color: "#e2e8f0";
                                    font.pixelSize: 9;
                                    font.family: "Consolas";
                                    width: 42;
                                    horizontalAlignment: Text.AlignRight;
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                            Text {
                                text: {
                                    var v = rateSlider.value;
                                    if (v <= 100) return "Very fast (high CPU load)";
                                    if (v <= 200) return "Fast";
                                    if (v <= 500) return "Normal";
                                    if (v <= 750) return "Slow";
                                    return "Very slow (low CPU load)";
                                }
                                color: "#94a3b8"
                                font.pixelSize: 8
                                font.italic: true
                            }
                        }

                        // ── BOIDS / REYNOLDS ──────────────────────────────────────
                        Rectangle { width: parent.width; height: 1; color: "#2d3748" }
                        Row { width: parent.width; spacing: 6
                            Text { text: "BOIDS (REYNOLDS FLOCKING)"; color: "#22c55e"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1; anchors.verticalCenter: parent.verticalCenter }
                            Item { width: parent.width - 280; height: 1 }
                            CheckBox {
                                text: "enabled"; checked: swarm ? swarm.boidsEnabled : false
                                onCheckedChanged: if (swarm) swarm.boidsEnabled = checked
                                contentItem: Text { text: parent.text; color: "#cbd5e1"; font.pixelSize: 9; leftPadding: 18; verticalAlignment: Text.AlignVCenter }
                                indicator: Rectangle { width: 14; height: 14; radius: 3; border.color: "#64748b"; border.width: 1; color: parent.checked ? "#22c55e" : "#1e2535"; anchors.verticalCenter: parent.verticalCenter }
                            }
                        }
                        Text {
                            width: parent.width
                            text: "ℹ️ Emergentes Schwarmverhalten: Separation (Abstand halten), Alignment (gleiche Richtung), Cohesion (zum Zentrum). ⚠️ Inkompatibel mit Leader-Follower."
                            color: "#94a3b8"
                            font.pixelSize: 8
                            wrapMode: Text.WordWrap
                        }
                        Grid { columns: 2; width: parent.width; columnSpacing: 6; rowSpacing: 6
                            Column { width: (parent.width - 6) / 2; spacing: 2
                                Text { text: "Separation Weight"; color: "#64748b"; font.pixelSize: 9 }
                                Row { width: parent.width; spacing: 4
                                    Slider {
                                        id: sepSlider
                                        width: parent.width - 50; height: 18
                                        from: 0; to: 3.0; stepSize: 0.1
                                        value: swarm ? swarm.separationWeight : 1.5
                                        onMoved: if (swarm) swarm.separationWeight = value
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                    Text {
                                        text: sepSlider.value.toFixed(1);
                                        color: "#e2e8f0";
                                        font.pixelSize: 9;
                                        font.family: "Consolas";
                                        width: 42;
                                        horizontalAlignment: Text.AlignRight;
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }
                                Text {
                                    text: {
                                        var v = sepSlider.value;
                                        if (v < 0.5) return "Very weak";
                                        if (v < 1.0) return "Weak";
                                        if (v < 2.0) return "Normal";
                                        if (v < 2.5) return "Strong";
                                        return "Very strong";
                                    }
                                    color: "#94a3b8"
                                    font.pixelSize: 8
                                    font.italic: true
                                }
                            }
                            Column { width: (parent.width - 6) / 2; spacing: 2
                                Text { text: "Alignment Weight"; color: "#64748b"; font.pixelSize: 9 }
                                Row { width: parent.width; spacing: 4
                                    Slider {
                                        id: alignSlider
                                        width: parent.width - 50; height: 18
                                        from: 0; to: 3.0; stepSize: 0.1
                                        value: swarm ? swarm.alignmentWeight : 1.0
                                        onMoved: if (swarm) swarm.alignmentWeight = value
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                    Text {
                                        text: alignSlider.value.toFixed(1);
                                        color: "#e2e8f0";
                                        font.pixelSize: 9;
                                        font.family: "Consolas";
                                        width: 42;
                                        horizontalAlignment: Text.AlignRight;
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }
                                Text {
                                    text: {
                                        var v = alignSlider.value;
                                        if (v < 0.5) return "Very weak";
                                        if (v < 1.0) return "Weak";
                                        if (v < 2.0) return "Normal";
                                        if (v < 2.5) return "Strong";
                                        return "Very strong";
                                    }
                                    color: "#94a3b8"
                                    font.pixelSize: 8
                                    font.italic: true
                                }
                            }
                            Column { width: (parent.width - 6) / 2; spacing: 2
                                Text { text: "Cohesion Weight"; color: "#64748b"; font.pixelSize: 9 }
                                Row { width: parent.width; spacing: 4
                                    Slider {
                                        id: cohSlider
                                        width: parent.width - 50; height: 18
                                        from: 0; to: 3.0; stepSize: 0.1
                                        value: swarm ? swarm.cohesionWeight : 1.0
                                        onMoved: if (swarm) swarm.cohesionWeight = value
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                    Text {
                                        text: cohSlider.value.toFixed(1);
                                        color: "#e2e8f0";
                                        font.pixelSize: 9;
                                        font.family: "Consolas";
                                        width: 42;
                                        horizontalAlignment: Text.AlignRight;
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }
                                Text {
                                    text: {
                                        var v = cohSlider.value;
                                        if (v < 0.5) return "Very weak";
                                        if (v < 1.0) return "Weak";
                                        if (v < 2.0) return "Normal";
                                        if (v < 2.5) return "Strong";
                                        return "Very strong";
                                    }
                                    color: "#94a3b8"
                                    font.pixelSize: 8
                                    font.italic: true
                                }
                            }
                            Column { width: (parent.width - 6) / 2; spacing: 2
                                Text { text: "Perception Radius (m)"; color: "#64748b"; font.pixelSize: 9 }
                                TextField {
                                    width: parent.width; height: 22
                                    text: swarm ? swarm.perceptionRadius.toString() : "50"
                                    background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748"; border.width: 1 }
                                    color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; leftPadding: 6
                                    onEditingFinished: if (swarm) swarm.perceptionRadius = parseInt(text) || 50
                                }
                            }
                        }

                        // ── LEADER-FOLLOWER ───────────────────────────────────────
                        Rectangle { width: parent.width; height: 1; color: "#2d3748" }
                        Row { width: parent.width; spacing: 6
                            Text { text: "LEADER-FOLLOWER FORMATION"; color: "#2563eb"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1; anchors.verticalCenter: parent.verticalCenter }
                            Item { width: parent.width - 280; height: 1 }
                            CheckBox {
                                text: "enabled"; checked: swarm ? swarm.leaderFollowerEnabled : false
                                onCheckedChanged: if (swarm) swarm.leaderFollowerEnabled = checked
                                contentItem: Text { text: parent.text; color: "#cbd5e1"; font.pixelSize: 9; leftPadding: 18; verticalAlignment: Text.AlignVCenter }
                                indicator: Rectangle { width: 14; height: 14; radius: 3; border.color: "#64748b"; border.width: 1; color: parent.checked ? "#2563eb" : "#1e2535"; anchors.verticalCenter: parent.verticalCenter }
                            }
                        }
                        Text {
                            width: parent.width
                            text: "ℹ️ Follower folgen dem Leader in fester Formation (Line, V, Circle, Grid). Follow Distance: Abstand zwischen Slots (8m empfohlen). ⚠️ Inkompatibel mit Boids."
                            color: "#94a3b8"
                            font.pixelSize: 8
                            wrapMode: Text.WordWrap
                        }
                        Grid { columns: 2; width: parent.width; columnSpacing: 6; rowSpacing: 6
                            Column { width: (parent.width - 6) / 2; spacing: 2
                                Text { text: "Leader Drone"; color: "#64748b"; font.pixelSize: 9 }
                                ComboBox {
                                    id: leaderCombo
                                    width: parent.width; height: 22
                                    model: swarm ? swarm.droneIds() : []
                                    background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748"; border.width: 1 }
                                    contentItem: Text { text: leaderCombo.displayText; color: "#e2e8f0"; font.pixelSize: 10; leftPadding: 6; verticalAlignment: Text.AlignVCenter }
                                    onActivated: function(index) { if (swarm) swarm.leaderDroneId = currentText }
                                    
                                    // Sync currentIndex with swarm.leaderDroneId
                                    Component.onCompleted: {
                                        if (swarm && swarm.leaderDroneId) {
                                            currentIndex = model.indexOf(swarm.leaderDroneId)
                                        }
                                    }
                                    Connections {
                                        target: swarm
                                        function onCountsChanged() {
                                            if (swarm && swarm.leaderDroneId) {
                                                leaderCombo.currentIndex = leaderCombo.model.indexOf(swarm.leaderDroneId)
                                            }
                                        }
                                    }
                                }
                            }
                            Column { width: (parent.width - 6) / 2; spacing: 2
                                Text { text: "Follow Distance (m)"; color: "#64748b"; font.pixelSize: 9 }
                                TextField {
                                    width: parent.width; height: 22
                                    text: swarm ? swarm.followDistance.toString() : "8"
                                    background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748"; border.width: 1 }
                                    color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; leftPadding: 6
                                    onEditingFinished: if (swarm) swarm.followDistance = parseInt(text) || 8
                                }
                            }
                            Column { width: (parent.width - 6) / 2; spacing: 2
                                Text { text: "Formation Type"; color: "#64748b"; font.pixelSize: 9 }
                                ComboBox {
                                    id: formCombo
                                    width: parent.width; height: 22
                                    model: ["Line", "V-Shape", "Circle", "Grid"]
                                    currentIndex: swarm ? Math.min(swarm.formationType, 3) : 0
                                    background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748"; border.width: 1 }
                                    contentItem: Text { text: formCombo.displayText; color: "#e2e8f0"; font.pixelSize: 10; leftPadding: 6; verticalAlignment: Text.AlignVCenter }
                                    onActivated: function(index) { if (swarm) swarm.formationType = index }
                                }
                            }
                            Column { width: (parent.width - 6) / 2; spacing: 2
                                Text { text: "Formation Size (0 = alle)"; color: "#64748b"; font.pixelSize: 9 }
                                TextField {
                                    width: parent.width; height: 22
                                    text: swarm ? swarm.formationSize.toString() : "0"
                                    background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748"; border.width: 1 }
                                    color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; leftPadding: 6
                                    onEditingFinished: if (swarm) swarm.formationSize = parseInt(text) >= 0 ? parseInt(text) : 0
                                }
                            }
                        }

                        // ── FORMATION PREVIEW ─────────────────────────────────────
                        Rectangle { width: parent.width; height: 1; color: "#2d3748" }
                        
                        Column {
                            width: parent.width
                            spacing: 8
                            
                            Row {
                                width: parent.width
                                spacing: 6
                                Text {
                                    text: "FORMATION PREVIEW"
                                    color: "#3b82f6"
                                    font.pixelSize: 9
                                    font.weight: Font.Bold
                                    font.letterSpacing: 1
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                                Item { width: parent.width - 200; height: 1 }
                                Text {
                                    text: "2D-Vorschau der Formation"
                                    color: "#64748b"
                                    font.pixelSize: 8
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                            
                            Cmp.FormationPreview {
                                id: formationPreview
                                width: parent.width
                                height: 180
                                
                                // Bind to swarm context properties
                                formationType: {
                                    if (!swarm) return "line"
                                    const types = ["line", "v", "circle", "grid"]
                                    const index = Math.min(swarm.formationType, 3)
                                    return types[index] || "line"
                                }
                                droneCount: {
                                    if (!swarm) return 2
                                    // Show minimum required drones for formation preview
                                    const mins = {"line": 2, "v": 2, "circle": 4, "grid": 4}
                                    const minRequired = mins[formationType] || 2
                                    return minRequired + 1  // +1 for leader
                                }
                                spacing: swarm ? swarm.followDistance : 8
                                
                                // Show warning if not enough drones (count = followers only)
                                property int minRequired: {
                                    const mins = {"line": 2, "v": 2, "circle": 4, "grid": 4}
                                    return mins[formationType] || 2
                                }
                                property bool hasEnoughDrones: droneCount >= minRequired
                            }
                            
                            // Warning if not enough drones for formation
                            Text {
                                width: parent.width
                                text: "⚠ " + formationPreview.formationType.toUpperCase() + " requires at least " + (formationPreview.minRequired + 1) + " drones (1 leader + " + formationPreview.minRequired + " followers)"
                                color: "#ef4444"
                                font.pixelSize: 9
                                horizontalAlignment: Text.AlignHCenter
                                visible: !formationPreview.hasEnoughDrones
                                wrapMode: Text.WordWrap
                            }
                        }

                        // ── CONSENSUS ─────────────────────────────────────────────
                        Rectangle { width: parent.width; height: 1; color: "#2d3748" }
                        Row { width: parent.width; spacing: 6
                            Text { text: "DISTRIBUTED CONSENSUS"; color: "#f59e0b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1; anchors.verticalCenter: parent.verticalCenter }
                            Item { width: parent.width - 280; height: 1 }
                            CheckBox {
                                text: "enabled"; checked: swarm ? swarm.consensusEnabled : false
                                onCheckedChanged: if (swarm) swarm.consensusEnabled = checked
                                contentItem: Text { text: parent.text; color: "#cbd5e1"; font.pixelSize: 9; leftPadding: 18; verticalAlignment: Text.AlignVCenter }
                                indicator: Rectangle { width: 14; height: 14; radius: 3; border.color: "#64748b"; border.width: 1; color: parent.checked ? "#f59e0b" : "#1e2535"; anchors.verticalCenter: parent.verticalCenter }
                            }
                        }
                        Text {
                            width: parent.width
                            text: "ℹ️ Democratic decision-making in the swarm. Byzantine Tolerance: Number of faulty drones that can be tolerated. ✅ Compatible with all algorithms."
                            color: "#94a3b8"
                            font.pixelSize: 8
                            wrapMode: Text.WordWrap
                        }
                        Grid { columns: 2; width: parent.width; columnSpacing: 6; rowSpacing: 6
                            Column { width: (parent.width - 6) / 2; spacing: 2
                                Text { text: "Algorithm"; color: "#64748b"; font.pixelSize: 9 }
                                ComboBox {
                                    id: consCombo
                                    width: parent.width; height: 22
                                    model: ["Basic Consensus", "Byzantine Fault Tolerance", "Distributed Consensus"]
                                    currentIndex: swarm ? swarm.consensusAlgorithm : 0
                                    background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748"; border.width: 1 }
                                    contentItem: Text { text: consCombo.displayText; color: "#e2e8f0"; font.pixelSize: 10; leftPadding: 6; verticalAlignment: Text.AlignVCenter }
                                    onActivated: function(index) { if (swarm) swarm.consensusAlgorithm = index }
                                }
                            }
                            Column { width: (parent.width - 6) / 2; spacing: 2
                                Text { text: "Byzantine Tolerance"; color: "#64748b"; font.pixelSize: 9 }
                                TextField {
                                    width: parent.width; height: 22
                                    text: swarm ? swarm.byzantineTolerance.toString() : "1"
                                    background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748"; border.width: 1 }
                                    color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; leftPadding: 6
                                    onEditingFinished: if (swarm) swarm.byzantineTolerance = parseInt(text) || 1
                                }
                            }
                        }
                        Row { width: parent.width; spacing: 6
                            Rectangle {
                                width: 120; height: 26; radius: 5
                                color: voteM.containsMouse ? "#b45309" : "#92400e"
                                border.color: "#f59e0b"; border.width: 1
                                opacity: (swarm && swarm.consensusEnabled) ? 1 : 0.5
                                Text { anchors.centerIn: parent; text: "START VOTE"; color: "#fde68a"; font.pixelSize: 9; font.weight: Font.Bold }
                                MouseArea { id: voteM; anchors.fill: parent; hoverEnabled: true
                                    enabled: swarm && swarm.consensusEnabled
                                    onClicked: if (swarm) swarm.startConsensusVote()
                                }
                            }
                            Text {
                                text: "State: " + (swarm ? swarm.consensusState : "N/A")
                                color: "#94a3b8"; font.pixelSize: 10; font.family: "Consolas"
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        // ── BEHAVIOR TREES ────────────────────────────────────────
                        Rectangle { width: parent.width; height: 1; color: "#2d3748" }
                        Row { width: parent.width; spacing: 6
                            Text { text: "BEHAVIOR TREES (AUTONOMOUS MISSIONS)"; color: "#8b5cf6"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1; anchors.verticalCenter: parent.verticalCenter }
                            Item { width: parent.width - 320; height: 1 }
                            CheckBox {
                                text: "enabled"; checked: swarm ? swarm.behaviorTreesEnabled : false
                                onCheckedChanged: if (swarm) swarm.behaviorTreesEnabled = checked
                                contentItem: Text { text: parent.text; color: "#cbd5e1"; font.pixelSize: 9; leftPadding: 18; verticalAlignment: Text.AlignVCenter }
                                indicator: Rectangle { width: 14; height: 14; radius: 3; border.color: "#64748b"; border.width: 1; color: parent.checked ? "#8b5cf6" : "#1e2535"; anchors.verticalCenter: parent.verticalCenter }
                            }
                        }
                        Text {
                            width: parent.width
                            text: "ℹ️ Autonomous mission execution with priorities. Safety First (safe), Mission First (fast), Balanced. ⚠️ Overrides other algorithms during execution."
                            color: "#94a3b8"
                            font.pixelSize: 8
                            wrapMode: Text.WordWrap
                        }
                        Grid { columns: 2; width: parent.width; columnSpacing: 6; rowSpacing: 6
                            Column { width: (parent.width - 6) / 2; spacing: 2
                                Text { text: "Mission Type"; color: "#64748b"; font.pixelSize: 9 }
                                ComboBox {
                                    id: missionCombo
                                    width: parent.width; height: 22
                                    model: ["Surveillance", "Search & Rescue", "Formation Flight", "Area Coverage"]
                                    currentIndex: swarm ? swarm.missionType : 0
                                    background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748"; border.width: 1 }
                                    contentItem: Text { text: missionCombo.displayText; color: "#e2e8f0"; font.pixelSize: 10; leftPadding: 6; verticalAlignment: Text.AlignVCenter }
                                    onActivated: function(index) { if (swarm) swarm.missionType = index }
                                }
                            }
                            Column { width: (parent.width - 6) / 2; spacing: 2
                                Text { text: "Priority Mode"; color: "#64748b"; font.pixelSize: 9 }
                                ComboBox {
                                    id: prioCombo
                                    width: parent.width; height: 22
                                    model: ["Safety First", "Mission First", "Balanced"]
                                    currentIndex: swarm ? swarm.missionPriority : 1
                                    background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748"; border.width: 1 }
                                    contentItem: Text { text: prioCombo.displayText; color: "#e2e8f0"; font.pixelSize: 10; leftPadding: 6; verticalAlignment: Text.AlignVCenter }
                                    onActivated: function(index) { if (swarm) swarm.missionPriority = index }
                                }
                            }
                        }
                        Row { width: parent.width; spacing: 6
                            Rectangle {
                                width: 140; height: 26; radius: 5
                                color: execM.containsMouse ? "#6d28d9" : "#5b21b6"
                                border.color: "#8b5cf6"; border.width: 1
                                opacity: (swarm && swarm.behaviorTreesEnabled) ? 1 : 0.5
                                Text { anchors.centerIn: parent; text: "EXECUTE MISSION"; color: "#ddd6fe"; font.pixelSize: 9; font.weight: Font.Bold }
                                MouseArea { id: execM; anchors.fill: parent; hoverEnabled: true
                                    enabled: swarm && swarm.behaviorTreesEnabled
                                    onClicked: if (swarm) swarm.executeBehaviorTreeMission()
                                }
                            }
                            Text {
                                text: "Status: " + (swarm ? swarm.missionStatus : "N/A")
                                color: "#94a3b8"; font.pixelSize: 10; font.family: "Consolas"
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        // ── Global Controls (Start / Stop / Reset) — at the bottom ──
                        Rectangle { width: parent.width; height: 1; color: "#2d3748" }
                        Row { width: parent.width; spacing: 6
                            Rectangle {
                                width: (parent.width - 12) / 3; height: 32; radius: 5
                                color: startAllM.containsMouse ? "#15803d" : "#166534"
                                border.color: "#22c55e"; border.width: 1
                                opacity: (swarm && !swarm.swarmAlgorithmsActive) ? 1 : 0.5
                                Row { anchors.centerIn: parent; spacing: 5
                                    Cmp.Icon { name: "play"; size: 11; color: "#bbf7d0"; anchors.verticalCenter: parent.verticalCenter }
                                    Text { text: "START ALGORITHMS"; color: "#bbf7d0"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 0.5; anchors.verticalCenter: parent.verticalCenter }
                                }
                                MouseArea { id: startAllM; anchors.fill: parent; hoverEnabled: true
                                    enabled: swarm && !swarm.swarmAlgorithmsActive
                                    onClicked: if (swarm) swarm.startSwarmAlgorithms()
                                }
                            }
                            Rectangle {
                                width: (parent.width - 12) / 3; height: 32; radius: 5
                                color: stopAllM.containsMouse ? "#991b1b" : "#7f1d1d"
                                border.color: "#ef4444"; border.width: 1
                                opacity: (swarm && swarm.swarmAlgorithmsActive) ? 1 : 0.5
                                Row { anchors.centerIn: parent; spacing: 5
                                    Cmp.Icon { name: "stop"; size: 11; color: "#fecaca"; anchors.verticalCenter: parent.verticalCenter }
                                    Text { text: "STOP"; color: "#fecaca"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 0.5; anchors.verticalCenter: parent.verticalCenter }
                                }
                                MouseArea { id: stopAllM; anchors.fill: parent; hoverEnabled: true
                                    enabled: swarm && swarm.swarmAlgorithmsActive
                                    onClicked: if (swarm) swarm.stopSwarmAlgorithms()
                                }
                            }
                            Rectangle {
                                width: (parent.width - 12) / 3; height: 32; radius: 5
                                color: resetM.containsMouse ? "#374151" : "#1e2535"
                                border.color: "#64748b"; border.width: 1
                                Row { anchors.centerIn: parent; spacing: 5
                                    Cmp.Icon { name: "refresh"; size: 11; color: "#cbd5e1"; anchors.verticalCenter: parent.verticalCenter }
                                    Text { text: "RESET"; color: "#cbd5e1"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 0.5; anchors.verticalCenter: parent.verticalCenter }
                                }
                                MouseArea { id: resetM; anchors.fill: parent; hoverEnabled: true
                                    onClicked: if (swarm) swarm.resetSwarmAlgorithms()
                                }
                            }
                        }
            }
        }
            }
        }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components" as Cmp

// Live telemetry dashboard for the selected drone
Item {
    id: root
    anchors.fill: parent

    property int telemetryTick: 0

    function snap(key, def) {
        var dummy = telemetryTick
        if (typeof swarm === "undefined" || swarm === null) return def
        var did = droneCombo.currentText
        if (!did) return def
        var s = swarm.droneSnapshot(did)
        return (s && s[key] !== undefined) ? s[key] : def
    }

    // Pick a sensible default — first CONNECTED drone, falling back to first
    // drone in the list. Called whenever the model changes or no selection exists.
    function _pickDefaultDrone() {
        if (typeof swarm === "undefined" || swarm === null) return ""
        var ids = swarm.droneIds()
        if (!ids || ids.length === 0) return ""
        for (var i = 0; i < ids.length; i++) {
            var s = swarm.droneSnapshot(ids[i])
            if (s && s.connected === true) return ids[i]
        }
        return ids[0]
    }

    // Refresh every telemetry tick
    Connections {
        target: swarm
        function onTelemetryUpdated(snapshot) {
            root.telemetryTick++
            var ids = swarm.droneIds()
            if (JSON.stringify(droneCombo.model) !== JSON.stringify(ids))
                droneCombo.model = ids
            // First-time auto-select once telemetry confirms a connection
            if ((!Cmp.AppState.selectedDroneId || Cmp.AppState.selectedDroneId === "")
                || ids.indexOf(Cmp.AppState.selectedDroneId) < 0) {
                var def = root._pickDefaultDrone()
                if (def) Cmp.AppState.selectedDroneId = def
            }
        }
        function onDroneAdded()   { droneCombo.model = swarm.droneIds() }
        function onDroneRemoved() { droneCombo.model = swarm.droneIds() }
    }

    // Single source of truth = AppState. Combobox writes back to it.
    property string selectedDroneId: Cmp.AppState.selectedDroneId
    onSelectedDroneIdChanged: {
        if (typeof swarm === "undefined" || swarm === null) return
        var ids = swarm.droneIds()
        var idx = ids.indexOf(selectedDroneId)
        if (idx >= 0 && idx !== droneCombo.currentIndex)
            droneCombo.currentIndex = idx
    }

    Component.onCompleted: {
        if (!Cmp.AppState.selectedDroneId || Cmp.AppState.selectedDroneId === "") {
            var def = root._pickDefaultDrone()
            if (def) Cmp.AppState.selectedDroneId = def
        }
    }

    ScrollView {
        id: dashScroll
        anchors { fill: parent; margins: 12 }
        clip: true
        contentWidth: availableWidth
        contentHeight: col.implicitHeight
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        Column {
            id: col
            width: dashScroll.availableWidth
            spacing: 10

            // ── Drone selector ───────────────────────────────────────────
            Row {
                width: parent.width
                spacing: 8

                Text { text: qsTr("DRONE"); color: "#64748b"; font.pixelSize: 10; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }

                ComboBox {
                    id: droneCombo
                    width: parent.width - 60
                    height: 30
                    model: swarm ? swarm.droneIds() : []
                    background: Rectangle { color: "#1e2535"; radius: 6; border.color: "#2d3748"; border.width: 1 }
                    contentItem: Text { text: droneCombo.displayText; color: "#e2e8f0"; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter; leftPadding: 8 }

                    // Push user picks back to the global state so all panels follow.
                    onActivated: {
                        if (currentText && currentText !== "")
                            Cmp.AppState.selectedDroneId = currentText
                    }

                    Connections {
                        target: swarm
                        function onDroneAdded(droneId) { if (swarm) droneCombo.model = swarm.droneIds() }
                        function onDroneRemoved(droneId) { if (swarm) droneCombo.model = swarm.droneIds() }
                    }
                }
            }

            // ── FSM State + type badges ──────────────────────────────────
            Row {
                width: parent.width; spacing: 6

                // FSM state badge
                Rectangle {
                    property string fsmSt: snap("fsmState", "DISCONNECTED")
                    property color fsmColor: {
                        var c = { "IDLE": "#64748b", "ARMING": "#f59e0b", "ARMED": "#eab308",
                                  "TAKEOFF": "#2563eb", "FLYING": "#22c55e", "MISSION": "#06b6d4",
                                  "RTL": "#f97316", "LANDING": "#8b5cf6", "EMERGENCY": "#ef4444",
                                  "ERROR": "#dc2626", "DISCONNECTED": "#374151" }
                        return c[fsmSt] || "#64748b"
                    }
                    width: fsmBadgeTxt.implicitWidth + 24; height: 26; radius: 13
                    color: Qt.rgba(fsmColor.r, fsmColor.g, fsmColor.b, 0.12); border.color: fsmColor; border.width: 1

                    Row {
                        anchors.centerIn: parent; spacing: 5
                        Rectangle {
                            width: 7; height: 7; radius: 3.5; anchors.verticalCenter: parent.verticalCenter
                            color: parent.parent.fsmColor
                            SequentialAnimation on opacity {
                                running: ["ARMING","TAKEOFF","LANDING","RTL"].indexOf(parent.parent.parent.fsmSt) >= 0
                                loops: Animation.Infinite
                                NumberAnimation { to: 0.2; duration: 500 }
                                NumberAnimation { to: 1.0; duration: 500 }
                            }
                        }
                        Text {
                            id: fsmBadgeTxt
                            text: {
                                var labels = {
                                    "IDLE":         qsTr("IDLE (Connected, ready)"),
                                    "ARMING":       qsTr("ARMING (Arming…)"),
                                    "ARMED":        qsTr("ARMED (Ready for takeoff)"),
                                    "TAKEOFF":      qsTr("TAKEOFF (Taking off…)"),
                                    "FLYING":       qsTr("FLYING (In the air)"),
                                    "MISSION":      qsTr("MISSION (Autopilot active)"),
                                    "RTL":          qsTr("RTL (Returning)"),
                                    "LANDING":      qsTr("LANDING (Landing…)"),
                                    "EMERGENCY":    qsTr("EMERGENCY (Emergency!)"),
                                    "ERROR":        qsTr("ERROR (Error)"),
                                    "DISCONNECTED": qsTr("DISCONNECTED (No connection)")
                                }
                                return labels[parent.parent.fsmSt] || parent.parent.fsmSt
                            }
                            color: parent.parent.fsmColor
                            font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1
                        }
                    }
                }

                // Drone type badge
                Rectangle {
                    property string dtype: snap("droneType", "generic")
                    width: dtypeTxt.implicitWidth + 20; height: 26; radius: 13
                    color: dtype === "observation" ? "#224c1d95" : "#221e2d40"
                    border.color: dtype === "observation" ? "#8b5cf6" : "#2563eb"; border.width: 1
                    Text {
                        id: dtypeTxt
                        anchors.centerIn: parent
                        text: parent.dtype === "observation" ? qsTr("Observation UAV (Gimbal/Camera)") : qsTr("Generic UAV (Standard)")
                        color: parent.dtype === "observation" ? "#c4b5fd" : "#93c5fd"
                        font.pixelSize: 9; font.weight: Font.Bold
                    }
                }

                // Swarm role badge (only if not 'none')
                Rectangle {
                    property string srole: snap("swarmRole", "none")
                    visible: srole !== "none"
                    width: sroleTxt.implicitWidth + 20; height: 26; radius: 13
                    color: { var c={"leader":"#aa14532d","follower":"#aa1e3a5f","coordinator":"#aa78350f"}; return c[srole] || "#1e2535" }
                    border.color: { var c={"leader":"#22c55e","follower":"#2563eb","coordinator":"#f59e0b"}; return c[srole] || "#64748b" }
                    border.width: 1
                    Text {
                        id: sroleTxt
                        anchors.centerIn: parent
                        text: { var i={"leader":qsTr("Leader"),"follower":qsTr("Follower"),"coordinator":qsTr("Coord.")}; return i[parent.srole] || parent.srole }
                        color: { var c={"leader":"#86efac","follower":"#93c5fd","coordinator":"#fcd34d"}; return c[parent.srole] || "#94a3b8" }
                        font.pixelSize: 9; font.weight: Font.Bold
                    }
                }
            }

            // ── FSM Flughinweis ───────────────────────────────────────────
            Rectangle {
                width: parent.width; height: fsmHintCol.implicitHeight + 16; radius: 8
                color: "#0c1a0c"; border.color: "#1a3a1a"; border.width: 1
                visible: snap("fsmState", "DISCONNECTED") !== "DISCONNECTED"

                Column {
                    id: fsmHintCol
                    anchors { left: parent.left; right: parent.right; margins: 12; verticalCenter: parent.verticalCenter }
                    spacing: 3

                    Text { text: qsTr("FSM CONTROL — Sequence:"); color: "#4ade80"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }
                    Text { text: qsTr("1. Press ARM (InstrBar above) → Status: ARMED"); color: "#6b7280"; font.pixelSize: 9 }
                    Text { text: qsTr("2. Press TAKEOFF → Status: TAKEOFF → FLYING"); color: "#6b7280"; font.pixelSize: 9 }
                    Text { text: qsTr("3. Set GOTO / Waypoints (Swarm tab)"); color: "#6b7280"; font.pixelSize: 9 }
                    Text { text: qsTr("4. RTL or LAND → Drone returns / lands"); color: "#6b7280"; font.pixelSize: 9 }
                    Text {
                        text: {
                            var hints = {
                                "IDLE":    qsTr("→ Drone is connected. Press ARM to start."),
                                "ARMING":  qsTr("→ Arming. Wait…"),
                                "ARMED":   qsTr("→ Armed! Press TAKEOFF."),
                                "TAKEOFF": qsTr("→ Taking off. Do not interfere."),
                                "FLYING":  qsTr("→ In the air. GOTO, Mission or RTL possible."),
                                "MISSION": qsTr("→ Autopilot flying mission. RTL to abort."),
                                "RTL":     qsTr("→ Returning to start point."),
                                "LANDING": qsTr("→ Landing. Do not press DISARM."),
                                "EMERGENCY": qsTr("→ EMERGENCY! DISARM or LAND immediately!")
                            }
                            var st = snap("fsmState", "")
                            return hints[st] || ""
                        }
                        color: "#22c55e"; font.pixelSize: 10; font.weight: Font.Bold
                        visible: text !== ""
                    }
                }
            }

            // ── FSM Transition History ────────────────────────────────────
            Column {
                width: parent.width; spacing: 4

                Text { text: qsTr("FSM HISTORY"); color: "#64748b"; font.pixelSize: 8; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width; height: fsmHistView.count > 0 ? Math.min(fsmHistView.count * 22 + 10, 110) : 32
                    radius: 6; color: "#0d1117"; border.color: "#1e293b"; border.width: 1

                    property var histData: []
                    Timer {
                        interval: 1000; running: true; repeat: true
                        onTriggered: {
                            if (typeof swarm === "undefined" || !swarm || !droneCombo.currentText) return
                            parent.histData = swarm.droneFsmHistory(droneCombo.currentText)
                        }
                    }

                    ListView {
                        id: fsmHistView
                        anchors { fill: parent; margins: 5 }
                        model: parent.histData
                        clip: true
                        verticalLayoutDirection: ListView.BottomToTop

                        delegate: Row {
                            width: fsmHistView.width; height: 20; spacing: 8
                            Text { text: modelData.t ? new Date(modelData.t * 1000).toLocaleTimeString("de-DE", {hour:"2-digit",minute:"2-digit",second:"2-digit"}) : ""; color: "#334155"; font.pixelSize: 8; font.family: "Consolas"; width: 55 }
                            Text { text: modelData.from || ""; color: "#64748b"; font.pixelSize: 8; font.family: "Consolas"; width: 70 }
                            Text { text: "→"; color: "#334155"; font.pixelSize: 8 }
                            Text {
                                text: modelData.to || ""
                                color: {
                                    var c={"FLYING":"#22c55e","ARMED":"#eab308","EMERGENCY":"#ef4444","LANDING":"#8b5cf6","RTL":"#f97316","TAKEOFF":"#2563eb","MISSION":"#06b6d4"}
                                    return c[modelData.to] || "#94a3b8"
                                }
                                font.pixelSize: 8; font.family: "Consolas"; font.weight: Font.Bold
                            }
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        visible: fsmHistView.count === 0
                        text: qsTr("No FSM transitions")
                        color: "#374151"; font.pixelSize: 9
                    }
                }
            }

            // ── KPI grid ─────────────────────────────────────────────────
            GridLayout {
                width: parent.width
                columns: 3
                columnSpacing: 6; rowSpacing: 6

                Repeater {
                    model: [
                        { label: "ALTITUDE",   icon: "▲", key: "alt_rel",     unit: "m",   fmt: 1, color: "#2563eb" },
                        { label: "SPEED",      icon: "→", key: "groundspeed", unit: "m/s", fmt: 1, color: "#22c55e" },
                        { label: "HEADING",    icon: "◎", key: "yaw",         unit: "°",   fmt: 2, color: "#8b5cf6" },
                        { label: "CLIMB",      icon: "↕", key: "climb",       unit: "m/s", fmt: 2, color: "#f59e0b" },
                        { label: "SATELLITES", icon: "◈", key: "satellites",  unit: "sat", fmt: 0, color: "#06b6d4" },
                        { label: "THROTTLE",   icon: "⚡", key: "throttle",   unit: "%",   fmt: 0, color: "#f97316" },
                    ]

                    delegate: Rectangle {
                        Layout.fillWidth: true; height: 64; radius: 6
                        color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                        Rectangle { width: 2; height: parent.height; radius: 1; color: modelData.color
                            anchors { left: parent.left; leftMargin: 0; verticalCenter: parent.verticalCenter } }

                        Column {
                            anchors { left: parent.left; leftMargin: 10; right: parent.right; rightMargin: 6; verticalCenter: parent.verticalCenter }
                            spacing: 1
                            Row {
                                spacing: 3
                                Text { text: modelData.icon; color: modelData.color; font.pixelSize: 10 }
                                Text { text: modelData.label; color: "#64748b"; font.pixelSize: 8; font.weight: Font.Bold; font.letterSpacing: 0.5 }
                            }
                            Text {
                                text: {
                                    var v = snap(modelData.key, 0)
                                    return modelData.fmt > 0 ? Number(v).toFixed(modelData.fmt) : String(v)
                                }
                                color: modelData.color; font.pixelSize: 18; font.weight: Font.Bold
                            }
                            Text { text: modelData.unit; color: "#64748b"; font.pixelSize: 9 }
                        }
                    }
                }
            }

            // ── Battery bar ──────────────────────────────────────────────
            Rectangle {
                width: parent.width; height: 54; radius: 8
                color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                Column {
                    anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
                    spacing: 4
                    Row {
                        spacing: 6
                        Text { text: qsTr("BATTERY"); color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }
                        Text { text: snap("battery_pct", -1) >= 0 ? snap("battery_pct",0).toFixed(0) + "%" : "—"; color: snap("battery_pct",50) > 20 ? "#22c55e" : "#ef4444"; font.pixelSize: 12; font.weight: Font.Bold }
                        Text { text: snap("battery_v", 0) > 0 ? snap("battery_v",0).toFixed(2) + "V" : ""; color: "#94a3b8"; font.pixelSize: 11 }
                    }
                    Rectangle {
                        width: root.width - 80; height: 10; radius: 5
                        color: "#0d1117"; border.color: "#2d3748"; border.width: 1
                        Rectangle {
                            width: Math.max(0, parent.width * Math.min(snap("battery_pct",0), 100) / 100)
                            height: parent.height; radius: 5
                            color: snap("battery_pct",50) > 50 ? "#22c55e" : (snap("battery_pct",50) > 20 ? "#f59e0b" : "#ef4444")
                            Behavior on width { NumberAnimation { duration: 300 } }
                        }
                    }
                }
            }

            // ── GPS strip ────────────────────────────────────────────────
            Rectangle {
                width: parent.width; height: 54; radius: 8
                color: "#1a2035"; border.color: "#2d3748"; border.width: 1
                Column {
                    anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
                    spacing: 3
                    Row {
                        spacing: 8
                        Text { text: "◈ GPS"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold }
                        Text { text: ["No Fix","No Fix","2D","3D","3D+DGPS"][Math.min(snap("gps_fix",0),4)]; color: snap("gps_fix",0) >= 3 ? "#22c55e" : "#f59e0b"; font.pixelSize: 10; font.weight: Font.Bold }
                        Text { text: snap("satellites",0) + " sat"; color: "#94a3b8"; font.pixelSize: 10 }
                    }
                    Text { text: snap("lat",0).toFixed(6) + ",  " + snap("lon",0).toFixed(6); color: "#94a3b8"; font.pixelSize: 10; font.family: "Consolas" }
                }
            }

        }
    }
}

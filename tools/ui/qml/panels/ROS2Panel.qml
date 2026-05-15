import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components" as Cmp

Item {
    id: root
    anchors.fill: parent

    property string selectedDroneId: ""
    property string _nodeStatus: (typeof ros2 !== "undefined" && ros2) ? ros2.nodeStatus() : "no_ros2"

    function statusColor(s) {
        if (s === "ok")           return "#22c55e"
        if (s === "no_px4_msgs") return "#f59e0b"
        return "#ef4444"
    }
    function statusLabel(s) {
        if (s === "ok")           return "ROS2 + px4_msgs OK"
        if (s === "no_px4_msgs") return "ROS2 OK — px4_msgs missing"
        return "rclpy not installed"
    }

    // Refresh node status every 2s
    Timer { interval: 2000; running: true; repeat: true
        onTriggered: root._nodeStatus = (typeof ros2 !== "undefined" && ros2) ? ros2.nodeStatus() : "no_ros2"
    }

    // ── Three-column horizontal layout (anchor-based, scroll-safe) ────────────────
    // ════════════════ LEFT COLUMN ════════════════
    ScrollView {
        id: leftSv
        anchors { top: parent.top; left: parent.left; bottom: parent.bottom; topMargin: 12; leftMargin: 12; bottomMargin: 12 }
        width: (parent.width - 44) * 0.30
        clip: true
        contentWidth: availableWidth
        contentHeight: leftCol.implicitHeight
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        Column {
            id: leftCol
            width: leftSv.availableWidth
            spacing: 8

            // ── ROS2 Node Status ─────────────────────────────────────
            Text { text: "ROS2 / uXRCE-DDS"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width; height: 40; radius: 8
                    color: "#0d1117"; border.color: statusColor(root._nodeStatus); border.width: 1
                    Row {
                        anchors { fill: parent; leftMargin: 10; rightMargin: 10 }
                        spacing: 8
                        Rectangle {
                            width: 10; height: 10; radius: 5; anchors.verticalCenter: parent.verticalCenter
                            color: statusColor(root._nodeStatus)
                            SequentialAnimation on opacity {
                                running: root._nodeStatus === "ok"; loops: Animation.Infinite
                                NumberAnimation { to: 0.3; duration: 800 }
                                NumberAnimation { to: 1.0; duration: 800 }
                            }
                        }
                        Text {
                            text: statusLabel(root._nodeStatus)
                            color: statusColor(root._nodeStatus)
                            font.pixelSize: 10; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }

                // ── Info box when not available ───────────────────────────
                Rectangle {
                    width: parent.width; height: infoCol.implicitHeight + 16; radius: 8
                    color: "#1a1500"; border.color: "#78350f"; border.width: 1
                    visible: root._nodeStatus !== "ok"

                    Column {
                        id: infoCol
                        anchors { fill: parent; margins: 10 }
                        spacing: 4
                        Text { text: root._nodeStatus === "no_ros2" ? "Install ROS2 Humble+:" : "Build px4_msgs:"; color: "#fcd34d"; font.pixelSize: 10; font.weight: Font.Bold }
                        Text {
                            text: root._nodeStatus === "no_ros2"
                                ? "sudo apt install ros-humble-desktop\nsource /opt/ros/humble/setup.bash\npip install rclpy"
                                : "cd ~/ros2_ws/src\ngit clone https://github.com/PX4/px4_msgs\ncd ~/ros2_ws && colcon build\nsource install/setup.bash"
                            color: "#94a3b8"; font.pixelSize: 9; font.family: "Consolas"
                            wrapMode: Text.WordWrap; width: parent.width
                        }
                        Text { text: "uXRCE-DDS Agent:"; color: "#fcd34d"; font.pixelSize: 10; font.weight: Font.Bold; visible: root._nodeStatus === "no_px4_msgs" }
                        Text {
                            visible: root._nodeStatus === "no_px4_msgs"
                            text: "MicroXRCEAgent udp4 -p 8888"
                            color: "#94a3b8"; font.pixelSize: 9; font.family: "Consolas"
                        }
                    }
                }

                // ── Bridge Konfiguration ──────────────────────────────────
                Text { text: "BRIDGE KONFIGURATION"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width; height: cfgCol.implicitHeight + 20; radius: 8
                    color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                    Column {
                        id: cfgCol
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                        spacing: 8

                        ComboBox {
                            id: droneCombo; width: parent.width; height: 28
                            model: (typeof swarm !== "undefined" && swarm) ? swarm.droneIds() : []
                            background: Rectangle { color: "#1e2535"; radius: 5; border.color: "#2d3748"; border.width: 1 }
                            contentItem: Text { text: droneCombo.displayText; color: "#e2e8f0"; font.pixelSize: 11; verticalAlignment: Text.AlignVCenter; leftPadding: 6 }
                            onCurrentTextChanged: { if (currentText) Cmp.AppState.selectedDroneId = currentText }
                        }

                        Row {
                            width: parent.width; spacing: 6
                            Text { text: "NS:"; color: "#64748b"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter; width: 22 }
                            TextField {
                                id: nsField; width: parent.width - 28; height: 26
                                placeholderText: "uav_1  (leer = /fmu/*)"
                                background: Rectangle { color: "#1e2535"; radius: 5; border.color: "#2d3748"; border.width: 1 }
                                color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; leftPadding: 6
                            }
                        }

                        Text {
                            width: parent.width
                            text: nsField.text.trim() === "" ? "/fmu/out/*  /fmu/in/*" : "/" + nsField.text.trim() + "/fmu/out|in/*"
                            color: "#475569"; font.pixelSize: 8; font.family: "Consolas"
                        }

                        property bool _bridgeActive: (typeof ros2 !== "undefined" && ros2 && root.selectedDroneId !== "") ? ros2.isBridgeActive(root.selectedDroneId) : false
                        Timer { interval: 500; running: true; repeat: true
                            onTriggered: cfgCol._bridgeActive = (typeof ros2 !== "undefined" && ros2 && root.selectedDroneId !== "") ? ros2.isBridgeActive(root.selectedDroneId) : false
                        }

                        Rectangle {
                            width: parent.width; height: 32; radius: 6
                            color: bridgeTogM.containsMouse ? (cfgCol._bridgeActive ? "#7f1d1d" : "#166534") : (cfgCol._bridgeActive ? "#450a0a" : "#14532d")
                            border.color: cfgCol._bridgeActive ? "#ef4444" : "#22c55e"; border.width: 1
                            Behavior on color { ColorAnimation { duration: 120 } }
                            Row {
                                anchors.centerIn: parent; spacing: 6
                                Text { text: cfgCol._bridgeActive ? "■" : "▶"; color: cfgCol._bridgeActive ? "#fca5a5" : "#86efac"; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                                Text { text: cfgCol._bridgeActive ? "Bridge stoppen" : "Bridge starten (uXRCE-DDS)"; color: cfgCol._bridgeActive ? "#fca5a5" : "#86efac"; font.pixelSize: 10; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                            }
                            MouseArea {
                                id: bridgeTogM; anchors.fill: parent; hoverEnabled: true
                                enabled: root._nodeStatus === "ok" && root.selectedDroneId !== ""
                                onClicked: {
                                    if (typeof ros2 === "undefined" || !ros2) return
                                    cfgCol._bridgeActive ? ros2.stopBridge(root.selectedDroneId) : ros2.startBridge(root.selectedDroneId, nsField.text.trim())
                                }
                            }
                        }
                    }
                }

                // ── uORB Topics ───────────────────────────────────────────
                Text { text: "uORB TOPICS"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width; height: topicsCol.implicitHeight + 16; radius: 8
                    color: "#0d1117"; border.color: "#2d3748"; border.width: 1

                    Column {
                        id: topicsCol
                        anchors { fill: parent; margins: 8 }
                        spacing: 3

                        property var topics: root.selectedDroneId !== "" && typeof ros2 !== "undefined" && ros2
                            ? ros2.getBridgeTopics(root.selectedDroneId) : []

                        Repeater {
                            model: topicsCol.topics
                            delegate: Row {
                                width: topicsCol.width; spacing: 5
                                Rectangle { width: 7; height: 7; radius: 3.5; anchors.verticalCenter: parent.verticalCenter; color: modelData.includes("/out/") ? "#22c55e" : "#2563eb" }
                                Text { text: modelData; color: "#64748b"; font.pixelSize: 8; font.family: "Consolas"; anchors.verticalCenter: parent.verticalCenter }
                                Text { text: modelData.includes("/out/") ? "← PX4" : "→ PX4"; color: modelData.includes("/out/") ? "#4422c55e" : "#442563eb"; font.pixelSize: 7; anchors.verticalCenter: parent.verticalCenter }
                            }
                        }

                        Text { visible: topicsCol.topics.length === 0; text: "Kein Drone ausgewählt"; color: "#374151"; font.pixelSize: 10; anchors.horizontalCenter: parent.horizontalCenter }
                    }
                }
            }
        }

        // ════════════════ CENTER COLUMN ════════════════
        ScrollView {
            id: centerSv
            anchors { top: parent.top; left: leftSv.right; bottom: parent.bottom; topMargin: 12; leftMargin: 10; bottomMargin: 12 }
            width: (parent.width - 44) * 0.38
            clip: true
            contentWidth: availableWidth
            contentHeight: centerCol.implicitHeight
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical.policy: ScrollBar.AsNeeded

            Column {
                id: centerCol
                width: centerSv.availableWidth
                spacing: 8

                // ── Live uORB Snapshot ────────────────────────────────────
                Text { text: "LIVE uORB SNAPSHOT"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width; height: snapCol.implicitHeight + 16; radius: 8
                    color: "#0d1117"; border.color: "#2d3748"; border.width: 1

                    property var snap: ({})
                    Timer {
                        interval: 200; running: true; repeat: true
                        onTriggered: { if (typeof ros2 === "undefined" || !ros2 || root.selectedDroneId === "") return; parent.snap = ros2.bridgeSnapshot(root.selectedDroneId) }
                    }

                    Column {
                        id: snapCol
                        anchors { fill: parent; margins: 8 }
                        spacing: 2
                        property var snap: parent.snap

                        Repeater {
                            model: [
                                { key: "armed",       label: "Armed",      fmt: function(v) { return v ? "ARMED" : "DISARMED" },                   color: function(v) { return v ? "#22c55e" : "#ef4444" } },
                                { key: "flight_mode", label: "Nav State",  fmt: function(v) { return v !== undefined ? v.toString() : "—" },        color: function(v) { return "#8be9fd" } },
                                { key: "lat",         label: "Lat",        fmt: function(v) { return v ? v.toFixed(6) : "—" },                      color: function(v) { return "#8be9fd" } },
                                { key: "lon",         label: "Lon",        fmt: function(v) { return v ? v.toFixed(6) : "—" },                      color: function(v) { return "#8be9fd" } },
                                { key: "alt_rel",     label: "Alt (rel)",  fmt: function(v) { return v !== undefined ? v.toFixed(2)+"m" : "—" },    color: function(v) { return "#8be9fd" } },
                                { key: "roll",        label: "Roll",       fmt: function(v) { return v !== undefined ? v.toFixed(1)+"°" : "—" },    color: function(v) { return "#8be9fd" } },
                                { key: "pitch",       label: "Pitch",      fmt: function(v) { return v !== undefined ? v.toFixed(1)+"°" : "—" },    color: function(v) { return "#8be9fd" } },
                                { key: "yaw",         label: "Yaw",        fmt: function(v) { return v !== undefined ? v.toFixed(1)+"°" : "—" },    color: function(v) { return "#8be9fd" } },
                                { key: "battery_pct", label: "Battery",    fmt: function(v) { return v !== undefined && v >= 0 ? v.toFixed(0)+"%" : "—" }, color: function(v) { return v > 20 ? "#22c55e" : "#ef4444" } },
                                { key: "battery_v",   label: "Voltage",    fmt: function(v) { return v ? v.toFixed(2)+"V" : "—" },                  color: function(v) { return "#8be9fd" } },
                                { key: "gps_fix",     label: "GPS Fix",    fmt: function(v) { return ["NoFix","NoFix","2D","3D","RTK"][Math.min(v||0,4)] }, color: function(v) { return v >= 3 ? "#22c55e" : "#f59e0b" } },
                                { key: "satellites",  label: "Sats",       fmt: function(v) { return v !== undefined ? v.toString() : "—" },        color: function(v) { return "#8be9fd" } },
                            ]
                            delegate: Row {
                                width: snapCol.width; height: 17; spacing: 4
                                Text { text: modelData.label + ":"; color: "#475569"; font.pixelSize: 9; width: 68 }
                                Text {
                                    text: { var s = snapCol.snap; var v = (s && s[modelData.key] !== undefined) ? s[modelData.key] : undefined; return v !== undefined ? modelData.fmt(v) : "—" }
                                    color: { var s = snapCol.snap; var v = (s && s[modelData.key] !== undefined) ? s[modelData.key] : undefined; return v !== undefined ? modelData.color(v) : "#374151" }
                                    font.pixelSize: 9; font.family: "Consolas"; font.weight: Font.Bold
                                }
                            }
                        }

                        Text { visible: Object.keys(snapCol.snap).length === 0; text: "Bridge nicht aktiv"; color: "#374151"; font.pixelSize: 10; anchors.horizontalCenter: parent.horizontalCenter }
                    }
                }

                // ── Offboard Control ──────────────────────────────────────
                Text { text: "OFFBOARD (TrajectorySetpoint)"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width; height: offboardCol.implicitHeight + 16; radius: 8
                    color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                    Column {
                        id: offboardCol
                        anchors { fill: parent; margins: 10 }
                        spacing: 6

                        // Mode tabs
                        Row {
                            id: offboardModeRow
                            spacing: 5
                            property int mode: 0

                            Rectangle {
                                width: 84; height: 24; radius: 5
                                color: offboardModeRow.mode === 0 ? "#1e3a5f" : "#1e2535"
                                border.color: offboardModeRow.mode === 0 ? "#2563eb" : "#334155"; border.width: 1
                                Text { anchors.centerIn: parent; text: "Position"; color: offboardModeRow.mode === 0 ? "#93c5fd" : "#64748b"; font.pixelSize: 9 }
                                MouseArea { anchors.fill: parent; onClicked: offboardModeRow.mode = 0 }
                            }
                            Rectangle {
                                width: 84; height: 24; radius: 5
                                color: offboardModeRow.mode === 1 ? "#1e3a5f" : "#1e2535"
                                border.color: offboardModeRow.mode === 1 ? "#f97316" : "#334155"; border.width: 1
                                Text { anchors.centerIn: parent; text: "Velocity"; color: offboardModeRow.mode === 1 ? "#fb923c" : "#64748b"; font.pixelSize: 9 }
                                MouseArea { anchors.fill: parent; onClicked: offboardModeRow.mode = 1 }
                            }
                        }

                        // Position inputs
                        Row {
                            width: parent.width; spacing: 4; visible: offboardModeRow.mode === 0
                            Column { width: (parent.width-8)/4; spacing: 1
                                Text { text: "N (m)"; color: "#64748b"; font.pixelSize: 8 }
                                TextField { id: northField; width: parent.width; height: 24; text: "0.0"; color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; leftPadding: 4; background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" } }
                            }
                            Column { width: (parent.width-8)/4; spacing: 1
                                Text { text: "E (m)"; color: "#64748b"; font.pixelSize: 8 }
                                TextField { id: eastField; width: parent.width; height: 24; text: "0.0"; color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; leftPadding: 4; background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" } }
                            }
                            Column { width: (parent.width-8)/4; spacing: 1
                                Text { text: "D (m)"; color: "#64748b"; font.pixelSize: 8 }
                                TextField { id: downField; width: parent.width; height: 24; text: "-5.0"; color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; leftPadding: 4; background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" } }
                            }
                            Column { width: (parent.width-8)/4; spacing: 1
                                Text { text: "Yaw(r)"; color: "#64748b"; font.pixelSize: 8 }
                                TextField { id: yawPosField; width: parent.width; height: 24; text: "0.0"; color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; leftPadding: 4; background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" } }
                            }
                        }

                        // Velocity inputs
                        Row {
                            width: parent.width; spacing: 4; visible: offboardModeRow.mode === 1
                            Column { width: (parent.width-8)/4; spacing: 1
                                Text { text: "vN"; color: "#64748b"; font.pixelSize: 8 }
                                TextField { id: vnField; width: parent.width; height: 24; text: "0.0"; color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; leftPadding: 4; background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" } }
                            }
                            Column { width: (parent.width-8)/4; spacing: 1
                                Text { text: "vE"; color: "#64748b"; font.pixelSize: 8 }
                                TextField { id: veField; width: parent.width; height: 24; text: "0.0"; color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; leftPadding: 4; background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" } }
                            }
                            Column { width: (parent.width-8)/4; spacing: 1
                                Text { text: "vD"; color: "#64748b"; font.pixelSize: 8 }
                                TextField { id: vdField; width: parent.width; height: 24; text: "0.0"; color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; leftPadding: 4; background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" } }
                            }
                            Column { width: (parent.width-8)/4; spacing: 1
                                Text { text: "YawR"; color: "#64748b"; font.pixelSize: 8 }
                                TextField { id: yawRateField; width: parent.width; height: 24; text: "0.0"; color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; leftPadding: 4; background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" } }
                            }
                        }

                        // Action buttons — proportional widths so they
                        // never overflow when the panel is narrow.
                        Row {
                            id: offboardActionsRow
                            width: parent.width; spacing: 5
                            readonly property real _w: (width - 10) / 4   // 4 slots, 2 spacings of 5

                            Rectangle {
                                width: offboardActionsRow._w * 2; height: 28; radius: 5
                                color: activateM.containsMouse ? "#c2410c" : "#9a3412"; border.color: "#f97316"; border.width: 1
                                Text { anchors.centerIn: parent; text: "OFFBOARD"; color: "#fed7aa"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1; elide: Text.ElideRight }
                                MouseArea { id: activateM; anchors.fill: parent; hoverEnabled: true; onClicked: { if (typeof ros2 !== "undefined" && ros2 && root.selectedDroneId !== "") ros2.activateOffboardMode(root.selectedDroneId) } }
                            }
                            Rectangle {
                                width: offboardActionsRow._w; height: 28; radius: 5
                                color: sendM.containsMouse ? "#1d4ed8" : "#1e3a5f"; border.color: "#2563eb"; border.width: 1
                                Text { anchors.centerIn: parent; text: "▶ SEND"; color: "#93c5fd"; font.pixelSize: 9; font.weight: Font.Bold; elide: Text.ElideRight }
                                MouseArea {
                                    id: sendM; anchors.fill: parent; hoverEnabled: true
                                    onClicked: {
                                        if (typeof ros2 === "undefined" || !ros2 || root.selectedDroneId === "") return
                                        if (offboardModeRow.mode === 0)
                                            ros2.setOffboardPosition(root.selectedDroneId, parseFloat(northField.text)||0, parseFloat(eastField.text)||0, parseFloat(downField.text)||-5, parseFloat(yawPosField.text)||0)
                                        else
                                            ros2.setOffboardVelocity(root.selectedDroneId, parseFloat(vnField.text)||0, parseFloat(veField.text)||0, parseFloat(vdField.text)||0, parseFloat(yawRateField.text)||0)
                                    }
                                }
                            }
                            Rectangle {
                                width: offboardActionsRow._w; height: 28; radius: 5
                                color: stopOffM.containsMouse ? "#7f1d1d" : "#1e2535"; border.color: "#ef4444"; border.width: 1
                                Text { anchors.centerIn: parent; text: "■ STOP"; color: "#fca5a5"; font.pixelSize: 9; font.weight: Font.Bold; elide: Text.ElideRight }
                                MouseArea { id: stopOffM; anchors.fill: parent; hoverEnabled: true; onClicked: { if (typeof ros2 !== "undefined" && ros2 && root.selectedDroneId !== "") ros2.stopOffboard(root.selectedDroneId) } }
                            }
                        }
                    }
                }

            }
        }

        // ════════════════ RIGHT COLUMN — Vehicle Commands ════════════════
        ScrollView {
            id: rightSv
            anchors { top: parent.top; left: centerSv.right; right: parent.right; bottom: parent.bottom; topMargin: 12; leftMargin: 10; rightMargin: 12; bottomMargin: 12 }
            clip: true
            contentWidth: availableWidth
            contentHeight: rightCol.implicitHeight
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical.policy: ScrollBar.AsNeeded

            Column {
                id: rightCol
                width: rightSv.availableWidth
                spacing: 8

                Text { text: "VEHICLE COMMANDS (uXRCE-DDS)"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width; height: cmdCol.implicitHeight + 20; radius: 8
                    color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                    Column {
                        id: cmdCol
                        anchors { fill: parent; margins: 10 }
                        spacing: 6

                        Repeater {
                            model: [
                                { label: "ARM",    color: "#22c55e", fn: "armBridge"    },
                                { label: "DISARM", color: "#ef4444", fn: "disarmBridge" },
                                { label: "LAND",   color: "#f59e0b", fn: "landBridge"   },
                                { label: "RTL",    color: "#f97316", fn: "rtlBridge"    },
                            ]
                            delegate: Rectangle {
                                width: rightCol.width - 20; height: 32; radius: 5
                                color: cMa.containsMouse ? Qt.rgba(Qt.color(modelData.color).r, Qt.color(modelData.color).g, Qt.color(modelData.color).b, 0.2) : "#1e2535"
                                border.color: cMa.containsMouse ? modelData.color : "#334155"; border.width: 1
                                Behavior on color { ColorAnimation { duration: 80 } }
                                Text { anchors.centerIn: parent; text: modelData.label; color: modelData.color; font.pixelSize: 11; font.weight: Font.Bold }
                                MouseArea {
                                    id: cMa; anchors.fill: parent; hoverEnabled: true
                                    onClicked: {
                                        if (typeof ros2 === "undefined" || !ros2 || root.selectedDroneId === "") return
                                        if      (modelData.fn === "armBridge")    ros2.armBridge(root.selectedDroneId)
                                        else if (modelData.fn === "disarmBridge") ros2.disarmBridge(root.selectedDroneId)
                                        else if (modelData.fn === "landBridge")   ros2.landBridge(root.selectedDroneId)
                                        else if (modelData.fn === "rtlBridge")    ros2.rtlBridge(root.selectedDroneId)
                                    }
                                }
                            }
                        }

                        // Takeoff row
                        Row {
                            spacing: 4
                            Rectangle {
                                width: rightCol.width - 64 - 20 - 8; height: 32; radius: 5
                                color: toMa.containsMouse ? "#1e3a5f" : "#1e2535"
                                border.color: toMa.containsMouse ? "#2563eb" : "#334155"; border.width: 1
                                Text { anchors.centerIn: parent; text: "TAKEOFF"; color: "#2563eb"; font.pixelSize: 10; font.weight: Font.Bold }
                                MouseArea { id: toMa; anchors.fill: parent; hoverEnabled: true; onClicked: { if (typeof ros2 !== "undefined" && ros2 && root.selectedDroneId !== "") ros2.takeoffBridge(root.selectedDroneId, parseFloat(toAlt.text) || 10) } }
                            }
                            TextField {
                                id: toAlt; width: 52; height: 32; text: "10"
                                background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" }
                                color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; leftPadding: 6
                            }
                            Text { text: "m"; color: "#64748b"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter }
                        }
                    }
                }
            }
        }
}

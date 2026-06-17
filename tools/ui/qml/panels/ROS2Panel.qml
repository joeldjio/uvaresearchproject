import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components" as Cmp

Item {
    id: root
    anchors.fill: parent

    property string selectedDroneId: ""
    property string _nodeStatus: (typeof ros2 !== "undefined" && ros2) ? ros2.nodeStatus() : "no_ros2"
    property var globalWaypoints: null  // Injected from main.qml

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

                // ── PX4 Connection ──────────────────────────────────
                Text { text: "PX4 CONNECTION"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

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
                            // Show button even if ROS2 not available, but with different color
                            color: {
                                if (root._nodeStatus !== "ok") return "#1e293b"  // Disabled gray
                                return bridgeTogM.containsMouse ? (cfgCol._bridgeActive ? "#7f1d1d" : "#166534") : (cfgCol._bridgeActive ? "#450a0a" : "#14532d")
                            }
                            border.color: {
                                if (root._nodeStatus !== "ok") return "#475569"  // Disabled gray
                                return cfgCol._bridgeActive ? "#ef4444" : "#22c55e"
                            }
                            border.width: 1
                            Behavior on color { ColorAnimation { duration: 120 } }
                            Row {
                                anchors.centerIn: parent; spacing: 6
                                Text {
                                    text: cfgCol._bridgeActive ? "■" : "▶"
                                    color: root._nodeStatus !== "ok" ? "#64748b" : (cfgCol._bridgeActive ? "#fca5a5" : "#86efac")
                                    font.pixelSize: 12
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                                Text {
                                    text: root._nodeStatus !== "ok" ? "Connect to PX4 (ROS2 required)" : (cfgCol._bridgeActive ? "Disconnect" : "Connect to PX4")
                                    color: root._nodeStatus !== "ok" ? "#64748b" : (cfgCol._bridgeActive ? "#fca5a5" : "#86efac")
                                    font.pixelSize: 10
                                    font.weight: Font.Bold
                                    anchors.verticalCenter: parent.verticalCenter
                                }
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

                // ── PX4 SITL Control ──────────────────────────────────────
                Text { text: "PX4 SITL STEUERUNG"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width; height: sitlCol.implicitHeight + 20; radius: 8
                    color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                    Column {
                        id: sitlCol
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                        spacing: 8

                        property bool _sitlRunning: (typeof ros2 !== "undefined" && ros2) ? ros2.isSitlRunning() : false
                        Timer { interval: 1000; running: true; repeat: true
                            onTriggered: sitlCol._sitlRunning = (typeof ros2 !== "undefined" && ros2) ? ros2.isSitlRunning() : false
                        }

                        // PX4 Directory
                        Row {
                            width: parent.width; spacing: 6
                            Text { text: "PX4:"; color: "#64748b"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter; width: 30 }
                            TextField {
                                id: px4DirField; width: parent.width - 36; height: 26
                                text: (typeof ros2 !== "undefined" && ros2) ? ros2.getSitlPx4Dir() : ""
                                placeholderText: "/home/user/PX4-Autopilot"
                                background: Rectangle { color: "#1e2535"; radius: 5; border.color: "#2d3748"; border.width: 1 }
                                color: "#e2e8f0"; font.pixelSize: 9; font.family: "Consolas"; leftPadding: 6
                                onEditingFinished: { if (typeof ros2 !== "undefined" && ros2) ros2.setSitlPx4Dir(text) }
                            }
                        }

                        // Model
                        Row {
                            width: parent.width; spacing: 6
                            Text { text: "Model:"; color: "#64748b"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter; width: 40 }
                            ComboBox {
                                id: modelCombo; width: parent.width - 46; height: 26
                                model: ["x500", "iris", "plane", "standard_vtol"]
                                currentIndex: {
                                    if (typeof ros2 === "undefined" || !ros2) return 0
                                    var m = ros2.getSitlModel()
                                    var idx = model.indexOf(m)
                                    return idx >= 0 ? idx : 0
                                }
                                background: Rectangle { color: "#1e2535"; radius: 5; border.color: "#2d3748"; border.width: 1 }
                                contentItem: Text { text: modelCombo.displayText; color: "#e2e8f0"; font.pixelSize: 10; verticalAlignment: Text.AlignVCenter; leftPadding: 6 }
                                onCurrentTextChanged: { if (typeof ros2 !== "undefined" && ros2) ros2.setSitlModel(currentText) }
                            }
                        }

                        // Namespace
                        Row {
                            width: parent.width; spacing: 6
                            Text { text: "NS:"; color: "#64748b"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter; width: 30 }
                            TextField {
                                id: sitlNsField; width: parent.width - 36; height: 26
                                text: (typeof ros2 !== "undefined" && ros2) ? ros2.getSitlNamespace() : "uav_1"
                                placeholderText: "uav_1"
                                background: Rectangle { color: "#1e2535"; radius: 5; border.color: "#2d3748"; border.width: 1 }
                                color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; leftPadding: 6
                                onEditingFinished: { if (typeof ros2 !== "undefined" && ros2) ros2.setSitlNamespace(text) }
                            }
                        }

                        // Start/Stop Button
                        Rectangle {
                            width: parent.width; height: 32; radius: 6
                            color: sitlTogM.containsMouse ? (sitlCol._sitlRunning ? "#7f1d1d" : "#166534") : (sitlCol._sitlRunning ? "#450a0a" : "#14532d")
                            border.color: sitlCol._sitlRunning ? "#ef4444" : "#22c55e"; border.width: 1
                            Behavior on color { ColorAnimation { duration: 120 } }
                            Row {
                                anchors.centerIn: parent; spacing: 6
                                Text { text: sitlCol._sitlRunning ? "■" : "▶"; color: sitlCol._sitlRunning ? "#fca5a5" : "#86efac"; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                                Text { text: sitlCol._sitlRunning ? qsTr("Stop SITL") : qsTr("Start SITL"); color: sitlCol._sitlRunning ? "#fca5a5" : "#86efac"; font.pixelSize: 10; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                            }
                            MouseArea {
                                id: sitlTogM; anchors.fill: parent; hoverEnabled: true
                                onClicked: {
                                    if (typeof ros2 === "undefined" || !ros2) return
                                    sitlCol._sitlRunning ? ros2.stopSitl() : ros2.startSitl()
                                }
                            }
                        }

                        // Info text
                        Text {
                            width: parent.width
                            text: sitlCol._sitlRunning
                                ? "✓ Running"
                                : "Agent + PX4 + Gazebo"
                            color: sitlCol._sitlRunning ? "#22c55e" : "#64748b"
                            font.pixelSize: 8
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                // Spacer
                Item { width: 1; height: 16 }

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
                                width: topicsCol.width; spacing: 4
                                Rectangle { width: 6; height: 6; radius: 3; anchors.verticalCenter: parent.verticalCenter; color: modelData.includes("/out/") ? "#22c55e" : "#2563eb" }
                                Text {
                                    text: modelData;
                                    color: "#64748b";
                                    font.pixelSize: 8;
                                    font.family: "Consolas";
                                    anchors.verticalCenter: parent.verticalCenter;
                                    elide: Text.ElideMiddle;
                                    width: topicsCol.width - 40
                                }
                            }
                        }

                        Text { visible: topicsCol.topics.length === 0; text: "Kein Drone ausgewählt"; color: "#374151"; font.pixelSize: 10; anchors.horizontalCenter: parent.horizontalCenter }
                    }
                }

                // Spacer
                Item { width: 1; height: 16 }

                // ── Formation Control ─────────────────────────────────────
                Text { text: "FORMATION CONTROL"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width; height: formCol.implicitHeight + 20; radius: 8
                    color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                    Column {
                        id: formCol
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                        spacing: 8

                        property bool _formActive: (typeof ros2 !== "undefined" && ros2) ? ros2.isFormationActive() : false
                        Timer { interval: 500; running: true; repeat: true
                            onTriggered: formCol._formActive = (typeof ros2 !== "undefined" && ros2) ? ros2.isFormationActive() : false
                        }

                        // Leader selection
                        Row {
                            width: parent.width; spacing: 6
                            Text { text: "Leader:"; color: "#64748b"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter; width: 50 }
                            ComboBox {
                                id: leaderCombo; width: parent.width - 56; height: 26
                                model: (typeof swarm !== "undefined" && swarm) ? swarm.droneIds() : []
                                background: Rectangle { color: "#1e2535"; radius: 5; border.color: "#2d3748"; border.width: 1 }
                                contentItem: Text { text: leaderCombo.displayText; color: "#e2e8f0"; font.pixelSize: 10; verticalAlignment: Text.AlignVCenter; leftPadding: 6 }
                            }
                        }

                        // Followers (multi-select would be complex, so just show count)
                        Text {
                            width: parent.width
                            text: "Followers: All other drones"
                            color: "#64748b"
                            font.pixelSize: 9
                        }

                        // Formation shape
                        Row {
                            width: parent.width; spacing: 6
                            Text { text: "Shape:"; color: "#64748b"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter; width: 50 }
                            ComboBox {
                                id: shapeCombo; width: parent.width - 56; height: 26
                                model: ["line", "v", "grid", "circle", "wedge"]
                                currentIndex: 1  // Default to V
                                background: Rectangle { color: "#1e2535"; radius: 5; border.color: "#2d3748"; border.width: 1 }
                                contentItem: Text { text: shapeCombo.displayText; color: "#e2e8f0"; font.pixelSize: 10; verticalAlignment: Text.AlignVCenter; leftPadding: 6 }
                            }
                        }

                        // Spacing slider
                        Row {
                            width: parent.width; spacing: 6
                            Text { text: "Spacing:"; color: "#64748b"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter; width: 50 }
                            Slider {
                                id: spacingSlider
                                width: parent.width - 100
                                from: 2.0; to: 20.0; value: 5.0; stepSize: 0.5
                                background: Rectangle {
                                    x: spacingSlider.leftPadding
                                    y: spacingSlider.topPadding + spacingSlider.availableHeight / 2 - height / 2
                                    width: spacingSlider.availableWidth; height: 4; radius: 2
                                    color: "#2d3748"
                                    Rectangle {
                                        width: spacingSlider.visualPosition * parent.width; height: parent.height; radius: 2
                                        color: "#3b82f6"
                                    }
                                }
                                handle: Rectangle {
                                    x: spacingSlider.leftPadding + spacingSlider.visualPosition * (spacingSlider.availableWidth - width)
                                    y: spacingSlider.topPadding + spacingSlider.availableHeight / 2 - height / 2
                                    width: 16; height: 16; radius: 8
                                    color: spacingSlider.pressed ? "#60a5fa" : "#3b82f6"
                                    border.color: "#1e293b"; border.width: 1
                                }
                            }
                            Text { text: spacingSlider.value.toFixed(1) + "m"; color: "#e2e8f0"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter; width: 40 }
                        }

                        // Start/Stop button
                        Rectangle {
                            width: parent.width; height: 32; radius: 6
                            color: formTogM.containsMouse ? (formCol._formActive ? "#7f1d1d" : "#166534") : (formCol._formActive ? "#450a0a" : "#14532d")
                            border.color: formCol._formActive ? "#ef4444" : "#22c55e"; border.width: 1
                            Behavior on color { ColorAnimation { duration: 120 } }
                            Row {
                                anchors.centerIn: parent; spacing: 6
                                Text { text: formCol._formActive ? "■" : "▶"; color: formCol._formActive ? "#fca5a5" : "#86efac"; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                                Text { text: formCol._formActive ? "Stop Formation" : "Start Formation"; color: formCol._formActive ? "#fca5a5" : "#86efac"; font.pixelSize: 10; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                            }
                            MouseArea {
                                id: formTogM; anchors.fill: parent; hoverEnabled: true
                                onClicked: {
                                    if (typeof ros2 === "undefined" || !ros2) return
                                    if (typeof swarm === "undefined" || !swarm) return
                                    
                                    if (formCol._formActive) {
                                        ros2.stopFormation()
                                    } else {
                                        var allDrones = swarm.droneIds()
                                        if (allDrones.length < 2) {
                                            console.log("Need at least 2 drones for formation")
                                            return
                                        }
                                        var leader = leaderCombo.currentText
                                        var followers = allDrones.filter(function(id) { return id !== leader })
                                        ros2.startFormation(leader, followers, shapeCombo.currentText, spacingSlider.value)
                                    }
                                }
                            }
                        }

                        // Control buttons (only when active)
                        Row {
                            width: parent.width; spacing: 4
                            visible: formCol._formActive

                            Rectangle {
                                width: (parent.width - 8) / 3; height: 28; radius: 5
                                color: armM.containsMouse ? "#166534" : "#14532d"
                                border.color: "#22c55e"; border.width: 1
                                Text { text: "ARM ALL"; color: "#86efac"; font.pixelSize: 9; font.weight: Font.Bold; anchors.centerIn: parent }
                                MouseArea {
                                    id: armM; anchors.fill: parent; hoverEnabled: true
                                    onClicked: { if (typeof ros2 !== "undefined" && ros2) ros2.armFormation() }
                                }
                            }

                            Rectangle {
                                width: (parent.width - 8) / 3; height: 28; radius: 5
                                color: offbM.containsMouse ? "#1e40af" : "#1e3a8a"
                                border.color: "#3b82f6"; border.width: 1
                                Text { text: "OFFBOARD"; color: "#93c5fd"; font.pixelSize: 9; font.weight: Font.Bold; anchors.centerIn: parent }
                                MouseArea {
                                    id: offbM; anchors.fill: parent; hoverEnabled: true
                                    onClicked: { if (typeof ros2 !== "undefined" && ros2) ros2.enableOffboardFormation() }
                                }
                            }

                            Rectangle {
                                width: (parent.width - 8) / 3; height: 28; radius: 5
                                color: disarmM.containsMouse ? "#7f1d1d" : "#450a0a"
                                border.color: "#ef4444"; border.width: 1
                                Text { text: "DISARM"; color: "#fca5a5"; font.pixelSize: 9; font.weight: Font.Bold; anchors.centerIn: parent }
                                MouseArea {
                                    id: disarmM; anchors.fill: parent; hoverEnabled: true
                                    onClicked: { if (typeof ros2 !== "undefined" && ros2) ros2.disarmFormation() }
                                }
                            }
                        }

                        // Position controls (only when active)
                        Column {
                            width: parent.width; spacing: 4
                            visible: formCol._formActive

                            Text { text: "Leader Position:"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold }

                            Row {
                                width: parent.width; spacing: 4
                                Text { text: "N:"; color: "#64748b"; font.pixelSize: 9; width: 15 }
                                TextField {
                                    id: formNorthField; width: (parent.width - 80) / 3; height: 24
                                    text: "0"; placeholderText: "0"
                                    background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748"; border.width: 1 }
                                    color: "#e2e8f0"; font.pixelSize: 9; leftPadding: 4
                                }
                                Text { text: "E:"; color: "#64748b"; font.pixelSize: 9; width: 15 }
                                TextField {
                                    id: formEastField; width: (parent.width - 80) / 3; height: 24
                                    text: "0"; placeholderText: "0"
                                    background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748"; border.width: 1 }
                                    color: "#e2e8f0"; font.pixelSize: 9; leftPadding: 4
                                }
                                Text { text: "Alt:"; color: "#64748b"; font.pixelSize: 9; width: 20 }
                                TextField {
                                    id: formAltField; width: (parent.width - 80) / 3; height: 24
                                    text: "10"; placeholderText: "10"
                                    background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748"; border.width: 1 }
                                    color: "#e2e8f0"; font.pixelSize: 9; leftPadding: 4
                                }
                            }

                            Rectangle {
                                width: parent.width; height: 26; radius: 5
                                color: setPosM.containsMouse ? "#1e40af" : "#1e3a8a"
                                border.color: "#3b82f6"; border.width: 1
                                Text { text: "Set Position"; color: "#93c5fd"; font.pixelSize: 9; font.weight: Font.Bold; anchors.centerIn: parent }
                                MouseArea {
                                    id: setPosM; anchors.fill: parent; hoverEnabled: true
                                    onClicked: {
                                        if (typeof ros2 !== "undefined" && ros2) {
                                            ros2.setFormationLeaderPosition(
                                                parseFloat(formNorthField.text),
                                                parseFloat(formEastField.text),
                                                parseFloat(formAltField.text),
                                                0.0  // yaw
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // Spacer
                Item { width: 1; height: 16 }

                // ── Bag Recording ─────────────────────────────────────
                Text { text: "BAG RECORDING"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width; height: bagCol.implicitHeight + 20; radius: 8
                    color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                    Column {
                        id: bagCol
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                        spacing: 8

                        property bool _recording: (typeof ros2 !== "undefined" && ros2) ? ros2.isBagRecording() : false
                        property var _status: (typeof ros2 !== "undefined" && ros2) ? ros2.getBagRecordingStatus() : ({})
                        
                        Timer { interval: 500; running: true; repeat: true
                            onTriggered: {
                                bagCol._recording = (typeof ros2 !== "undefined" && ros2) ? ros2.isBagRecording() : false
                                bagCol._status = (typeof ros2 !== "undefined" && ros2) ? ros2.getBagRecordingStatus() : ({})
                            }
                        }

                        // Topic selection
                        Text { text: "Topics to record:"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold }
                        
                        Column {
                            width: parent.width; spacing: 2
                            
                            CheckBox {
                                id: topicOdom
                                text: "/fmu/out/vehicle_odometry"
                                checked: true
                                contentItem: Text { 
                                    text: topicOdom.text
                                    color: "#e2e8f0"
                                    font.pixelSize: 9
                                    leftPadding: topicOdom.indicator.width + 4
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                            
                            CheckBox {
                                id: topicStatus
                                text: "/fmu/out/vehicle_status"
                                checked: true
                                contentItem: Text { 
                                    text: topicStatus.text
                                    color: "#e2e8f0"
                                    font.pixelSize: 9
                                    leftPadding: topicStatus.indicator.width + 4
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                            
                            CheckBox {
                                id: topicBattery
                                text: "/fmu/out/battery_status"
                                checked: false
                                contentItem: Text { 
                                    text: topicBattery.text
                                    color: "#e2e8f0"
                                    font.pixelSize: 9
                                    leftPadding: topicBattery.indicator.width + 4
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                            
                            CheckBox {
                                id: topicGPS
                                text: "/fmu/out/vehicle_gps_position"
                                checked: false
                                contentItem: Text { 
                                    text: topicGPS.text
                                    color: "#e2e8f0"
                                    font.pixelSize: 9
                                    leftPadding: topicGPS.indicator.width + 4
                                    verticalAlignment: Text.AlignVCenter
                                }
                            }
                        }

                        // Start/Stop button
                        Rectangle {
                            width: parent.width; height: 32; radius: 6
                            color: bagTogM.containsMouse ? (bagCol._recording ? "#7f1d1d" : "#166534") : (bagCol._recording ? "#450a0a" : "#14532d")
                            border.color: bagCol._recording ? "#ef4444" : "#22c55e"; border.width: 1
                            Behavior on color { ColorAnimation { duration: 120 } }
                            Row {
                                anchors.centerIn: parent; spacing: 6
                                Text { text: bagCol._recording ? "⏹" : "⏺"; color: bagCol._recording ? "#fca5a5" : "#86efac"; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
                                Text { text: bagCol._recording ? "Stop Recording" : "Start Recording"; color: bagCol._recording ? "#fca5a5" : "#86efac"; font.pixelSize: 10; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                            }
                            MouseArea {
                                id: bagTogM; anchors.fill: parent; hoverEnabled: true
                                onClicked: {
                                    if (typeof ros2 === "undefined" || !ros2) return
                                    
                                    if (bagCol._recording) {
                                        ros2.stopBagRecording()
                                    } else {
                                        // Collect selected topics
                                        var topics = []
                                        if (topicOdom.checked) topics.push(topicOdom.text)
                                        if (topicStatus.checked) topics.push(topicStatus.text)
                                        if (topicBattery.checked) topics.push(topicBattery.text)
                                        if (topicGPS.checked) topics.push(topicGPS.text)
                                        
                                        if (topics.length === 0) {
                                            console.log("[BAG] No topics selected")
                                            return
                                        }
                                        
                                        ros2.startBagRecording(topics, "", "zstd")
                                    }
                                }
                            }
                        }

                        // Recording status (only when active)
                        Column {
                            width: parent.width; spacing: 4
                            visible: bagCol._recording

                            Text { 
                                text: "Recording Status:"
                                color: "#64748b"
                                font.pixelSize: 9
                                font.weight: Font.Bold
                            }

                            Row {
                                width: parent.width
                                spacing: 4
                                Text { text: "Duration:"; color: "#64748b"; font.pixelSize: 9; width: 60 }
                                Text { 
                                    text: bagCol._status.duration_sec ? bagCol._status.duration_sec.toFixed(1) + "s" : "0.0s"
                                    color: "#e2e8f0"
                                    font.pixelSize: 9
                                }
                            }

                            Row {
                                width: parent.width
                                spacing: 4
                                Text { text: "Size:"; color: "#64748b"; font.pixelSize: 9; width: 60 }
                                Text {
                                    text: bagCol._status.size_mb ? bagCol._status.size_mb.toFixed(2) + " MB" : "0.00 MB"
                                    color: "#e2e8f0"
                                    font.pixelSize: 9
                                }
                            }

                            Row {
                                width: parent.width
                                spacing: 4
                                Text { text: "Path:"; color: "#64748b"; font.pixelSize: 9; width: 60 }
                                Text {
                                    text: bagCol._status.bag_path ? bagCol._status.bag_path : "./bags/"
                                    color: "#e2e8f0"
                                    font.pixelSize: 8
                                    elide: Text.ElideMiddle
                                    width: parent.width - 64
                                }
                            }
                        }

                        // Info text
                        Text {
                            width: parent.width
                            text: "◉ Bags saved to: <project_root>/bags/"
                            color: "#64748b"
                            font.pixelSize: 8
                            wrapMode: Text.WordWrap
                        }
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

                // ── Frame Conversion Debug ────────────────────────────────
                Text { text: "FRAME CONVERSION (NED ↔ ENU)"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width; height: frameCol.implicitHeight + 16; radius: 8
                    color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                    property var frameData: ({})
                    Timer {
                        interval: 200; running: true; repeat: true
                        onTriggered: {
                            if (typeof ros2 === "undefined" || !ros2 || root.selectedDroneId === "") return
                            parent.frameData = ros2.getFrameData(root.selectedDroneId)
                        }
                    }

                    Column {
                        id: frameCol
                        anchors { fill: parent; margins: 10 }
                        spacing: 8

                        // Info text
                        Text {
                            width: parent.width
                            text: "PX4 uses NED (North-East-Down), ROS2 uses ENU (East-North-Up). Conversion: [E,N,U] = [E,N,-D]"
                            color: "#64748b"; font.pixelSize: 8
                            wrapMode: Text.WordWrap
                        }

                        // Side-by-side comparison
                        Row {
                            width: parent.width; spacing: 10

                            // NED (PX4)
                            Column {
                                width: (parent.width - 10) / 2
                                spacing: 4

                                Rectangle {
                                    width: parent.width; height: 24; radius: 4
                                    color: "#7f1d1d"; border.color: "#ef4444"; border.width: 1
                                    Text {
                                        anchors.centerIn: parent
                                        text: "NED (PX4 Native)"
                                        color: "#fca5a5"; font.pixelSize: 10; font.weight: Font.Bold
                                    }
                                }

                                Column {
                                    width: parent.width; spacing: 2
                                    Repeater {
                                        model: [
                                            { key: "ned_north", label: "North", unit: "m", color: "#ef4444" },
                                            { key: "ned_east",  label: "East",  unit: "m", color: "#ef4444" },
                                            { key: "ned_down",  label: "Down",  unit: "m", color: "#ef4444" },
                                        ]
                                        delegate: Row {
                                            width: parent.width; height: 20; spacing: 4
                                            Text {
                                                text: modelData.label + ":"
                                                color: "#94a3b8"; font.pixelSize: 9; width: 50
                                            }
                                            Text {
                                                text: {
                                                    var val = frameCol.parent.frameData[modelData.key]
                                                    return val !== undefined ? val.toFixed(2) + modelData.unit : "—"
                                                }
                                                color: modelData.color
                                                font.pixelSize: 10; font.family: "Consolas"; font.weight: Font.Bold
                                            }
                                        }
                                    }
                                }
                            }

                            // ENU (ROS2)
                            Column {
                                width: (parent.width - 10) / 2
                                spacing: 4

                                Rectangle {
                                    width: parent.width; height: 24; radius: 4
                                    color: "#14532d"; border.color: "#22c55e"; border.width: 1
                                    Text {
                                        anchors.centerIn: parent
                                        text: "ENU (ROS2 Standard)"
                                        color: "#86efac"; font.pixelSize: 10; font.weight: Font.Bold
                                    }
                                }

                                Column {
                                    width: parent.width; spacing: 2
                                    Repeater {
                                        model: [
                                            { key: "enu_east",  label: "East",  unit: "m", color: "#22c55e" },
                                            { key: "enu_north", label: "North", unit: "m", color: "#22c55e" },
                                            { key: "enu_up",    label: "Up",    unit: "m", color: "#22c55e" },
                                        ]
                                        delegate: Row {
                                            width: parent.width; height: 20; spacing: 4
                                            Text {
                                                text: modelData.label + ":"
                                                color: "#94a3b8"; font.pixelSize: 9; width: 50
                                            }
                                            Text {
                                                text: {
                                                    var val = frameCol.parent.frameData[modelData.key]
                                                    return val !== undefined ? val.toFixed(2) + modelData.unit : "—"
                                                }
                                                color: modelData.color
                                                font.pixelSize: 10; font.family: "Consolas"; font.weight: Font.Bold
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // 2D Visualization (Top-down view)
                        Rectangle {
                            width: parent.width; height: 180; radius: 6
                            color: "#0d1117"; border.color: "#2d3748"; border.width: 1

                            Canvas {
                                id: frameCanvas
                                anchors.fill: parent
                                anchors.margins: 5

                                property var frameData: frameCol.parent.frameData

                                onFrameDataChanged: requestPaint()

                                onPaint: {
                                    var ctx = getContext("2d")
                                    ctx.clearRect(0, 0, width, height)

                                    var centerX = width / 2
                                    var centerY = height / 2
                                    var scale = 15  // pixels per meter

                                    // Draw grid
                                    ctx.strokeStyle = "#1e293b"
                                    ctx.lineWidth = 1
                                    for (var i = -10; i <= 10; i++) {
                                        if (i === 0) continue
                                        // Vertical lines
                                        ctx.beginPath()
                                        ctx.moveTo(centerX + i * scale, 0)
                                        ctx.lineTo(centerX + i * scale, height)
                                        ctx.stroke()
                                        // Horizontal lines
                                        ctx.beginPath()
                                        ctx.moveTo(0, centerY + i * scale)
                                        ctx.lineTo(width, centerY + i * scale)
                                        ctx.stroke()
                                    }

                                    // Draw axes
                                    // North (red, up)
                                    ctx.strokeStyle = "#ef4444"
                                    ctx.lineWidth = 2
                                    ctx.beginPath()
                                    ctx.moveTo(centerX, centerY)
                                    ctx.lineTo(centerX, centerY - 40)
                                    ctx.stroke()
                                    ctx.fillStyle = "#ef4444"
                                    ctx.font = "bold 10px sans-serif"
                                    ctx.fillText("N", centerX + 5, centerY - 35)

                                    // East (red, right)
                                    ctx.strokeStyle = "#ef4444"
                                    ctx.beginPath()
                                    ctx.moveTo(centerX, centerY)
                                    ctx.lineTo(centerX + 40, centerY)
                                    ctx.stroke()
                                    ctx.fillStyle = "#ef4444"
                                    ctx.fillText("E", centerX + 35, centerY - 5)

                                    // Draw drone position
                                    var ned_n = frameData.ned_north || 0
                                    var ned_e = frameData.ned_east || 0
                                    var droneX = centerX + ned_e * scale
                                    var droneY = centerY - ned_n * scale  // Invert Y for screen coords

                                    // Drone circle
                                    ctx.fillStyle = "#2563eb"
                                    ctx.beginPath()
                                    ctx.arc(droneX, droneY, 6, 0, 2 * Math.PI)
                                    ctx.fill()

                                    // Line from origin to drone
                                    ctx.strokeStyle = "#3b82f6"
                                    ctx.lineWidth = 1
                                    ctx.setLineDash([3, 3])
                                    ctx.beginPath()
                                    ctx.moveTo(centerX, centerY)
                                    ctx.lineTo(droneX, droneY)
                                    ctx.stroke()
                                    ctx.setLineDash([])

                                    // Position label
                                    ctx.fillStyle = "#93c5fd"
                                    ctx.font = "9px Consolas"
                                    ctx.fillText("(" + ned_n.toFixed(1) + ", " + ned_e.toFixed(1) + ")", droneX + 10, droneY)
                                }
                            }

                            Text {
                                anchors { bottom: parent.bottom; left: parent.left; margins: 5 }
                                text: "Top-down view (NED frame)"
                                color: "#475569"; font.pixelSize: 8
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

                // ── Mission Management ────────────────────────────────────
                Text { text: "MISSION MANAGEMENT"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

                Rectangle {
                    width: parent.width; height: missionCol.implicitHeight + 20; radius: 8
                    color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                    Column {
                        id: missionCol
                        anchors { fill: parent; margins: 10 }
                        spacing: 8

                        // Mission Status Display
                        property var missionStatus: ({})
                        Timer {
                            interval: 500; running: true; repeat: true
                            onTriggered: {
                                if (typeof ros2 === "undefined" || !ros2 || root.selectedDroneId === "") return
                                missionCol.missionStatus = ros2.getMissionStatus(root.selectedDroneId)
                            }
                        }

                        // Status indicator
                        Rectangle {
                            width: parent.width; height: 50; radius: 6
                            color: "#0d1117"; border.color: missionCol.missionStatus.active ? "#22c55e" : "#374151"; border.width: 1

                            Column {
                                anchors { fill: parent; margins: 8 }
                                spacing: 4

                                Row {
                                    spacing: 6
                                    Rectangle {
                                        width: 8; height: 8; radius: 4; anchors.verticalCenter: parent.verticalCenter
                                        color: (missionCol.missionStatus.active || false) ? "#22c55e" : "#6b7280"
                                        SequentialAnimation on opacity {
                                            running: missionCol.missionStatus.active || false
                                            loops: Animation.Infinite
                                            NumberAnimation { to: 0.3; duration: 800 }
                                            NumberAnimation { to: 1.0; duration: 800 }
                                        }
                                    }
                                    Text {
                                        text: missionCol.missionStatus.finished ? "Mission Complete" :
                                              missionCol.missionStatus.failure ? "Mission Failed" :
                                              missionCol.missionStatus.active ? "Mission Active" : "No Mission"
                                        color: missionCol.missionStatus.finished ? "#22c55e" :
                                               missionCol.missionStatus.failure ? "#ef4444" :
                                               missionCol.missionStatus.active ? "#22c55e" : "#6b7280"
                                        font.pixelSize: 10; font.weight: Font.Bold
                                    }
                                }

                                // Progress bar
                                Rectangle {
                                    width: parent.width; height: 20; radius: 4
                                    color: "#1e2535"; border.color: "#2d3748"; border.width: 1
                                    visible: missionCol.missionStatus.total_count > 0

                                    Rectangle {
                                        width: missionCol.missionStatus.total_count > 0 ?
                                               (parent.width - 2) * (missionCol.missionStatus.current_seq / missionCol.missionStatus.total_count) : 0
                                        height: parent.height - 2; radius: 3
                                        anchors { left: parent.left; top: parent.top; margins: 1 }
                                        color: "#22c55e"
                                        Behavior on width { NumberAnimation { duration: 200 } }
                                    }

                                    Text {
                                        anchors.centerIn: parent
                                        text: "WP " + (missionCol.missionStatus.current_seq + 1) + " / " + missionCol.missionStatus.total_count
                                        color: "#e2e8f0"; font.pixelSize: 9; font.weight: Font.Bold
                                    }
                                }
                            }
                        }

                        // Mission Control Buttons
                        Row {
                            width: parent.width; spacing: 4

                            Rectangle {
                                width: (parent.width - 8) / 3; height: 28; radius: 5
                                color: startMa.containsMouse ? "#166534" : "#14532d"
                                border.color: "#22c55e"; border.width: 1
                                Text { anchors.centerIn: parent; text: "▶ START"; color: "#86efac"; font.pixelSize: 9; font.weight: Font.Bold }
                                MouseArea {
                                    id: startMa; anchors.fill: parent; hoverEnabled: true
                                    onClicked: {
                                        if (typeof ros2 !== "undefined" && ros2 && root.selectedDroneId !== "")
                                            ros2.startMission(root.selectedDroneId)
                                    }
                                }
                            }

                            Rectangle {
                                width: (parent.width - 8) / 3; height: 28; radius: 5
                                color: pauseMa.containsMouse ? "#c2410c" : "#9a3412"
                                border.color: "#f97316"; border.width: 1
                                Text { anchors.centerIn: parent; text: "⏸ PAUSE"; color: "#fed7aa"; font.pixelSize: 9; font.weight: Font.Bold }
                                MouseArea {
                                    id: pauseMa; anchors.fill: parent; hoverEnabled: true
                                    onClicked: {
                                        if (typeof ros2 !== "undefined" && ros2 && root.selectedDroneId !== "")
                                            ros2.pauseMission(root.selectedDroneId)
                                    }
                                }
                            }

                            Rectangle {
                                width: (parent.width - 8) / 3; height: 28; radius: 5
                                color: clearMa.containsMouse ? "#7f1d1d" : "#450a0a"
                                border.color: "#ef4444"; border.width: 1
                                Text { anchors.centerIn: parent; text: "✕ CLEAR"; color: "#fca5a5"; font.pixelSize: 9; font.weight: Font.Bold }
                                MouseArea {
                                    id: clearMa; anchors.fill: parent; hoverEnabled: true
                                    onClicked: {
                                        if (typeof ros2 !== "undefined" && ros2 && root.selectedDroneId !== "")
                                            ros2.clearMission(root.selectedDroneId)
                                    }
                                }
                            }
                        }

                        // Upload Mission Button
                        Rectangle {
                            width: parent.width; height: 32; radius: 5
                            color: uploadMa.containsMouse ? "#1e3a5f" : "#1e2535"
                            border.color: "#2563eb"; border.width: 1
                            Text { anchors.centerIn: parent; text: "⬆ UPLOAD MISSION"; color: "#93c5fd"; font.pixelSize: 10; font.weight: Font.Bold }
                            MouseArea {
                                id: uploadMa; anchors.fill: parent; hoverEnabled: true
                                onClicked: {
                                    // Open mission upload dialog
                                    missionDialog.open()
                                }
                            }
                        }

                        // Info text
                        Text {
                            width: parent.width
                            text: "Upload waypoints, then ARM + TAKEOFF before starting mission"
                            color: "#64748b"; font.pixelSize: 8
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }

        // ── Mission Upload Dialog ─────────────────────────────────────────────
        Dialog {
            id: missionDialog
            title: "Upload Mission"
            modal: true
            anchors.centerIn: parent
            width: 500; height: 600

            background: Rectangle {
                color: "#1a2035"; radius: 8
                border.color: "#2d3748"; border.width: 1
            }

            // Local waypoint model (copy from global + manual additions)
            ListModel { id: dialogWaypoints }

            onOpened: {
                // Load waypoints from map when dialog opens
                dialogWaypoints.clear()
                if (root.globalWaypoints && root.globalWaypoints.count > 0) {
                    for (var i = 0; i < root.globalWaypoints.count; i++) {
                        var wp = root.globalWaypoints.get(i)
                        dialogWaypoints.append({
                            lat: wp.lat,
                            lon: wp.lon,
                            alt: wp.alt,
                            hold_time: 2.0
                        })
                    }
                }
            }

            Column {
                anchors.fill: parent
                spacing: 10

                Text {
                    text: "Mission Waypoints"
                    color: "#e2e8f0"; font.pixelSize: 12; font.weight: Font.Bold
                }

                Text {
                    text: dialogWaypoints.count > 0 ?
                          dialogWaypoints.count + " waypoint(s) from map" :
                          "No waypoints set. Add waypoints on the map first or use test mission."
                    color: "#94a3b8"; font.pixelSize: 9
                    wrapMode: Text.WordWrap; width: parent.width
                }

                // Waypoint list
                Rectangle {
                    width: parent.width; height: 300
                    color: "#0d1117"; radius: 6
                    border.color: "#2d3748"; border.width: 1

                    ScrollView {
                        anchors.fill: parent
                        anchors.margins: 5
                        clip: true

                        ListView {
                            id: waypointList
                            model: dialogWaypoints
                            spacing: 4

                            delegate: Rectangle {
                                width: waypointList.width; height: 60; radius: 4
                                color: "#1e2535"; border.color: "#334155"; border.width: 1

                                Column {
                                    anchors { fill: parent; margins: 8 }
                                    spacing: 2

                                    Row {
                                        spacing: 10
                                        Text {
                                            text: "WP" + (index + 1)
                                            color: "#2563eb"; font.pixelSize: 10; font.weight: Font.Bold
                                            width: 30
                                        }
                                        Text {
                                            text: "Lat: " + model.lat.toFixed(6) + "  Lon: " + model.lon.toFixed(6)
                                            color: "#e2e8f0"; font.pixelSize: 9
                                        }
                                    }
                                    Row {
                                        spacing: 10
                                        Text { text: "Alt: " + model.alt.toFixed(1) + "m"; color: "#94a3b8"; font.pixelSize: 8; width: 80 }
                                        Text { text: "Hold: " + model.hold_time.toFixed(1) + "s"; color: "#94a3b8"; font.pixelSize: 8 }
                                    }
                                }

                                // Delete button
                                Rectangle {
                                    anchors { right: parent.right; top: parent.top; margins: 4 }
                                    width: 20; height: 20; radius: 3
                                    color: delMa.containsMouse ? "#7f1d1d" : "#450a0a"
                                    border.color: "#ef4444"; border.width: 1
                                    Text { anchors.centerIn: parent; text: "✕"; color: "#fca5a5"; font.pixelSize: 10 }
                                    MouseArea {
                                        id: delMa; anchors.fill: parent; hoverEnabled: true
                                        onClicked: dialogWaypoints.remove(index)
                                    }
                                }
                            }
                        }
                    }
                }

                // Add waypoint manually
                Row {
                    spacing: 5
                    TextField {
                        id: newLat; width: 100; height: 28
                        placeholderText: "Latitude"
                        background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" }
                        color: "#e2e8f0"; font.pixelSize: 9
                    }
                    TextField {
                        id: newLon; width: 100; height: 28
                        placeholderText: "Longitude"
                        background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" }
                        color: "#e2e8f0"; font.pixelSize: 9
                    }
                    TextField {
                        id: newAlt; width: 60; height: 28
                        placeholderText: "Alt"
                        text: "15"
                        background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" }
                        color: "#e2e8f0"; font.pixelSize: 9
                    }
                    Button {
                        text: "+ Add"
                        height: 28
                        onClicked: {
                            var lat = parseFloat(newLat.text)
                            var lon = parseFloat(newLon.text)
                            var alt = parseFloat(newAlt.text) || 15.0
                            if (!isNaN(lat) && !isNaN(lon)) {
                                dialogWaypoints.append({
                                    lat: lat, lon: lon, alt: alt, hold_time: 2.0
                                })
                                newLat.text = ""
                                newLon.text = ""
                            }
                        }
                    }
                }

                // Action buttons
                Row {
                    spacing: 10
                    Button {
                        text: "Upload Mission (" + dialogWaypoints.count + " WP)"
                        enabled: dialogWaypoints.count > 0
                        onClicked: {
                            console.log("[Mission Upload] Button clicked")
                            console.log("[Mission Upload] ros2 defined:", typeof ros2 !== "undefined")
                            console.log("[Mission Upload] selectedDroneId:", root.selectedDroneId)
                            console.log("[Mission Upload] waypoint count:", dialogWaypoints.count)
                            
                            if (typeof ros2 === "undefined" || !ros2) {
                                console.log("[Mission Upload] ERROR: ros2 not available")
                                return
                            }
                            if (root.selectedDroneId === "") {
                                console.log("[Mission Upload] ERROR: No drone selected")
                                return
                            }
                            
                            // Convert to array
                            var waypoints = []
                            for (var i = 0; i < dialogWaypoints.count; i++) {
                                var wp = dialogWaypoints.get(i)
                                waypoints.push({
                                    "lat": wp.lat,
                                    "lon": wp.lon,
                                    "alt": wp.alt,
                                    "hold_time": wp.hold_time
                                })
                            }
                            
                            console.log("[Mission Upload] Calling ros2.uploadMission with", waypoints.length, "waypoints")
                            var success = ros2.uploadMission(root.selectedDroneId, waypoints)
                            console.log("[Mission Upload] Upload result:", success)
                            
                            if (success) {
                                console.log("[Mission Upload] Success! Closing dialog")
                                missionDialog.close()
                            } else {
                                console.log("[Mission Upload] Upload failed")
                            }
                        }
                    }
                    Button {
                        text: "Load Test Mission"
                        onClicked: {
                            dialogWaypoints.clear()
                            // Test mission waypoints (Zurich area)
                            dialogWaypoints.append({ "lat": 47.397742, "lon": 8.545594, "alt": 15.0, "hold_time": 2.0 })
                            dialogWaypoints.append({ "lat": 47.397842, "lon": 8.545694, "alt": 20.0, "hold_time": 3.0 })
                            dialogWaypoints.append({ "lat": 47.397942, "lon": 8.545794, "alt": 15.0, "hold_time": 2.0 })
                        }
                    }
                    Button {
                        text: "Cancel"
                        onClicked: missionDialog.close()
                    }
                }
            }
        }
}

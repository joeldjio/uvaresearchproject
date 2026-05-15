import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components" as Cmp

Item {
    id: root
    anchors.fill: parent

    property string selectedDroneId: typeof swarm !== "undefined" ? (swarm.droneIds().length > 0 ? swarm.droneIds()[0] : "") : ""

    function isObservation(did) {
        if (!did || typeof swarm === "undefined" || !swarm) return false
        return swarm.droneType(did) === "observation"
    }

    ScrollView {
        id: sv
        anchors { fill: parent; margins: 12 }
        clip: true
        contentWidth: availableWidth
        contentHeight: colMain.implicitHeight
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        Column {
            id: colMain
            width: sv.availableWidth
            spacing: 10

            // ── Drone selector ──────────────────────────────────────────
            Text { text: "GIMBAL / KAMERA"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

            Rectangle {
                width: parent.width; height: 36; radius: 8
                color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                Row {
                    anchors { fill: parent; leftMargin: 10; rightMargin: 10 }
                    spacing: 8

                    Text { text: "Drone:"; color: "#64748b"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter }
                    ComboBox {
                        id: droneCombo
                        width: parent.width - 60; height: 26
                        model: (typeof swarm !== "undefined" && swarm) ? swarm.droneIds() : []
                        background: Rectangle { color: "#1e2535"; radius: 5; border.color: "#2d3748"; border.width: 1 }
                        contentItem: Text { text: droneCombo.displayText; color: "#e2e8f0"; font.pixelSize: 11; verticalAlignment: Text.AlignVCenter; leftPadding: 6 }
                        onCurrentTextChanged: { if (currentText) Cmp.AppState.selectedDroneId = currentText }
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }

            // ── Observation-only warning ────────────────────────────────
            Rectangle {
                width: parent.width; height: 34; radius: 6
                color: "#78350f22"
                border.color: "#f59e0b"; border.width: 1
                visible: root.selectedDroneId !== "" && !isObservation(root.selectedDroneId)

                Row {
                    anchors { fill: parent; leftMargin: 10 }
                    spacing: 6
                    Text { text: "⚠"; color: "#f59e0b"; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
                    Text {
                        text: "Gimbal nur für Observation UAV (Drone-Typ = observation)"
                        color: "#fcd34d"; font.pixelSize: 10
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }

            // ── Gimbal controls ─────────────────────────────────────────
            Rectangle {
                width: parent.width; height: gimbalCol.implicitHeight + 20; radius: 8
                color: "#1a2035"; border.color: "#2d3748"; border.width: 1
                enabled: isObservation(root.selectedDroneId)
                opacity: enabled ? 1.0 : 0.4

                Column {
                    id: gimbalCol
                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
                    spacing: 10

                    // PITCH
                    Column {
                        width: parent.width; spacing: 3
                        Row {
                            width: parent.width
                            Text { text: "PITCH"; color: "#94a3b8"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1; anchors.verticalCenter: parent.verticalCenter }
                            Item { width: parent.width - 80; height: 1 }
                            Text { text: pitchSlider.value.toFixed(0) + "°"; color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; anchors.verticalCenter: parent.verticalCenter }
                        }
                        Slider {
                            id: pitchSlider
                            width: parent.width; from: -90; to: 0; value: 0
                            background: Rectangle {
                                x: pitchSlider.leftPadding; y: pitchSlider.topPadding + pitchSlider.availableHeight / 2 - height / 2
                                width: pitchSlider.availableWidth; height: 4; radius: 2; color: "#1e293b"
                                Rectangle { width: pitchSlider.visualPosition * parent.width; height: parent.height; radius: 2; color: "#2563eb" }
                            }
                            handle: Rectangle {
                                x: pitchSlider.leftPadding + pitchSlider.visualPosition * (pitchSlider.availableWidth - width)
                                y: pitchSlider.topPadding + pitchSlider.availableHeight / 2 - height / 2
                                width: 16; height: 16; radius: 8; color: "#2563eb"; border.color: "#93c5fd"; border.width: 2
                            }
                        }
                        Row {
                            width: parent.width
                            Text { text: "-90°"; color: "#334155"; font.pixelSize: 8 }
                            Item { width: parent.width - 30; height: 1 }
                            Text { text: "0°"; color: "#334155"; font.pixelSize: 8 }
                        }
                    }

                    // ROLL
                    Column {
                        width: parent.width; spacing: 3
                        Row {
                            width: parent.width
                            Text { text: "ROLL"; color: "#94a3b8"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1; anchors.verticalCenter: parent.verticalCenter }
                            Item { width: parent.width - 80; height: 1 }
                            Text { text: rollSlider.value.toFixed(0) + "°"; color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; anchors.verticalCenter: parent.verticalCenter }
                        }
                        Slider {
                            id: rollSlider
                            width: parent.width; from: -45; to: 45; value: 0
                            background: Rectangle {
                                x: rollSlider.leftPadding; y: rollSlider.topPadding + rollSlider.availableHeight / 2 - height / 2
                                width: rollSlider.availableWidth; height: 4; radius: 2; color: "#1e293b"
                                Rectangle { x: Math.min(rollSlider.visualPosition, 0.5) * parent.width; width: Math.abs(rollSlider.visualPosition - 0.5) * parent.width; height: parent.height; radius: 2; color: "#8b5cf6" }
                            }
                            handle: Rectangle {
                                x: rollSlider.leftPadding + rollSlider.visualPosition * (rollSlider.availableWidth - width)
                                y: rollSlider.topPadding + rollSlider.availableHeight / 2 - height / 2
                                width: 16; height: 16; radius: 8; color: "#8b5cf6"; border.color: "#c4b5fd"; border.width: 2
                            }
                        }
                    }

                    // YAW
                    Column {
                        width: parent.width; spacing: 3
                        Row {
                            width: parent.width
                            Text { text: "YAW"; color: "#94a3b8"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1; anchors.verticalCenter: parent.verticalCenter }
                            Item { width: parent.width - 80; height: 1 }
                            Text { text: yawSlider.value.toFixed(0) + "°"; color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"; anchors.verticalCenter: parent.verticalCenter }
                        }
                        Slider {
                            id: yawSlider
                            width: parent.width; from: -180; to: 180; value: 0
                            background: Rectangle {
                                x: yawSlider.leftPadding; y: yawSlider.topPadding + yawSlider.availableHeight / 2 - height / 2
                                width: yawSlider.availableWidth; height: 4; radius: 2; color: "#1e293b"
                                Rectangle { width: yawSlider.visualPosition * parent.width; height: parent.height; radius: 2; color: "#06b6d4" }
                            }
                            handle: Rectangle {
                                x: yawSlider.leftPadding + yawSlider.visualPosition * (yawSlider.availableWidth - width)
                                y: yawSlider.topPadding + yawSlider.availableHeight / 2 - height / 2
                                width: 16; height: 16; radius: 8; color: "#06b6d4"; border.color: "#67e8f9"; border.width: 2
                            }
                        }
                    }

                    // Action buttons
                    Row {
                        width: parent.width; spacing: 8

                        Rectangle {
                            width: (parent.width - 8) * 0.6; height: 32; radius: 6
                            color: applyM.containsMouse ? "#1d4ed8" : "#1e3a5f"
                            border.color: "#2563eb"; border.width: 1
                            Behavior on color { ColorAnimation { duration: 100 } }
                            Text { anchors.centerIn: parent; text: "APPLY GIMBAL"; color: "#93c5fd"; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                            MouseArea {
                                id: applyM; anchors.fill: parent; hoverEnabled: true
                                onClicked: {
                                    if (!root.selectedDroneId || typeof swarm === "undefined") return
                                    swarm.gimbalPoint(root.selectedDroneId,
                                        pitchSlider.value, rollSlider.value, yawSlider.value)
                                }
                            }
                        }

                        Rectangle {
                            width: (parent.width - 8) * 0.4; height: 32; radius: 6
                            color: homeM.containsMouse ? "#374151" : "#1e2535"
                            border.color: "#4b5563"; border.width: 1
                            Text { anchors.centerIn: parent; text: "⌂ HOME"; color: "#94a3b8"; font.pixelSize: 10 }
                            MouseArea {
                                id: homeM; anchors.fill: parent; hoverEnabled: true
                                onClicked: {
                                    if (!root.selectedDroneId || typeof swarm === "undefined") return
                                    pitchSlider.value = 0; rollSlider.value = 0; yawSlider.value = 0
                                    swarm.gimbalHome(root.selectedDroneId)
                                }
                            }
                        }
                    }

                    // Quick presets
                    Text { text: "PRESETS"; color: "#64748b"; font.pixelSize: 8; font.weight: Font.Bold; font.letterSpacing: 1 }
                    Row {
                        width: parent.width; spacing: 6

                        Repeater {
                            model: [
                                { label: "Down",    pitch: -90, roll: 0, yaw: 0 },
                                { label: "Forward", pitch: 0,   roll: 0, yaw: 0 },
                                { label: "45°",     pitch: -45, roll: 0, yaw: 0 },
                            ]
                            delegate: Rectangle {
                                width: (parent.width - 12) / 3; height: 28; radius: 5
                                color: pM.containsMouse ? "#334155" : "#1e2535"
                                border.color: "#334155"; border.width: 1
                                Text { anchors.centerIn: parent; text: modelData.label; color: "#94a3b8"; font.pixelSize: 10 }
                                MouseArea {
                                    id: pM; anchors.fill: parent; hoverEnabled: true
                                    onClicked: {
                                        pitchSlider.value = modelData.pitch
                                        rollSlider.value  = modelData.roll
                                        yawSlider.value   = modelData.yaw
                                        if (root.selectedDroneId && typeof swarm !== "undefined")
                                            swarm.gimbalPoint(root.selectedDroneId, modelData.pitch, modelData.roll, modelData.yaw)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // ── Current gimbal state ────────────────────────────────────
            Text { text: "AKTUELLER STATUS"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

            Rectangle {
                width: parent.width; height: 44; radius: 8
                color: "#0d1117"; border.color: "#2d3748"; border.width: 1

                Timer {
                    interval: 500; running: true; repeat: true
                    onTriggered: {
                        if (!root.selectedDroneId || typeof swarm === "undefined") return
                        var s = swarm.gimbalState(root.selectedDroneId)
                        if (s) {
                            pitchLabel.text = "P: " + (s.pitch || 0).toFixed(0) + "°"
                            rollLabel.text  = "R: " + (s.roll  || 0).toFixed(0) + "°"
                            yawLabel.text   = "Y: " + (s.yaw   || 0).toFixed(0) + "°"
                        }
                    }
                }

                Row {
                    anchors.centerIn: parent; spacing: 24
                    Text { id: pitchLabel; text: "P: —"; color: "#2563eb"; font.pixelSize: 13; font.family: "Consolas"; font.weight: Font.Bold }
                    Text { id: rollLabel;  text: "R: —"; color: "#8b5cf6"; font.pixelSize: 13; font.family: "Consolas"; font.weight: Font.Bold }
                    Text { id: yawLabel;   text: "Y: —"; color: "#06b6d4"; font.pixelSize: 13; font.family: "Consolas"; font.weight: Font.Bold }
                }
            }
        }
    }
}

import QtQuick
import QtQuick.Controls

// Vertical icon sidebar — each button toggles a named panel
Rectangle {
    id: root
    width: 58
    color: "#0f1117"

    // ── Border right ──────────────────────────────────────────────────────
    Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: "#2d3748" }

    property var panels: []  // list of { id, icon, label, color }
    signal panelToggled(string panelId)

    Column {
        anchors { top: parent.top; topMargin: 12; horizontalCenter: parent.horizontalCenter }
        spacing: 4

        Repeater {
            model: root.panels

            delegate: Item {
                width: 46
                height: 46

                property bool active: false

                Rectangle {
                    anchors.fill: parent
                    radius: 10
                    color: parent.active
                        ? (modelData.color + "33")
                        : (navMouse.containsMouse ? "#1e2535" : "transparent")
                    Behavior on color { ColorAnimation { duration: 120 } }

                    // Active indicator bar on left
                    Rectangle {
                        visible: parent.parent.active
                        width: 3; height: 24
                        anchors { left: parent.left; verticalCenter: parent.verticalCenter }
                        radius: 2
                        color: modelData.color
                    }

                    Column {
                        anchors.centerIn: parent
                        spacing: 2

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.icon
                            font.pixelSize: 18
                            color: parent.parent.parent.active ? modelData.color : "#64748b"
                            Behavior on color { ColorAnimation { duration: 120 } }
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.label
                            font.pixelSize: 7
                            font.weight: Font.Medium
                            color: parent.parent.parent.active ? modelData.color : "#4a5568"
                        }
                    }

                    MouseArea {
                        id: navMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            parent.parent.active = !parent.parent.active
                            root.panelToggled(modelData.id)
                        }
                    }
                }
            }
        }
    }
}

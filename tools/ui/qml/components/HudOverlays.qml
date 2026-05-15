import QtQuick

// ── Bottom HUD overlays (always visible above map) ───────────────────
// Three pieces:
//   - Bottom-left: coords/source label
//   - Bottom-center: selected drone indicator
//   - Bottom-right: drone count + connected count
//
// Properties:
//   selectedDroneId : current drone (string)
//   droneCount      : telemetryModel count
//   connectedCount  : swarm.connectedDrones
Item {
    id: hud
    anchors.fill: parent

    property string selectedDroneId: ""
    property int    droneCount:      0
    property int    connectedCount:  0

    // Bottom-left
    Rectangle {
        anchors { bottom: parent.bottom; left: parent.left; bottomMargin: 8; leftMargin: 8 }
        height: 22; width: coordTxt.implicitWidth + 16; radius: 4
        color: "#cc0f1117"
        Text {
            id: coordTxt
            anchors.centerIn: parent
            text: "OSM · Leaflet"
            color: "#64748b"; font.pixelSize: 10; font.family: "Consolas"
        }
    }

    // Bottom-center: selected drone
    Rectangle {
        anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter; bottomMargin: 8 }
        height: 24; width: selDroneTxt.implicitWidth + 20; radius: 4
        property string _selType: {
            if (!hud.selectedDroneId || typeof swarm === "undefined" || !swarm) return "generic"
            var s = swarm.droneSnapshot(hud.selectedDroneId)
            return (s && s.droneType) ? s.droneType : "generic"
        }
        property color _typeCol: _selType === "observation" ? "#8b5cf6" : "#2563eb"
        color: hud.selectedDroneId
                ? Qt.rgba(Qt.color(_typeCol).r, Qt.color(_typeCol).g, Qt.color(_typeCol).b, 0.18)
                : "#cc0f1117"
        border.color: hud.selectedDroneId ? _typeCol : "transparent"
        border.width: 1
        visible: hud.selectedDroneId !== ""
        Text {
            id: selDroneTxt
            anchors.centerIn: parent
            text: hud.selectedDroneId
                      ? (parent._selType === "observation" ? "[OBS] " : "") + hud.selectedDroneId
                    : ""
            color: parent._typeCol
            font.pixelSize: 11; font.weight: Font.Bold; font.family: "Consolas"
        }
    }

    // Bottom-right: drone counts
    Rectangle {
        anchors { bottom: parent.bottom; right: parent.right; bottomMargin: 8; rightMargin: 8 }
        height: 22; width: hudRow.implicitWidth + 16; radius: 4
        color: "#cc0f1117"
        Row {
            id: hudRow
            anchors.centerIn: parent
            spacing: 12
            Text {
                text: "●  " + hud.droneCount + " drones"
                color: hud.droneCount > 0 ? "#22c55e" : "#64748b"
                font.pixelSize: 10
            }
            Text {
                text: "⚡  " + hud.connectedCount
                color: "#2563eb"
                font.pixelSize: 10
            }
        }
    }
}

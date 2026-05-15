import QtQuick
import QtQuick.Controls

// Animated slide-in panel container.
// Set 'open: true' to show, 'open: false' to hide (slides out to right).
Rectangle {
    id: root

    property bool   open:    false
    property string title:   "Panel"
    property string accentColor: "#2563eb"
    property int    panelWidth: 360
    property alias  content: contentArea.data

    width:   open ? panelWidth : 0
    height:  parent ? parent.height : 600
    clip:    true
    color:   "#161b27"

    // ── Slide animation ───────────────────────────────────────────────────
    Behavior on width {
        NumberAnimation { duration: 220; easing.type: Easing.InOutCubic }
    }

    // Left border accent
    Rectangle {
        width: 2; height: parent.height
        color: root.accentColor
        opacity: root.open ? 0.7 : 0
        Behavior on opacity { NumberAnimation { duration: 200 } }
    }

    // Right border
    Rectangle {
        anchors.right: parent.right
        width: 1; height: parent.height
        color: "#2d3748"
    }

    // ── Header bar ────────────────────────────────────────────────────────
    Rectangle {
        id: panelHeader
        anchors { top: parent.top; left: parent.left; right: parent.right }
        height: 42
        color: "#1a2035"

        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#2d3748" }

        Row {
            anchors { left: parent.left; leftMargin: 14; verticalCenter: parent.verticalCenter }
            spacing: 8
            Rectangle { width: 3; height: 16; radius: 2; color: root.accentColor; anchors.verticalCenter: parent.verticalCenter }
            Text {
                text: root.title.toUpperCase()
                color: "#e2e8f0"
                font.pixelSize: 11
                font.weight: Font.Bold
                font.letterSpacing: 1.2
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // Close button
        Rectangle {
            anchors { right: parent.right; rightMargin: 10; verticalCenter: parent.verticalCenter }
            width: 22; height: 22; radius: 11
            color: closeM.containsMouse ? "#374151" : "transparent"
            Behavior on color { ColorAnimation { duration: 100 } }

            Text { anchors.centerIn: parent; text: "✕"; color: "#64748b"; font.pixelSize: 10 }

            MouseArea { id: closeM; anchors.fill: parent; hoverEnabled: true; onClicked: root.open = false }
        }
    }

    // ── Content area ──────────────────────────────────────────────────────
    Item {
        id: contentArea
        anchors { top: panelHeader.bottom; left: parent.left; right: parent.right; bottom: parent.bottom }
        clip: true
    }
}

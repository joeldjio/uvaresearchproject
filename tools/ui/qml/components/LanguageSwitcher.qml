import QtQuick
import QtQuick.Controls

// Language switcher component for i18n support
Rectangle {
    id: root
    width: 100
    height: 28
    radius: 6
    color: "#1e2535"
    border.color: "#2d3748"
    border.width: 1

    property var languages: ["Deutsch", "English"]
    property var languageCodes: ["de", "en"]
    property int currentIndex: 0

    signal languageChanged(string languageCode)

    Row {
        anchors.fill: parent
        anchors.margins: 2
        spacing: 0

        Repeater {
            model: root.languages
            delegate: Rectangle {
                width: (parent.width - (root.languages.length - 1) * 2) / root.languages.length
                height: parent.height
                radius: 4
                color: root.currentIndex === index ? "#2563eb" : "transparent"
                
                Behavior on color {
                    ColorAnimation { duration: 150 }
                }

                Text {
                    anchors.centerIn: parent
                    text: modelData
                    color: root.currentIndex === index ? "#e2e8f0" : "#64748b"
                    font.pixelSize: 10
                    font.weight: Font.Medium
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (root.currentIndex !== index) {
                            root.currentIndex = index
                            root.languageChanged(root.languageCodes[index])
                        }
                    }
                }
            }
        }
    }

    // Globe icon on the left
    Text {
        anchors {
            left: parent.left
            leftMargin: -24
            verticalCenter: parent.verticalCenter
        }
        text: "🌐"
        font.pixelSize: 16
    }
}
// ─────────────────────────────────────────────────────────────────────
//  LicenseOverlay — full-window modal shown when the free trial is
//  over and no valid license key has been activated.
//
//  Bound to ``licenseManager`` (tools.ui.license.LicenseManager).
//  Sits on top of every panel (z = 9999) and blocks every click + key
//  press until the user types a valid key or quits the app.
// ─────────────────────────────────────────────────────────────────────
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    anchors.fill: parent
    visible: typeof licenseManager !== "undefined" && licenseManager.state === "expired"
    z: 9999

    // Block every mouse and key event behind the card.
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.AllButtons
        onClicked: mouse.accepted = true
        onWheel:   wheel.accepted = true
    }

    Rectangle {
        anchors.fill: parent
        color: "#dd000000"

        // Soft glow accent in the centre.
        Rectangle {
            anchors.centerIn: parent
            width: 720; height: 720; radius: 360
            opacity: 0.18
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#f59e0b" }
                GradientStop { position: 1.0; color: "transparent" }
            }
        }

        // ── Activation card ──────────────────────────────────────────
        Rectangle {
            id: card
            anchors.centerIn: parent
            width:  Math.min(560, parent.width  - 80)
            height: contentCol.implicitHeight + 48
            radius: 14
            color: "#0f1117"
            border.color: "#f59e0b"; border.width: 2

            ColumnLayout {
                id: contentCol
                anchors {
                    left: parent.left; leftMargin: 28
                    right: parent.right; rightMargin: 28
                    top: parent.top; topMargin: 24
                }
                spacing: 14

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    Text {
                        text: "⛔"; color: "#f59e0b"
                        font.pixelSize: 28
                    }
                    ColumnLayout {
                        spacing: 2
                        Layout.fillWidth: true
                        Text {
                            text: "Trial-Phase beendet"
                            color: "#f59e0b"
                            font.pixelSize: 20; font.bold: true
                        }
                        Text {
                            text: "RZ GCS · RZ Solutions"
                            color: "#64748b"
                            font.pixelSize: 11
                        }
                    }
                }

                Rectangle { height: 1; color: "#1e293b"; Layout.fillWidth: true }

                Text {
                    Layout.fillWidth: true
                    text: licenseManager
                        ? "Die " + licenseManager.trialDays + "-tägige Test-Phase ist abgelaufen.\n" +
                          "Um RZ GCS weiter zu nutzen, gib bitte einen Lizenz-Schlüssel ein. " +
                          "Den Schlüssel erhältst du von:\n" +
                          licenseManager.contactInfo
                        : ""
                    color: "#cbd5e1"
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                    lineHeight: 1.35
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Text {
                        text: "Lizenz-Schlüssel"
                        color: "#94a3b8"; font.pixelSize: 10
                        font.letterSpacing: 1.5
                    }
                    TextField {
                        id: keyField
                        Layout.fillWidth: true
                        placeholderText: "RZGCS-XXXX-XXXX-XXXX-YYYYMMDD"
                        font.family: "Consolas"
                        font.pixelSize: 13
                        selectByMouse: true
                        color: "#e2e8f0"
                        background: Rectangle {
                            radius: 6
                            color: "#161b27"
                            border.color: keyField.activeFocus ? "#f59e0b" : "#334155"
                            border.width: 1
                        }
                        Keys.onReturnPressed: activateBtn.clicked()
                    }
                    Text {
                        visible: licenseManager && licenseManager.lastError.length > 0
                        text:    visible ? licenseManager.lastError : ""
                        color:   "#ef4444"; font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Button {
                        id: activateBtn
                        text: "Aktivieren"
                        Layout.fillWidth: true
                        onClicked: if (licenseManager) licenseManager.activate(keyField.text)
                        background: Rectangle {
                            radius: 6
                            color: parent.hovered ? "#fb923c" : "#f59e0b"
                        }
                        contentItem: Text {
                            text: parent.text
                            color: "#0d1117"
                            font.pixelSize: 13; font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            topPadding: 8; bottomPadding: 8
                        }
                    }
                    Button {
                        text: "Beenden"
                        onClicked: Qt.quit()
                        background: Rectangle {
                            radius: 6
                            color: parent.hovered ? "#1f2937" : "#161b27"
                            border.color: "#334155"; border.width: 1
                        }
                        contentItem: Text {
                            text: parent.text
                            color: "#cbd5e1"
                            font.pixelSize: 12
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 18; rightPadding: 18
                            topPadding: 8; bottomPadding: 8
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: "Hinweis: Der Schlüssel wird offline geprüft — keine Internet-Verbindung erforderlich."
                    color: "#64748b"
                    font.pixelSize: 10; font.italic: true
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}

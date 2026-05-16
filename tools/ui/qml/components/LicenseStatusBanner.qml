// ─────────────────────────────────────────────────────────────────────
//  LicenseStatusBanner — non-blocking banner used inside the Help panel.
//
//  Shows the current license state and lets the user paste an
//  activation key without waiting for the trial to expire (the
//  blocking overlay in LicenseOverlay.qml only kicks in once
//  ``licenseManager.state === "expired"``).
//
//  Bound to the ``licenseManager`` context property
//  (tools.ui.license.LicenseManager).
// ─────────────────────────────────────────────────────────────────────
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    radius: 10
    color:  "#0d1117"

    readonly property string st: (typeof licenseManager !== "undefined") ? licenseManager.state : "trial"
    readonly property color accent:
        st === "trial"    ? "#3b82f6" :
        st === "licensed" ? "#22c55e" :
                            "#ef4444"
    border.color: accent
    border.width: 1
    implicitHeight: col.implicitHeight + 24

    // Accent stripe on the left edge
    Rectangle {
        width: 4
        anchors { left: parent.left; leftMargin: 6; top: parent.top; topMargin: 12; bottom: parent.bottom; bottomMargin: 12 }
        radius: 2
        color: root.accent
    }

    ColumnLayout {
        id: col
        anchors {
            left: parent.left; leftMargin: 20
            right: parent.right; rightMargin: 14
            verticalCenter: parent.verticalCenter
        }
        spacing: 6

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Text {
                text:
                    root.st === "licensed" ? "✓" :
                    root.st === "expired"  ? "✕" :
                                             "⏳"
                color: root.accent
                font.pixelSize: 16; font.bold: true
            }
            Text {
                Layout.fillWidth: true
                color: "#e2e8f0"
                font.pixelSize: 13; font.weight: Font.Bold
                text:
                    root.st === "licensed"
                        ? "Lizenziert · gültig bis " + (licenseManager ? licenseManager.expiryDate : "")
                    : root.st === "expired"
                        ? "Test-Phase beendet · Aktivierung erforderlich"
                    : "Test-Phase · noch " + (licenseManager ? licenseManager.daysLeft : 0) + " Tage"
            }
            Button {
                visible: root.st !== "expired"   // expired state has its own overlay
                text: form.visible ? "Schließen" : "Lizenz aktivieren"
                onClicked: form.visible = !form.visible
                background: Rectangle {
                    radius: 6
                    color: parent.hovered ? "#1f2937" : "#161b27"
                    border.color: "#334155"; border.width: 1
                }
                contentItem: Text {
                    text: parent.text
                    color: "#cbd5e1"
                    font.pixelSize: 11
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 10; rightPadding: 10
                    topPadding: 5; bottomPadding: 5
                }
            }
        }

        Text {
            Layout.fillWidth: true
            visible: !form.visible
            color: "#94a3b8"
            font.pixelSize: 10
            wrapMode: Text.WordWrap
            text:
                root.st === "licensed"
                    ? "Voller Funktionsumfang freigeschaltet."
                : "Nach Ablauf der Test-Phase ist die Eingabe eines Lizenz-Schlüssels erforderlich. "
                + "Schlüssel anfordern: " + (licenseManager ? licenseManager.contactInfo : "")
        }

        // ── Inline activation form (collapsed by default) ────────────
        ColumnLayout {
            id: form
            Layout.fillWidth: true
            visible: false
            spacing: 6

            TextField {
                id: keyField
                Layout.fillWidth: true
                placeholderText: "RZGCS-XXXX-XXXX-XXXX-YYYYMMDD"
                font.family: "Consolas"
                font.pixelSize: 12
                selectByMouse: true
                color: "#e2e8f0"
                background: Rectangle {
                    radius: 6
                    color: "#161b27"
                    border.color: keyField.activeFocus ? root.accent : "#334155"
                    border.width: 1
                }
                Keys.onReturnPressed: activateBtn.clicked()
            }
            RowLayout {
                Layout.fillWidth: true
                Button {
                    id: activateBtn
                    text: "Aktivieren"
                    onClicked: {
                        if (!licenseManager) return
                        if (licenseManager.activate(keyField.text)) {
                            keyField.text = ""
                            form.visible = false
                        }
                    }
                    background: Rectangle {
                        radius: 6
                        color: parent.hovered ? "#16a34a" : "#22c55e"
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "#0d1117"
                        font.pixelSize: 11; font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        leftPadding: 14; rightPadding: 14
                        topPadding: 5; bottomPadding: 5
                    }
                }
                Text {
                    Layout.fillWidth: true
                    visible: licenseManager && licenseManager.lastError.length > 0
                    text:    visible ? licenseManager.lastError : ""
                    color:   "#ef4444"
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}

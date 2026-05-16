// ─────────────────────────────────────────────────────────────────────
//  UpdateBanner — shows the current RZ GCS version + lets the user
//  check for updates and one-click install a newer release.
//
//  Bound to the ``updater`` context property exposed by
//  tools.ui.updater.UpdaterContext.
//
//  All states are driven by ``updater.state``:
//    idle        Initial state, "Check for Updates" button visible.
//    checking    Spinner + "Checking GitHub…"
//    uptodate    Green tick + "You're on the latest version"
//    available   Yellow banner + version + "Download & Install" button
//    downloading Progress bar 0..100
//    ready       (transient) installer launching, app about to exit
//    error       Red banner + error message + retry
// ─────────────────────────────────────────────────────────────────────
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    radius: 10
    border.width: 1

    // Color the border + accent stripe based on state
    readonly property string st: (typeof updater !== "undefined") ? updater.state : "idle"
    readonly property color accent:
        st === "available"   ? "#f59e0b" :
        st === "uptodate"    ? "#22c55e" :
        st === "error"       ? "#ef4444" :
        st === "checking"    ? "#3b82f6" :
        st === "downloading" ? "#3b82f6" :
        st === "ready"       ? "#22c55e" :
                               "#334155"
    color:        "#0d1117"
    border.color: accent
    implicitHeight: row.implicitHeight + 24

    // Accent stripe on the left edge
    Rectangle {
        width: 4
        anchors { left: parent.left; leftMargin: 6; top: parent.top; topMargin: 12; bottom: parent.bottom; bottomMargin: 12 }
        radius: 2
        color:  root.accent
    }

    RowLayout {
        id: row
        anchors {
            left: parent.left; leftMargin: 20
            right: parent.right; rightMargin: 14
            verticalCenter: parent.verticalCenter
        }
        spacing: 14

        // ── Left: status icon + version block ────────────────────────
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 3

            RowLayout {
                spacing: 8
                Text {
                    text:
                        root.st === "available"   ? "⬆"  :
                        root.st === "uptodate"    ? "✓"  :
                        root.st === "error"       ? "✕"  :
                        root.st === "checking"    ? "…"  :
                        root.st === "downloading" ? "↓"  :
                        root.st === "ready"       ? "↻"  :
                                                    "ℹ"
                    color: root.accent
                    font.pixelSize: 16; font.bold: true
                }
                Text {
                    text:
                        root.st === "available"   ? "Update verfügbar: v" + (updater ? updater.latestVersion : "") :
                        root.st === "uptodate"    ? "Du nutzt die aktuelle Version" :
                        root.st === "error"       ? "Update-Check fehlgeschlagen" :
                        root.st === "checking"    ? "Suche nach Updates…" :
                        root.st === "downloading" ? "Lade Update herunter…" :
                        root.st === "ready"       ? "Installer wird gestartet…" :
                                                    "Software-Updates"
                    color: "#e2e8f0"
                    font.pixelSize: 13; font.weight: Font.Bold
                }
            }

            Text {
                text:
                    (updater ? "Aktuell installiert: v" + updater.currentVersion : "") +
                    (root.st === "error" && updater
                        ? "  ·  " + updater.errorMessage
                        : "")
                color: "#94a3b8"
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            // Release notes preview (only when an update is available)
            Text {
                visible: root.st === "available" && updater && updater.releaseNotes.length > 0
                text:    visible ? updater.releaseNotes : ""
                color:   "#cbd5e1"
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Layout.maximumHeight: 60
                clip: true
            }

            // Download progress bar
            ProgressBar {
                visible: root.st === "downloading"
                from: 0; to: 100
                value: (updater && root.st === "downloading") ? updater.progress : 0
                Layout.fillWidth: true
                Layout.preferredHeight: 6
            }
        }

        // ── Right: action buttons ────────────────────────────────────
        RowLayout {
            spacing: 8

            Button {
                visible: root.st === "available"
                text: "Herunterladen & Installieren"
                onClicked: if (updater) updater.downloadAndInstall()
                background: Rectangle {
                    radius: 6
                    color: parent.hovered ? "#fb923c" : "#f59e0b"
                }
                contentItem: Text {
                    text: parent.text
                    color: "#0d1117"
                    font.pixelSize: 11; font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 12; rightPadding: 12
                    topPadding: 6; bottomPadding: 6
                }
            }

            Button {
                visible: root.st !== "downloading" && root.st !== "ready"
                text:
                    root.st === "checking" ? "Prüft…" :
                    root.st === "available" ? "Auf GitHub ansehen" :
                                              "Nach Updates suchen"
                enabled: root.st !== "checking"
                onClicked: {
                    if (!updater) return
                    if (root.st === "available")
                        updater.openReleasesPage()
                    else
                        updater.check()
                }
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
                    topPadding: 6; bottomPadding: 6
                }
            }
        }
    }
}

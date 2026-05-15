import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

Item {
    id: root
    anchors.fill: parent

    property string currentMode: "script"
    property string selectedScript: ""

    // ── File Dialog ───────────────────────────────────────────────────────
    FileDialog {
        id: pyFileDlg
        title: "Python-Script öffnen"
        nameFilters: ["Python Scripts (*.py)", "Alle Dateien (*)"]
        onAccepted: {
            var pathStr = selectedFile.toString()
            var content = swarm.readFile(pathStr)
            if (content && content.length > 0) {
                scriptEditor.text = content
                scriptNameField.text = pathStr.split("/").pop().split("\\").pop()
                currentMode = "script"
            }
        }
    }

    // Hidden example script template
    TextEdit {
        id: exampleScript
        visible: false
        text: "\"\"\"
Hover Stability Experiment
--------------------------
Verbindet 3 SITL-Drohnen, hebt ab, schwebt 30s,
misst Positionsfehler, landet.
\"\"\"
import time

DRONES = {
    'UAV_1': 'tcp:127.0.0.1:5762',
    'UAV_2': 'tcp:127.0.0.1:5772',
    'UAV_3': 'tcp:127.0.0.1:5782',
}
TAKEOFF_ALT = 10.0
HOVER_TIME  = 30

from droneresearch.sdk.swarm import Swarm

swarm = Swarm()
for did, conn in DRONES.items():
    swarm.add(did, conn)

swarm.connect_all(timeout=15)
connected = [d for d in swarm.drones() if d.connected]

if connected:
    swarm.arm_all()
    time.sleep(3)
    swarm.takeoff_all(altitude=TAKEOFF_ALT)
    time.sleep(8)
    t0 = time.time()
    while time.time() - t0 < HOVER_TIME:
        time.sleep(5)
    swarm.land_all()
    time.sleep(10)
    swarm.disconnect_all()
"
    }

    // ── Mode Tab Bar ──────────────────────────────────────────────────────
    Row {
        id: tabBar
        anchors { top: parent.top; left: parent.left; right: parent.right; topMargin: 8; leftMargin: 12; rightMargin: 12 }
        height: 34
        spacing: 0

        Rectangle {
            width: parent.width / 2; height: parent.height
            color: currentMode === "script" ? "#2563eb" : "#1a2035"
            border.color: "#2d3748"; border.width: 1; radius: 6
            Text {
                anchors.centerIn: parent
                text: "Python Script"
                color: currentMode === "script" ? "white" : "#94a3b8"
                font.pixelSize: 11; font.weight: Font.Bold
            }
            MouseArea { anchors.fill: parent; onClicked: currentMode = "script" }
        }

        Rectangle {
            width: parent.width / 2; height: parent.height
            color: currentMode === "json" ? "#2563eb" : "#1a2035"
            border.color: "#2d3748"; border.width: 1; radius: 6
            Text {
                anchors.centerIn: parent
                text: "JSON Scenario"
                color: currentMode === "json" ? "white" : "#94a3b8"
                font.pixelSize: 11; font.weight: Font.Bold
            }
            MouseArea { anchors.fill: parent; onClicked: currentMode = "json" }
        }
    }

    // ── PYTHON SCRIPT MODE ────────────────────────────────────────────────
    Item {
        id: scriptPane
        visible: currentMode === "script"
        anchors {
            top: tabBar.bottom; topMargin: 8
            left: parent.left; right: parent.right; bottom: parent.bottom
            leftMargin: 12; rightMargin: 12; bottomMargin: 8
        }

        // Name field
        TextField {
            id: scriptNameField
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height: 32
            placeholderText: "script_name.py"
            background: Rectangle { color: "#1e2535"; radius: 5; border.color: "#2d3748"; border.width: 1 }
            color: "#e2e8f0"; font.pixelSize: 11; leftPadding: 8
        }

        // Action buttons
        Row {
            id: actionRow
            anchors { top: scriptNameField.bottom; topMargin: 8; left: parent.left; right: parent.right }
            height: 36
            spacing: 6

            Rectangle {
                width: (parent.width - 18) / 4; height: parent.height; radius: 6
                color: openPyM.containsMouse ? "#1d4ed8" : "#2563eb"
                Row { anchors.centerIn: parent; spacing: 5
                    Text { text: "OPEN"; color: "#cbd5e1"; font.pixelSize: 9; font.weight: Font.Bold }
                    Text { text: "Laden"; color: "white"; font.pixelSize: 10; font.weight: Font.Bold }
                }
                MouseArea { id: openPyM; anchors.fill: parent; hoverEnabled: true; onClicked: pyFileDlg.open() }
            }

            Rectangle {
                width: (parent.width - 18) / 4; height: parent.height; radius: 6
                color: savePyM.containsMouse ? "#15803d" : "#22c55e"
                opacity: scriptEditor.text.length > 0 ? 1.0 : 0.4
                Row { anchors.centerIn: parent; spacing: 5
                    Text { text: "SAVE"; color: "#cbd5e1"; font.pixelSize: 9; font.weight: Font.Bold }
                    Text { text: "Speichern"; color: "white"; font.pixelSize: 10; font.weight: Font.Bold }
                }
                MouseArea {
                    id: savePyM; anchors.fill: parent; hoverEnabled: true
                    onClicked: { if (scriptNameField.text !== "" && experiment) experiment.saveAndRunScript(scriptNameField.text, scriptEditor.text) }
                }
            }

            Rectangle {
                width: (parent.width - 18) / 4; height: parent.height; radius: 6
                color: (experiment && experiment.busy) ? "#7c2d12" : (runPyM.containsMouse ? "#ea580c" : "#f97316")
                Row { anchors.centerIn: parent; spacing: 5
                    Text { text: (experiment && experiment.busy) ? "STOP" : "RUN"; color: "white"; font.pixelSize: 12; font.weight: Font.Bold }
                    Text { text: (experiment && experiment.busy) ? "Stop" : "Ausführen"; color: "white"; font.pixelSize: 10; font.weight: Font.Bold }
                }
                MouseArea {
                    id: runPyM; anchors.fill: parent; hoverEnabled: true
                    onClicked: {
                        if (!experiment) return
                        if (experiment.busy) experiment.stopScript()
                        else if (scriptEditor.text.length > 0) experiment.runPythonScript(scriptEditor.text, {})
                    }
                }
            }

            Rectangle {
                width: (parent.width - 18) / 4; height: parent.height; radius: 6
                color: exM.containsMouse ? "#7e22ce" : "#6d28d9"
                Row { anchors.centerIn: parent; spacing: 5
                    Text { text: "COPY"; color: "#cbd5e1"; font.pixelSize: 9; font.weight: Font.Bold }
                    Text { text: "Beispiel"; color: "white"; font.pixelSize: 10; font.weight: Font.Bold }
                }
                MouseArea {
                    id: exM; anchors.fill: parent; hoverEnabled: true
                    onClicked: { scriptNameField.text = "hover_experiment.py"; scriptEditor.text = exampleScript.text }
                }
            }
        }

        // Script editor — fills ALL remaining height
        Rectangle {
            id: editorBox
            anchors {
                top: actionRow.bottom; topMargin: 8
                left: parent.left; right: parent.right; bottom: parent.bottom
            }
            radius: 8
            color: "#0d1117"
            border.color: "#2d3748"; border.width: 1
            clip: true

            Flickable {
                id: scriptFlick
                anchors { fill: parent; margins: 2 }
                contentWidth:  Math.max(width,  scriptEditor.contentWidth  + 20)
                contentHeight: Math.max(height, scriptEditor.contentHeight + 20)
                boundsBehavior: Flickable.StopAtBounds
                flickableDirection: Flickable.HorizontalAndVerticalFlick
                clip: true

                ScrollBar.vertical:   ScrollBar { policy: ScrollBar.AsNeeded }
                ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }

                TextArea {
                    id: scriptEditor
                    width: Math.max(scriptFlick.width, contentWidth)
                    leftPadding: 10; rightPadding: 10
                    topPadding: 10;  bottomPadding: 10
                    color: "#8be9fd"
                    font.pixelSize: 11
                    font.family: "Consolas"
                    background: null
                    wrapMode: TextEdit.NoWrap
                    selectByMouse: true
                    persistentSelection: true
                    text: "# Python Experiment Script\n# Klicke auf 'Beispiel' fuer ein fertiges Experiment\n\nprint('Script bereit.')\n"
                }
            }
        }
    }

    // ── JSON SCENARIO MODE ────────────────────────────────────────────────
    ScrollView {
        visible: currentMode === "json"
        anchors {
            top: tabBar.bottom; topMargin: 8
            left: parent.left; right: parent.right; bottom: parent.bottom
            leftMargin: 12; rightMargin: 12; bottomMargin: 8
        }
        clip: true
        contentWidth: availableWidth
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        Column {
            width: parent.width
            spacing: 10

            Rectangle {
                width: parent.width; height: cfgCol.implicitHeight + 20; radius: 8
                color: "#1a2035"; border.color: "#2d3748"; border.width: 1

                Column {
                    id: cfgCol
                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                    spacing: 6

                    TextField {
                        id: nameField; width: parent.width; height: 30
                        placeholderText: "Scenario name"
                        background: Rectangle { color: "#1e2535"; radius: 5; border.color: "#2d3748"; border.width: 1 }
                        color: "#e2e8f0"; font.pixelSize: 12; leftPadding: 8
                        text: "my_scenario"
                    }

                    Text { text: "Mission Steps (JSON array)"; color: "#64748b"; font.pixelSize: 10 }
                    Rectangle {
                        width: parent.width; height: 120; radius: 5
                        color: "#0d1117"; border.color: "#2d3748"; border.width: 1
                        TextArea {
                            anchors.fill: parent
                            text: '[\n  {"action": "takeoff", "altitude": 10},\n  {"action": "hover", "duration": 30},\n  {"action": "land"}\n]'
                            color: "#8be9fd"; font.pixelSize: 10; font.family: "Consolas"
                            background: null
                        }
                    }

                    Row {
                        spacing: 8
                        CheckBox {
                            id: sitlCheck; checked: true; text: "Use SITL"
                            contentItem: Text { text: sitlCheck.text; color: "#94a3b8"; font.pixelSize: 11; leftPadding: sitlCheck.indicator.width + 4 }
                        }
                    }

                    Rectangle {
                        width: parent.width; height: 32; radius: 6
                        color: (experiment && experiment.busy) ? "#374151" : (runJsonM.containsMouse ? "#1d4ed8" : "#2563eb")
                        Behavior on color { ColorAnimation { duration: 100 } }
                        Row {
                            anchors.centerIn: parent; spacing: 6
                            Text { text: (experiment && experiment.busy) ? "⏳" : "▶"; color: "white"; font.pixelSize: 14 }
                            Text { text: (experiment && experiment.busy) ? "Running…" : "Run JSON Scenario"; color: "white"; font.pixelSize: 11; font.weight: Font.Bold }
                        }
                        MouseArea {
                            id: runJsonM; anchors.fill: parent; hoverEnabled: true
                            onClicked: {
                                if (experiment && !experiment.busy) {
                                    var d = { name: nameField.text, use_sitl: sitlCheck.checked, mission: [] }
                                    experiment.run(JSON.stringify(d), sitlCheck.checked)
                                }
                            }
                        }
                    }
                }
            }

            Text { text: "RESULTS"; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }

            ListView {
                width: parent.width
                height: Math.min(resultsModel.count * 44, 150)
                model: ListModel { id: resultsModel }
                clip: true
                spacing: 4
                delegate: Rectangle {
                    width: ListView.view.width; height: 40; radius: 6
                    color: "#1a2035"; border.color: "#2d3748"; border.width: 1
                    Row {
                        anchors { fill: parent; leftMargin: 12 }
                        spacing: 10
                        Text { text: "#" + (index + 1); color: "#64748b"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: model.success ? "✓ OK" : "✗ FAIL"; color: model.success ? "#22c55e" : "#ef4444"; font.pixelSize: 11; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: model.duration.toFixed(1) + "s"; color: "#94a3b8"; font.pixelSize: 11; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: model.mode || ""; color: "#64748b"; font.pixelSize: 9; anchors.verticalCenter: parent.verticalCenter }
                    }
                }
            }
        }
    }

    // ── Connections ───────────────────────────────────────────────────────
    Connections {
        target: experiment

        function onResultReady(result) {
            resultsModel.append({ success: result.success ?? false, duration: result.duration_s ?? 0, mode: "JSON" })
        }

        function onScriptFinished(success, message) {
            resultsModel.append({ success: success, duration: 0, mode: "Python" })
        }

        function onBusyChanged() {
            if (experiment && !experiment.busy) refreshSavedScripts()
        }
    }

    // ── Functions ─────────────────────────────────────────────────────────
    function refreshSavedScripts() {
        if (!experiment) return
        // savedScriptsModel not shown in script mode anymore, kept for compatibility
    }

    Component.onCompleted: { refreshSavedScripts() }
}

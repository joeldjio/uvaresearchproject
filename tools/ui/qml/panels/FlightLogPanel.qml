import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components" as Cmp

Item {
    id: root
    anchors.fill: parent

    property var    rows:     []
    property string logName:  ""
    property int    hoverIdx: -1

    // ── Helpers ───────────────────────────────────────────────────────────
    function repaintAll() {
        altCanvas.requestPaint()
        spdCanvas.requestPaint()
        batCanvas.requestPaint()
        vzCanvas.requestPaint()
    }

    onHoverIdxChanged: repaintAll()

    // ── CSV Parser ────────────────────────────────────────────────────────
    property real _altMax: 120
    property real _spdMax: 30

    function loadCsv(text) {
        var lines = text.split("\n")
        if (lines.length < 2) return
        var hdrs = lines[0].split(",").map(function(h){ return h.trim() })
        var parsed = []
        var t0 = -1
        for (var i = 1; i < lines.length; i++) {
            var line = lines[i].trim()
            if (!line) continue
            var cols = line.split(",")
            var getCol = function(name, c) {
                var idx = hdrs.indexOf(name)
                return idx >= 0 ? (parseFloat(c[idx]) || 0) : 0
            }
            var t = getCol("timestamp", cols)
            if (t0 < 0) t0 = t
            parsed.push({
                t:   t - t0,
                alt: getCol("alt_rel",     cols),
                spd: getCol("groundspeed", cols),
                bat: getCol("battery_pct", cols),
                vz:  getCol("vz",          cols),
            })
        }
        rows = parsed
        if (parsed.length > 0) {
            var maxAlt = 0, maxSpd = 0
            for (var j = 0; j < parsed.length; j++) {
                if (parsed[j].alt > maxAlt) maxAlt = parsed[j].alt
                if (parsed[j].spd > maxSpd) maxSpd = parsed[j].spd
            }
            _altMax = Math.max(20, Math.ceil(maxAlt * 1.15 / 10) * 10)
            _spdMax = Math.max(10, Math.ceil(maxSpd * 1.15 / 5)  * 5)
        }
        repaintAll()
        statsRow.visible = parsed.length > 0
    }

    // ── Helper: Format seconds as MM:SS ───────────────────────────────────
    function formatTime(seconds) {
        var mins = Math.floor(seconds / 60)
        var secs = Math.floor(seconds % 60)
        return mins.toString() + ":" + (secs < 10 ? "0" : "") + secs.toString()
    }

    // ── Chart drawing ─────────────────────────────────────────────────────
    function drawChart(ctx, w, h, dataRows, yKey, yMin, yMax, col, title, hover) {
        var pad = { l: 38, r: 10, t: 22, b: 28 }
        var W = w - pad.l - pad.r
        var H = h - pad.t - pad.b
        ctx.fillStyle = "#0a0e1a"; ctx.fillRect(0, 0, w, h)

        ctx.fillStyle = "#4a5568"; ctx.font = "bold 9px Consolas, Courier New"
        ctx.textAlign = "left"; ctx.textBaseline = "top"
        ctx.fillText(title, pad.l + 2, 4)

        for (var g = 0; g <= 4; g++) {
            var gy = pad.t + H - g * H / 4
            ctx.strokeStyle = g === 0 ? "#2d3748" : "#1a2035"
            ctx.lineWidth   = g === 0 ? 1.2 : 0.8
            ctx.beginPath(); ctx.moveTo(pad.l, gy); ctx.lineTo(pad.l + W, gy); ctx.stroke()
            var lv = yMin + g * (yMax - yMin) / 4
            ctx.fillStyle = "#374151"; ctx.font = "8px Consolas, Courier New"
            ctx.textAlign = "right"; ctx.textBaseline = "middle"
            ctx.fillText(lv % 1 === 0 ? lv : lv.toFixed(1), pad.l - 3, gy)
        }

        if (!dataRows || dataRows.length < 2) {
            ctx.fillStyle = "#2d3748"; ctx.font = "bold 11px Consolas"
            ctx.textAlign = "center"; ctx.textBaseline = "middle"
            ctx.fillText("Kein Log — LOG ÖFFNEN drücken", w / 2, h / 2)
            return
        }

        var tMax = dataRows[dataRows.length - 1].t || 1
        ctx.fillStyle = "#374151"; ctx.font = "8px Consolas, Courier New"
        ctx.textAlign = "left";  ctx.textBaseline = "bottom"; ctx.fillText("0s", pad.l, h - 2)
        ctx.textAlign = "right"; ctx.fillText(tMax.toFixed(0) + "s", pad.l + W, h - 2)

        ctx.strokeStyle = col; ctx.lineWidth = 1.8
        ctx.beginPath()
        for (var i = 0; i < dataRows.length; i++) {
            var x = pad.l + (dataRows[i].t / tMax) * W
            var y = pad.t + H - ((dataRows[i][yKey] - yMin) / (yMax - yMin)) * H
            if (i === 0) ctx.moveTo(x, y)
            else         ctx.lineTo(x, y)
        }
        ctx.stroke()

        if (hover && hoverIdx >= 0 && hoverIdx < dataRows.length) {
            var hx = pad.l + (dataRows[hoverIdx].t / tMax) * W
            var hy = pad.t + H - ((dataRows[hoverIdx][yKey] - yMin) / (yMax - yMin)) * H
            ctx.strokeStyle = "#fbbf24"; ctx.lineWidth = 1
            ctx.beginPath(); ctx.moveTo(hx, pad.t); ctx.lineTo(hx, pad.t + H); ctx.stroke()
            ctx.fillStyle = col; ctx.beginPath(); ctx.arc(hx, hy, 4, 0, 2*Math.PI); ctx.fill()
            ctx.fillStyle = "#fbbf24"; ctx.font = "bold 10px Consolas"
            ctx.textAlign = "center"; ctx.textBaseline = "bottom"
            ctx.fillText(dataRows[hoverIdx][yKey].toFixed(1), hx, hy - 8)
        }
    }

    function updateHover(canvasX, canvasWidth) {
        if (!rows || rows.length < 2) return
        var tMax = rows[rows.length - 1].t
        var t = (canvasX - 38) / (canvasWidth - 48) * tMax
        var best = 0, bestDt = 1e9
        for (var i = 0; i < rows.length; i++) {
            var dt = Math.abs(rows[i].t - t)
            if (dt < bestDt) { bestDt = dt; best = i }
        }
        hoverIdx = best
    }

    // ── File Dialogs ──────────────────────────────────────────────────────
    FileDialog {
        id: csvFileDlg
        title: "CSV Flight Log öffnen"
        nameFilters: ["CSV Logs (*.csv)", "Alle Dateien (*)"]
        onAccepted: {
            var pathStr = selectedFile.toString()
            root.logName = pathStr.split("/").pop().split("\\").pop()
            var content = swarm.readFile(pathStr)
            if (content && content.length > 0)
                root.loadCsv(content)
            else
                loadErrorFlash.visible = true
        }
    }

    FileDialog {
        id: bagFileDlg
        title: "ROS2 Bag öffnen"
        nameFilters: ["ROS2 Bags (*.mcap *.db3)", "Alle Dateien (*)"]
        onAccepted: {
            var pathStr = selectedFile.toString()
            root.logName = pathStr.split("/").pop().split("\\").pop()
            bagPlayback.loadBag(pathStr)
        }
    }

    Rectangle {
        id: loadErrorFlash
        visible: false
        anchors { top: parent.top; horizontalCenter: parent.horizontalCenter; topMargin: 8 }
        width: errTxt.implicitWidth + 24; height: 32; radius: 6; z: 10
        color: "#7f1d1d"; border.color: "#ef4444"; border.width: 1
        Text { id: errTxt; anchors.centerIn: parent; text: "Datei konnte nicht gelesen werden"; color: "#fca5a5"; font.pixelSize: 11 }
        Timer { interval: 3000; running: loadErrorFlash.visible; onTriggered: loadErrorFlash.visible = false }
    }

    // ── Main Layout ───────────────────────────────────────────────────────
    Flickable {
        anchors { fill: parent; margins: 12 }
        contentHeight: mainColumn.height
        contentWidth: width
        clip: true
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        ColumnLayout {
            id: mainColumn
            width: parent.width
            spacing: 8

            // ── Top Bar (Buttons + Filename) ──────────────────────────────
            Row {
                Layout.fillWidth: true
                height: 32
                spacing: 8

                Rectangle {
                    width: 120; height: 32; radius: 6
                    color: csvBtnMa.containsMouse ? "#2563eb" : "#1e2535"
                    border.color: "#2563eb"; border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: "OPEN CSV"
                        color: "#e2e8f0"
                        font.pixelSize: 10
                        font.weight: Font.Bold
                    }
                    MouseArea { id: csvBtnMa; anchors.fill: parent; hoverEnabled: true; onClicked: csvFileDlg.open() }
                }

                Rectangle {
                    width: 120; height: 32; radius: 6
                    color: bagBtnMa.containsMouse ? "#059669" : "#1e2535"
                    border.color: "#059669"; border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: "OPEN BAG"
                        color: "#e2e8f0"
                        font.pixelSize: 10
                        font.weight: Font.Bold
                    }
                    MouseArea { id: bagBtnMa; anchors.fill: parent; hoverEnabled: true; onClicked: bagFileDlg.open() }
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.logName !== "" ? root.logName : "— kein Log geladen —"
                    color: root.logName !== "" ? "#94a3b8" : "#374151"
                    font.pixelSize: 11; font.family: "Consolas"
                    elide: Text.ElideLeft
                    width: parent.width - 256
                }
            }

            // ── Bag Playback Controls ─────────────────────────────────────
            Rectangle {
                id: bagPlaybackSection
                Layout.fillWidth: true
                Layout.preferredHeight: 120
                radius: 8
                color: "#1a2035"
                border.color: "#2d3748"
                border.width: 1

                ColumnLayout {
                    anchors { fill: parent; margins: 12 }
                    spacing: 8

                    // Title + State
                    Row {
                        Layout.fillWidth: true
                        spacing: 8
                        Text {
                            text: "ROS2 Bag Playback"
                            color: "#94a3b8"
                            font.pixelSize: 12
                            font.weight: Font.Bold
                        }
                        Rectangle {
                            width: stateText.implicitWidth + 12
                            height: 18
                            radius: 4
                            color: bagPlayback.state === "playing" ? "#059669" : bagPlayback.state === "paused" ? "#d97706" : "#374151"
                            Text {
                                id: stateText
                                anchors.centerIn: parent
                                text: bagPlayback.state === "playing" ? "PLAYING" : bagPlayback.state === "paused" ? "PAUSED" : "STOPPED"
                                color: "#f1f5f9"
                                font.pixelSize: 9
                                font.weight: Font.Bold
                            }
                        }
                    }

                    // Timeline
                    Row {
                        Layout.fillWidth: true
                        spacing: 8

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: formatTime(bagPlayback.progress * bagPlayback.duration)
                            color: "#64748b"
                            font.pixelSize: 10
                            font.family: "Consolas"
                            width: 50
                        }

                        Slider {
                            id: timelineSlider
                            width: parent.width - 120
                            from: 0.0
                            to: 1.0
                            value: bagPlayback.progress
                            enabled: bagPlayback.state !== "stopped"
                            onMoved: bagPlayback.seek(value)

                            background: Rectangle {
                                x: timelineSlider.leftPadding
                                y: timelineSlider.topPadding + timelineSlider.availableHeight / 2 - height / 2
                                width: timelineSlider.availableWidth
                                height: 4
                                radius: 2
                                color: "#2d3748"
                                Rectangle {
                                    width: timelineSlider.visualPosition * parent.width
                                    height: parent.height
                                    radius: 2
                                    color: "#059669"
                                }
                            }

                            handle: Rectangle {
                                x: timelineSlider.leftPadding + timelineSlider.visualPosition * (timelineSlider.availableWidth - width)
                                y: timelineSlider.topPadding + timelineSlider.availableHeight / 2 - height / 2
                                width: 14
                                height: 14
                                radius: 7
                                color: timelineSlider.pressed ? "#10b981" : "#059669"
                                border.color: "#f1f5f9"
                                border.width: 2
                            }
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: formatTime(bagPlayback.duration)
                            color: "#64748b"
                            font.pixelSize: 10
                            font.family: "Consolas"
                            width: 50
                        }
                    }

                    // Control Buttons
                    Row {
                        spacing: 6

                        Rectangle {
                            width: 80; height: 28; radius: 6
                            color: playBtnMa.containsMouse ? "#059669" : "#1e2535"
                            border.color: "#059669"; border.width: 1
                            visible: bagPlayback.state !== "playing"
                            Text {
                                anchors.centerIn: parent
                                text: "PLAY"
                                color: "#e2e8f0"
                                font.pixelSize: 10
                                font.weight: Font.Bold
                            }
                            MouseArea { id: playBtnMa; anchors.fill: parent; hoverEnabled: true; onClicked: bagPlayback.play() }
                        }

                        Rectangle {
                            width: 80; height: 28; radius: 6
                            color: pauseBtnMa.containsMouse ? "#d97706" : "#1e2535"
                            border.color: "#d97706"; border.width: 1
                            visible: bagPlayback.state === "playing"
                            Text {
                                anchors.centerIn: parent
                                text: "PAUSE"
                                color: "#e2e8f0"
                                font.pixelSize: 10
                                font.weight: Font.Bold
                            }
                            MouseArea { id: pauseBtnMa; anchors.fill: parent; hoverEnabled: true; onClicked: bagPlayback.pause() }
                        }

                        Rectangle {
                            width: 80; height: 28; radius: 6
                            color: stopBtnMa.containsMouse ? "#dc2626" : "#1e2535"
                            border.color: "#dc2626"; border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: "STOP"
                                color: "#e2e8f0"
                                font.pixelSize: 10
                                font.weight: Font.Bold
                            }
                            MouseArea { id: stopBtnMa; anchors.fill: parent; hoverEnabled: true; onClicked: bagPlayback.stop() }
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "Speed: " + bagPlayback.playbackRate.toFixed(1) + "x"
                            color: "#64748b"
                            font.pixelSize: 10
                            font.family: "Consolas"
                        }

                        Rectangle {
                            width: 28; height: 28; radius: 6
                            color: speedDownMa.containsMouse ? "#374151" : "#1e2535"
                            border.color: "#475569"; border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: "−"
                                color: "#e2e8f0"
                                font.pixelSize: 14
                                font.weight: Font.Bold
                            }
                            MouseArea {
                                id: speedDownMa
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: bagPlayback.playbackRate = Math.max(0.1, bagPlayback.playbackRate - 0.5)
                            }
                        }

                        Rectangle {
                            width: 28; height: 28; radius: 6
                            color: speedUpMa.containsMouse ? "#374151" : "#1e2535"
                            border.color: "#475569"; border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: "+"
                                color: "#e2e8f0"
                                font.pixelSize: 14
                                font.weight: Font.Bold
                            }
                            MouseArea {
                                id: speedUpMa
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: bagPlayback.playbackRate = Math.min(10.0, bagPlayback.playbackRate + 0.5)
                            }
                        }
                    }
                }
            }

            // ── Stats Strip ───────────────────────────────────────────────
            Row {
                id: statsRow
                visible: false
                Layout.fillWidth: true
                height: 52
                spacing: 6

                property var stats: [
                    { label: "DAUER",   icon: "T", col: "#06b6d4",
                      val: function(r){ return r.length > 1 ? r[r.length-1].t.toFixed(0)+"s" : "—" } },
                    { label: "MAX ALT", icon: "A",  col: "#2563eb",
                      val: function(r){ if (!r.length) return "—"; var m=r[0].alt; for(var i=1;i<r.length;i++) if(r[i].alt>m) m=r[i].alt; return m.toFixed(1)+"m" } },
                    { label: "MAX SPD", icon: "S",  col: "#22c55e",
                      val: function(r){ if (!r.length) return "—"; var m=r[0].spd; for(var i=1;i<r.length;i++) if(r[i].spd>m) m=r[i].spd; return m.toFixed(1)+"m/s" } },
                    { label: "BATT D",  icon: "B", col: "#ef4444",
                      val: function(r){ return r.length > 1 ? (r[0].bat-r[r.length-1].bat).toFixed(0)+"%" : "—" } },
                ]

                Repeater {
                    model: statsRow.stats
                    delegate: Rectangle {
                        width: (statsRow.width - 18) / 4; height: 52; radius: 8
                        color: "#1a2035"; border.color: "#2d3748"; border.width: 1
                        Column {
                            anchors.centerIn: parent; spacing: 2
                            Row {
                                anchors.horizontalCenter: parent.horizontalCenter; spacing: 4
                                Text { text: modelData.icon; color: modelData.col; font.pixelSize: 14 }
                                Text { text: modelData.label; color: "#64748b"; font.pixelSize: 9; font.weight: Font.Bold }
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: modelData.val(rows)
                                color: "#e2e8f0"
                                font.pixelSize: 16
                                font.weight: Font.Bold
                                font.family: "Consolas"
                            }
                        }
                    }
                }
            }

            // ── CSV Charts (2x2 Grid) ────────────────────────────────────
            Grid {
                Layout.fillWidth: true
                Layout.preferredHeight: 400
                columns: 2
                rowSpacing: 8
                columnSpacing: 8

                // Altitude
                Rectangle {
                    width: (parent.width - 8) / 2; height: (parent.height - 8) / 2
                    color: "#0a0e1a"; radius: 6; border.color: "#1e293b"; border.width: 1
                    Canvas {
                        id: altCanvas
                        anchors.fill: parent
                        onPaint: root.drawChart(getContext("2d"), width, height, rows, "alt", 0, _altMax, "#2563eb", "Altitude (m) [0-120m]", true)
                    }
                    MouseArea {
                        anchors.fill: parent; hoverEnabled: true
                        onPositionChanged: root.updateHover(mouseX, width)
                        onExited: { hoverIdx = -1 }
                    }
                }

                // Groundspeed
                Rectangle {
                    width: (parent.width - 8) / 2; height: (parent.height - 8) / 2
                    color: "#0a0e1a"; radius: 6; border.color: "#1e293b"; border.width: 1
                    Canvas {
                        id: spdCanvas
                        anchors.fill: parent
                        onPaint: root.drawChart(getContext("2d"), width, height, rows, "spd", 0, _spdMax, "#22c55e", "Groundspeed (m/s) [0-30m/s]", true)
                    }
                    MouseArea {
                        anchors.fill: parent; hoverEnabled: true
                        onPositionChanged: root.updateHover(mouseX, width)
                        onExited: { hoverIdx = -1 }
                    }
                }

                // Battery
                Rectangle {
                    width: (parent.width - 8) / 2; height: (parent.height - 8) / 2
                    color: "#0a0e1a"; radius: 6; border.color: "#1e293b"; border.width: 1
                    Canvas {
                        id: batCanvas
                        anchors.fill: parent
                        onPaint: root.drawChart(getContext("2d"), width, height, rows, "bat", 0, 100, "#f59e0b", "Battery (%)", true)
                    }
                    MouseArea {
                        anchors.fill: parent; hoverEnabled: true
                        onPositionChanged: root.updateHover(mouseX, width)
                        onExited: { hoverIdx = -1 }
                    }
                }

                // Vertical Speed
                Rectangle {
                    width: (parent.width - 8) / 2; height: (parent.height - 8) / 2
                    color: "#0a0e1a"; radius: 6; border.color: "#1e293b"; border.width: 1
                    Canvas {
                        id: vzCanvas
                        anchors.fill: parent
                        onPaint: root.drawChart(getContext("2d"), width, height, rows, "vz", -5, 5, "#8b5cf6", "Vertical Speed (m/s)", true)
                    }
                    MouseArea {
                        anchors.fill: parent; hoverEnabled: true
                        onPositionChanged: root.updateHover(mouseX, width)
                        onExited: { hoverIdx = -1 }
                    }
                }
            }
        }
    }
}

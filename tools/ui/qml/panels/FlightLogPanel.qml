import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

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
        repaintAll()
        statsRow.visible = parsed.length > 0
    }

    // ── Chart drawing (on root so every Canvas child can call root.drawChart) ──
    function drawChart(ctx, w, h, dataRows, yKey, yMin, yMax, col, title, hover) {
        var pad = { l: 38, r: 10, t: 22, b: 28 }
        var W = w - pad.l - pad.r
        var H = h - pad.t - pad.b
        ctx.fillStyle = "#0a0e1a"; ctx.fillRect(0, 0, w, h)

        ctx.fillStyle = "#4a5568"; ctx.font = "bold 9px Consolas"
        ctx.textAlign = "left"; ctx.textBaseline = "top"
        ctx.fillText(title, pad.l + 2, 4)

        for (var g = 0; g <= 4; g++) {
            var gy = pad.t + H - g * H / 4
            ctx.strokeStyle = g === 0 ? "#2d3748" : "#1a2035"
            ctx.lineWidth   = g === 0 ? 1.2 : 0.8
            ctx.beginPath(); ctx.moveTo(pad.l, gy); ctx.lineTo(pad.l + W, gy); ctx.stroke()
            var lv = yMin + g * (yMax - yMin) / 4
            ctx.fillStyle = "#374151"; ctx.font = "8px Consolas"
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
        ctx.fillStyle = "#374151"; ctx.font = "8px Consolas"
        ctx.textAlign = "left";  ctx.textBaseline = "bottom"; ctx.fillText("0s", pad.l, h - 2)
        ctx.textAlign = "right"; ctx.fillText(tMax.toFixed(0) + "s", pad.l + W, h - 2)

        function toX(t)   { return pad.l + (t / tMax) * W }
        function toY(val) { return pad.t + H - Math.max(0, Math.min(1, (val - yMin) / (yMax - yMin))) * H }

        if (yMin < 0) {
            var zy = toY(0)
            ctx.strokeStyle = "#334155"; ctx.lineWidth = 0.8
            ctx.setLineDash([4, 4])
            ctx.beginPath(); ctx.moveTo(pad.l, zy); ctx.lineTo(pad.l + W, zy); ctx.stroke()
            ctx.setLineDash([])
        }

        ctx.fillStyle = col + "1a"
        ctx.beginPath()
        ctx.moveTo(toX(dataRows[0].t), pad.t + H)
        ctx.lineTo(toX(dataRows[0].t), toY(dataRows[0][yKey]))
        for (var i = 1; i < dataRows.length; i++)
            ctx.lineTo(toX(dataRows[i].t), toY(dataRows[i][yKey]))
        ctx.lineTo(toX(dataRows[dataRows.length - 1].t), pad.t + H)
        ctx.closePath(); ctx.fill()

        ctx.strokeStyle = col; ctx.lineWidth = 1.8; ctx.lineJoin = "round"
        ctx.beginPath(); ctx.moveTo(toX(dataRows[0].t), toY(dataRows[0][yKey]))
        for (var j = 1; j < dataRows.length; j++)
            ctx.lineTo(toX(dataRows[j].t), toY(dataRows[j][yKey]))
        ctx.stroke()

        if (hover >= 0 && hover < dataRows.length) {
            var hr = dataRows[hover]
            var hx = toX(hr.t), hy = toY(hr[yKey])
            ctx.strokeStyle = "#ffffff33"; ctx.lineWidth = 1; ctx.setLineDash([3, 3])
            ctx.beginPath(); ctx.moveTo(hx, pad.t); ctx.lineTo(hx, pad.t + H); ctx.stroke()
            ctx.setLineDash([])
            ctx.fillStyle = col
            ctx.beginPath(); ctx.arc(hx, hy, 4.5, 0, Math.PI * 2); ctx.fill()
            ctx.fillStyle = "#0a0e1a"
            ctx.beginPath(); ctx.arc(hx, hy, 2, 0, Math.PI * 2); ctx.fill()
            var tv = hr[yKey].toFixed(1)
            ctx.fillStyle = col; ctx.font = "bold 10px Consolas"
            ctx.textAlign = hx > pad.l + W * 0.6 ? "right" : "left"
            ctx.textBaseline = "bottom"
            ctx.fillText(tv, hx + (hx > pad.l + W * 0.6 ? -7 : 7), hy - 5)
        }
    }

    function updateHover(mx, canvasW) {
        if (!rows || rows.length < 2) return
        var W = canvasW - 48
        var t = (mx - 38) / W * rows[rows.length - 1].t
        var best = 0, bestDt = 1e9
        for (var i = 0; i < rows.length; i++) {
            var dt = Math.abs(rows[i].t - t)
            if (dt < bestDt) { bestDt = dt; best = i }
        }
        hoverIdx = best
    }

    // ── File dialog ───────────────────────────────────────────────────────
    FileDialog {
        id: fileDlg
        title: "Flight Log öffnen"
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

    Rectangle {
        id: loadErrorFlash
        visible: false
        anchors { top: parent.top; horizontalCenter: parent.horizontalCenter; topMargin: 8 }
        width: errTxt.implicitWidth + 24; height: 32; radius: 6; z: 10
        color: "#7f1d1d"; border.color: "#ef4444"; border.width: 1
        Text { id: errTxt; anchors.centerIn: parent; text: "Datei konnte nicht gelesen werden"; color: "#fca5a5"; font.pixelSize: 11 }
        Timer { interval: 3000; running: loadErrorFlash.visible; onTriggered: loadErrorFlash.visible = false }
    }

    // ── Layout ────────────────────────────────────────────────────────────
    Flickable {
        anchors { fill: parent; margins: 12 }
        contentHeight: Math.max(flightContent.implicitHeight, height)
        contentWidth: width
        clip: true

        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        Item {
            id: flightContent
            width: parent.width
            implicitHeight: topBar.height + 8 + (statsRow.visible ? statsRow.height + 8 : 0) + 600

        // ── Top bar ───────────────────────────────────────────────────────
        Row {
            id: topBar
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height: 32; spacing: 8

            Rectangle {
                width: 120; height: 32; radius: 6
                color: openBtnMa.containsMouse ? "#2563eb" : "#1e2535"
                border.color: "#2563eb"; border.width: 1
                Behavior on color { ColorAnimation { duration: 100 } }
                Row {
                    anchors.centerIn: parent; spacing: 5
                    Text { text: "OPEN"; color: "#cbd5e1"; font.pixelSize: 10; font.weight: Font.Bold }
                    Text { text: "LOG ÖFFNEN"; color: "#e2e8f0"; font.pixelSize: 10; font.weight: Font.Bold }
                }
                MouseArea { id: openBtnMa; anchors.fill: parent; hoverEnabled: true; onClicked: fileDlg.open() }
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: root.logName !== "" ? root.logName : "— kein Log geladen —"
                color: root.logName !== "" ? "#94a3b8" : "#374151"
                font.pixelSize: 11; font.family: "Consolas"
                elide: Text.ElideLeft; width: parent.width - 136
            }
        }

        // ── Stats strip ───────────────────────────────────────────────────
        Row {
            id: statsRow
            visible: false
            anchors { top: topBar.bottom; topMargin: 8; left: parent.left; right: parent.right }
            height: 52; spacing: 6

            property var stats: [
                { label: "DAUER",   icon: "⏱", col: "#06b6d4",
                  val: function(r){ return r.length > 1 ? r[r.length-1].t.toFixed(0)+"s" : "—" } },
                { label: "MAX ALT", icon: "▲",  col: "#2563eb",
                  val: function(r){ if (!r.length) return "—"; var m=r[0].alt; for(var i=1;i<r.length;i++) if(r[i].alt>m) m=r[i].alt; return m.toFixed(1)+"m" } },
                { label: "MAX SPD", icon: "→",  col: "#22c55e",
                  val: function(r){ if (!r.length) return "—"; var m=r[0].spd; for(var i=1;i<r.length;i++) if(r[i].spd>m) m=r[i].spd; return m.toFixed(1)+"m/s" } },
                { label: "BATT Δ",  icon: "⛯", col: "#ef4444",
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
                            Text { text: modelData.icon; font.pixelSize: 11; color: modelData.col }
                            Text { text: modelData.label; color: "#64748b"; font.pixelSize: 8; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: root.rows.length > 0 ? modelData.val(root.rows) : "—"
                            color: modelData.col; font.pixelSize: 15; font.weight: Font.Bold; font.family: "Consolas"
                        }
                    }
                }
            }
        }

        // ── Charts 2×2 grid ───────────────────────────────────────────────
        Item {
            id: chartArea
            anchors {
                top: statsRow.visible ? statsRow.bottom : topBar.bottom
                topMargin: 8
                left: parent.left; right: parent.right; bottom: parent.bottom
            }

            // ALT ── top-left
            Rectangle {
                x: 0; y: 0
                width: (parent.width - 8) / 2; height: (parent.height - 8) / 2
                radius: 8; color: "#0a0e1a"; border.color: "#1e2535"; border.width: 1; clip: true
                Canvas {
                    id: altCanvas; anchors.fill: parent
                    onPaint: root.drawChart(getContext("2d"), width, height, root.rows, "alt",  0,  120, "#2563eb", "Altitude (m)",       root.hoverIdx)
                }
                MouseArea {
                    anchors.fill: parent; hoverEnabled: true
                    onPositionChanged: function(m) { root.updateHover(m.x, altCanvas.width) }
                    onExited: root.hoverIdx = -1
                }
                onWidthChanged:  altCanvas.requestPaint()
                onHeightChanged: altCanvas.requestPaint()
            }

            // SPD ── top-right
            Rectangle {
                x: (parent.width - 8) / 2 + 8; y: 0
                width: (parent.width - 8) / 2; height: (parent.height - 8) / 2
                radius: 8; color: "#0a0e1a"; border.color: "#1e2535"; border.width: 1; clip: true
                Canvas {
                    id: spdCanvas; anchors.fill: parent
                    onPaint: root.drawChart(getContext("2d"), width, height, root.rows, "spd",  0,   30, "#22c55e", "Groundspeed (m/s)", root.hoverIdx)
                }
                MouseArea {
                    anchors.fill: parent; hoverEnabled: true
                    onPositionChanged: function(m) { root.updateHover(m.x, spdCanvas.width) }
                    onExited: root.hoverIdx = -1
                }
                onWidthChanged:  spdCanvas.requestPaint()
                onHeightChanged: spdCanvas.requestPaint()
            }

            // BAT ── bottom-left
            Rectangle {
                x: 0; y: (parent.height - 8) / 2 + 8
                width: (parent.width - 8) / 2; height: (parent.height - 8) / 2
                radius: 8; color: "#0a0e1a"; border.color: "#1e2535"; border.width: 1; clip: true
                Canvas {
                    id: batCanvas; anchors.fill: parent
                    onPaint: root.drawChart(getContext("2d"), width, height, root.rows, "bat",  0,  100, "#ef4444", "Battery (%)",        root.hoverIdx)
                }
                MouseArea {
                    anchors.fill: parent; hoverEnabled: true
                    onPositionChanged: function(m) { root.updateHover(m.x, batCanvas.width) }
                    onExited: root.hoverIdx = -1
                }
                onWidthChanged:  batCanvas.requestPaint()
                onHeightChanged: batCanvas.requestPaint()
            }

            // VZ ── bottom-right
            Rectangle {
                x: (parent.width - 8) / 2 + 8; y: (parent.height - 8) / 2 + 8
                width: (parent.width - 8) / 2; height: (parent.height - 8) / 2
                radius: 8; color: "#0a0e1a"; border.color: "#1e2535"; border.width: 1; clip: true
                Canvas {
                    id: vzCanvas; anchors.fill: parent
                    onPaint: root.drawChart(getContext("2d"), width, height, root.rows, "vz",  -6,    6, "#f59e0b", "Vertical Speed (m/s)", root.hoverIdx)
                }
                MouseArea {
                    anchors.fill: parent; hoverEnabled: true
                    onPositionChanged: function(m) { root.updateHover(m.x, vzCanvas.width) }
                    onExited: root.hoverIdx = -1
                }
                onWidthChanged:  vzCanvas.requestPaint()
                onHeightChanged: vzCanvas.requestPaint()
            }
        }
        }  // Item flightContent
    }  // Flickable
}

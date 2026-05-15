import QtQuick

// ── Global log store + connections ────────────────────────────────────
// Aggregates log messages from swarm/experiment/safety into a single
// ListModel that survives panel open/close cycles.
//
// Exposes:
//   model            → ListModel of {time, level, text}
//   maxEntries       → ring buffer cap (default 3000)
//
// Drop this into any parent and reference it via id, e.g.:
//   GlobalLogHandler { id: globalLog }
//   ...
//   model: globalLog.model
Item {
    id: handler

    property alias  model:      logModel
    property int    maxEntries: 3000

    // External listeners (e.g. status bar) can hook this
    signal newEntry(string level, string text)

    ListModel { id: logModel }

    // ── Syslog auto-save (always-on, regardless of LogPanel being loaded) ──
    property string _syslogPath: ""
    property bool   _autoSaveDirty: false

    function _ensureSyslogPath() {
        if (_syslogPath !== "") return
        var d = new Date()
        var stamp = d.getFullYear() + "-" +
                    String(d.getMonth()+1).padStart(2,"0") + "-" +
                    String(d.getDate()).padStart(2,"0") + "_" +
                    String(d.getHours()).padStart(2,"0") +
                    String(d.getMinutes()).padStart(2,"0") +
                    String(d.getSeconds()).padStart(2,"0")
        _syslogPath = "c:/Users/fuckheinerkleinehack/Documents/DroneResearch/tools/ui/syslogs/" + stamp + ".txt"
    }

    function _flushSyslog() {
        if (!_autoSaveDirty) return
        if (typeof swarm === "undefined" || !swarm || !swarm.writeFile) return
        _ensureSyslogPath()
        var lines = []
        for (var i = 0; i < logModel.count; i++) {
            var e = logModel.get(i)
            lines.push(e.time + "  [" + e.level + "]  " + e.text)
        }
        swarm.writeFile(_syslogPath, lines.join("\n"))
        _autoSaveDirty = false
    }

    // Throttled writer — at most every 1 s
    Timer {
        id: syslogFlushTimer
        interval: 1000; repeat: true; running: true
        onTriggered: handler._flushSyslog()
    }

    function _append(level, text) {
        var d = new Date()
        logModel.append({
            time:  Qt.formatTime(d, "hh:mm:ss"),
            level: level,
            text:  text
        })
        if (logModel.count > handler.maxEntries)
            logModel.remove(0, 1)
        _autoSaveDirty = true
        handler.newEntry(level, text)
    }

    Connections {
        target: (typeof swarm !== "undefined") ? swarm : null
        function onLogMessage(level, text) { handler._append(level, text) }
        function onFsmStateChanged(droneId, fsmState) {
            var lvl = fsmState === "EMERGENCY" ? "ERROR"
                    : (fsmState === "RTL" || fsmState === "LANDING") ? "WARN" : "INFO"
            handler._append(lvl, "[FSM] " + droneId + ": " + fsmState)
        }
    }

    Connections {
        target: (typeof experiment !== "undefined") ? experiment : null
        function onLogMessage(text) {
            handler._append("INFO", "[EXP] " + text)
        }
        function onScriptLogMessage(text) {
            var lvl = text.startsWith("[ERROR]") ? "ERROR"
                    : text.startsWith("[WARN]")  ? "WARN" : "INFO"
            handler._append(lvl, "[SCRIPT] " + text)
        }
    }
}

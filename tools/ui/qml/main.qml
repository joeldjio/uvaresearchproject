import QtQuick
import QtQuick.Controls
import "components" as Cmp

// ── Root window — Tab-based architecture ────────────────────────────────────
// Layout:
//   [Header 52px]
//   [InstrBar 110px]
//   [NavBar 70px (left)] + [Tab content (fills remaining)]
//   [StatusBar 28px]
//
// First tab = Map (with waypoint-add mode).
// Other tabs = panels (Dashboard, Swarm, Safety, Gimbal, ROS2, Experiment, FlightLog, Log).
// ─────────────────────────────────────────────────────────────────────────────

Window {
    id: root
    // Start the window maximised so the user never has to resize on launch.
    // Maximised (not FullScreen) keeps the title bar + taskbar visible —
    // important for a GCS where the operator switches between SITL, terminals
    // and this UI constantly. Pass --fullscreen on the CLI for true FS.
    visibility: Window.Maximized
    visible: true
    width:  1440
    height: 900
    minimumWidth:  1100
    minimumHeight: 700
    title: "RZ GCS"
    color: "#0f1117"

    // ── Tab definitions ───────────────────────────────────────────────────────
    readonly property var tabs: [
        { id: "map",        svg: "map",        label: "Map",       color: "#06b6d4", title: "Map View" },
        { id: "dashboard",  svg: "dashboard",  label: "Telemetry", color: "#2563eb", title: "Dashboard" },
        { id: "swarm",      svg: "swarm",      label: "Swarm",     color: "#22c55e", title: "Swarm Control" },
        { id: "safety",     svg: "safety",     label: "Safety",    color: "#ef4444", title: "Safety / APF" },
        { id: "gimbal",     svg: "experiment", label: "Gimbal",    color: "#8b5cf6", title: "Gimbal / Camera" },
        { id: "ros2",       svg: "log",        label: "ROS2",      color: "#06b6d4", title: "ROS2 / uXRCE" },
        { id: "experiment", svg: "experiment", label: "Scenario",  color: "#f59e0b", title: "Experiment" },
        { id: "flightlog",  svg: "log",        label: "FlightLog", color: "#a78bfa", title: "Flight Log" },
        { id: "log",        svg: "log",        label: "Log",       color: "#64748b", title: "System Log" },
        { id: "help",       svg: "log",        label: "Help",      color: "#fbbf24", title: "Hilfe / Feature-Übersicht" },
    ]

    property int currentTab: 0

    function selectTab(idx) { currentTab = idx }
    function selectTabById(tid) {
        for (var i = 0; i < tabs.length; i++)
            if (tabs[i].id === tid) { currentTab = i; return }
    }

    // ── Global selected drone (mirrored from Cmp.AppState singleton) ─────────
    // selectedDroneId is the single source of truth used by Telemetry, HUDs
    // and the InstrBar. It is bound one-way from the AppState singleton so
    // anyone can write `Cmp.AppState.selectedDroneId = X` and the rest of the
    // UI follows.
    readonly property string selectedDroneId: Cmp.AppState.selectedDroneId
    property var    _zoomedDrones:   ({})

    function selectDrone(did) { Cmp.AppState.selectedDroneId = did }

    // ── Global mission waypoints (shared between Map and SwarmPanel) ──────────
    ListModel { id: globalMissionWaypoints }

    // Mission-target multi-selection now lives in Cmp.AppState — see
    // components/AppState.qml. Use Cmp.AppState.toggleMissionTarget(id),
    // Cmp.AppState.missionTargetCount, Cmp.AppState.effectiveMissionTargets().

    function startGlobalMission() {
        if (typeof swarm === "undefined" || !swarm) return
        if (globalMissionWaypoints.count === 0) return
        var arr = []
        for (var i = 0; i < globalMissionWaypoints.count; i++) {
            var w = globalMissionWaypoints.get(i)
            arr.push({ lat: w.lat, lon: w.lon, alt: w.alt })
        }
        var ids = Cmp.AppState.effectiveMissionTargets()
        if (ids.length === 0) return
        swarm.runMissionMulti(JSON.stringify(ids), JSON.stringify(arr))
        // ── One-shot semantics: snapshot the dispatched waypoints into the
        //    map's persistent "dispatched" layer (green markers + dashed
        //    polyline) so the user can still see the mission path, then
        //    clear the editable queue. The next "Add WP" → "Start Mission"
        //    will only dispatch the freshly added waypoints, not replay
        //    the already-flown ones.
        if (mapLoader.item && mapLoader.item.commitDispatchedWaypoints)
            mapLoader.item.commitDispatchedWaypoints(JSON.stringify(arr))
        globalMissionWaypoints.clear()
        syncWaypointsToMap()
    }

    // Push current waypoints from the ListModel down to the Leaflet map
    function syncWaypointsToMap() {
        if (!mapLoader.item) return
        var arr = []
        for (var i = 0; i < globalMissionWaypoints.count; i++) {
            var w = globalMissionWaypoints.get(i)
            arr.push({ lat: w.lat, lon: w.lon, alt: w.alt })
        }
        mapLoader.item.updateWaypoints(JSON.stringify(arr))
    }

    Connections {
        target: globalMissionWaypoints
        function onCountChanged() { root.syncWaypointsToMap() }
    }

    // Toggle: when active, clicking the map adds a waypoint.
    property bool mapWaypointMode: false
    property real mapWaypointAlt: 10.0

    function toggleMapWaypointMode() {
        mapWaypointMode = !mapWaypointMode
        if (mapLoader.item) mapLoader.item.setPickMode(mapWaypointMode)
    }

    // ── Legacy map-pick support (for SwarmPanel "From Map" button) ────────────
    property bool   mapPickMode: false
    property var    _mapPickTarget: null

    function startMapPick(targetItem) {
        _mapPickTarget = targetItem
        mapPickMode = true
        mapWaypointMode = false
        if (mapLoader.item) mapLoader.item.setPickMode(true)
        selectTab(0)  // jump to Map tab so user can click
    }

    function deliverMapPick(lat, lon) {
        // Routing: either waypoint-add mode OR legacy single-pick mode
        if (mapWaypointMode) {
            globalMissionWaypoints.append({
                lat: lat, lon: lon, alt: mapWaypointAlt
            })
            syncWaypointsToMap()
            return
        }
        mapPickMode = false
        if (mapLoader.item) mapLoader.item.setPickMode(false)
        if (_mapPickTarget && typeof _mapPickTarget.setWaypointFromMap === "function")
            _mapPickTarget.setWaypointFromMap(lat, lon)
        _mapPickTarget = null
    }

    // ── Global log handler (encapsulated) ─────────────────────────────────────
    Cmp.GlobalLogHandler { id: globalLog }
    property alias globalLogModel: globalLog.model

    // ── Main layout ───────────────────────────────────────────────────────────
    Item {
        anchors.fill: parent

        // Header
        Loader {
            id: headerLoader
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height: 52
            asynchronous: true
            source: "components/Header.qml"
            onLoaded: {
                item.droneSelected.connect(function(did) {
                    Cmp.AppState.selectedDroneId = did
                })
            }
        }

        // InstrBar — directly below header
        Loader {
            id: instrBarLoader
            anchors {
                top:   headerLoader.bottom
                left:  parent.left
                right: parent.right
            }
            height: 110
            asynchronous: true
            source: "components/InstrBar.qml"
            onLoaded: {
                item.selectedDroneId = Qt.binding(function() { return root.selectedDroneId })
                if (typeof swarm !== "undefined") item.swarmRef = swarm
            }
        }

        // Body row — fills space between instrBar and statusBar
        Row {
            id: bodyRow
            anchors {
                top:    instrBarLoader.bottom
                bottom: statusBar.top
                left:   parent.left
                right:  parent.right
            }
            spacing: 0
            clip: true

            // ── Left nav sidebar (TabBar) ─────────────────────────────────
            Rectangle {
                id: navBar
                width: 70
                height: parent.height
                color: "#0f1117"

                Rectangle {
                    anchors.right: parent.right
                    width: 1; height: parent.height
                    color: "#2d3748"
                }

                ScrollView {
                    anchors { top: parent.top; bottom: parent.bottom; horizontalCenter: parent.horizontalCenter }
                    width: parent.width
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded

                    Column {
                        anchors { top: parent.top; topMargin: 10; horizontalCenter: parent.horizontalCenter }
                        spacing: 4

                        Repeater {
                            id: navRepeater
                            model: root.tabs

                            delegate: Item {
                                id: navBtn
                                width: 58; height: 56

                                readonly property bool active: root.currentTab === index

                                Rectangle {
                                    anchors.fill: parent
                                    radius: 10
                                    // NOTE: cannot use `modelData.color + "28"` — Qt parses 8-digit
                                    // hex as #AARRGGBB, not RGB+alpha. Use Qt.rgba() with the
                                    // unpacked channels so the active tint is a faint version
                                    // of the tab colour rather than a random bright hue.
                                    color: navBtn.active
                                        ? Qt.rgba(
                                            Qt.color(modelData.color).r,
                                            Qt.color(modelData.color).g,
                                            Qt.color(modelData.color).b,
                                            0.16)
                                        : (navHover.containsMouse ? "#1e2535" : "transparent")

                                    Behavior on color { ColorAnimation { duration: 120 } }

                                    // Active accent bar
                                    Rectangle {
                                        visible: navBtn.active
                                        width: 3; height: 26; radius: 2
                                        anchors { left: parent.left; verticalCenter: parent.verticalCenter }
                                        color: modelData.color
                                    }

                                    Column {
                                        anchors.centerIn: parent
                                        spacing: 3

                                        // Vector icon canvas
                                        Canvas {
                                            id: navIconCanvas
                                            width: 24; height: 24
                                            anchors.horizontalCenter: parent.horizontalCenter

                                            property string iconId: modelData.svg
                                            property color  iconColor: navBtn.active ? modelData.color : "#64748b"
                                            property bool   isActive: navBtn.active

                                            onIconColorChanged: requestPaint()
                                            onIsActiveChanged:  requestPaint()
                                            Component.onCompleted: requestPaint()

                                            onPaint: {
                                                var ctx = getContext("2d")
                                                // Reset accumulated transform — Canvas keeps
                                                // CTM state across repaints, so without this
                                                // every click would compound the scale() below
                                                // and the icon would grow on every redraw.
                                                ctx.setTransform(1, 0, 0, 1, 0, 0)
                                                ctx.globalAlpha = 1.0
                                                ctx.clearRect(0, 0, width, height)
                                                var col = navIconCanvas.iconColor.toString()
                                                ctx.strokeStyle = col
                                                ctx.fillStyle   = col
                                                ctx.lineWidth   = 1.6
                                                ctx.lineCap     = "round"
                                                ctx.lineJoin    = "round"

                                                var k = navIconCanvas.iconId
                                                var sx = width / 22, sy = height / 22
                                                ctx.scale(sx, sy)

                                                if (k === "map") {
                                                    // Map pin
                                                    ctx.beginPath()
                                                    ctx.arc(11, 9, 6, Math.PI, 0)
                                                    ctx.lineTo(11, 20)
                                                    ctx.closePath()
                                                    ctx.stroke()
                                                    ctx.beginPath()
                                                    ctx.arc(11, 9, 2.5, 0, Math.PI*2)
                                                    ctx.fill()
                                                } else if (k === "dashboard") {
                                                    function rrect(rx,ry,rw,rh,rr){
                                                        ctx.beginPath()
                                                        ctx.moveTo(rx+rr, ry); ctx.lineTo(rx+rw-rr, ry)
                                                        ctx.arcTo(rx+rw,ry, rx+rw,ry+rr, rr)
                                                        ctx.lineTo(rx+rw, ry+rh-rr)
                                                        ctx.arcTo(rx+rw,ry+rh, rx+rw-rr,ry+rh, rr)
                                                        ctx.lineTo(rx+rr, ry+rh)
                                                        ctx.arcTo(rx,ry+rh, rx,ry+rh-rr, rr)
                                                        ctx.lineTo(rx, ry+rr)
                                                        ctx.arcTo(rx,ry, rx+rr,ry, rr)
                                                        ctx.closePath()
                                                    }
                                                    var bars = [{x:2,h:10},{x:7,h:16},{x:12,h:7},{x:17,h:13}]
                                                    bars.forEach(function(b){
                                                        var bh = b.h, by = 20 - bh
                                                        rrect(b.x, by, 3.5, bh, 1); ctx.fill()
                                                    })
                                                    ctx.beginPath(); ctx.moveTo(1, 20.5); ctx.lineTo(21, 20.5); ctx.stroke()
                                                } else if (k === "swarm") {
                                                    function miniDrone(dx, dy, s) {
                                                        ctx.beginPath(); ctx.arc(dx, dy, s*1.5, 0, Math.PI*2); ctx.stroke()
                                                        ctx.beginPath(); ctx.moveTo(dx-s*2.2,dy); ctx.lineTo(dx-s*0.8,dy); ctx.stroke()
                                                        ctx.beginPath(); ctx.moveTo(dx+s*0.8,dy); ctx.lineTo(dx+s*2.2,dy); ctx.stroke()
                                                    }
                                                    miniDrone(11, 4.5, 1.8); miniDrone(4, 16, 1.5); miniDrone(18, 16, 1.5)
                                                    ctx.globalAlpha = 0.4
                                                    ctx.beginPath()
                                                    ctx.moveTo(11,6); ctx.lineTo(4,14.5)
                                                    ctx.moveTo(11,6); ctx.lineTo(18,14.5)
                                                    ctx.moveTo(4,14.5); ctx.lineTo(18,14.5)
                                                    ctx.stroke()
                                                    ctx.globalAlpha = 1.0
                                                } else if (k === "safety") {
                                                    ctx.beginPath()
                                                    ctx.moveTo(11, 2); ctx.lineTo(20, 6); ctx.lineTo(20, 12)
                                                    ctx.bezierCurveTo(20, 17, 15, 20, 11, 21)
                                                    ctx.bezierCurveTo(7, 20, 2, 17, 2, 12); ctx.lineTo(2, 6); ctx.closePath()
                                                    ctx.stroke()
                                                    ctx.lineWidth = 1.8
                                                    ctx.beginPath()
                                                    ctx.moveTo(7, 11.5); ctx.lineTo(10, 14.5); ctx.lineTo(15.5, 8.5)
                                                    ctx.stroke()
                                                } else if (k === "experiment") {
                                                    ctx.beginPath()
                                                    ctx.moveTo(8, 2); ctx.lineTo(8, 10); ctx.lineTo(3, 19)
                                                    ctx.bezierCurveTo(3, 21, 5, 22, 7, 21); ctx.lineTo(15, 21)
                                                    ctx.bezierCurveTo(17, 22, 19, 21, 19, 19)
                                                    ctx.lineTo(14, 10); ctx.lineTo(14, 2); ctx.closePath()
                                                    ctx.stroke()
                                                    ctx.beginPath(); ctx.moveTo(7,3); ctx.lineTo(15,3); ctx.stroke()
                                                    ctx.globalAlpha = 0.6
                                                    ctx.beginPath(); ctx.arc(9, 17, 1.2, 0, Math.PI*2); ctx.fill()
                                                    ctx.beginPath(); ctx.arc(13, 15, 0.9, 0, Math.PI*2); ctx.fill()
                                                    ctx.globalAlpha = 1.0
                                                } else if (k === "log") {
                                                    ctx.beginPath()
                                                    ctx.moveTo(3, 1); ctx.lineTo(13, 1); ctx.lineTo(17, 5)
                                                    ctx.lineTo(17, 19); ctx.lineTo(3, 19); ctx.closePath()
                                                    ctx.stroke()
                                                    ctx.beginPath()
                                                    ctx.moveTo(13, 1); ctx.lineTo(17, 5); ctx.lineTo(13, 5); ctx.closePath(); ctx.stroke()
                                                    ctx.globalAlpha = 0.7
                                                    ;[7, 10, 13, 16].forEach(function(y){
                                                        ctx.beginPath(); ctx.moveTo(6, y); ctx.lineTo(14, y); ctx.stroke()
                                                    })
                                                    ctx.globalAlpha = 1.0
                                                }
                                            }
                                        }

                                        Text {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            text: modelData.label
                                            font.pixelSize: 8; font.weight: Font.Medium
                                            font.letterSpacing: 0.3
                                            color: navBtn.active ? modelData.color : "#4a5568"
                                            Behavior on color { ColorAnimation { duration: 120 } }
                                        }
                                    }

                                    MouseArea {
                                        id: navHover
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onClicked: root.selectTab(index)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // ── Tab content area ──────────────────────────────────────────
            Item {
                id: workspace
                width:  parent.width - navBar.width
                height: parent.height
                clip: true

                // ── TAB 0: Map (always-loaded, kept alive across tab switches) ──
                Item {
                    id: mapTab
                    anchors.fill: parent
                    visible: root.currentTab === 0

                    Loader {
                        id: mapLoader
                        anchors.fill: parent
                        asynchronous: true
                        source: "MapView.qml"
                        onLoaded: {
                            item.mapPickSelected.connect(root.deliverMapPick)
                        }
                    }

                    // Floating WP-toolbar over the map (bottom center)
                    Rectangle {
                        anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter; bottomMargin: 16 }
                        width: wpToolbar.implicitWidth + 24
                        height: 40; radius: 8
                        color: "#161b27ee"
                        border.color: root.mapWaypointMode ? "#22c55e" : "#2d3748"
                        border.width: 1

                        Row {
                            id: wpToolbar
                            anchors.centerIn: parent
                            spacing: 8

                            Rectangle {
                                width: 150; height: 28; radius: 5
                                color: root.mapWaypointMode ? "#15803d" : (wpModeM.containsMouse ? "#1e3a5f" : "#1e2535")
                                border.color: root.mapWaypointMode ? "#22c55e" : "#2563eb"; border.width: 1
                                anchors.verticalCenter: parent.verticalCenter
                                Row {
                                    anchors.centerIn: parent; spacing: 6
                                    Cmp.Icon { name: root.mapWaypointMode ? "check" : "plus"; size: 12; color: "white"; anchors.verticalCenter: parent.verticalCenter }
                                    Text {
                                        text: root.mapWaypointMode ? "WP-MODUS AKTIV" : "WAYPOINT HINZUFÜGEN"
                                        color: "white"; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 0.5
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }
                                MouseArea { id: wpModeM; anchors.fill: parent; hoverEnabled: true; onClicked: root.toggleMapWaypointMode() }
                            }

                            Text { text: "Alt:"; color: "#94a3b8"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter }

                            TextField {
                                width: 52; height: 26; text: root.mapWaypointAlt.toString()
                                background: Rectangle { color: "#1e2535"; radius: 4; border.color: "#2d3748" }
                                color: "#e2e8f0"; font.pixelSize: 10; font.family: "Consolas"
                                anchors.verticalCenter: parent.verticalCenter
                                onTextChanged: { var v = parseFloat(text); if (!isNaN(v)) root.mapWaypointAlt = v }
                            }
                            Text { text: "m"; color: "#64748b"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter }

                            Rectangle {
                                width: 64; height: 28; radius: 5
                                color: clrM.containsMouse ? "#7f1d1d" : "#1e2535"
                                border.color: "#ef4444"; border.width: 1
                                anchors.verticalCenter: parent.verticalCenter
                                visible: globalMissionWaypoints.count > 0
                                Row {
                                    anchors.centerIn: parent; spacing: 4
                                    Cmp.Icon { name: "trash"; size: 11; color: "#fecaca"; anchors.verticalCenter: parent.verticalCenter }
                                    Text { text: "CLEAR"; color: "#fecaca"; font.pixelSize: 9; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter }
                                }
                                MouseArea { id: clrM; anchors.fill: parent; hoverEnabled: true; onClicked: { globalMissionWaypoints.clear(); root.syncWaypointsToMap() } }
                            }

                            // ── MISSION STARTEN ─────────────────────────
                            Rectangle {
                                id: startMissionBtn
                                height: 28; radius: 5
                                width: startMissionRow.implicitWidth + 18
                                anchors.verticalCenter: parent.verticalCenter
                                visible: globalMissionWaypoints.count > 0
                                property bool _enabled: root.selectedDroneId !== "" || Cmp.AppState.missionTargetCount > 0
                                color: !_enabled ? "#0d1117"
                                                  : (startMM.containsMouse ? "#15803d" : "#166534")
                                border.color: _enabled ? "#22c55e" : "#374151"; border.width: 1
                                Row {
                                    id: startMissionRow
                                    anchors.centerIn: parent; spacing: 5
                                    Cmp.Icon { name: "play"; size: 11; color: parent.parent._enabled ? "#bbf7d0" : "#374151"; anchors.verticalCenter: parent.verticalCenter }
                                    Text {
                                        text: {
                                            var n = Cmp.AppState.missionTargetCount > 0 ? Cmp.AppState.missionTargetCount : (root.selectedDroneId ? 1 : 0)
                                            return "MISSION STARTEN (" + globalMissionWaypoints.count + " WP" + (n > 1 ? " · " + n + " Drohnen" : "") + ")"
                                        }
                                        color: parent.parent._enabled ? "#bbf7d0" : "#374151"
                                        font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 0.5
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }
                                MouseArea {
                                    id: startMM; anchors.fill: parent; hoverEnabled: true
                                    enabled: parent._enabled
                                    onClicked: root.startGlobalMission()
                                }
                            }

                            Rectangle {
                                width: wpCntT.implicitWidth + 16; height: 26; radius: 13
                                color: "#1e3a5f"
                                border.color: "#2563eb"; border.width: 1
                                anchors.verticalCenter: parent.verticalCenter
                                visible: globalMissionWaypoints.count > 0
                                Text {
                                    id: wpCntT
                                    anchors.centerIn: parent
                                    text: globalMissionWaypoints.count + " WP"
                                    color: "#93c5fd"; font.pixelSize: 9; font.weight: Font.Bold
                                }
                            }
                        }
                    }

                    // HUD overlays (only on map tab)
                    Cmp.HudOverlays {
                        selectedDroneId: root.selectedDroneId
                        droneCount:      telemetryModel ? telemetryModel.count : 0
                        connectedCount:  swarm ? swarm.connectedDrones : 0
                    }
                }

                // ── Telemetry → map bridge ────────────────────────────────
                Connections {
                    target: swarm
                    function onTelemetryUpdated(snapshot) {
                        if (!mapLoader.item) return
                        var drones = {}
                        var ids = swarm.droneIds()
                        if (!ids) return
                        for (var i = 0; i < ids.length; i++) {
                            var id = ids[i]
                            var s = swarm.droneSnapshot(id)
                            if (s && s.lat !== undefined && s.lat !== 0.0) {
                                drones[id] = { lat: s.lat, lon: s.lon, heading: s.yaw || 0, armed: s.armed || false, droneType: (s.droneType || "generic") }
                                if (!root._zoomedDrones[id]) {
                                    var zd = Object.assign({}, root._zoomedDrones)
                                    zd[id] = true
                                    root._zoomedDrones = zd
                                    mapLoader.item.flyTo(s.lat, s.lon)
                                }
                            }
                        }
                        mapLoader.item.updateDrones(JSON.stringify(drones))
                        mapLoader.item.setSelectedDrone(root.selectedDroneId)
                    }
                }

                // ── Swarm → map visualization bridge ────────────────────────
                Connections {
                    target: swarm
                    function onFormationUpdated(leaderId, positions) {
                        if (mapLoader.item) {
                            mapLoader.item.updateFormation(leaderId, positions)
                        }
                    }
                }
                
                // ── TABS 1..N: Panel Loaders ──────────────────────────────
                // Each tab gets its own Loader. Inactive tabs are unloaded
                // (active=false) to save memory; first-tab visit triggers load.
                Repeater {
                    id: panelRepeater
                    model: root.tabs

                    delegate: Item {
                        readonly property var cfg: modelData
                        readonly property int tabIndex: index
                        anchors.fill: parent
                        visible: root.currentTab === tabIndex && tabIndex !== 0

                        // Header bar (panel title)
                        Rectangle {
                            id: tabHeader
                            visible: parent.visible
                            anchors { top: parent.top; left: parent.left; right: parent.right }
                            height: 36
                            color: "#1a2035"
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#2d3748" }
                            Row {
                                anchors { left: parent.left; leftMargin: 16; verticalCenter: parent.verticalCenter }
                                spacing: 8
                                Rectangle { width: 3; height: 14; radius: 2; color: cfg.color; anchors.verticalCenter: parent.verticalCenter }
                                Text { text: cfg.title.toUpperCase(); color: "#e2e8f0"; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.1; anchors.verticalCenter: parent.verticalCenter }
                            }
                        }

                        Loader {
                            id: panelLoader
                            anchors { top: tabHeader.bottom; left: parent.left; right: parent.right; bottom: parent.bottom }
                            asynchronous: true
                            // Stay loaded once visited (avoids reloads on tab switching)
                            property bool everVisited: false
                            active: everVisited || (root.currentTab === tabIndex && tabIndex !== 0)
                            Connections {
                                target: root
                                function onCurrentTabChanged() {
                                    if (root.currentTab === tabIndex && tabIndex !== 0 && !panelLoader.everVisited) {
                                        panelLoader.everVisited = true
                                    }
                                }
                            }
                            source: tabIndex === 0 ? "" : (function(){
                                var overrides = {
                                    "flightlog": "FlightLogPanel",
                                    "gimbal":    "GimbalPanel",
                                    "ros2":      "ROS2Panel"
                                }
                                var name = overrides[cfg.id] || (cfg.id.charAt(0).toUpperCase() + cfg.id.slice(1) + "Panel")
                                return "panels/" + name + ".qml"
                            })()
                            onLoaded: {
                                if (item && item.hasOwnProperty("activeLogModel"))
                                    item.activeLogModel = globalLogModel
                                if (item && item.hasOwnProperty("selectedDroneId"))
                                    item.selectedDroneId = Qt.binding(function(){ return root.selectedDroneId })
                                if (item && item.hasOwnProperty("swarmRef"))
                                    item.swarmRef = swarm
                                if (item && item.hasOwnProperty("experiment"))
                                    item.experiment = experiment
                                if (item && item.hasOwnProperty("globalWaypoints"))
                                    item.globalWaypoints = globalMissionWaypoints
                            }
                        }
                    }
                }
            }
        }

        // ── Status bar ────────────────────────────────────────────────────────
        Rectangle {
            id: statusBar
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
            height: 28
            z: 2
            color: statusBar.lastLevel === "ERROR" ? "#7f1d1d" : (statusBar.lastLevel === "WARN" ? "#78350f" : "#161b27")
            Behavior on color { ColorAnimation { duration: 200 } }
            Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: "#2d3748" }

            property string lastLevel: "INFO"

            Row {
                anchors { fill: parent; leftMargin: 16; rightMargin: 16 }
                spacing: 12

                property int errorCount: {
                    var count = 0
                    for (var i = 0; i < globalLogModel.count; i++) {
                        if (globalLogModel.get(i).level === "ERROR") count++
                    }
                    return count
                }
                property int warnCount: {
                    var count = 0
                    for (var i = 0; i < globalLogModel.count; i++) {
                        if (globalLogModel.get(i).level === "WARN") count++
                    }
                    return count
                }

                Text {
                    id: statusMsg
                    text: "RZ GCS ready."
                    color: parent.parent.lastLevel === "ERROR" ? "white" : (parent.parent.lastLevel === "WARN" ? "#fcd34d" : "#94a3b8")
                    font.pixelSize: 11
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 150
                    elide: Text.ElideRight
                }

                Item { width: parent.width - 300; height: parent.height }

                Row {
                    spacing: 8
                    anchors.verticalCenter: parent.verticalCenter

                    Rectangle {
                        width: errBadge.implicitWidth + 12; height: 18; radius: 9
                        color: parent.parent.errorCount > 0 ? "#7f1d1d" : "transparent"
                        visible: parent.parent.errorCount > 0
                        Text {
                            id: errBadge
                            anchors.centerIn: parent
                            text: parent.parent.errorCount + " ⚠"
                            color: "#fca5a5"; font.pixelSize: 9; font.weight: Font.Bold
                        }
                    }

                    Rectangle {
                        width: warnBadge.implicitWidth + 12; height: 18; radius: 9
                        color: parent.parent.warnCount > 0 ? "#78350f" : "transparent"
                        visible: parent.parent.warnCount > 0
                        Text {
                            id: warnBadge
                            anchors.centerIn: parent
                            text: parent.parent.warnCount + " ⚡"
                            color: "#fcd34d"; font.pixelSize: 9; font.weight: Font.Bold
                        }
                    }
                }

                Rectangle {
                    width: 60; height: 20; radius: 4
                    color: logBtnM.containsMouse ? "#374151" : "#1e2535"
                    border.color: "#2d3748"; border.width: 1
                    anchors.verticalCenter: parent.verticalCenter
                    Text { anchors.centerIn: parent; text: "LOGS"; color: "#94a3b8"; font.pixelSize: 9; font.weight: Font.Bold; font.letterSpacing: 1 }
                    MouseArea {
                        id: logBtnM; anchors.fill: parent; hoverEnabled: true
                        onClicked: root.selectTabById("log")
                    }
                }

                Connections {
                    target: swarm
                    function onLogMessage(level, text) {
                        statusMsg.text = "[" + level + "] " + text
                        statusBar.lastLevel = level
                        clearTimer.interval = (level === "ERROR" || level === "WARN") ? 10000 : 5000
                        clearTimer.restart()
                    }
                }

                Connections {
                    target: safety
                    function onApfLogMessage(text) {
                        if (text.includes("VIOLATION") || text.includes("ERROR")) {
                            statusMsg.text = "[SAFETY] " + text
                            statusBar.lastLevel = "ERROR"
                            clearTimer.interval = 15000
                            clearTimer.restart()
                        }
                    }
                    function onGeofenceBreached(droneId, reason) {
                        statusMsg.text = "[ALERT] " + droneId + ": " + reason
                        statusBar.lastLevel = "ERROR"
                        clearTimer.interval = 15000
                        clearTimer.restart()
                    }
                }

                Timer {
                    id: clearTimer; interval: 5000
                    onTriggered: {
                        statusMsg.text = "RZ GCS ready."
                        statusBar.lastLevel = "INFO"
                    }
                }
            }

            Row {
                anchors { right: parent.right; rightMargin: 16; verticalCenter: parent.verticalCenter }
                spacing: 16
                Text { text: "PyQt6 + QML"; color: "#2d3748"; font.pixelSize: 9 }
                Text { text: "RZ GCS v0.2.0"; color: "#2d3748"; font.pixelSize: 9 }
            }
        }
    }

    // -- License overlay (covers everything when trial expired) --
    Cmp.LicenseOverlay { }
}

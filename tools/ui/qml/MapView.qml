import QtQuick
import QtQuick.Controls
import QtWebEngine

// Full-screen OSM map + HUD instruments + 3D drone overlay
Item {
    id: root

    // ── live telemetry helpers (first drone or selected) ──────────────────
    property string selectedDroneId: ""

    function snap(key, def) {
        if (telemetryModel.count === 0) return def
        // resolve which drone ID to use
        var ids = swarm.droneIds()
        if (ids.length === 0) return def
        var did = (selectedDroneId !== "" && ids.indexOf(selectedDroneId) >= 0)
                  ? selectedDroneId
                  : ids[0]
        var s = telemetryModel.snapshotFor(did)
        return (s && s[key] !== undefined) ? s[key] : def
    }

    property bool pickMode: false
    property bool boundaryDrawMode: false
    property string currentMapType: "dark"

    function setMapType(typeName) {
        currentMapType = typeName
        webView.runJavaScript("setMapType('" + typeName + "')")
    }

    function setPickMode(enabled) {
        pickMode = enabled
        webView.runJavaScript("setPickMode(" + enabled + ")")
    }

    function setBoundaryDrawMode(enabled) {
        boundaryDrawMode = enabled
        webView.runJavaScript("setBoundaryDrawMode(" + enabled + ")")
    }

    function updateFieldBoundary(points) {
        webView.runJavaScript("updateFieldBoundary(" + JSON.stringify(points) + ")")
    }

    function updateCoverageWaypoints(waypoints) {
        webView.runJavaScript("updateCoverageWaypoints(" + JSON.stringify(waypoints) + ")")
    }

    function clearFieldCoverage() {
        webView.runJavaScript("clearFieldCoverage()")
    }

    function updateCollisionPredictions(predictions) {
        webView.runJavaScript("updateCollisionPredictions(" + JSON.stringify(predictions) + ")")
    }

    function clearCollisionPredictions() {
        webView.runJavaScript("clearCollisionVisualization()")
    }

    // ── Map ──────────────────────────────────────────────────────────────
    WebEngineView {
        id: webView
        anchors.fill: parent
        z: 0
        Component.onCompleted: loadHtml(root.mapHtml, "qrc:/")
        onLoadingChanged: function(info) {
            if (info.status === WebEngineLoadingInfo.LoadSucceededStatus)
                console.log("[MapView] Leaflet OK")
        }
        onNavigationRequested: function(req) {
            var url = req.url.toString()
            if (url.startsWith("qrc://pick?")) {
                req.reject()
                var params = url.substring("qrc://pick?".length).split("&")
                var lat = 0, lon = 0
                for (var i = 0; i < params.length; i++) {
                    var kv = params[i].split("=")
                    if (kv[0] === "lat") lat = parseFloat(kv[1])
                    if (kv[0] === "lon") lon = parseFloat(kv[1])
                }
                root.mapPickSelected(lat, lon)
            } else if (url.startsWith("qrc://boundary-point?")) {
                req.reject()
                var params = url.substring("qrc://boundary-point?".length).split("&")
                var lat = 0, lon = 0
                for (var i = 0; i < params.length; i++) {
                    var kv = params[i].split("=")
                    if (kv[0] === "lat") lat = parseFloat(kv[1])
                    if (kv[0] === "lon") lon = parseFloat(kv[1])
                }
                root.boundaryPointSelected(lat, lon)
            } else if (url.startsWith("qrc://waypoint-moved?")) {
                req.reject()
                var params = url.substring("qrc://waypoint-moved?".length).split("&")
                var index = -1, lat = 0, lon = 0
                for (var i = 0; i < params.length; i++) {
                    var kv = params[i].split("=")
                    if (kv[0] === "index") index = parseInt(kv[1])
                    if (kv[0] === "lat") lat = parseFloat(kv[1])
                    if (kv[0] === "lon") lon = parseFloat(kv[1])
                }
                if (index >= 0) {
                    root.waypointMoved(index, lat, lon)
                }
            } else {
                req.accept()
            }
        }
    }

    // ── Map type switcher overlay ─────────────────────────────────────
    Row {
        anchors { top: parent.top; right: parent.right; topMargin: 10; rightMargin: 10 }
        spacing: 4
        z: 10

        Repeater {
            model: [
                { id: "dark",      label: "Dark",      icon: "◐" },
                { id: "street",    label: "Street",    icon: "▢" },
                { id: "satellite", label: "Satellite", icon: "🛰" },
                { id: "hybrid",    label: "Hybrid",    icon: "◆" },
                { id: "topo",      label: "Topo",      icon: "⛰" },
            ]
            delegate: Rectangle {
                width: 70; height: 26; radius: 5
                color: root.currentMapType === modelData.id
                       ? "#2563eb" : "#cc0d1117"
                border.color: root.currentMapType === modelData.id
                              ? "#3b82f6" : "#334155"
                border.width: 1
                Behavior on color { ColorAnimation { duration: 120 } }
                Row {
                    anchors.centerIn: parent; spacing: 4
                    Text { text: modelData.icon; font.pixelSize: 11 }
                    Text {
                        text: modelData.label
                        color: root.currentMapType === modelData.id ? "white" : "#94a3b8"
                        font.pixelSize: 9; font.weight: Font.Bold
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: root.setMapType(modelData.id)
                }
            }
        }
    }

    // Pick mode cursor overlay
    Rectangle {
        anchors.fill: parent
        color: "transparent"
        visible: root.pickMode
        border.color: "#f59e0b"; border.width: 2
        Rectangle {
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height: 32; color: "#ccf59e0b"
            Text {
                anchors.centerIn: parent
                text: "WAYPOINT MODE  —  Click on map to set waypoint  —  ESC to cancel"
                color: "white"; font.pixelSize: 12; font.weight: Font.Bold
            }
            MouseArea { anchors.fill: parent }
        }
        Keys.onEscapePressed: root.deliverMapPick(0, 0)
        focus: visible
    }

    // Called from main.qml on telemetry
    function updateDrones(jsonStr)      { webView.runJavaScript("updateDrones(" + jsonStr + ")") }
    function updateWaypoints(jsonStr)   { webView.runJavaScript("updateWaypoints(" + jsonStr + ")") }
    // Snapshot the current pending waypoints into the "dispatched" layer so
    // they stay visible on the map (different colour) after the WP list is
    // cleared post-mission-start.
    function commitDispatchedWaypoints(jsonStr) { webView.runJavaScript("commitDispatchedWaypoints(" + jsonStr + ")") }
    function clearDispatchedWaypoints()         { webView.runJavaScript("clearDispatchedWaypoints()") }
    function updateGeofence(lat,lon,r)  { webView.runJavaScript("updateGeofence("+lat+","+lon+","+r+")") }
    function centerMap(lat, lon)        { webView.runJavaScript("map.setView(["+lat+","+lon+"], map.getZoom())") }
    function clearTracks()              { webView.runJavaScript("clearTracks()") }
    function flyTo(lat, lon)            { webView.runJavaScript("map.flyTo(["+lat+","+lon+"], 18);") }
    function setSelectedDrone(did)      { webView.runJavaScript("setSelectedDrone('" + did + "')") }

    // Swarm algorithm visualization functions
    function clearSwarmVisualization() {
        webView.runJavaScript("clearSwarmVisualization()")
    }

    function updateFormation(leaderId, positions) {
        webView.runJavaScript("updateFormation('"+leaderId+"', "+JSON.stringify(positions)+")")
    }

    function updateBoidsVisualization(activeDrones) {
        webView.runJavaScript("updateBoidsVisualization("+JSON.stringify(activeDrones)+")")
    }

    function updateConsensusVisualization(votingDrones) {
        webView.runJavaScript("updateConsensusVisualization("+JSON.stringify(votingDrones)+")")
    }

    function updateBehaviorTreeVisualization(missionType, activeDrones) {
        webView.runJavaScript("updateBehaviorTreeVisualization("+missionType+", "+JSON.stringify(activeDrones)+")")
    }

    signal mapPickSelected(real lat, real lon)
    signal waypointMoved(int index, real lat, real lon)
    signal boundaryPointSelected(real lat, real lon)

    // Drone-color palette (mirrors Python DRONE_COLORS)
    readonly property var droneColors: [
        "#2563eb","#22c55e","#f59e0b","#8b5cf6","#ef4444",
        "#06b6d4","#f97316","#ec4899","#84cc16","#14b8a6"
    ]

    property string mapHtml: '
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html,body,#map { margin:0;padding:0;width:100%;height:100%;background:#0f1117; }
  .drone-label { background:transparent;border:none;color:#e2e8f0;font-size:11px;font-weight:700;font-family:Consolas,monospace;white-space:nowrap; }
</style>
</head>
<body>
<div id="map"></div>
<script>
var map = L.map("map", {
  center: [48.137, 11.575],
  zoom: 15,
  zoomControl: true,
  attributionControl: false
});

var mapLayers = {
  dark: L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom:19, opacity:0.85}),
  street: L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom:19, opacity:0.95}),
  satellite: L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {maxZoom:19, opacity:0.95, attribution:"Esri World Imagery"}),
  hybrid: L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {maxZoom:19, opacity:0.95}),
  topo: L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {maxZoom:17, opacity:0.9}),
};
// Road overlay for hybrid mode
var roadOverlay = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {maxZoom:19, opacity:0.35, className:"hybrid-roads"});
var hybridActive = false;

var darkStyle = document.createElement("style");
darkStyle.id = "dark-filter";
darkStyle.innerHTML = ".leaflet-tile { filter: invert(1) hue-rotate(180deg) brightness(0.85) saturate(1.1); }";
document.head.appendChild(darkStyle);

var currentLayer = mapLayers.dark;
currentLayer.addTo(map);

function setMapType(type) {
  if (hybridActive) { try { map.removeLayer(roadOverlay); } catch(e){} hybridActive = false; }
  if (currentLayer) map.removeLayer(currentLayer);
  currentLayer = mapLayers[type] || mapLayers.dark;
  currentLayer.addTo(map);
  if (type === "hybrid") { roadOverlay.addTo(map); hybridActive = true; }
  var ds = document.getElementById("dark-filter");
  if (type === "dark") {
    ds.innerHTML = ".leaflet-tile { filter: invert(1) hue-rotate(180deg) brightness(0.85) saturate(1.1); }";
  } else if (type === "topo") {
    ds.innerHTML = ".leaflet-tile { filter: brightness(0.85) saturate(0.9); }";
  } else if (type === "satellite" || type === "hybrid") {
    ds.innerHTML = ".leaflet-tile { filter: brightness(1.05) saturate(1.1); }";
  } else {
    ds.innerHTML = ".leaflet-tile { filter: none; }";
  }
}

var droneMarkers = {}, droneTracks = {}, waypointMarkers = [], waypointLine = null, geofenceCircle = null;
// "Dispatched" waypoints — already sent to drones via Mission Start.
// Drawn in a different colour and kept on the map until the user manually
// clears them (so the user can visually follow what has been flown).
var dispatchedMarkers = [], dispatchedLine = null;
var droneTypes = {};  // id -> droneType
var selectedDroneId = "";

// Swarm algorithm visualization
var formationLines = [], leaderMarker = null, formationCircles = [];

function droneColor(id) {
  return droneTypes[id] === "observation" ? "#8b5cf6" : "#2563eb";
}

function setSelectedDrone(did) {
  selectedDroneId = did;
  Object.keys(droneMarkers).forEach(function(id) {
    var m = droneMarkers[id];
    if (m && m._lastData) m.setIcon(makeDroneIcon(id, m._lastData, id === did));
  });
}

function makeDroneIcon(id, d, selected) {
  var col = droneColor(id);
  var hdg = d.heading || 0;
  var armed = d.armed || false;
  var sz = selected ? 52 : 42;
  var cx = sz / 2;
  var armR = cx * 0.75;
  var rotR = cx * 0.18;
  var bodyR = cx * 0.26;
  // Glow ring (selected)
  var glow = selected
    ? \'<circle cx="\'+cx+\'" cy="\'+cx+\'" r="\'+(cx-1)+\'" fill="none" stroke="#f59e0b" stroke-width="2.5" opacity="0.95"/>\' : \'\';
  // Armed pulse ring
  var ring = armed
    ? \'<circle cx="\'+cx+\'" cy="\'+cx+\'" r="\'+(cx*0.52)+\'" fill="none" stroke="\'+col+\'" stroke-width="1.2" opacity="0.45" stroke-dasharray="3 3"/>\' : \'\';
  // 4 arms (X-config, 45/135/225/315 deg)
  var arms = \'\';
  var aAngles = [45,135,225,315];
  for (var i=0;i<4;i++) {
    var rad = (aAngles[i]-90)*Math.PI/180;
    var bx = cx + bodyR*Math.cos(rad), by = cx + bodyR*Math.sin(rad);
    var tx = cx + armR*Math.cos(rad), ty = cx + armR*Math.sin(rad);
    arms += \'<line x1="\'+bx+\'" y1="\'+by+\'" x2="\'+tx+\'" y2="\'+ty+\'" stroke="\'+col+\'" stroke-width="\'+(sz*0.075)+\'" stroke-linecap="round"/>\';
    arms += \'<circle cx="\'+tx+\'" cy="\'+ty+\'" r="\'+rotR+\'" fill="\'+col+\'" opacity="0.28"/>\';
    arms += \'<circle cx="\'+tx+\'" cy="\'+ty+\'" r="\'+rotR+\'" fill="none" stroke="\'+col+\'" stroke-width="1.2" opacity="0.8"/>\';
  }
  // Body
  var body = \'<circle cx="\'+cx+\'" cy="\'+cx+\'" r="\'+bodyR+\'" fill="\'+col+\'" opacity="0.95"/>\';
  body += \'<circle cx="\'+cx+\'" cy="\'+cx+\'" r="\'+(bodyR*0.48)+\'" fill="#0f1117"/>\';
  // Heading arrow (points forward, rotated by heading)
  var arrowTip = cx - armR*0.82;
  var arrowW   = sz*0.065;
  var arrow = \'<g transform="rotate(\'+hdg+\',\'+cx+\',\'+cx+\')">\';
  arrow += \'<line x1="\'+cx+\'" y1="\'+cx+\'" x2="\'+cx+\'" y2="\'+arrowTip+\'" stroke="white" stroke-width="\'+(sz*0.055)+\'" stroke-linecap="round" opacity="0.9"/>\';
  arrow += \'<polygon points="\'+cx+\',\'+(arrowTip-1)+\' \'+(cx-arrowW)+\',\'+(arrowTip+sz*0.11)+\' \'+(cx+arrowW)+\',\'+(arrowTip+sz*0.11)+\'" fill="white" opacity="0.9"/>\';
  arrow += \'</g>\';
  var svg = \'<svg xmlns="http://www.w3.org/2000/svg" width="\'+sz+\'" height="\'+sz+\'" viewBox="0 0 \'+sz+\' \'+sz+\'">\' + glow + ring + arms + body + arrow + \'</svg>\';
  return L.divIcon({ className:"", html:svg, iconSize:[sz,sz], iconAnchor:[cx,cx] });
}

function updateDrones(data) {
  var ids = Object.keys(data);
  ids.forEach(function(id) {
    var d = data[id];
    if (!d.lat || !d.lon) return;
    // Store/update type so droneColor() uses it
    var prevType = droneTypes[id];
    droneTypes[id] = d.droneType || "generic";
    var col = droneColor(id);
    var sel = (id === selectedDroneId);
    var icon = makeDroneIcon(id, d, sel);
    if (!droneMarkers[id]) {
      droneMarkers[id] = L.marker([d.lat,d.lon],{icon:icon,zIndexOffset: sel?1000:0}).addTo(map);
      // Tooltip: show type icon + id
      var typeIcon = droneTypes[id] === "observation" ? "[OBS] " : "";
      droneMarkers[id].bindTooltip(typeIcon + id,{permanent:true,className:"drone-label",direction:"right",offset:[sel?26:20,0]});
      droneTracks[id] = L.polyline([[d.lat,d.lon]],{color:col,weight:2,opacity:0.55}).addTo(map);
    } else {
      droneMarkers[id].setLatLng([d.lat,d.lon]).setIcon(icon);
      // Update track color if type changed
      if (prevType !== droneTypes[id] && droneTracks[id]) {
        droneTracks[id].setStyle({color: col});
      }
    }
    droneMarkers[id]._lastData = d;
    droneTracks[id].addLatLng([d.lat,d.lon]);
  });
  // Remove stale
  Object.keys(droneMarkers).forEach(function(id) {
    if (!data[id]) {
      map.removeLayer(droneMarkers[id]);
      map.removeLayer(droneTracks[id]);
      delete droneMarkers[id]; delete droneTracks[id];
    }
  });
}

function updateWaypoints(wps) {
  waypointMarkers.forEach(function(m){ map.removeLayer(m); });
  waypointMarkers = [];
  if (waypointLine) { map.removeLayer(waypointLine); waypointLine = null; }
  
  if (!wps || wps.length === 0) return;
  
  var latlngs = [];
  wps.forEach(function(wp, i) {
    var icon = L.divIcon({ className:"", iconSize:[22,22], iconAnchor:[11,11],
      html:\'<div style="width:22px;height:22px;border-radius:50%;border:2px solid #f59e0b;background:#78350f;display:flex;align-items:center;justify-content:center;color:#fcd34d;font-size:9px;font-weight:bold;">\' + (i+1) + \'</div>\'});
    
    // Create draggable marker
    var marker = L.marker([wp.lat,wp.lon], {
      icon: icon,
      draggable: true,
      autoPan: true
    }).bindTooltip("WP"+(i+1)+": "+wp.alt+"m",{direction:"top"}).addTo(map);
    
    // Drag start - visual feedback
    marker.on("dragstart", function(e) {
      e.target.setOpacity(0.6);
      if (waypointLine) waypointLine.setStyle({opacity: 0.3});
    });
    
    // Dragging - update line in real-time
    marker.on("drag", function(e) {
      if (waypointLine) {
        var newLatLngs = [];
        waypointMarkers.forEach(function(m) {
          newLatLngs.push(m.getLatLng());
        });
        waypointLine.setLatLngs(newLatLngs);
      }
    });
    
    // Drag end - notify QML and restore opacity
    marker.on("dragend", function(e) {
      e.target.setOpacity(1.0);
      if (waypointLine) waypointLine.setStyle({opacity: 0.7});
      
      var newPos = e.target.getLatLng();
      
      // Find current index of this marker in the array (in case waypoints were added/removed)
      var idx = -1;
      for (var j = 0; j < waypointMarkers.length; j++) {
        if (waypointMarkers[j] === e.target) {
          idx = j;
          break;
        }
      }
      
      if (idx >= 0) {
        // Notify QML about waypoint position change
        window.location = "qrc://waypoint-moved?index=" + idx + "&lat=" + newPos.lat + "&lon=" + newPos.lng;
      }
    });
    
    waypointMarkers.push(marker);
    latlngs.push([wp.lat, wp.lon]);
  });
  
  // Draw connecting line between waypoints
  if (latlngs.length > 1) {
    waypointLine = L.polyline(latlngs, {
      color: "#f59e0b",
      weight: 2,
      opacity: 0.7,
      dashArray: "8,4"
    }).addTo(map);
  }
}

function commitDispatchedWaypoints(wps) {
  if (!wps || wps.length === 0) return;
  var idxOffset = dispatchedMarkers.length;
  var latlngs = [];
  // Preserve any previous polyline endpoints so successive dispatches connect
  if (dispatchedLine) {
    dispatchedLine.getLatLngs().forEach(function(p){ latlngs.push(p); });
  }
  wps.forEach(function(wp, i) {
    var n = idxOffset + i + 1;
    var icon = L.divIcon({ className:"", iconSize:[22,22], iconAnchor:[11,11],
      html:\'<div style="width:22px;height:22px;border-radius:50%;border:2px solid #22c55e;background:#14532d;display:flex;align-items:center;justify-content:center;color:#bbf7d0;font-size:9px;font-weight:bold;">\' + n + \'</div>\'});
    dispatchedMarkers.push(
      L.marker([wp.lat, wp.lon], { icon: icon })
        .bindTooltip("Mission WP " + n + ": " + wp.alt + "m", { direction: "top" })
        .addTo(map)
    );
    latlngs.push([wp.lat, wp.lon]);
  });
  if (dispatchedLine) map.removeLayer(dispatchedLine);
  dispatchedLine = L.polyline(latlngs, {
    color: "#22c55e", weight: 2, opacity: 0.6, dashArray: "6,4"
  }).addTo(map);
}

function clearDispatchedWaypoints() {
  dispatchedMarkers.forEach(function(m){ map.removeLayer(m); });
  dispatchedMarkers = [];
  if (dispatchedLine) { map.removeLayer(dispatchedLine); dispatchedLine = null; }
}

function updateGeofence(lat, lon, r) {
  if (geofenceCircle) map.removeLayer(geofenceCircle);
  geofenceCircle = L.circle([lat,lon],{radius:r,color:"#ef4444",fillColor:"#ef4444",fillOpacity:0.04,weight:2,dashArray:"6 4"}).addTo(map);
}

function clearTracks() {
  Object.values(droneTracks).forEach(function(t){ t.setLatLngs([]); });
}

var _pickMode = false;
function setPickMode(enabled) {
  _pickMode = enabled;
  map.getContainer().style.cursor = enabled ? "crosshair" : "";
}

// ── Field Coverage Planning ──────────────────────────────────────────────────
var _boundaryDrawMode = false;
var boundaryMarkers = [], boundaryLine = null;
var coverageWaypointMarkers = [], coverageWaypointLine = null;

function setBoundaryDrawMode(enabled) {
  _boundaryDrawMode = enabled;
  map.getContainer().style.cursor = enabled ? "crosshair" : "";
}

function updateFieldBoundary(points) {
  // Clear existing boundary
  boundaryMarkers.forEach(function(m){ map.removeLayer(m); });
  boundaryMarkers = [];
  if (boundaryLine) { map.removeLayer(boundaryLine); boundaryLine = null; }
  
  if (!points || points.length === 0) return;
  
  var latlngs = [];
  points.forEach(function(pt, i) {
    var icon = L.divIcon({
      className:"",
      iconSize:[18,18],
      iconAnchor:[9,9],
      html:\'<div style="width:18px;height:18px;border-radius:50%;border:2px solid #22c55e;background:#14532d;display:flex;align-items:center;justify-content:center;color:#bbf7d0;font-size:8px;font-weight:bold;">\' + (i+1) + \'</div>\'
    });
    
    var marker = L.marker([pt.lat, pt.lon], {icon: icon})
      .bindTooltip("Boundary Point " + (i+1), {direction:"top"})
      .addTo(map);
    
    boundaryMarkers.push(marker);
    latlngs.push([pt.lat, pt.lon]);
  });
  
  // Close the polygon
  if (latlngs.length >= 3) {
    latlngs.push(latlngs[0]);
    boundaryLine = L.polyline(latlngs, {
      color: "#22c55e",
      weight: 2,
      opacity: 0.7,
      dashArray: "5, 5"
    }).addTo(map);
  }
}

function updateCoverageWaypoints(waypoints) {
  // Clear existing coverage waypoints
  coverageWaypointMarkers.forEach(function(m){ map.removeLayer(m); });
  coverageWaypointMarkers = [];
  if (coverageWaypointLine) { map.removeLayer(coverageWaypointLine); coverageWaypointLine = null; }
  
  if (!waypoints || waypoints.length === 0) return;
  
  var latlngs = [];
  waypoints.forEach(function(wp, i) {
    var icon = L.divIcon({
      className:"",
      iconSize:[16,16],
      iconAnchor:[8,8],
      html:\'<div style="width:16px;height:16px;border-radius:50%;border:2px solid #3b82f6;background:#1e3a8a;display:flex;align-items:center;justify-content:center;color:#93c5fd;font-size:7px;font-weight:bold;">\' + (i+1) + \'</div>\'
    });
    
    var marker = L.marker([wp.lat, wp.lon], {icon: icon})
      .bindTooltip("Coverage WP" + (i+1) + ": " + wp.alt + "m", {direction:"top"})
      .addTo(map);
    
    coverageWaypointMarkers.push(marker);
    latlngs.push([wp.lat, wp.lon]);
  });
  
  // Draw coverage path
  if (latlngs.length > 1) {
    coverageWaypointLine = L.polyline(latlngs, {
      color: "#3b82f6",
      weight: 2,
      opacity: 0.6,
      dashArray: "4, 4"
    }).addTo(map);
  }
}

function clearFieldCoverage() {
  boundaryMarkers.forEach(function(m){ map.removeLayer(m); });
  boundaryMarkers = [];
  if (boundaryLine) { map.removeLayer(boundaryLine); boundaryLine = null; }
  
  coverageWaypointMarkers.forEach(function(m){ map.removeLayer(m); });
  coverageWaypointMarkers = [];
  if (coverageWaypointLine) { map.removeLayer(coverageWaypointLine); coverageWaypointLine = null; }
}

map.on("click", function(e) {
  if (_pickMode) {
    window.location = "qrc://pick?lat=" + e.latlng.lat + "&lon=" + e.latlng.lng;
  } else if (_boundaryDrawMode) {
    window.location = "qrc://boundary-point?lat=" + e.latlng.lat + "&lon=" + e.latlng.lng;
  }
});

// Swarm algorithm visualization functions
function clearSwarmVisualization() {
  formationLines.forEach(function(line) { map.removeLayer(line); });
  formationLines = [];
  formationCircles.forEach(function(circle) { map.removeLayer(circle); });
  formationCircles = [];
  if (leaderMarker) { map.removeLayer(leaderMarker); leaderMarker = null; }
}

function _validLatLng(p) {
  // Accepts [lat, lon, ...] arrays AND {0:lat,1:lon,...} pseudo-arrays.
  if (p === null || p === undefined) return null;
  var lat = (p[0] !== undefined) ? p[0] : p.lat;
  var lon = (p[1] !== undefined) ? p[1] : p.lon;
  if (typeof lat !== "number" || typeof lon !== "number") return null;
  if (isNaN(lat) || isNaN(lon)) return null;
  if (lat === 0 && lon === 0) return null;
  return [lat, lon];
}

function updateFormation(leaderId, positions) {
  clearSwarmVisualization();

  if (!leaderId || !positions || positions.length === 0) return;

  // Find leader drone position
  var leaderPos = null;
  if (droneMarkers[leaderId] && droneMarkers[leaderId]._lastData) {
    var ld = droneMarkers[leaderId]._lastData;
    leaderPos = _validLatLng([ld.lat, ld.lon]);
  }

  if (!leaderPos) return;

  // Draw formation lines from leader to followers
  positions.forEach(function(pos, index) {
    if (index === 0) return; // Skip leader position

    var followerPos = _validLatLng(pos);
    if (!followerPos) return;

    // Draw line from leader to follower
    var line = L.polyline([leaderPos, followerPos], {
      color: "#f97316",
      weight: 2,
      opacity: 0.7,
      dashArray: "5, 5"
    }).addTo(map);
    formationLines.push(line);

    // Draw circle at follower position
    var circle = L.circle(followerPos, {
      radius: 15,
      color: "#f97316",
      fillColor: "#f97316",
      fillOpacity: 0.3,
      weight: 2
    }).addTo(map);
    formationCircles.push(circle);
  });

  // Highlight leader with special marker
  if (droneMarkers[leaderId]) {
    var leaderIcon = L.divIcon({
      className: "",
      iconSize: [30, 30],
      iconAnchor: [15, 15],
      html: \'<div style="width:30px;height:30px;border-radius:50%;border:3px solid #f97316;background:#f97316;display:flex;align-items:center;justify-content:center;color:white;font-size:12px;font-weight:bold;">👑</div>\'
    });
    leaderMarker = L.marker(leaderPos, { icon: leaderIcon, zIndexOffset: 2000 }).addTo(map);
  }
}

function updateBoidsVisualization(activeDrones) {
  clearSwarmVisualization();

  if (!activeDrones || activeDrones.length === 0) return;

  // Draw perception radius circles for active boids
  activeDrones.forEach(function(droneId) {
    if (droneMarkers[droneId] && droneMarkers[droneId]._lastData) {
      var d = droneMarkers[droneId]._lastData;
      var pos = [d.lat, d.lon];

      // Draw perception radius circle (50m default)
      var circle = L.circle(pos, {
        radius: 50,
        color: "#22c55e",
        fillColor: "#22c55e",
        fillOpacity: 0.1,
        weight: 1,
        dashArray: "3, 3"
      }).addTo(map);
      formationCircles.push(circle);
    }
  });
}

function updateConsensusVisualization(votingDrones) {
  clearSwarmVisualization();

  if (!votingDrones || votingDrones.length === 0) return;

  // Visualize voting drones with special indicators
  votingDrones.forEach(function(droneId) {
    if (droneMarkers[droneId] && droneMarkers[droneId]._lastData) {
      var d = droneMarkers[droneId]._lastData;
      var pos = [d.lat, d.lon];

      // Draw voting indicator
      var circle = L.circle(pos, {
        radius: 25,
        color: "#3b82f6",
        fillColor: "#3b82f6",
        fillOpacity: 0.2,
        weight: 2
      }).addTo(map);
      formationCircles.push(circle);
    }
  });
}

function updateBehaviorTreeVisualization(missionType, activeDrones) {
  clearSwarmVisualization();

  if (!activeDrones || activeDrones.length === 0) return;

  // Different visualization based on mission type
  var colors = {
    0: "#ef4444", // Surveillance - red
    1: "#f59e0b", // Search & Rescue - amber
    2: "#8b5cf6", // Formation Flight - purple
    3: "#06b6d4"  // Area Coverage - cyan
  };

  var color = colors[missionType] || "#64748b";

  activeDrones.forEach(function(droneId) {
    if (droneMarkers[droneId] && droneMarkers[droneId]._lastData) {
      var d = droneMarkers[droneId]._lastData;
      var pos = [d.lat, d.lon];

      // Draw mission area indicator
      var circle = L.circle(pos, {
        radius: 35,
        color: color,
        fillColor: color,
        fillOpacity: 0.15,
        weight: 2
      }).addTo(map);
      formationCircles.push(circle);
    }
  });
}

// ── Collision Prediction Visualization ──────────────────────────────────────
var collisionLines = [], collisionMarkers = [], collisionZones = [];

function clearCollisionVisualization() {
  collisionLines.forEach(function(line) { map.removeLayer(line); });
  collisionLines = [];
  collisionMarkers.forEach(function(marker) { map.removeLayer(marker); });
  collisionMarkers = [];
  collisionZones.forEach(function(zone) { map.removeLayer(zone); });
  collisionZones = [];
}

function updateCollisionPredictions(predictions) {
  clearCollisionVisualization();
  
  if (!predictions || predictions.length === 0) return;
  
  predictions.forEach(function(pred) {
    // Get drone positions
    var droneA = droneMarkers[pred.droneA];
    var droneB = droneMarkers[pred.droneB];
    
    if (!droneA || !droneB || !droneA._lastData || !droneB._lastData) return;
    
    var posA = [droneA._lastData.lat, droneA._lastData.lon];
    var posB = [droneB._lastData.lat, droneB._lastData.lon];
    
    // Determine color based on severity
    var colors = {
      "critical": "#ef4444",  // red
      "warning": "#f59e0b",   // amber
      "caution": "#eab308"    // yellow
    };
    var color = colors[pred.severity] || "#64748b";
    
    // Draw warning line between drones
    var line = L.polyline([posA, posB], {
      color: color,
      weight: 3,
      opacity: 0.8,
      dashArray: "10, 5"
    }).addTo(map);
    collisionLines.push(line);
    
    // Add tooltip to line
    var tooltipText = pred.droneA + " ↔ " + pred.droneB +
                     "<br>Collision in " + pred.timeToCollision + "s" +
                     "<br>Min distance: " + pred.minDistance + "m" +
                     "<br>Severity: " + pred.severity.toUpperCase();
    line.bindTooltip(tooltipText, {permanent: false, sticky: true});
    
    // Convert collision point from local NED to lat/lon
    // This requires the reference point from SafetyContext
    // For now, we will mark the midpoint between drones
    var midLat = (droneA._lastData.lat + droneB._lastData.lat) / 2;
    var midLon = (droneA._lastData.lon + droneB._lastData.lon) / 2;
    
    // Draw collision zone circle
    var radius = pred.minDistance * 2; // meters
    var zone = L.circle([midLat, midLon], {
      radius: radius,
      color: color,
      fillColor: color,
      fillOpacity: 0.15,
      weight: 2,
      dashArray: "5, 5"
    }).addTo(map);
    collisionZones.push(zone);
    
    // Draw collision point marker
    var icon = L.divIcon({
      className: "",
      iconSize: [32, 32],
      iconAnchor: [16, 16],
      html: \'<div style="width:32px;height:32px;border-radius:50%;border:3px solid \' + color + \';background:rgba(239,68,68,0.2);display:flex;align-items:center;justify-content:center;font-size:18px;">⚠</div>\'
    });
    
    var marker = L.marker([midLat, midLon], {
      icon: icon,
      zIndexOffset: 1500
    }).addTo(map);
    
    marker.bindTooltip(tooltipText, {permanent: false, direction: "top"});
    collisionMarkers.push(marker);
    
    // Pulse animation for critical collisions
    if (pred.severity === "critical") {
      var pulseCircle = L.circle([midLat, midLon], {
        radius: radius * 1.5,
        color: color,
        fillColor: "none",
        weight: 2,
        opacity: 0.6,
        dashArray: "3, 3"
      }).addTo(map);
      collisionZones.push(pulseCircle);
    }
  });
}
</script>
</body>
</html>
'
}

# DroneResearch GCS — UI Dokumentation

> Vollständige Funktionsbeschreibung aller UI-Komponenten und Panels.  
> Stand: Mai 2026 | Architektur: PyQt6 + QML + QtWebEngine

---

## Architektur-Überblick

```
┌─────────────────────────────────────────────────────────────────────┐
│  app.py  — Einstiegspunkt, registriert alle Context-Objekte         │
│                                                                     │
│  Python Context-Objekte (in QML als globale Variablen sichtbar):    │
│  • swarm       → SwarmContext     (Flottenmanagement + Telemetrie)   │
│  • telemetryModel → TelemetryModel (ListModel, eine Zeile/Drone)    │
│  • experiment  → ExperimentContext (Szenario-Runner)                 │
│  • safety      → SafetyContext    (APF + Geofence)                  │
│  • ros2        → ROS2Context      (PX4 uXRCE-DDS Bridge)            │
└─────────────────────────────────────────────────────────────────────┘

main.qml — Root Window
 ├── Header.qml           (52 px oben) — Verbindung, Uhr, Drone-Badges
 ├── InstrBar.qml         (110 px)     — Instrumententafel + Schnellbefehle
 ├── NavBar               (58 px links)— Icon-Seitenleiste
 ├── MapView.qml          (Mitte)      — Leaflet-Karte + HUD
 └── Panel-Drawer (rechts, animiert):
      ├── DashboardPanel.qml    — Live-Telemetrie + FSM
      ├── SwarmPanel.qml        — Flottensteuerung + Rollen
      ├── SafetyPanel.qml       — APF + Geofence
      ├── GimbalPanel.qml       — Gimbal-Steuerung (Observation UAV)
      ├── ROS2Panel.qml         — uXRCE-DDS Bridge
      ├── ExperimentPanel.qml   — Python-Script / JSON-Szenario
      ├── LogPanel.qml          — System-Log
      └── FlightLogPanel.qml    — CSV-Fluglog-Charts
```

---

## 1. Globales Layout (`main.qml`)

### Panel-System

Das UI kann **bis zu 3 Panels gleichzeitig** offen haben. Panels schieben von rechts herein (animiert, 220 ms Cubic-Ease).

| Funktion | Beschreibung |
|---|---|
| `togglePanel(panelId)` | Panel öffnen/schließen. Bei > 3 offenen Panels wird automatisch das älteste geschlossen (FIFO). |
| `isPanelOpen(panelId)` | Gibt `true` zurück wenn das Panel gerade sichtbar ist. |
| `selectDrone(did)` | Setzt die global ausgewählte Drone-ID — alle Panels binden sich daran. |
| `startMapPick(targetItem)` | Aktiviert den Karten-Klick-Modus; sobald der Nutzer einen Punkt auf der Karte klickt, wird `setWaypointFromMap(lat, lon)` am `targetItem` aufgerufen. |
| `deliverMapPick(lat, lon)` | Wird von `MapView` aufgerufen wenn ein Punkt gewählt wurde; leitet Koordinaten ans wartende Panel weiter. |

### NavItems — verfügbare Panels

| ID | Label | Farbe | Zweck |
|---|---|---|---|
| `dashboard` | Telemetry | Blau | Live-Telemetrie, FSM-State, GPS |
| `swarm` | Swarm | Grün | Flottenmanagement, Rollen, Mission |
| `safety` | Safety | Rot | APF-Konfiguration, Geofence, Verletzungen |
| `gimbal` | Gimbal | Lila | Gimbal-Steuerung für Observation UAV |
| `ros2` | ROS2 | Cyan | uXRCE-DDS Bridge, Offboard-Mode |
| `experiment` | Scenario | Orange | Python-Script / JSON-Szenario ausführen |
| `log` | Log | Grau | Echtzeit-Systemlog aller Drohnen |
| `flightlog` | FlightLog | Violett | CSV-Fluglog-Visualisierung |

### Globaler Log-Store

`globalLogModel` (ListModel) speichert alle Log-Einträge persistent, auch wenn Panels geschlossen sind. Max. 3000 Einträge (älteste werden verworfen).

Felder pro Eintrag: `{ time, level, text }` — level: `INFO | WARN | ERROR`

---

## 2. Header (`components/Header.qml`)

**Höhe:** 52 px — immer sichtbar oben.

### Verbindungs-Widgets

| Element | Funktion |
|---|---|
| Verbindungstyp-Tabs | Umschalten zwischen **Serial**, **UDP**, **TCP** |
| Serial-Modus | Auswahl COM-Port (automatisch erkannt via `swarm.availableSerialPorts()`) + Baud-Rate (9600 / 57600 / 115200 / 921600) |
| UDP/TCP-Modus | IP-Adresse + Port-Eingabe |
| `buildConnStr()` | Baut aus den Eingaben den Connection-String (z.B. `tcp:127.0.0.1:5760` oder `COM3:57600`) |
| `doConnect()` | Prüft auf Duplikate, generiert automatische Drone-ID (`drone1`, `drone2`, …), ruft `swarm.addDrone()` |
| Refresh-Button | Aktualisiert die Serial-Port-Liste |

### Drone-Badges

Für jede verbundene Drohne erscheint ein klickbares Badge:
- **Grün** = verbunden, **Rot** = offline
- Klick auf Badge → setzt `selectedDroneId` global → alle Panels wechseln zu dieser Drohne
- Badges reagieren auf `swarm.droneAdded`, `swarm.droneRemoved`, `swarm.connectedChanged`

### Statuszeile (rechts)

- **Uhr** — live UTC-Uhrzeit (1-Sekunden-Timer)
- **Drone-Zähler** — Anzahl verbundener / Gesamt-Drohnen
- **Duplikat-Flash** — rote Warnung wenn gleicher Connection-String zweimal verbunden wird

---

## 3. Instrumententafel (`components/InstrBar.qml`)

**Höhe:** 110 px — direkt unterhalb des Headers.

### Instrument-Tiles (von links nach rechts)

#### ARMED / MODE Tile (88 px)
- Pulsierender grüner Punkt wenn `armed = true`
- Zeigt Flight-Mode-String (z.B. `GUIDED`, `AUTO`, `LOITER`)
- Hintergrundfarbe wechselt grün wenn armed

#### ARTIFICIAL HORIZON (Canvas, 90 px)
- Echter Horizont — rollt und neigt sich mit `roll` / `pitch` Telemetrie-Werten
- Braun/blau-geteilter Horizont, weiße Mittelmarkierung
- Aktualisiert bei 10 Hz

#### KOMPASS-ROSE (Canvas, 90 px)
- Dreht sich mit `yaw`-Telemetrie
- Zeigt N/S/E/W Beschriftungen + Gradeinteilung
- Numerischer Heading-Wert darunter

#### HÖHE / GESCHWINDIGKEIT Tile (82 px)
- `ALT` = relative Höhe in Metern (1 Dezimalstelle)
- `SPD` = Groundspeed in m/s
- `CLB` = Climb-Rate (grün wenn steigend, rot wenn sinkend)

#### BATTERIE Tile (72 px)
- Prozentzahl + Volt-Wert
- Farbe: Grün (>50%) → Orange (20–50%) → Rot (<20%)
- GPS-Fix-Status + Satelliten-Anzahl darunter

#### QUICK COMMANDS (3×2 Grid)
Schnellzugriff auf die 6 häufigsten Befehle für die aktuell ausgewählte Drohne:

| Button | Signal | Beschreibung |
|---|---|---|
| **ARM** ▶ | `swarm.armDrone(did)` | MAVLink ARM-Befehl |
| **DISARM** ■ | `swarm.disarmDrone(did)` | MAVLink DISARM |
| **TAKEOFF** ↑ | `swarm.takeoffDrone(did, alt)` | Takeoff auf eingestellte Höhe |
| **LAND** ↓ | `swarm.landDrone(did)` | Landung einleiten |
| **RTL** ⌂ | `swarm.rtlDrone(did)` | Return to Launch |
| **HOLD** ⊙ | Modus `LOITER` / `HOLD` setzen |

#### ALTITUDE CONTROL
- **Takeoff-Alt Spinner** — Höhe in Metern (1–120 m), die für TAKEOFF-Befehl verwendet wird
- **Change Alt Button** — ändert die Zielhöhe einer fliegenden Drohne via `swarm.changeAltitude(did, alt)`

#### APF QUICK TOGGLE
- Zeigt APF-Status (aktiv/inaktiv) + Verletzungszähler
- Toggle-Button: APF aktivieren (`safety.configureAPF()`) oder deaktivieren (`safety.disableAPF()`)

---

## 4. Karte (`MapView.qml`)

Leaflet.js-basierte Karte eingebettet via `QtWebEngineView`.

### Kartenfunktionen

| Funktion | Beschreibung |
|---|---|
| `setMapType(typeName)` | Kartenstil wechseln: `dark`, `satellite`, `osm`, `topo` |
| `setPickMode(enabled)` | Karten-Klick-Modus — Klick auf Karte liefert GPS-Koordinaten zurück |
| `mapPickSelected(lat, lon)` | Signal: Koordinaten nach Klick auf Karte |

### Drone-Marker
- Für jede verbundene Drohne ein animierter Marker mit Heading-Pfeil
- Klick auf Marker → selektiert diese Drohne

### HUD-Overlay
- Attitude-Anzeige (Roll/Pitch/Yaw) als Canvas direkt über der Karte
- Wird mit derselben `snap(key, def)` Funktion befüllt wie InstrBar

---

## 5. Dashboard Panel (`panels/DashboardPanel.qml`)

Live-Telemetrie-Übersicht für eine einzelne Drohne.

### Drone-Auswahl
- ComboBox oben — synchronisiert mit globalem `selectedDroneId`
- Wird automatisch aktualisiert wenn Drohnen hinzukommen/entfernt werden

### FSM-State Badge (neu)
Farbiger Badge zeigt den aktuellen FSM-Zustand der Drohne:

| State | Farbe | Animation |
|---|---|---|
| `IDLE` | Grau | — |
| `ARMING` | Orange | Blinkt |
| `ARMED` | Gelb | — |
| `TAKEOFF` | Blau | Blinkt |
| `FLYING` | Grün | — |
| `MISSION` | Cyan | — |
| `RTL` | Orange | Blinkt |
| `LANDING` | Lila | Blinkt |
| `EMERGENCY` | Rot | — |
| `ERROR` | Dunkelrot | — |
| `DISCONNECTED` | Dunkelgrau | — |

### Drone-Typ Badge
- `⚙ Generic` (Blau) — GenericUAVModel mit FSM + Swarm
- `📷 Observation` (Lila) — ObservationUAVModel mit Gimbal + Kamera

### Swarm-Rollen Badge
Erscheint nur wenn Rolle nicht `none`:
- `★ Leader` (Grün) — führt Formation
- `→ Follower` (Blau) — folgt Leader
- `⊕ Coord.` (Gelb) — verwaltet Schwarm

### FSM-Transition History
- Scrollbare Liste der letzten 30 FSM-Zustandswechsel
- Format: `HH:MM:SS  ALTZUSTAND → NEUZUSTAND`
- Aktualisiert jede Sekunde via Timer
- Neueste Einträge unten (ListView.BottomToTop)

### KPI-Kacheln (2-spaltiges Grid)

| KPI | Einheit | Beschreibung |
|---|---|---|
| ALTITUDE | m | Relative Höhe über Home |
| SPEED | m/s | Groundspeed |
| HEADING | ° | Magnetischer Kurs (Yaw) |
| CLIMB | m/s | Steig-/Sinkrate |
| SATELLITES | sat | GPS-Satelliten |
| THROTTLE | % | Motorleistung |

### Batterie-Balken
- Prozentzahl + Volt-Wert
- Progressbar mit Farbverlauf: Grün → Orange → Rot

### GPS-Strip
- Fix-Typ: No Fix / 2D / 3D / 3D+DGPS
- Latitude/Longitude (6 Dezimalstellen)

---

## 6. Swarm Panel (`panels/SwarmPanel.qml`)

Flottenmanagement — Drohnen hinzufügen, Waypoints, Rollen, Mission.

### ADD DRONE

| Feld | Beschreibung |
|---|---|
| Drone ID | Frei wählbarer Bezeichner (z.B. `D1`, `Alpha`) |
| Connection String | MAVLink-Verbindung: `tcp:IP:PORT`, `udp:IP:PORT`, `COM3:57600` |
| **Drone-Typ Auswahl** | **Generic UAV** (FSM + Swarm + Mission) oder **Observation UAV** (Gimbal + Kamera + ROS2) |
| ＋ Add & Connect | Ruft `swarm.addDroneTyped(id, conn, type)` — verbindet im Hintergrund-Thread |

### WAYPOINT / GOTO

| Feld/Button | Beschreibung |
|---|---|
| Latitude / Longitude | GPS-Zielkoordinaten manuell eingeben |
| Altitude (m) | Zielhöhe |
| Distance Preview | Haversine-Berechnung der Entfernung vom Drone zum Zielpunkt in Echtzeit |
| 🎯 GOTO | `swarm.gotoDrone(did, lat, lon, alt)` — Drohne fliegt direkt zum Punkt |
| ➕ Add WP | Koordinaten zur Mission-Waypoint-Liste hinzufügen |
| 🗑 Clear | Alle Waypoints löschen |
| 🗺 From Map | Kartenklick-Modus — Koordinaten durch Klick auf Karte setzen |

### MISSION WAYPOINTS
- Scrollbare Liste aller hinzugefügten Waypoints
- **↑ / ↓** — Reihenfolge ändern
- **×** — Einzelnen Waypoint entfernen
- **▶ Start Mission** — Sendet Waypoint-Liste als JSON an `swarm.runMission(did, json)`
- **💾 Speichern** — Waypoints als JSON-Datei exportieren

### SWARM ROLLE & FORMATION (neu)

| Element | Beschreibung |
|---|---|
| Drone-Auswahl | ComboBox wählt welche Drohne die Rolle bekommt |
| **None** | Standalone-Betrieb, kein Schwarm |
| **Leader** | Führt Formation — andere Drohnen orientieren sich an ihrer Position |
| **Follower** | Folgt dem Leader; Leader-ID muss angegeben werden |
| **Coordinator** | Verwaltet den gesamten Schwarm (Strategie/Koordination) |
| Leader ID | Sichtbar nur bei `Follower` — ID der Leitdrohne (z.B. `D1`) |
| Formation Offset | N/E/Alt in Metern — relativer Versatz vom Leader in NED-Koordinaten |
| ✓ Rolle & Offset setzen | Ruft `swarm.setDroneRole()` + `swarm.setFormationOffset()` |

**Funktionsweise Formation:** Die Formation-Offsets werden direkt an `GenericUAVModel.set_formation_offset(north, east, alt)` weitergegeben. Die Drohne berechnet ihre Zielposition als `LeaderPosition + Offset` in NED.

### ACTIVE DRONES
- Listet alle registrierten Drohnen mit Status
- **⏏ Disc.** / **⟳ Reconn.** — Disconnect/Reconnect-Toggle
- **✕** — Drohne aus Flotte entfernen

---

## 7. Safety Panel (`panels/SafetyPanel.qml`)

Sicherheits-System mit Artificial Potential Fields (APF) und Geofence.

### APF Status-Header
- `🛡 APF ACTIVE` (grün) oder `⚠ APF INACTIVE` (orange)
- Verletzungszähler (`N violations`)

### APF Konfiguration

| Parameter | Default | Beschreibung |
|---|---|---|
| `minSeparation` | 3.0 m | Minimaler Sicherheitsabstand zwischen Drohnen |
| `maxSpeed` | 5.0 m/s | Maximale erlaubte Fluggeschwindigkeit |
| `repulsionGain` | 3.0 | Stärke der Abstoßungskraft bei Annäherung |
| `attractionGain` | 1.0 | Stärke der Anziehungskraft zum Ziel |
| `geofenceRadius` | 50.0 m | Radius des erlaubten Flugbereichs |
| `geofenceAltMin` | 1.0 m | Minimale Flughöhe |
| `geofenceAltMax` | 30.0 m | Maximale Flughöhe |
| `obstacleRadius` | 4.0 m | Abstoßungsradius um statische Hindernisse |

**Apply** → `safety.configureAPF(params)` — Parameter werden sofort aktiv

### APF Enable/Disable
- `safety.configureAPF(params)` → aktiviert
- `safety.disableAPF()` → deaktiviert

### Violations-Log
- Scrollbare Liste der letzten APF-Verstöße (Geofence-Breaches, Kollisionswarnungen)
- Level: `WARN` für Näherungswarnung, `ERROR` für Geofence-Breach

---

## 8. Gimbal Panel (`panels/GimbalPanel.qml`)

Steuerung der Kameragimbal für **Observation UAV** (`drone_type = "observation"`).

> **Hinweis:** Alle Gimbal-Slider und Buttons sind deaktiviert (Opacity 0.4) wenn die ausgewählte Drohne kein Observation UAV ist.

### Drone-Auswahl
- ComboBox zeigt alle Drohnen
- Wechsel zeigt Warnung wenn nicht Observation-Typ

### Slider

| Achse | Bereich | Farbe | Beschreibung |
|---|---|---|---|
| **PITCH** | -90° … 0° | Blau | Neigung (0° = gerade aus, -90° = senkrecht nach unten) |
| **ROLL** | -45° … +45° | Lila | Seitenneigung der Kamera |
| **YAW** | -180° … +180° | Cyan | Horizontale Drehung (relativ zum Drone-Heading) |

### Buttons

| Button | Funktion |
|---|---|
| 📷 APPLY GIMBAL | `swarm.gimbalPoint(did, pitch, roll, yaw)` — sendet MAVLink CMD_DO_MOUNT_CONTROL (ID 205) |
| ⌂ HOME | Alle Slider auf 0° zurücksetzen + `swarm.gimbalHome(did)` |

### Quick Presets

| Preset | Pitch | Roll | Yaw | Verwendung |
|---|---|---|---|---|
| Down | -90° | 0° | 0° | Senkrechte Aufnahme (Mapping) |
| Forward | 0° | 0° | 0° | Vorwärtskamera |
| 45° | -45° | 0° | 0° | Schräge Aufnahme |

### Aktueller Status
- Zeigt live die vom Drone gemeldete Gimbal-Position (P/R/Y)
- Aktualisiert alle 500 ms via `swarm.gimbalState(did)`

---

## 9. ROS2 Panel (`panels/ROS2Panel.qml`)

Native PX4-Integration über **uXRCE-DDS** (kein MAVLink).

> **Voraussetzung:** ROS2 Humble+ mit `px4_msgs` installiert + `MicroXRCEAgent` laufend.

### ROS2 Node Status (Statusleiste)

| Status | Farbe | Bedeutung |
|---|---|---|
| `ROS2 + px4_msgs ✓` | Grün (pulsiert) | Vollständig einsatzbereit |
| `ROS2 OK — px4_msgs missing` | Orange | rclpy installiert, aber px4_msgs fehlen |
| `rclpy not installed` | Rot | ROS2 nicht installiert |

Bei nicht-OK-Status erscheint ein Anleitungskasten mit Install-Befehlen.

### Bridge Konfiguration

| Feld | Beschreibung |
|---|---|
| Drone ID | ComboBox wählt für welche Drohne die Bridge gilt |
| Namespace | uXRCE-DDS Namespace (leer = `/fmu/*`, z.B. `uav_1` → `/uav_1/fmu/*`) |
| Topics-Vorschau | Zeigt die erwarteten Topic-Pfade an |

### Bridge Toggle

**▶ Bridge starten** → `ros2.startBridge(droneId, namespace)`
- Erstellt `PX4ROS2Bridge`-Instanz
- Subscribt auf alle PX4 uORB Out-Topics
- Startet `rclpy.spin()` in eigenem Thread
- **Hinweis:** MAVLink und ROS2 Bridge sollten nicht gleichzeitig verwendet werden (konkurrierende Ressourcen)

**■ Bridge stoppen** → `ros2.stopBridge(droneId)`
- Beendet ROS2-Node, gibt Ressourcen frei
- MAVLink kann danach wieder verwendet werden

### uORB Topics Viewer
Zeigt alle abonnierten (← PX4) und publizierten (→ PX4) Topics:

| Topic | Richtung | Inhalt |
|---|---|---|
| `.../vehicle_global_position` | ← | GPS lat/lon/alt |
| `.../vehicle_local_position` | ← | NED-Position + Geschwindigkeit |
| `.../vehicle_attitude` | ← | Quaternion → Roll/Pitch/Yaw (konvertiert FRD→FLU) |
| `.../vehicle_status` | ← | Arm-State, Nav-State (Flight-Mode) |
| `.../battery_status` | ← | Batterie % + Volt |
| `.../vehicle_gps_position` | ← | GPS-Fix-Typ + Satelliten |
| `.../vehicle_command` | → | VehicleCommand-Nachrichten |
| `.../offboard_control_mode` | → | Offboard-Mode-Keepalive |
| `.../trajectory_setpoint` | → | Position/Velocity Setpoints |

### Live uORB Snapshot
- Zeigt alle aktuellen Telemetrie-Werte der Bridge in Echtzeit (5 Hz)
- Felder: Armed, Nav State, Lat/Lon, Alt, Roll/Pitch/Yaw, Battery, GPS

### Offboard Mode — TrajectorySetpoint

#### Modus-Tabs
- **Position** — Absolute NED-Koordinaten
- **Velocity** — Geschwindigkeitsvektoren

#### Position-Modus Felder
| Feld | Einheit | Beschreibung |
|---|---|---|
| North | m | NED-Nord-Position relativ zum Home |
| East | m | NED-Ost-Position |
| Down | m | NED-Down (negativ = höher als Home, z.B. `-5.0` = 5m Höhe) |
| Yaw | rad | Ziel-Heading in Bogenmass |

#### Velocity-Modus Felder
| Feld | Einheit | Beschreibung |
|---|---|---|
| vN | m/s | Geschwindigkeit Nord |
| vE | m/s | Geschwindigkeit Ost |
| vD | m/s | Geschwindigkeit Down (positiv = sinken) |
| YawRate | rad/s | Drehrate um Vertikalachse |

#### Offboard-Buttons

| Button | Funktion |
|---|---|
| ⚡ OFFBOARD | `ros2.activateOffboardMode(did)` — schaltet PX4 in Offboard-Mode |
| ▶ SEND | Sendet Setpoint (Position oder Velocity) |
| ■ STOP | `ros2.stopOffboard(did)` — hört auf Setpoints zu senden |

> **Wichtig:** PX4 verlässt Offboard-Mode automatisch wenn keine Setpoints mehr kommen. STOP ist daher ein sanfter Übergang (PX4 fällt in Loiter zurück).

### Vehicle Commands via uXRCE-DDS

| Button | Funktion |
|---|---|
| ARM | `ros2.armBridge(did)` |
| DISARM | `ros2.disarmBridge(did)` |
| LAND | `ros2.landBridge(did)` |
| RTL | `ros2.rtlBridge(did)` |
| TAKEOFF + Höhe | `ros2.takeoffBridge(did, alt)` |

---

## 10. Experiment Panel (`panels/ExperimentPanel.qml`)

Ausführung von Flugszenarien — Python-Script oder JSON.

### Modus-Tabs
- **🐍 Python Script** — freier Python-Code der Zugriff auf das `swarm`-Objekt hat
- **📋 JSON Scenario** — strukturiertes Szenario-Format

### Python Script Modus

| Element | Funktion |
|---|---|
| Script-Name-Feld | Anzeigename des Scripts |
| 📂 Laden | Öffnet FileDialog → lädt `.py`-Datei in Editor |
| Inline-Editor | Mehrzeiliger Text-Editor direkt im Panel |
| ▶ Run | `experiment.runScript(name, code)` — führt Python im Hintergrund aus |
| ■ Stop | `experiment.stopScript()` |
| 💾 Speichern | Speichert Editor-Inhalt als `.py`-Datei |

**Verfügbare Variablen im Script-Scope:** `swarm`, `safety`, `time`, `math`

### JSON Scenario Modus

Strukturiertes Szenario mit Sequenz von Befehlen:

```json
{
  "name": "Mein Szenario",
  "drones": ["D1", "D2"],
  "steps": [
    { "cmd": "arm",     "drones": ["D1", "D2"] },
    { "cmd": "takeoff", "altitude": 10 },
    { "cmd": "wait",    "seconds": 5 },
    { "cmd": "goto",    "lat": 52.5, "lon": 13.4, "alt": 15 },
    { "cmd": "rtl" }
  ]
}
```

Unterstützte Befehle: `arm`, `disarm`, `takeoff`, `land`, `rtl`, `goto`, `wait`, `set_mode`

---

## 11. Log Panel (`panels/LogPanel.qml`)

Echtzeit-Systemlog für alle Drohnen und Systemereignisse.

### Header-Statistiken
- Gesamtanzahl Log-Einträge
- Anzahl nach Level (INFO / WARN / ERROR)
- **🗑 Clear** — Log leeren

### Filter
- **ALL / INFO / WARN / ERROR** — Tabs filtern nach Log-Level
- **Suchfeld** — Freitextsuche in Log-Nachrichten (Groß-/Kleinschreibung-unabhängig)

### Log-Einträge
- Format: `HH:MM:SS  [LEVEL]  [DRONE_ID] Nachricht`
- Drone-ID wird farbig hervorgehoben (Hash-basierte Farbzuweisung)
- Automatisches Scrollen zum neuesten Eintrag
- `[SWARM]` Einträge in Lila
- `[FSM]` Einträge kennzeichnen FSM-Zustandswechsel

### Log speichern
- 💾 Speichern-Button → `FileDialog` → `swarm.writeFile(path, content)`
- Format: eine Zeile pro Eintrag: `HH:MM:SS  [LEVEL]  Text`

---

## 12. Flight Log Panel (`panels/FlightLogPanel.qml`)

Nachträgliche Visualisierung von aufgezeichneten Flügen aus CSV-Dateien.

### CSV laden
- 📂 Öffnen → FileDialog wählt `.csv`-Datei
- Erwartet Spalten: `timestamp, alt_rel, groundspeed, battery_pct, vz`
- Timestamps werden relativ zu `t0` (ersten Wert) normalisiert

### Charts (Canvas-basiert)

| Chart | Y-Achse | Farbe |
|---|---|---|
| Höhenprofil | Relative Höhe (m) | Blau |
| Geschwindigkeit | Groundspeed (m/s) | Grün |
| Batterie | Ladezustand (%) | Orange |
| Vertikalgeschwindigkeit | vz (m/s) | Lila |

**Interaktion:**
- Hover über Chart → zeigt Crosshair-Linie und Wert an der Cursor-Position
- Hover synchronisiert sich über alle 4 Charts gleichzeitig (gleicher Zeitindex)

### Statistiken
- Flugdauer, Max-Höhe, Max-Geschwindigkeit, Min-Batterie
- Erscheinen sobald CSV geladen wurde

---

## 13. Python Context-Objekte (Backend)

### SwarmContext (`swarm`)

| Slot / Methode | Signatur | Beschreibung |
|---|---|---|
| `addDrone` | `(id, conn)` | Drone hinzufügen (Generic-Typ) |
| `addDroneTyped` | `(id, conn, type)` | Drone mit Typ hinzufügen: `"generic"` oder `"observation"` |
| `removeDrone` | `(id)` | Drone aus Flotte entfernen |
| `disconnectDrone` | `(id)` | MAVLink trennen (Drone bleibt in Liste) |
| `reconnectDrone` | `(id)` | Erneut verbinden |
| `armDrone` | `(id)` | ARM-Befehl |
| `disarmDrone` | `(id)` | DISARM |
| `takeoffDrone` | `(id, alt)` | Takeoff auf `alt` Meter |
| `landDrone` | `(id)` | Landen |
| `rtlDrone` | `(id)` | Return to Launch |
| `gotoDrone` | `(id, lat, lon, alt)` | Zu GPS-Position fliegen |
| `changeAltitude` | `(id, alt)` | Höhe im Flug ändern |
| `armAll` / `disarmAll` | `()` | Alle Drohnen armen/disarmen |
| `takeoffAll` / `landAll` / `rtlAll` | `(alt)` | Swarm-Befehle |
| `emergencyStop` | `()` | Force-DISARM alle Drohnen |
| `droneFsmState` | `(id) → str` | FSM-Zustand: `IDLE\|ARMING\|ARMED\|...` |
| `droneFsmHistory` | `(id) → list` | Letzte 30 FSM-Übergänge |
| `droneType` | `(id) → str` | `"generic"` oder `"observation"` |
| `droneRole` | `(id) → str` | `"none"\|"leader"\|"follower"\|"coordinator"` |
| `setDroneRole` | `(id, role, leaderId)` | Swarm-Rolle setzen |
| `setFormationOffset` | `(id, N, E, alt)` | Formation-Offset in Metern (NED) |
| `gimbalPoint` | `(id, pitch, roll, yaw)` | Gimbal ausrichten |
| `gimbalHome` | `(id)` | Gimbal zurücksetzen |
| `gimbalState` | `(id) → dict` | Aktuelle Gimbal-Position |
| `droneSnapshot` | `(id) → dict` | Kompletter Telemetrie-Snapshot |
| `droneIds` | `() → list` | Alle registrierten Drone-IDs |
| `availableSerialPorts` | `() → list` | Erkannte COM-Ports |
| `isDroneConnected` | `(id) → bool` | Verbindungsstatus |
| `readFile` | `(path) → str` | Dateiinhalt lesen |
| `writeFile` | `(path, content) → bool` | Datei schreiben |

**Signale:**
- `droneAdded(droneId)` — neue Drohne registriert
- `droneRemoved(droneId)` — Drohne entfernt
- `telemetryUpdated(snapshot)` — Telemetrie-Dict für alle Drohnen (5 Hz)
- `connectedChanged(droneId, connected)` — Verbindungsstatus geändert
- `fsmStateChanged(droneId, fsmState)` — FSM-Zustand gewechselt
- `logMessage(level, text)` — Log-Eintrag

### ROS2Context (`ros2`)

| Slot | Signatur | Beschreibung |
|---|---|---|
| `nodeStatus` | `() → str` | `"ok"\|"no_ros2"\|"no_px4_msgs"` |
| `isBridgeActive` | `(id) → bool` | Bridge-Status |
| `activeBridges` | `() → list` | Alle aktiven Bridge-IDs |
| `startBridge` | `(id, namespace)` | Bridge starten |
| `stopBridge` | `(id)` | Bridge stoppen |
| `activateOffboardMode` | `(id)` | PX4 in Offboard-Mode schalten |
| `setOffboardPosition` | `(id, N, E, D, yaw)` | NED Position-Setpoint |
| `setOffboardVelocity` | `(id, vN, vE, vD, yawRate)` | NED Velocity-Setpoint |
| `stopOffboard` | `(id)` | Setpoints stoppen |
| `armBridge` | `(id)` | ARM via VehicleCommand |
| `disarmBridge` | `(id)` | DISARM via VehicleCommand |
| `takeoffBridge` | `(id, alt)` | Takeoff via VehicleCommand |
| `landBridge` | `(id)` | Land |
| `rtlBridge` | `(id)` | RTL |
| `bridgeSnapshot` | `(id) → dict` | Aktueller uORB Telemetrie-Snapshot |
| `getBridgeTopics` | `(id) → list` | Liste der Topic-Pfade |

**Signale:**
- `bridgeStatusChanged(droneId, active)` — Bridge gestartet/gestoppt
- `telemetryReceived(droneId, snapshot)` — uORB Telemetrie-Update
- `ros2LogMessage(level, text)` — Bridge-Log-Eintrag
- `nodeStatusChanged(status)` — ROS2-Node Status geändert

### SafetyContext (`safety`)

| Slot | Beschreibung |
|---|---|
| `configureAPF(params)` | APF mit Parametern aktivieren |
| `disableAPF()` | APF deaktivieren |
| `updateDronePositions(snapshot)` | Positions-Update aus Telemetrie (intern) |

**Properties:**
- `apfActive: bool` — APF aktiv?
- `violationCount: int` — Anzahl Verstöße

**Signale:**
- `geofenceBreached(droneId, reason)` — Geofence-Verletzung
- `apfLogMessage(text)` — APF-Ereignis
- `logMessage(level, text)` — Allgemeines Log

### TelemetryModel (`telemetryModel`)

ListModel mit einer Zeile pro Drohne. Jede Zeile hat:

```
droneId, connected, armed, flightMode, altRel, groundspeed,
lat, lon, yaw, batteryPct, fsmState, droneType, swarmRole
```

---

## 14. FSM-Zustände und erlaubte Übergänge

```
IDLE ──────────────────────────────────────────────────────────────────
  │
  ├─[arm()]──→ ARMING ──[ok]──→ ARMED ──[takeoff()]──→ TAKEOFF ──→ FLYING
  │                │                         │
  │              [fail]                   [fail]
  │                │                         │
  │             IDLE                     EMERGENCY
  │
FLYING ────────────────────────────────────────────────────────────────
  │
  ├─[mission()]──→ MISSION ──[done/abort]──→ FLYING
  ├─[rtl()]──────→ RTL ──[landed]──→ IDLE
  ├─[land()]─────→ LANDING ──[landed]──→ IDLE
  └─[emergency()]─→ EMERGENCY

Any State ──[emergency()]──→ EMERGENCY
```

Alle Zustandswechsel erzeugen:
1. `fsm_state_changed(droneId, newState)` Signal (Python → QML)
2. Log-Eintrag in globalem Log mit Level INFO/WARN/ERROR
3. Dashboard-Badge-Update (live, keine manuelle Aktualisierung nötig)

---

## 15. Datenfluss-Übersicht

```
PX4/ArduPilot  ←──MAVLink──→  DroneBackend  ──→  SwarmBackend  ──→  SwarmContext
                                    │                                      │
                               GenericUAVModel                        pyqtSignal
                               ObservationUAVModel                   telemetryUpdated
                               FSM.on_transition                     fsmStateChanged
                                    │                                      │
                              PX4ROS2Bridge ←──uXRCE-DDS──→ PX4     ROS2Context
                                    │                                      │
                               rclpy.spin()                          pyqtSignal
                               TrajectorySetpoint                    telemetryReceived
                               VehicleCommand                        bridgeStatusChanged
                                                                           │
                                                                      QML / main.qml
                                                                      ┌────────────────┐
                                                                      │ globalLogModel  │
                                                                      │ selectedDroneId │
                                                                      │ openPanels      │
                                                                      └────────────────┘
```

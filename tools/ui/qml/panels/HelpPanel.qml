import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components" as Cmp

// ─────────────────────────────────────────────────────────────────────────────
// HelpPanel — Vollständige Feature-Referenz der RZ Drone Solutions GCS
//
// Aufbau:
//   1. Quickstart (5-Schritt-Workflow)
//   2. Globale Konzepte (Selected vs. Mission-Target, FSM, APF, …)
//   3. Pro Tab: was es macht, wie man es benutzt, worauf man achten muss
//   4. Konventionen, Gotchas, Shortcuts
//
// Reine Dokumentation. Keine Bindings auf swarm/experiment/safety.
// ─────────────────────────────────────────────────────────────────────────────
Item {
    id: root
    anchors.fill: parent

    // ── Inline section component ─────────────────────────────────────────────
    component HelpSection: Rectangle {
        property string title: ""
        property string subtitle: ""
        property color  accent: "#fbbf24"
        property string body: ""
        width: parent ? parent.width : 600
        radius: 10
        color: "#0d1117"
        border.color: "#1e293b"; border.width: 1
        height: secCol.implicitHeight + 24

        Rectangle {
            width: 4; height: parent.height - 16
            anchors { left: parent.left; leftMargin: 6; verticalCenter: parent.verticalCenter }
            radius: 2; color: parent.accent
        }

        Column {
            id: secCol
            anchors {
                left: parent.left; leftMargin: 20
                right: parent.right; rightMargin: 14
                top: parent.top; topMargin: 12
            }
            spacing: 6

            Text {
                text: parent.parent.title
                color: parent.parent.accent
                font.pixelSize: 14; font.weight: Font.Bold; font.letterSpacing: 0.5
            }
            Text {
                visible: parent.parent.subtitle.length > 0
                text: parent.parent.subtitle
                color: "#64748b"; font.pixelSize: 10; font.italic: true
                wrapMode: Text.WordWrap
                width: parent.width
            }
            Text {
                text: parent.parent.body
                color: "#cbd5e1"; font.pixelSize: 11
                wrapMode: Text.WordWrap
                width: parent.width
                lineHeight: 1.4
                textFormat: Text.RichText
            }
        }
    }

    // ── Two-column glossary row component ────────────────────────────────────
    component GlossaryRow: Row {
        property string term: ""
        property string def: ""
        spacing: 10
        width: parent ? parent.width : 0
        Text {
            text: parent.term
            color: "#93c5fd"; font.pixelSize: 11; font.weight: Font.Bold
            font.family: "Consolas"
            width: 170
            wrapMode: Text.WordWrap
        }
        Text {
            text: parent.def
            color: "#cbd5e1"; font.pixelSize: 11
            width: parent.width - 180
            wrapMode: Text.WordWrap
            textFormat: Text.RichText
        }
    }

    ScrollView {
        anchors { fill: parent; margins: 14 }
        clip: true
        contentWidth: availableWidth
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        Column {
            width: parent.availableWidth
            spacing: 14

            // ── Header ──────────────────────────────────────────────────────
            Rectangle {
                width: parent.width; height: 88
                radius: 10
                color: "#161b27"
                border.color: "#fbbf24"; border.width: 1
                Column {
                    anchors { left: parent.left; leftMargin: 18; verticalCenter: parent.verticalCenter }
                    spacing: 4
                    Text {
                        text: "RZ Drone Solutions · Ground Control Station"
                        color: "#fbbf24"; font.pixelSize: 18; font.weight: Font.Bold
                    }
                    Text {
                        text: "Vollständige Feature-Referenz · Workflows · Konventionen"
                        color: "#94a3b8"; font.pixelSize: 11
                    }
                    Text {
                        text: "Lies mindestens Quickstart + Globale Konzepte, bevor du eine Drohne armst."
                        color: "#64748b"; font.pixelSize: 10; font.italic: true
                    }
                }
            }

            // ── 1. Quickstart ───────────────────────────────────────────────
            HelpSection {
                title: "1 · QUICKSTART (5 Schritte zur ersten Mission)"
                subtitle: "Annahme: SITL läuft bereits (z. B. ArduCopter auf tcp:127.0.0.1:5762)"
                accent: "#22c55e"
                body:
                    "<b>① Drohne hinzufügen</b><br>" +
                    "&nbsp;&nbsp;Swarm-Tab → <b>+ DROHNE</b> → ID (z. B. <code>UAV_1</code>) + Connection-String (<code>tcp:127.0.0.1:5762</code>) → <b>Verbinden</b>. " +
                    "Status-Badge wechselt zu <span style='color:#22c55e'>grün</span>, FSM springt von <code>DISCONNECTED</code> auf <code>IDLE</code>.<br><br>" +
                    "<b>② Wegpunkte setzen</b><br>" +
                    "&nbsp;&nbsp;Map-Tab → <b>WAYPOINT HINZUFÜGEN</b> aktivieren → linke Maustaste auf der Karte. " +
                    "Höhe (AGL) oben rechts einstellen. ESC bricht den Modus ab. " +
                    "Alternativ: Swarm-Tab → Lat/Lon/Alt eintippen → <b>Add WP</b>.<br><br>" +
                    "<b>③ Mission-Targets auswählen</b><br>" +
                    "&nbsp;&nbsp;Swarm-Tab → Häkchen ☑ links neben jeder Drohne, die mitfliegen soll. " +
                    "Keine Häkchen → die aktuell <i>selected</i> Drohne ist Target. Mehrere Häkchen → Multi-Drone-Dispatch.<br><br>" +
                    "<b>④ Sicherheits-Check</b><br>" +
                    "&nbsp;&nbsp;Safety-Tab öffnen → <b>APF ENABLE</b> (Kollisionsschutz an). " +
                    "Geofence-Radius prüfen (Default 50 m ist für Multi-Drohne meist zu klein → auf 200 m setzen).<br><br>" +
                    "<b>⑤ Mission starten</b><br>" +
                    "&nbsp;&nbsp;Swarm-Tab → <b>MISSION STARTEN</b>. " +
                    "Die UI armed → takeoffed → fliegt WPs ab → landet. " +
                    "Während der Mission siehst du den Pfad als <span style='color:#22c55e'>grüne Marker + gestrichelte Linie</span> auf der Map. " +
                    "FSM-Badge im Telemetry-Tab folgt: <code>ARMED → TAKEOFF → MISSION → RTL → LANDING → IDLE</code>."
            }

            // ── 2. Globale Konzepte ────────────────────────────────────────
            HelpSection {
                title: "2 · GLOBALE KONZEPTE (musst du verstehen, bevor du irgendwas klickst)"
                accent: "#06b6d4"
                body:
                    "<b>Selected Drone vs. Mission-Targets</b><br>" +
                    "&nbsp;&nbsp;• <b>Selected</b> (im Header / Combo-Box) = die <i>eine</i> Drohne, deren Telemetrie gerade im Telemetry-Tab und InstrBar angezeigt wird.<br>" +
                    "&nbsp;&nbsp;• <b>Mission-Targets</b> (Häkchen-Set im Swarm-Tab) = Drohnen, die <i>Aktionen</i> empfangen (ARM, TAKEOFF, GOTO, MISSION, Mode-Switch). " +
                    "Leeres Set → fällt automatisch auf Selected zurück.<br>" +
                    "&nbsp;&nbsp;<span style='color:#f59e0b'>Folge:</span> Du kannst Drohne A <i>anschauen</i> (Selected) während Drohne B+C eine Mission fliegen (Targets).<br><br>" +
                    "<b>FSM (Finite State Machine) pro Drohne</b><br>" +
                    "&nbsp;&nbsp;Jede Drohne hat einen lokalen Zustand: <code>DISCONNECTED → IDLE → ARMING → ARMED → TAKEOFF → FLYING → MISSION → RTL → LANDING → IDLE</code>. " +
                    "<code>EMERGENCY</code> und <code>ERROR</code> sind Sackgassen, aus denen nur Reconnect / Reset rauskommt. " +
                    "Ungültige Übergänge werden im Log als <code>FSM rejected X → Y</code> protokolliert.<br><br>" +
                    "<b>APF (Artificial Potential Field) — der Kollisionsschutz</b><br>" +
                    "&nbsp;&nbsp;Läuft mit 10 Hz im Hintergrund. Schiebt Drohnen auseinander, sobald sie sich unter <i>min_distance</i> nähern. " +
                    "Der Push wird als GOTO-Override an die jeweils <i>alphabetisch größere</i> Drohnen-ID geschickt → deterministisch, kein gegenseitiges Wackeln.<br>" +
                    "&nbsp;&nbsp;<span style='color:#ef4444'>Wichtig:</span> APF kann Formation- und Mission-Befehle überschreiben. Wenn Formation-Slots enger sind als <i>min_distance</i>, gewinnt APF und die Formation kollabiert.<br><br>" +
                    "<b>Höhen sind AGL</b> (above ground at launch). " +
                    "Eine Takeoff-Höhe von 10 m bedeutet 10 m über dem Spawn-Punkt, <i>nicht</i> 10 m MSL.<br><br>" +
                    "<b>Log-Persistenz:</b> alles, was du im Log-Tab siehst, wird parallel nach <code>tools/ui/syslogs/&lt;datum&gt;_&lt;zeit&gt;.txt</code> geschrieben. " +
                    "Bei Bug-Reports diese Datei mitschicken."
            }

            // ── 3. Tab: Map ────────────────────────────────────────────────
            HelpSection {
                title: "TAB · MAP"
                subtitle: "Leaflet-basierte Karte mit Live-Drohnen-Markers, Tracks, Wegpunkten und Geofence-Overlay."
                accent: "#06b6d4"
                body:
                    "<b>Was du siehst</b><br>" +
                    "&nbsp;&nbsp;• Drohnen-Marker mit Live-Position (Update ~5 Hz).<br>" +
                    "&nbsp;&nbsp;• Track-Polyline (Verlauf), farbig nach Typ: blau = generic, lila = observation.<br>" +
                    "&nbsp;&nbsp;• Editierbare Wegpunkt-Marker (orange, nummeriert).<br>" +
                    "&nbsp;&nbsp;• Bereits dispatched Mission-Pfad (grüne Marker + gestrichelte Linie) — bleibt nach Mission-Start als visuelle Referenz.<br>" +
                    "&nbsp;&nbsp;• Geofence (roter dashed Kreis, falls in Safety aktiviert).<br><br>" +
                    "<b>Wie du es benutzt</b><br>" +
                    "&nbsp;&nbsp;• <b>WAYPOINT HINZUFÜGEN</b> (Toolbar oben) → Cursor wird Fadenkreuz → Klick auf Karte legt WP an.<br>" +
                    "&nbsp;&nbsp;• <b>ESC</b> bricht den Modus ab, ohne WP zu setzen.<br>" +
                    "&nbsp;&nbsp;• <b>Höhen-Feld</b> oben rechts = AGL für den nächsten gesetzten WP.<br>" +
                    "&nbsp;&nbsp;• <b>Kartenstil</b> umschaltbar: Hell · Dunkel · Topo.<br>" +
                    "&nbsp;&nbsp;• <b>Center-on-Drone</b>: Klick auf eine Drohne in der Sidebar zoomt die Map auf ihre Position.<br>" +
                    "&nbsp;&nbsp;• <b>Mausrad</b>: Zoom. Rechtsklick + Drag: Pan.<br><br>" +
                    "<span style='color:#f59e0b'><b>Häufige Stolpersteine</b></span><br>" +
                    "&nbsp;&nbsp;• Karte wirkt leer → Drohnen-Spawn liegt außerhalb des Viewports. Sidebar-Klick auf Drohne zentriert.<br>" +
                    "&nbsp;&nbsp;• WP wird nicht gesetzt → der WP-Modus ist aus. Toolbar-Button noch mal drücken.<br>" +
                    "&nbsp;&nbsp;• Drohne springt sichtbar auf der Karte → Telemetry-Lücke (häufig beim ersten GPS-Fix in SITL). Normal."
            }

            // ── 4. Tab: Telemetry ──────────────────────────────────────────
            HelpSection {
                title: "TAB · TELEMETRY (Dashboard)"
                subtitle: "Live-Cockpit für eine einzelne Drohne — die per Combo-Box oder Sidebar ausgewählte."
                accent: "#2563eb"
                body:
                    "<b>Was du siehst</b><br>" +
                    "&nbsp;&nbsp;• <b>FSM-Badge</b> oben: aktueller Zustand der Drohne mit animiertem Indikator bei Übergängen.<br>" +
                    "&nbsp;&nbsp;• <b>Typ- und Rollen-Badge</b>: generic/observation, Leader/Follower/none.<br>" +
                    "&nbsp;&nbsp;• <b>FSM Flight-Hint</b>: kontextspezifischer Tipp je nach Zustand (z. B. „Drohne ist ARMED – sichere Stelle? TAKEOFF drücken“).<br>" +
                    "&nbsp;&nbsp;• <b>FSM-Verlauf</b>: letzte ~30 Übergänge, neueste oben.<br>" +
                    "&nbsp;&nbsp;• <b>KPI-Grid</b>: Altitude (rel + AMSL), Speed (groundspeed + km/h), Heading, Climb-Rate, Satellites, Throttle.<br>" +
                    "&nbsp;&nbsp;• <b>Battery-Bar</b>: %-Anzeige farbcodiert (grün &gt; 50 %, gelb &gt; 20 %, rot ≤ 20 %) plus Spannung in V.<br>" +
                    "&nbsp;&nbsp;• <b>GPS-Strip</b>: Fix-Type (NoFix/2D/3D/RTK) und Satelliten-Anzahl.<br><br>" +
                    "<b>Wie du es benutzt</b><br>" +
                    "&nbsp;&nbsp;Combo-Box ändern → globale Selected-Drohne wird ebenfalls umgeschaltet (überall in der UI synchron). " +
                    "Auto-Pick: die erste verbundene Drohne wird beim Öffnen des Tabs ausgewählt.<br><br>" +
                    "<span style='color:#f59e0b'><b>Häufige Stolpersteine</b></span><br>" +
                    "&nbsp;&nbsp;• Alle Werte zeigen 0 / „—“ → Drohne ist nicht verbunden oder Telemetry-Stream wurde noch nicht angefordert. " +
                    "In SITL kann das erste GPS-Fix bis 30 s dauern.<br>" +
                    "&nbsp;&nbsp;• <code>flight_mode</code> bleibt „UNKNOWN“ → SDK kennt den FC-Modus nicht. Reconnect oft hilfreich."
            }

            // ── 5. Tab: Swarm ──────────────────────────────────────────────
            HelpSection {
                title: "TAB · SWARM CONTROL"
                subtitle: "Hauptarbeitsplatz für Multi-Drohnen-Operationen: Verbindung, Mission, Formationen, Algorithmen."
                accent: "#22c55e"
                body:
                    "<b>Linke Spalte — Drohnen-Management</b><br>" +
                    "&nbsp;&nbsp;• <b>+ DROHNE</b>: Dialog mit ID + Connection-String (<code>tcp:…</code>, <code>udp:…</code>, <code>serial:…</code>).<br>" +
                    "&nbsp;&nbsp;• Typ-Toggle: <i>generic</i> (Standard) vs. <i>observation</i> (mit Gimbal-Modell).<br>" +
                    "&nbsp;&nbsp;• Drohnen-Liste mit ☑ Mission-Target-Häkchen, Verbindungs-Status, Disconnect- und Remove-Buttons.<br><br>" +
                    "<b>Rechte Spalte — Mission & Algorithmen</b><br>" +
                    "&nbsp;&nbsp;<u>Swarm-Quick-Commands</u> (oberer Block): ARM/DISARM/TAKEOFF/LAND/RTL für <i>alle</i> verbundenen Drohnen.<br>" +
                    "&nbsp;&nbsp;<u>WP-Editor</u>: Lat/Lon/Alt manuell tippen oder per Map-Pick (Button „Karte“). " +
                    "Distanz-Preview zeigt Luftlinie zur aktuell ersten Target-Drohne.<br>" +
                    "&nbsp;&nbsp;<u>GOTO (N)</u>: feuert SET_POSITION an <i>alle</i> Mission-Targets. Label zeigt Anzahl.<br>" +
                    "&nbsp;&nbsp;<u>Mission-Liste</u>: alle gesetzten Wegpunkte mit Index. <b>MISSION STARTEN</b> dispatched die Liste als " +
                    "echte MAVLink-Mission (Upload-Phase) oder fällt auf sequentielles GOTO zurück, falls der Autopilot kein Upload unterstützt.<br><br>" +
                    "<b>Swarm-Algorithmen (eigene Sektion)</b><br>" +
                    "&nbsp;&nbsp;• <b>Boids</b> – Separation / Alignment / Cohesion mit konfigurierbaren Gewichten. Gut für „Schwarm-Look“ ohne Mission.<br>" +
                    "&nbsp;&nbsp;• <b>Leader-Follower</b> – Du wählst einen Leader, alle anderen berechnen relative Slot-Positionen.<br>" +
                    "&nbsp;&nbsp;&nbsp;&nbsp;Formation-Typen: <i>Line · V-Shape · Circle · Grid · RZ-Logo · Letter R · Letter Z</i>.<br>" +
                    "&nbsp;&nbsp;&nbsp;&nbsp;<b>Formation Size</b>: <code>0</code> = alle verbundenen Drohnen werden eingebunden. Sonst: Leader + (Size−1) Follower.<br>" +
                    "&nbsp;&nbsp;&nbsp;&nbsp;<b>Follow Distance</b>: Slot-Abstand in m (Default 8 m, sicher gegen APF min_distance 2 m).<br>" +
                    "&nbsp;&nbsp;• <b>Consensus</b> – Verteilte Voting-Logik (z. B. Mehrheitsbeschluss über RTL).<br>" +
                    "&nbsp;&nbsp;• <b>Behavior Trees</b> – Vorgefertigte Missions-Templates (Surveillance, Search&amp;Rescue, Coverage …).<br><br>" +
                    "<b>Letter-Templates – Drohnen-Anforderungen</b><br>" +
                    "&nbsp;&nbsp;Letter R = 14 Drohnen · Letter Z = 12 · RZ-Logo = 25. Bei weniger Drohnen wird das Template gestaucht oder Slots bleiben leer.<br><br>" +
                    "<span style='color:#f59e0b'><b>Häufige Stolpersteine</b></span><br>" +
                    "&nbsp;&nbsp;• Formation läuft nicht an → Formation Size kleiner als Drohnen-Anzahl, oder kein Leader gesetzt.<br>" +
                    "&nbsp;&nbsp;• Drohnen kollidieren in der Formation → Follow Distance &lt; APF min_distance. Beide aufeinander abstimmen.<br>" +
                    "&nbsp;&nbsp;• Mission startet nicht → keine Mission-Targets markiert + keine Drohne selected.<br>" +
                    "&nbsp;&nbsp;• Mission-Liste verschwindet nach Start → das ist Absicht (One-Shot-Queue). Die grünen Map-Marker bleiben."
            }

            // ── 6. Tab: Safety ─────────────────────────────────────────────
            HelpSection {
                title: "TAB · SAFETY / APF"
                subtitle: "Aktiver Kollisionsschutz, Geofence und Battery-Limits — die einzige Schicht zwischen dir und Crashes."
                accent: "#ef4444"
                body:
                    "<b>APF (Artificial Potential Field)</b><br>" +
                    "&nbsp;&nbsp;Schiebt Drohnen mit einer repulsiven Kraft auseinander. Konfigurierbar:<br>" +
                    "&nbsp;&nbsp;• <b>min separation</b> (m) – ab wann der Push einsetzt.<br>" +
                    "&nbsp;&nbsp;• <b>max speed</b> (m/s) – Kappung der Avoidance-Geschwindigkeit.<br>" +
                    "&nbsp;&nbsp;• <b>repulsion gain</b> – Stärke des Pushs.<br>" +
                    "&nbsp;&nbsp;<b>ENABLE APF</b> startet das 10-Hz-Monitoring; <b>DISABLE</b> stoppt es. Aktiv-State pulsiert grün.<br><br>" +
                    "<b>Geofence</b><br>" +
                    "&nbsp;&nbsp;• <b>Radius</b> (m vom Spawn-Punkt) – horizontale Begrenzung.<br>" +
                    "&nbsp;&nbsp;• <b>Alt min/max</b> – vertikale Begrenzung in m AGL.<br>" +
                    "&nbsp;&nbsp;Verletzung → <code>geofenceBreached</code>-Signal, Log-ERROR, je nach Konfig Auto-RTL.<br><br>" +
                    "<b>Obstacles</b><br>" +
                    "&nbsp;&nbsp;Statische Hindernis-Sphären (Lat/Lon/Alt/Radius) hinzufügbar. APF behandelt sie wie Drohnen.<br><br>" +
                    "<b>Live-Violations-Tabelle</b><br>" +
                    "&nbsp;&nbsp;Aktuelle Konflikt-Paare mit Distanz. Rate-limitiert (max. 1 Log-Eintrag / 2 s pro Paar) damit das System-Log nicht überflutet wird.<br><br>" +
                    "<span style='color:#f59e0b'><b>Häufige Stolpersteine</b></span><br>" +
                    "&nbsp;&nbsp;• APF „kämpft“ gegen Formation → Follow Distance &lt; min_distance. Lösung: Follow Distance erhöhen oder min_distance senken.<br>" +
                    "&nbsp;&nbsp;• SITL spawnt alle Drohnen am exakt gleichen Punkt → APF eskaliert beim Takeoff. " +
                    "Lösung: Drohnen in Höhenstaffeln starten (5/8/11/14 m) <i>vor</i> dem Aktivieren von APF.<br>" +
                    "&nbsp;&nbsp;• Geofence-Default 50 m ist für Letter-Templates zu klein (RZ-Logo spannt ~25 m + Spawn-Streuung)."
            }

            // ── 7. Tab: Gimbal ─────────────────────────────────────────────
            HelpSection {
                title: "TAB · GIMBAL / CAMERA"
                subtitle: "Pan/Tilt-Steuerung und Live-Preview für Observation-Drohnen."
                accent: "#8b5cf6"
                body:
                    "<b>Steuerung</b><br>" +
                    "&nbsp;&nbsp;• Pan- und Tilt-Slider in Grad, sofortige MAVLink-Mount-Command-Sendung.<br>" +
                    "&nbsp;&nbsp;• <b>Presets</b>: Forward (0°/0°), Down/Nadir (0°/−90°), Tracking-Modus (folgt aktuellem Mission-WP).<br>" +
                    "&nbsp;&nbsp;• <b>Snapshot</b>: speichert den aktuellen Frame nach <code>logs/snapshots/&lt;timestamp&gt;_&lt;drone&gt;.png</code>.<br><br>" +
                    "<b>Voraussetzungen</b><br>" +
                    "&nbsp;&nbsp;• Drohne muss als <i>observation</i>-Typ hinzugefügt sein.<br>" +
                    "&nbsp;&nbsp;• Autopilot muss MAV_CMD_DO_MOUNT_CONTROL unterstützen (ArduCopter: ja, PX4: teilweise).<br><br>" +
                    "<span style='color:#f59e0b'><b>Häufige Stolpersteine</b></span><br>" +
                    "&nbsp;&nbsp;• Slider bewegen sich, aber nichts passiert → SITL-Build ohne Gimbal-Mount kompiliert.<br>" +
                    "&nbsp;&nbsp;• Kein Live-Bild → in SITL ist normalerweise kein Stream verfügbar; das Panel zeigt Placeholder."
            }

            // ── 8. Tab: ROS2 ───────────────────────────────────────────────
            HelpSection {
                title: "TAB · ROS2 / uXRCE-DDS (PX4-Bridge)"
                subtitle: "Direkter ROS2-Bridge-Zugriff für PX4-Drohnen über uXRCE-DDS — ohne MAVLink-Umweg."
                accent: "#06b6d4"
                body:
                    "<b>Drei-Spalten-Layout</b><br><br>" +
                    "<b>Links — Status &amp; Konfig</b><br>" +
                    "&nbsp;&nbsp;• <b>Node-Status</b>: <span style='color:#22c55e'>ok</span> · <span style='color:#f59e0b'>no_px4_msgs</span> (rclpy da, aber px4_msgs fehlt) · <span style='color:#ef4444'>no_ros2</span> (rclpy nicht installiert).<br>" +
                    "&nbsp;&nbsp;• <b>Installations-Hinweise</b>: zeigen direkt die nötigen Shell-Commands für ROS2 Humble + px4_msgs + MicroXRCEAgent.<br>" +
                    "&nbsp;&nbsp;• <b>Bridge-Konfig</b>: Drohne wählen, Namespace setzen (leer = <code>/fmu/*</code>), Bridge per Button starten/stoppen.<br>" +
                    "&nbsp;&nbsp;• <b>uORB Topics</b>: Live-Liste aller subscribed/published Topics für diese Bridge.<br><br>" +
                    "<b>Mitte — Live uORB Snapshot &amp; Offboard</b><br>" +
                    "&nbsp;&nbsp;• Aktuelle Telemetrie aus den uORB-Streams (lat/lon/alt/roll/pitch/yaw/battery/gps, 5 Hz).<br>" +
                    "&nbsp;&nbsp;• <b>Offboard-Modus</b> aktivieren, dann <i>Position</i>- oder <i>Velocity</i>-Setpoints in NED-Frame senden.<br>" +
                    "&nbsp;&nbsp;• <b>STOP</b> deaktiviert die kontinuierliche Setpoint-Stream sofort.<br><br>" +
                    "<b>Rechts — Vehicle Commands</b><br>" +
                    "&nbsp;&nbsp;ARM / DISARM / LAND / RTL / TAKEOFF direkt über VEHICLE_COMMAND (umgeht MAVLink-Path).<br><br>" +
                    "<b>Voraussetzungen</b><br>" +
                    "&nbsp;&nbsp;1. ROS2 Humble oder Jazzy installiert (Linux/WSL2).<br>" +
                    "&nbsp;&nbsp;2. <code>px4_msgs</code> in einem ROS2-Workspace gebaut und gesourced.<br>" +
                    "&nbsp;&nbsp;3. <code>MicroXRCEAgent udp4 -p 8888</code> läuft im Hintergrund.<br>" +
                    "&nbsp;&nbsp;4. PX4 mit DDS-Client gestartet (SITL: läuft per Default).<br><br>" +
                    "<span style='color:#f59e0b'><b>Häufige Stolpersteine</b></span><br>" +
                    "&nbsp;&nbsp;• Status bleibt <i>no_ros2</i> auf Windows-nativ → ROS2 läuft nur in WSL2. Die GCS muss in WSL gestartet werden.<br>" +
                    "&nbsp;&nbsp;• Bridge startet, aber Snapshot bleibt leer → MicroXRCEAgent läuft nicht oder falscher Port."
            }

            // ── 9. Tab: Scenario / Experiment ──────────────────────────────
            HelpSection {
                title: "TAB · SCENARIO (Experiment Runner)"
                subtitle: "Zwei Modi: Python-Scripts ad-hoc oder JSON-Szenarien aus Files. Beide nutzen den ExperimentContext."
                accent: "#f59e0b"
                body:
                    "<b>Modus 1 — Python Script</b><br>" +
                    "&nbsp;&nbsp;• <b>OPEN</b>: lädt eine .py-Datei in den Editor.<br>" +
                    "&nbsp;&nbsp;• <b>SAVE</b>: speichert den aktuellen Editor-Inhalt nach <code>experiments/uploads/&lt;name&gt;.py</code> und startet ihn sofort.<br>" +
                    "&nbsp;&nbsp;• <b>RUN/STOP</b>: führt Editor-Inhalt direkt aus (ohne zu speichern) bzw. stoppt den laufenden Script kooperativ via <code>stop_event</code>. " +
                    "Wenn Stop nicht reagiert: Force-Stop benutzt <code>PyThreadState_SetAsyncExc</code> (Best-Effort, kann C-Blockings nicht unterbrechen).<br>" +
                    "&nbsp;&nbsp;• <b>Beispiel</b>: lädt ein Hover-Stability-Experiment (3 SITL-Drohnen, Hover 30 s, Land).<br>" +
                    "&nbsp;&nbsp;• Script-Output (print/stderr) wird in den globalen Log gestreamt mit Prefix <code>[SCRIPT]</code>.<br><br>" +
                    "<b>Modus 2 — JSON Scenario</b><br>" +
                    "&nbsp;&nbsp;• Vordefinierte Schritt-Liste (<code>takeoff</code>, <code>hover</code>, <code>goto</code>, <code>land</code>) wird vom <code>ScenarioRunner</code> ausgeführt.<br>" +
                    "&nbsp;&nbsp;• <i>Use SITL</i>-Checkbox: erzeugt SITL-Instanzen automatisch.<br>" +
                    "&nbsp;&nbsp;• Ergebnisse landen in der <b>RESULTS</b>-Liste (Pass/Fail + Dauer).<br><br>" +
                    "<b>Globaler Watchdog</b><br>" +
                    "&nbsp;&nbsp;Per <code>experiment.setScriptTimeout(seconds)</code> kann ein Hard-Timeout gesetzt werden, der nach Ablauf force_stop() triggert.<br><br>" +
                    "<span style='color:#f59e0b'><b>Häufige Stolpersteine</b></span><br>" +
                    "&nbsp;&nbsp;• Script läuft nicht weiter → <code>exit()</code>/<code>quit()</code> sind im Sandbox-Namespace disabled, benutze <code>return</code> auf Modul-Ebene oder Exception.<br>" +
                    "&nbsp;&nbsp;• <i>Busy</i>-State hängt → Script in C-Bibliothek geblockt. Force-Stop probieren; sonst App neu starten."
            }

            // ── 10. Tab: FlightLog ─────────────────────────────────────────
            HelpSection {
                title: "TAB · FLIGHT LOG"
                subtitle: "Offline-Replay & Plots aus den Telemetry-CSVs jeder vergangenen Verbindung."
                accent: "#a78bfa"
                body:
                    "<b>Datenquelle</b><br>" +
                    "&nbsp;&nbsp;Jede Drohnen-Verbindung schreibt <code>logs/&lt;timestamp&gt;_&lt;drone&gt;_telemetry.csv</code> via <code>TelemetryLogger</code>. " +
                    "Bei Queue-Sättigung werden Frames gedroppt und am Ende als <code>dropped_count</code> protokolliert (rate-limited Warnings).<br><br>" +
                    "<b>Funktionen</b><br>" +
                    "&nbsp;&nbsp;• Datei-Auswahl (Multi-Select für Vergleichs-Overlay).<br>" +
                    "&nbsp;&nbsp;• Plots: Altitude · Battery · Speed · Heading über Zeit.<br>" +
                    "&nbsp;&nbsp;• Multi-Drohne-Overlay mit Farbcode pro Drohne.<br>" +
                    "&nbsp;&nbsp;• PNG-Export der Plots für Berichte.<br><br>" +
                    "<span style='color:#f59e0b'><b>Häufige Stolpersteine</b></span><br>" +
                    "&nbsp;&nbsp;• Plot leer → CSV ist leer (Drohne war nie verbunden) oder Spalten-Header nicht erkannt. " +
                    "TelemetryLogger schreibt einen Header beim ersten Frame."
            }

            // ── 11. Tab: Log ───────────────────────────────────────────────
            HelpSection {
                title: "TAB · SYSTEM LOG"
                subtitle: "Aggregierter Live-Stream aller Backend-Logs aus swarm/experiment/safety/ros2."
                accent: "#64748b"
                body:
                    "<b>Was du siehst</b><br>" +
                    "&nbsp;&nbsp;• Live-Einträge mit Zeitstempel (HH:MM:SS), Level-Badge (INFO/WARN/ERROR), Drohnen-Tag (farbcodiert per Hash) und Nachricht.<br>" +
                    "&nbsp;&nbsp;• Auto-Scroll am unteren Ende; bei neuer Nachricht wird gescrollt.<br>" +
                    "&nbsp;&nbsp;• Error-Counter-Badge im Header zeigt Anzahl ERROR-Einträge.<br><br>" +
                    "<b>Filter</b><br>" +
                    "&nbsp;&nbsp;• Level-Dropdown: ALL / INFO / WARN / ERROR.<br>" +
                    "&nbsp;&nbsp;• Suchfeld (case-insensitive, sucht in Level + Text).<br>" +
                    "&nbsp;&nbsp;• <b>CLEAR</b>: leert das in-memory Log (die auto-save-Datei bleibt erhalten).<br><br>" +
                    "<b>Persistenz</b><br>" +
                    "&nbsp;&nbsp;Alles wird <i>zusätzlich</i> nach <code>tools/ui/syslogs/&lt;datum&gt;_&lt;zeit&gt;.txt</code> geschrieben (Throttle 1 s, Ring-Buffer 3000 in memory). " +
                    "Bei Bug-Reports immer mitschicken."
            }

            // ── 12. InstrBar (oben) ────────────────────────────────────────
            HelpSection {
                title: "INSTRBAR (oberer Streifen, immer sichtbar)"
                subtitle: "Cockpit-Instrumente + Quick-Commands über alle Tabs hinweg."
                accent: "#3b82f6"
                body:
                    "<b>Tiles (links → rechts)</b><br>" +
                    "&nbsp;&nbsp;1. <b>DRONE</b> – Combo + Connection-Indikator. Wechseln synchronisiert globale Selected.<br>" +
                    "&nbsp;&nbsp;2. <b>ARMED/MODE</b> – pulsierender Indikator wenn ARMED, Flight-Mode-Anzeige, Drohnen-ID.<br>" +
                    "&nbsp;&nbsp;3. <b>Künstlicher Horizont</b> – Roll/Pitch live aus ATTITUDE-Stream (Canvas, 10 Hz refresh).<br>" +
                    "&nbsp;&nbsp;4. <b>Kompass</b> – Heading mit Cardinal-Labels.<br>" +
                    "&nbsp;&nbsp;5. <b>ALT/SPEED/CLIMB</b> – Numeric Tiles mit Trend-Bars und Einheiten-Konversion (m/s → km/h).<br>" +
                    "&nbsp;&nbsp;6. <b>BATTERY/GPS</b> – %-Anzeige + Voltage + Fix-Type + Sat-Count.<br>" +
                    "&nbsp;&nbsp;7. <b>QUICK CMD</b> – 6 Buttons: ARM · DISARM · TAKEOFF · LAND · RTL · HOLD. Set-Altitude-Feld daneben für Takeoff-Höhe.<br>" +
                    "&nbsp;&nbsp;8. <b>FLIGHT MODE</b> – 6 Modi: Stab · Alt-H · Loiter · Guided · Auto · PosHld. Klick switched <i>alle</i> Mission-Targets.<br><br>" +
                    "<b>Wichtig:</b> alle Quick-Cmds und Mode-Switches feuern auf <i>alle markierten Mission-Targets</i> simultan. " +
                    "Wenn keine markiert sind, fallen sie auf die Selected-Drohne zurück."
            }

            // ── 13. Konventionen & Gotchas ─────────────────────────────────
            HelpSection {
                title: "KONVENTIONEN, GOTCHAS & TROUBLESHOOTING"
                accent: "#ef4444"
                body:
                    "<b>Connection-Strings</b><br>" +
                    "&nbsp;&nbsp;• <code>tcp:127.0.0.1:5762</code> – ArduCopter SITL Standard.<br>" +
                    "&nbsp;&nbsp;• <code>tcp:127.0.0.1:5772</code> – SITL Drohne #2 (jede +10).<br>" +
                    "&nbsp;&nbsp;• <code>udp:127.0.0.1:14550</code> – PX4 SITL Standard.<br>" +
                    "&nbsp;&nbsp;• <code>serial:/dev/ttyACM0:57600</code> oder <code>serial:COM5:57600</code> – Hardware.<br><br>" +
                    "<b>Höhen</b><br>" +
                    "&nbsp;&nbsp;• Alle Eingaben in der UI sind <b>AGL</b> (above ground at launch).<br>" +
                    "&nbsp;&nbsp;• <code>alt_rel</code> = Höhe über Spawn. <code>alt</code> bzw. <code>alt_amsl</code> = MSL.<br>" +
                    "&nbsp;&nbsp;• SITL CMAC spawnt typischerweise auf 583 m MSL.<br><br>" +
                    "<b>Mission-Queue ist One-Shot</b><br>" +
                    "&nbsp;&nbsp;Nach <i>MISSION STARTEN</i> wird die Editier-Liste geleert. Die <i>grünen</i> Map-Marker bleiben als visuelle Referenz. " +
                    "Neue WPs hinzufügen → nächster Mission-Start nimmt nur die neuen.<br><br>" +
                    "<b>SITL-Spawn am gleichen Punkt</b><br>" +
                    "&nbsp;&nbsp;Standardmäßig spawnen alle SITL-Drohnen auf derselben Lat/Lon. APF eskaliert beim Takeoff. " +
                    "Lösung: in Höhenstaffeln starten (5/8/11/14 m) oder Spawn-Offset im SITL-Build-Skript setzen.<br><br>" +
                    "<b>Throttling</b><br>" +
                    "&nbsp;&nbsp;• Formation-Goto: 2 Hz pro Drohne (verhindert MAVLink-Bus-Saturation).<br>" +
                    "&nbsp;&nbsp;• GOTO-Buttons: unbeschränkt (Operator-Triggered).<br>" +
                    "&nbsp;&nbsp;• Telemetry-Aggregation: 5 Hz. Per-Drone-Polling: 10 Hz.<br><br>" +
                    "<b>FSM-Sackgassen</b><br>" +
                    "&nbsp;&nbsp;• <code>EMERGENCY</code> – nur per Reset/Reconnect verlassbar.<br>" +
                    "&nbsp;&nbsp;• <code>ERROR</code> – Hard-Fault, Drohne neu verbinden.<br>" +
                    "&nbsp;&nbsp;• <code>DISCONNECTED</code> – Verbindung verloren; Auto-Reconnect-Versuch alle 5 s.<br><br>" +
                    "<b>Diagnose-Sammlung bei Bug-Reports</b><br>" +
                    "&nbsp;&nbsp;1. Aktuelle <code>tools/ui/syslogs/&lt;datum&gt;_&lt;zeit&gt;.txt</code><br>" +
                    "&nbsp;&nbsp;2. Konsolen-Output der GCS (stdout + stderr)<br>" +
                    "&nbsp;&nbsp;3. Relevante <code>logs/&lt;timestamp&gt;_&lt;drone&gt;_telemetry.csv</code><br>" +
                    "&nbsp;&nbsp;4. SITL-Konsolen-Output falls Simulation"
            }

            // ── 14. Glossar ────────────────────────────────────────────────
            Rectangle {
                width: parent.width; radius: 10
                color: "#0d1117"
                border.color: "#1e293b"; border.width: 1
                height: glossCol.implicitHeight + 24

                Rectangle {
                    width: 4; height: parent.height - 16
                    anchors { left: parent.left; leftMargin: 6; verticalCenter: parent.verticalCenter }
                    radius: 2; color: "#0ea5e9"
                }

                Column {
                    id: glossCol
                    anchors {
                        left: parent.left; leftMargin: 20
                        right: parent.right; rightMargin: 14
                        top: parent.top; topMargin: 12
                    }
                    spacing: 8

                    Text {
                        text: "GLOSSAR"
                        color: "#0ea5e9"
                        font.pixelSize: 14; font.weight: Font.Bold; font.letterSpacing: 0.5
                    }

                    GlossaryRow { term: "AGL";           def: "Above Ground at Launch — Höhe über dem Takeoff-Punkt." }
                    GlossaryRow { term: "AMSL / MSL";    def: "Above Mean Sea Level — absolute Höhe." }
                    GlossaryRow { term: "APF";           def: "Artificial Potential Field — repulsiver Kollisionsschutz, 10 Hz." }
                    GlossaryRow { term: "FSM";           def: "Finite State Machine — Zustandsautomat pro Drohne (IDLE/ARMED/FLYING/…)." }
                    GlossaryRow { term: "Selected Drone";def: "Die <i>eine</i> Drohne, deren Telemetrie aktuell angezeigt wird." }
                    GlossaryRow { term: "Mission-Target";def: "Drohne mit ☑ — bekommt Aktionen (ARM, GOTO, MISSION, …)." }
                    GlossaryRow { term: "WP";            def: "Waypoint — Lat/Lon/Alt-Punkt in der Mission." }
                    GlossaryRow { term: "RTL";           def: "Return To Launch — Drohne fliegt zum Spawn-Punkt zurück." }
                    GlossaryRow { term: "SITL";          def: "Software In The Loop — Drohnen-Simulation ohne Hardware." }
                    GlossaryRow { term: "uXRCE-DDS";     def: "Micro XRCE-DDS — PX4-Bridge nach ROS2 (ersetzt MAVLink-bridge)." }
                    GlossaryRow { term: "uORB";          def: "Micro Object Request Broker — PX4-interner Message-Bus." }
                    GlossaryRow { term: "NED";           def: "North-East-Down lokales Koordinatensystem (PX4-Standard)." }
                    GlossaryRow { term: "Geofence";      def: "Virtuelle Begrenzung (Radius + Alt-min/max); Verletzung → Log + Auto-RTL." }
                    GlossaryRow { term: "Boids";         def: "Schwarm-Algorithmus mit Separation/Alignment/Cohesion." }
                    GlossaryRow { term: "Leader-Follower"; def: "Formation-Modell: ein Leader, N Follower mit relativen Slot-Offsets." }
                }
            }

            // ── 15. Tastatur ───────────────────────────────────────────────
            HelpSection {
                title: "TASTATUR & MAUS"
                accent: "#fbbf24"
                body:
                    "<b>ESC</b> &mdash; Waypoint-Modus / Map-Pick abbrechen<br>" +
                    "<b>Klick auf Drohne in Sidebar</b> &mdash; Selected-Drone setzen<br>" +
                    "<b>Klick auf Häkchen ☑</b> &mdash; Mission-Target toggeln (multi-select)<br>" +
                    "<b>Linksklick Map (im WP-Modus)</b> &mdash; Wegpunkt setzen<br>" +
                    "<b>Mausrad auf Map</b> &mdash; Zoom<br>" +
                    "<b>Rechtsklick + Drag auf Map</b> &mdash; Pan<br>" +
                    "<b>Strg+S in Script-Editor</b> &mdash; Save&amp;Run (Experiment-Tab)"
            }

            // ── Footer ─────────────────────────────────────────────────────
            Rectangle {
                width: parent.width; height: 56
                radius: 8
                color: "#161b27"
                border.color: "#1e293b"; border.width: 1
                Column {
                    anchors.centerIn: parent
                    spacing: 3
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Bei Problemen: System-Log + syslogs/*.txt + Konsolen-Output sammeln."
                        color: "#64748b"; font.pixelSize: 10; font.italic: true
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "Dieses Help-Panel ist read-only — keine Bindings, keine Side-Effects."
                        color: "#475569"; font.pixelSize: 9; font.italic: true
                    }
                }
            }

            Item { width: 1; height: 8 }
        }
    }
}

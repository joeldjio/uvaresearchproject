# DroneResearch Platform — Verbesserungs-Dokumentation

**Branch:** `fix/bugfixes-analysis`  
**Basis:** `ui-dashboard` (Commit `d59d681`)  
**Datum:** 2026-06-06  
**Autor:** Zed AI Agent (Code-Review & Implementierung)

---

## Inhaltsverzeichnis

1. [Analysemethodik](#1-analysemethodik)
2. [Projektarchitektur-Überblick](#2-projektarchitektur-überblick)
3. [Gefundene und gefixte Bugs](#3-gefundene-und-gefixte-bugs)
4. [Verbesserungen — Core SDK](#4-verbesserungen--core-sdk)
5. [Verbesserungen — GCS UI](#5-verbesserungen--gcs-ui)
6. [Verbesserungen — Infrastruktur](#6-verbesserungen--infrastruktur)
7. [Neue Regressionstests](#7-neue-regressionstests)
8. [Geänderte Dateien — Vollständige Liste](#8-geänderte-dateien--vollständige-liste)
9. [Test-Ergebnis](#9-test-ergebnis)
10. [Commit-Historie](#10-commit-historie)

---

## 1. Analysemethodik

Das gesamte Projekt wurde in zwei Phasen analysiert:

**Phase 1 — Strukturanalyse:**  
Lesen aller Verzeichnisse, `README.md`, `PROJECT_OVERVIEW.md`, `pyproject.toml` und aller `__init__.py`-Dateien. Ziel: vollständiger Überblick über Modulstruktur, Abhängigkeiten, Tech-Stack und Deployment-Wege.

**Phase 2 — Tiefenanalyse:**  
Lesen jeder einzelnen Python-Quelldatei, inklusive:
- `droneresearch/core/connection.py` — MAVLink-Parsing und Command-Handling
- `droneresearch/core/fsm.py` — Finite State Machine
- `droneresearch/sdk/drone.py` + `swarm_api.py` + `formations.py`
- `droneresearch/safety/apf.py` — APF-Filter-Logik
- `droneresearch/llm/swarm_commander.py` — LLM-Integration
- `droneresearch/models/generic_uav.py` + `coordinator_uav.py`
- `droneresearch/control/mission.py` + `script_runner.py`
- `droneresearch/exploration/frontier_bridge.py`
- `droneresearch/simulation/sitl.py`
- `droneresearch/experiment/metrics.py` + `manager.py`
- `droneresearch/data/logger.py` + `store.py`
- `tools/ui/app.py`, `backend.py`, `service_locator.py`, `license.py`, `updater.py`
- `tools/ui/context/swarm_context.py`, `safety_context.py`, `telemetry_context.py`

Dabei wurden 20 potenzielle Verbesserungspunkte identifiziert, in 4 Prioritätsstufen eingeteilt und vollständig umgesetzt.

---

## 2. Projektarchitektur-Überblick

Das Projekt besteht aus zwei klar getrennten Schichten:

```
┌─────────────────────────────────────────────────────────────┐
│  uavresearch gcs  (tools/ui/)          PyQt6 + QML                   │
│  ┌─────────────┐  ┌──────────┐  ┌────────┐  ┌───────────┐  │
│  │SwarmContext  │  │Safety    │  │Updater │  │License    │  │
│  │(Boids/LF/   │  │Context   │  │Context │  │Manager    │  │
│  │ Consensus)  │  │(APF/Geo) │  │(GitHub)│  │(HMAC-Key) │  │
│  └──────┬──────┘  └────┬─────┘  └────────┘  └───────────┘  │
│         │ ServiceLocator (DI-Container)                      │
│         ▼                                                    │
│  DroneBackend / SwarmBackend    (Qt ↔ SDK-Brücke)           │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│  droneresearch SDK       Python 3.10+                       │
│  ┌──────┐ ┌───────┐ ┌──────────┐ ┌────────┐ ┌──────────┐  │
│  │Drone │ │Swarm  │ │Experiment│ │Safety  │ │LLM       │  │
│  │SDK   │ │API    │ │/Metrics  │ │APF     │ │Commander │  │
│  └──┬───┘ └───┬───┘ └──────────┘ └────────┘ └──────────┘  │
│     │         │                                             │
│  ┌──▼─────────▼──────────────────┐                         │
│  │  MAVLinkConnection             │  pymavlink              │
│  │  (connect/reconnect/parse)     │                         │
│  └────────────────────────────────┘                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐ │
│  │StateMachine│  │TelemetryState│ │MissionEngine           │ │
│  │(FSM 10     │  │(~40 Felder,│  │(upload/start/abort)    │ │
│  │ Zustände)  │  │thread-safe)│  │                        │ │
│  └────────────┘  └────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Gefundene und gefixte Bugs

> **Commit:** `751ae02`  
> **Dateien:** `core/connection.py`, `sdk/swarm_api.py`, `exploration/frontier_bridge.py`, `models/generic_uav.py`

---

### Bug 1 — `MAVLinkConnection.goto()`: Veraltetes MAVLink-Kommando

**Datei:** `droneresearch/core/connection.py`

**Problem:**  
`goto()` nutzte `mission_item_send` — ein veraltetes MAVLink-Kommando das:
- von PX4 im OFFBOARD/GUIDED-Modus ignoriert wird
- beim Standard MAVLink-Protokoll in keiner Weise mit GUIDED-Modus interagiert
- keine definierte Semantik für "fliege jetzt zu diesem Punkt" hat

```python
# Vorher (falsch):
self._mav.mav.mission_item_send(
    self._mav.target_system,
    self._mav.target_component,
    0, 3, 16, 2, 1, 0, 0, 0, 0,
    lat, lon, alt,
)
```

**Fix:**  
Ersetzt durch `SET_POSITION_TARGET_GLOBAL_INT` (MAVLink Message #86):

```python
# Nachher (korrekt):
self._mav.mav.set_position_target_global_int_send(
    0,                   # time_boot_ms
    self._mav.target_system,
    self._mav.target_component,
    6,                   # MAV_FRAME_GLOBAL_RELATIVE_ALT
    0x0FF8,              # type_mask: Position only (ignore vel/accel/yaw)
    int(lat * 1e7),      # lat_int  (Grad × 1e7)
    int(lon * 1e7),      # lon_int  (Grad × 1e7)
    float(alt),          # alt (m über Home)
    0.0, 0.0, 0.0,       # vx, vy, vz  (ignoriert)
    0.0, 0.0, 0.0,       # afx, afy, afz (ignoriert)
    0.0, 0.0,            # yaw, yaw_rate (ignoriert)
)
```

**Wirkung:** Goto funktioniert jetzt korrekt mit ArduPilot (GUIDED) und PX4 (OFFBOARD).  
**type_mask `0x0FF8`:** Bits 0-2 = 0 (Position verwenden), Bits 3-11 = 1 (Velocity/Accel/Yaw ignorieren).

---

### Bug 2 — `Swarm.formation()`: Off-by-One bei Follower-Offset-Zuweisung

**Datei:** `droneresearch/sdk/swarm_api.py`

**Problem:**  
Die Schleife nutzte den Drohnenlisten-Index `i` um in das Offset-Array zu indexieren. Da `_calc_offsets()` aber nur `count-1` Offsets zurückgibt (kein Leader-Slot), bekam der letzte Follower immer `(0, 0)` wenn der Leader nicht am Ende der Liste stand.

```python
# Vorher (falsch):
offsets = self._calc_offsets(shape, len(drones), spacing)  # N-1 Offsets
for i, drone in enumerate(drones):          # i geht von 0 bis N-1
    if drone is leader_drone:
        continue
    off = offsets[i] if i < len(offsets) else (0, 0)  # ← i kann >= len sein!
```

**Beispiel:** 4 Drohnen, Leader an Index 0:
- `offsets` hat 3 Einträge: [0], [1], [2]
- i=0: Leader, skip
- i=1: D2 → `offsets[1]` ✓
- i=2: D3 → `offsets[2]` ✓
- i=3: D4 → `offsets[3]` = IndexError → Fallback `(0,0)` ✗

**Fix:**  
Separater Follower-Zähler:

```python
# Nachher (korrekt):
follower_idx = 0
for drone in drones:
    if drone is leader_drone:
        continue
    off = offsets[follower_idx] if follower_idx < len(offsets) else (0.0, 0.0)
    follower_idx += 1
```

**Wirkung:** Alle Follower erhalten korrekte, distinkte Offsets — unabhängig von der Position des Leaders in der Drohnenliste.

---

### Bug 3 — `FrontierExplorationBridge`: GPS-Koordinaten als NED-Meter

**Datei:** `droneresearch/exploration/frontier_bridge.py`

**Problem:**  
`_FrontierNode._publish_telemetry()` veröffentlichte rohe GPS-Koordinaten (Breitengrad in Dezimalgrad) als lokale NED-Meter-Position an den ROS2 Frontier-Explorer:

```python
# Vorher (falsch):
odom.pose.pose.position.x = t.lat   # z.B. 48.137 — keine Meter!
odom.pose.pose.position.y = t.lon   # z.B. 11.575 — keine Meter!
```

**Problem:** 48,137° Breitengrad ≠ 48,137 Meter. Der Frontier-Explorer berechnete damit vollständig falsche Distanzen und Frontierplanungs-Entscheidungen.

**Fix:**  
Referenzpunkt beim ersten gültigen GPS-Fix setzen, dann GPS → NED-Meter via Haversine-Linearisierung:

```python
# Nachher (korrekt):
def _set_ref_if_needed(self, lat, lon) -> bool:
    if self._ref_lat is None and lat != 0.0 and lon != 0.0:
        self._ref_lat = lat
        self._ref_lon = lon
    return self._ref_lat is not None

def _gps_to_ned(self, lat, lon) -> tuple:
    north = (lat - self._ref_lat) * 111_320.0
    east  = (lon - self._ref_lon) * 111_320.0 * math.cos(math.radians(self._ref_lat))
    return north, east

def _publish_telemetry(self):
    if not self._set_ref_if_needed(t.lat, t.lon):
        return  # Noch kein GPS-Fix
    north, east = self._gps_to_ned(t.lat, t.lon)
    odom.pose.pose.position.x = north  # ← jetzt echte Meter
    odom.pose.pose.position.y = east   # ← jetzt echte Meter
```

**Wirkung:** Frontier-Explorer erhält korrekte lokale NED-Koordinaten. Explorations-Distanzen und Planungsentscheidungen sind physikalisch korrekt.

---

### Bug 4 — `GenericUAVModel`: FSM bleibt bei Reconnect auf IDLE

**Datei:** `droneresearch/models/generic_uav.py`

**Problem:**  
`_sync_armed()` und `_sync_mode()` behandelten nur normale Arm/Disarm-Sequenzen. Nach einem Verbindungsabbruch und Wiederverbindung zu einer bereits fliegenden Drohne blieb das FSM dauerhaft auf `IDLE` stehen — `can_mission()`, `is_airborne()` etc. lieferten falsche Werte.

```python
# Vorher (unvollständig):
def _sync_armed(self, armed: bool):
    if armed and self.fsm.state == DroneState.ARMING:
        self.fsm.transition(DroneState.ARMED)  # Nur normaler Arming-Pfad
    elif not armed:
        if self.fsm.state in (DroneState.LANDING, DroneState.RTL):
            if self.altitude < 1.0:
                self.fsm.transition(DroneState.IDLE, force=True)
    # Reconnect-Fall (armed=True, FSM=IDLE): NICHT behandelt!
```

**Fix:**  
Beide Callbacks erkennen jetzt den Reconnect-Fall und pushen das FSM mit `force=True`:

```python
# Nachher (vollständig):
def _sync_armed(self, armed: bool):
    if armed:
        if self.fsm.state == DroneState.ARMING:
            self.fsm.transition(DroneState.ARMED)          # Normaler Pfad
        elif self.fsm.state == DroneState.IDLE:
            self.fsm.transition(DroneState.ARMED, force=True)  # Reconnect
            if self.altitude > 1.0:
                self.fsm.transition(DroneState.FLYING, force=True)  # Airborne
    else:
        if self.fsm.state in (DroneState.LANDING, DroneState.RTL):
            if self.altitude < 1.0:
                self.fsm.transition(DroneState.IDLE, force=True)

def _sync_mode(self, mode: str):
    # Reconnect: Drohne fliegt schon, FSM ist IDLE/ARMED
    if (mode in ("GUIDED", "LOITER", "AUTO", "POSHOLD", "OFFBOARD", ...)
            and self.fsm.state in (DroneState.IDLE, DroneState.ARMED)
            and self.telemetry.armed and self.altitude > 1.0):
        self.fsm.transition(DroneState.FLYING, force=True)
    # Normale Übergänge...
```

**Wirkung:** Das FSM spiegelt nach Reconnect korrekt den tatsächlichen Autopilot-Zustand wider.

---

## 4. Verbesserungen — Core SDK

---

### V1 — MAVLink Reconnect mit Exponentialem Backoff

**Datei:** `droneresearch/core/connection.py`  
**Commit:** `1beaa52`

**Problem:** Der `_loop()`-Thread terminierte bei jeder Exception still. Danach war das `Drone`-Objekt permanent tot — keine automatische Wiederverbindung.

**Implementierung:**  
Die `_loop()`-Methode wurde in drei Schichten aufgeteilt:

```
_loop()            ← Äußere Orchestrierung (reconnect-Entscheidung)
  _recv_loop()     ← Innere Empfangsschleife (wirft Exception bei Abbruch)
  _reconnect_loop() ← Backoff-Sequenz mit State-Recovery
```

Backoff-Sequenz: 1s → 2s → 4s → 8s → 16s → max. 30s zwischen Versuchen.  
Nach erfolgreichem Reconnect: `_request_streams()`, `_request_autopilot_version()`, Event `"connected"` emittiert.

Neuer Konstruktor-Parameter: `auto_reconnect: bool = True` (kann deaktiviert werden).

---

### V2 — Input-Validierung für Connection-Strings

**Datei:** `droneresearch/core/connection.py`  
**Commit:** `1beaa52`

Neue statische Methode `validate_connection_string(s: str) -> str`:

| Format | Beispiel | Gültig |
|--------|----------|--------|
| `tcp:HOST:PORT` | `tcp:127.0.0.1:5760` | ✓ |
| `udp:HOST:PORT` | `udp:0.0.0.0:14550` | ✓ |
| `/dev/tty...` | `/dev/ttyUSB0` | ✓ |
| `serial:/dev/...` | `serial:/dev/ttyUSB0:57600` | ✓ |
| `COMx` / `COMx:BAUD` | `COM3`, `COM3:57600` | ✓ |
| Alles andere | `foo:bar` | ✗ → `ValueError` |

Wird am Anfang von `connect()` aufgerufen. Fehlerhafte Strings emittieren einen verständlichen `statustext`-Event statt kryptischer pymavlink-Exceptions.

---

### V3 — MAVLink Mission Upload: Hybrid-Handshake-Protokoll

**Datei:** `droneresearch/control/mission.py`  
**Commit:** `1beaa52`

**Problem:** Die Upload-Implementierung schickte alle Waypoints blind mit 50ms-Pacing, ohne auf `MISSION_REQUEST`-Nachrichten des Autopiloten zu warten. Das korrekte MAVLink-Protokoll ist ein Request/Response-Handshake.

**Implementierung: Hybrid-Ansatz (rückwärtskompatibel)**

```
upload()
  ├── Sende MISSION_COUNT
  ├── Warte bis 250ms auf MISSION_REQUEST(0)
  │   ├── MISSION_REQUEST empfangen  → _upload_handshake()
  │   │     Für jeden seq: warte auf MISSION_REQUEST(seq), sende Item
  │   │     Am Ende: warte auf MISSION_ACK(ACCEPTED)
  │   └── Kein MISSION_REQUEST      → _upload_push_all()
  │         Legacy: sende alle Items mit 50ms-Pacing (ArduPilot-kompatibel)
  └── finally: deregistriere Message-Listener
```

Der Handshake-Pfad ist korrekt nach MAVLink-Standard. Der Push-All-Pfad ist der bisherige Fallback für ältere/nicht-standardkonforme Firmware. Bestehende Tests laufen weiterhin (kein MISSION_REQUEST → Fallback-Pfad).

---

### V4 — PX4-kompatibler Takeoff/Goto-Modus

**Datei:** `droneresearch/sdk/drone.py`  
**Commit:** `5df0c56`

**Problem:** `takeoff()` und `goto()` setzten immer `GUIDED`-Modus. PX4 benötigt für Positionsbefehle `OFFBOARD`-Modus.

```python
# Vorher:
self.set_mode("GUIDED")  # PX4 ignoriert Positionsbefehle in GUIDED

# Nachher:
ap = self._conn.telemetry.autopilot
mode = "OFFBOARD" if ap == "px4" else "GUIDED"
self.set_mode(mode)
```

Gilt für `takeoff()` und `goto()`.

---

### V5 — Kontinuierlicher Formation-Follow-Loop

**Datei:** `droneresearch/sdk/swarm_api.py`  
**Commit:** `5df0c56`

**Problem:** `Swarm.formation()` setzte Positionen nur einmalig. Bei einem sich bewegenden Leader liefen Follower sofort auseinander.

Neue Methoden:

```python
swarm.start_follow(shape="line", spacing=5.0, leader="D1", update_hz=2.0)
# Startet Daemon-Thread "swarm-follow", der im Takt formation() aufruft

swarm.stop_follow()
# Stoppt den Thread sauber (join mit 2s Timeout)
```

---

### V6 — `position_error`-Metrik (RMS-Pfadabweichung)

**Datei:** `droneresearch/experiment/metrics.py`  
**Commit:** `5df0c56`

**Problem:** `position_error` war im Docstring dokumentiert, aber nie implementiert.

Neue API:

```python
metrics = MetricsCollector(["position_error", "flight_time"])
metrics.set_intended_path([
    {"lat": 48.137, "lon": 11.575},
    {"lat": 48.138, "lon": 11.576},
])
metrics.start()
# ... Flug ...
metrics.stop()
result = metrics.summary()
# result["position_error_rms_m"]  → RMS-Abweichung in Metern
# result["position_error_max_m"]  → Maximale Abweichung in Metern
```

Berechnung: Minimale Haversine-Distanz (in Metern) zum nächsten Pfad-Waypoint. Gesammelt bei jedem Sample (0.5 Hz). Am Ende: RMS und Maximum.

---

### V7 — TelemetryLogger: Periodischer CSV-Flush

**Datei:** `droneresearch/data/logger.py`  
**Commit:** `5df0c56`

**Problem:** Die CSV-Datei wurde nie explizit geflusht. Bei einem Absturz gingen die letzten Datenpunkte aus dem I/O-Buffer verloren.

**Fix:** Der Writer-Thread flusht jetzt:
- nach jeweils 50 geschriebenen Zeilen, **oder**
- nach spätestens 1 Sekunde, **oder**
- bei jeder `Empty`-Exception (Idle-Phase)

```python
# Im _writer()-Thread:
if rows_since_flush >= 50 or (now - last_flush) >= 1.0:
    if self._csv_file:
        self._csv_file.flush()
```

---

### V8 — TelemetryLogger: JSONL-Events (Crash-Safe)

**Datei:** `droneresearch/data/logger.py`  
**Commit:** `5df0c56`

**Problem:** Events wurden im Speicher gesammelt und erst beim `stop()` als vollständiges JSON-Array geschrieben. Bei einem Absturz gingen alle Events verloren.

**Fix:** Zusätzliche `_events.jsonl`-Datei im Newline-Delimited JSON Format:

```python
logger.log_event("armed",   {"force": False})  # → sofort in .jsonl
logger.log_event("takeoff", {"altitude": 10.0}) # → sofort in .jsonl
```

Jede Zeile ist ein vollständiges JSON-Objekt — crash-safe, streambar, kein Array-Parsing nötig.  
Die `_events.json`-Datei bleibt rückwärtskompatibel erhalten.

---

### V9 — TelemetryStore: SQLite-Persistenz

**Datei:** `droneresearch/data/store.py`  
**Commit:** `43dadb7`

**Problem:** Der In-Memory-Ringpuffer verliert alle Daten bei App-Neustart.

Neue optionale SQLite-Persistenz:

```python
store = TelemetryStore(max_history=2000, db_path="logs/telemetry.db")
store.push("D1", snapshot)

# Historische Abfrage (auch nach Neustart):
history = store.query_db("D1", since=time.time() - 3600, limit=500)
```

Tabellen-Schema:
```sql
CREATE TABLE telemetry (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    drone_id TEXT NOT NULL,
    ts       REAL NOT NULL,     -- Unix-Timestamp
    snapshot TEXT NOT NULL      -- JSON-serialisiertes Dict
);
CREATE INDEX idx_drone_ts ON telemetry(drone_id, ts);
```

Thread-safe: `sqlite3.connect(check_same_thread=False)` mit Lock vom übergeordneten `_lock`.

---

### V10 — SITL-Cluster: Paralleler Start

**Datei:** `droneresearch/simulation/sitl.py`  
**Commit:** `1beaa52`

**Problem:** `SITLCluster.start()` startete Instanzen sequentiell mit 2s Pause zwischen jeder → N×2s Wartezeit.

**Fix:** Paralleler Start aller Instanzen via `threading.Thread`, minimaler Stagger (0.5s) nur zur Port-Initialisierung:

```python
# Vorher: N × 2s = 6s für 3 Drohnen
# Nachher: max(0.5s × (N-1)) + Startzeit = ~1s für 3 Drohnen
```

---

### V11 — ScriptRunner: Subprocess-Sandbox Option

**Datei:** `droneresearch/control/script_runner.py`  
**Commit:** `43dadb7`

**Problem:** Scripts liefen in-process. Ein Fehler (z.B. Endlosschleife, Speicherleck, Segfault durch C-Extension) konnte den gesamten GCS-Prozess zum Absturz bringen.

Neue Option `use_subprocess=True`:

```python
runner.run_string(code, use_subprocess=True)
# Script läuft in separatem Python-Prozess
# Output wird live gestreamt
# Crash im Script → GCS läuft weiter
# Stop via runner.stop() → subprocess.terminate()
```

Im Subprocess-Modus verbindet sich das Script über die `connection_string` des übergeordneten `Drone`-Objekts neu — der `drone`-Context ist also live, aber nicht direkt geteilt.

---

## 5. Verbesserungen — GCS UI

---

### V12 — DroneBackend: Differenz-basierte Telemetrie-Emission

**Datei:** `tools/ui/backend.py`  
**Commit:** `3f899c5`

**Problem:** Jeder Poll-Tick (10 Hz) emittierte das komplette ~40-Felder-Snapshot als Qt-Signal, auch wenn sich nichts geändert hatte. Bei 13 Drohnen: 130 Signals/s × 40 Felder = ~5200 unnötige Vergleiche + Signal-Dispatches.

**Fix:**

```python
def _poll(self) -> None:
    if not (self._drone and self._drone.connected):
        return
    snap = self._drone.telemetry.snapshot()
    if snap != self._last_snap:          # ← nur bei Änderung
        self._last_snap = snap
        self._safe_emit(self.telemetry_updated, snap)
    self._safe_emit(self.state_changed, snap.get("flight_mode", "UNKNOWN"))
```

`state_changed` wird weiterhin bei jedem Tick emittiert (billiger String-Vergleich in QML).

**Wirkung:** Bei ruhendem Schwarm (typischer Idle-Betrieb) near-zero unnötige Qt-Signal-Dispatches.

---

### V13 — SwarmContext Boids: Echte Reynolds-Implementierung in NED-Metern

**Datei:** `tools/ui/context/swarm_context.py`  
**Commit:** `3f899c5`

**Problem:** Die Boids-Implementierung hatte zwei kritische Fehler:
1. GPS-Koordinaten (Grad) wurden als Meter verwendet — physikalisch falsch
2. `send_velocity()` wurde aufgerufen, existiert aber nicht auf dem Backend

**Fix:** Vollständige Reynolds-Boids-Implementierung in lokalen NED-Metern:

```
Für jede Drohne pro Tick:
1. GPS → NED (Zentroid als Referenz)
2. Separation:  weg von Nachbarn < Wahrnehmungsradius
3. Alignment:   Geschwindigkeit der Nachbarn nachahmen (NED vx/vy)
4. Cohesion:    hin zur Mitte der Nachbarn
5. Gewichtete Summe der drei Kräfte
6. Speed-Clamping auf max. 3 m/s
7. Target = aktuelle_position + velocity × dt
8. GPS-Rückrechnung: NED → Lat/Lon via Referenzpunkt
9. backend.goto(tgt_lat, tgt_lon, alt)
```

---

### V14 — Updater: SHA256-Checksum-Verifikation

**Datei:** `tools/ui/updater.py`  
**Commit:** `3f899c5`

**Problem:** Der heruntergeladene Installer wurde ohne Integritätsprüfung direkt ausgeführt.

**Implementierung:**
- `_CheckWorker` sucht nach einem `.sha256`-Asset im GitHub Release (z.B. `uavresearch-gcs-setup-1.2.3.sha256`)
- Falls vorhanden: SHA256-URL wird zusammen mit der Installer-URL weitergegeben
- `_DownloadWorker` lädt zuerst den Installer, dann die `.sha256`-Datei
- Verifikation via `hashlib.sha256()` mit 64KB-Chunks
- Bei Mismatch: Installer wird gelöscht, State → `"error"`, Fehlermeldung angezeigt
- Kein SHA256-Asset vorhanden: wird ohne Prüfung fortgefahren (rückwärtskompatibel)

```python
def _verify_sha256(self, file_path: str, expected_sha256: str) -> bool:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    actual   = sha.hexdigest().lower()
    expected = expected_sha256.strip().lower().split()[0]
    return actual == expected
```

---

## 6. Verbesserungen — Infrastruktur

---

### V15 — Docker: Health Checks für alle Services

**Datei:** `docker/docker-compose.yml`  
**Commit:** `3f899c5`

Alle drei Services (`gcs`, `uav_generic`, `uav_observation`) bekamen identische Health Checks:

```yaml
healthcheck:
  test: ["CMD", "python", "-c",
    "import urllib.request; urllib.request.urlopen('http://localhost:8080/health', timeout=3)"]
  interval:     30s
  timeout:       5s
  retries:         3
  start_period:  20s
```

Docker Compose markiert Container jetzt als `healthy`/`unhealthy`. Automatischer Neustart bei anhaltend unhealthy Container via `restart: unless-stopped`.

---

## 7. Neue Regressionstests

> **Commit:** `43dadb7`  
> **6 neue Testdateien, +21 neue Tests**

---

### `tests/test_goto_cmd.py` (3 Tests)

Prüft Bug-Fix #1 (goto-Kommando):

| Test | Was geprüft wird |
|------|-----------------|
| `test_goto_uses_set_position_target_global_int` | `set_position_target_global_int_send` wird aufgerufen, `mission_item_send` nicht |
| `test_goto_encodes_lat_lon_correctly` | lat/lon korrekt als `int32(deg × 1e7)` kodiert |
| `test_goto_uses_relative_alt_frame` | Frame = 6 (`MAV_FRAME_GLOBAL_RELATIVE_ALT`) |

---

### `tests/test_swarm_formation_offby1.py` (5 Tests)

Prüft Bug-Fix #2 (Formation Off-by-One), parametrisiert über verschiedene Leader-Positionen:

| Parameterset | Leader-Index | Drohnen |
|---|---|---|
| `[0-4]` | 0 (erster) | 4 |
| `[1-4]` | 1 (Mitte) | 4 |
| `[3-4]` | 3 (letzter) | 4 |
| `[0-2]` | 0 | 2 (minimal) |
| `[0-6]` | 0 | 6 (größerer Schwarm) |

Prüft: Alle Follower erhalten genau einen `goto()`-Aufruf. Alle Zielkoordinaten sind mindestens 1m vom Leader entfernt. Alle Follower-Ziele sind paarweise verschieden.

---

### `tests/test_reconnect_fsm.py` (4 Tests)

Prüft Bug-Fix #4 (FSM-Reconnect):

| Test | Szenario |
|------|----------|
| `test_armed_drone_on_reconnect_advances_to_armed` | armed=True, alt=0 → FSM: IDLE → ARMED |
| `test_airborne_drone_on_reconnect_advances_to_flying` | armed=True, alt=15m → FSM: IDLE → FLYING |
| `test_mode_change_on_already_flying_advances_fsm` | GUIDED + armed + alt=10m → FSM: IDLE → FLYING |
| `test_normal_disarm_resets_to_idle` | LANDING + alt<1m → FSM: LANDING → IDLE |

---

### `tests/test_frontier_ned.py` (4 Tests)

Prüft Bug-Fix #3 (GPS→NED-Konversion):

| Test | Was geprüft wird |
|------|-----------------|
| `test_origin_maps_to_zero` | Referenzpunkt → (0, 0) |
| `test_100m_north` | +100m Nord → north≈100m, east≈0m |
| `test_100m_east` | +100m Ost → north≈0m, east≈100m |
| `test_gps_degrees_not_used_as_metres` | 10m-Versatz liefert ~10m, nicht ~0.00009° |

---

### `tests/test_metrics_position_error.py` (3 Tests)

Prüft Verbesserung V6 (position_error-Metrik):

| Test | Ergebnis |
|------|----------|
| Leerer Pfad | Kein `position_error_rms_m` in Summary |
| Drohne auf dem Pfad | `position_error_rms_m` < 1m |
| Drohne 100m neben Pfad | `position_error_rms_m` > 50m |

---

### `tests/test_logger_jsonl.py` (2 Tests)

Prüft Verbesserung V8 (JSONL-Events):

| Test | Was geprüft wird |
|------|-----------------|
| `test_events_written_immediately_as_jsonl` | JSONL-Datei existiert vor `stop()`, hat 2 Zeilen |
| `test_each_line_is_valid_json` | 5 Events → 5 valide JSON-Zeilen, alle mit `event` + `timestamp` |

---

## 8. Geänderte Dateien — Vollständige Liste

| Datei | Art | Änderungen |
|-------|-----|-----------|
| `droneresearch/core/connection.py` | Bug-Fix + Feature | goto()-Kommando, Reconnect-Loop, Input-Validierung |
| `droneresearch/control/mission.py` | Feature | Hybrid Mission-Upload-Handshake |
| `droneresearch/control/script_runner.py` | Feature | Subprocess-Sandbox-Option |
| `droneresearch/data/logger.py` | Feature | Periodischer CSV-Flush, JSONL-Events |
| `droneresearch/data/store.py` | Feature | SQLite-Persistenz-Option |
| `droneresearch/experiment/metrics.py` | Feature | `position_error` RMS/Max-Metrik |
| `droneresearch/exploration/frontier_bridge.py` | Bug-Fix | GPS→NED-Koordinatenkonvertierung |
| `droneresearch/models/generic_uav.py` | Bug-Fix | FSM-Sync nach Reconnect |
| `droneresearch/sdk/drone.py` | Feature | PX4-kompatibler Takeoff/Goto-Modus |
| `droneresearch/sdk/swarm_api.py` | Bug-Fix + Feature | Formation Off-by-One, Follow-Loop |
| `droneresearch/simulation/sitl.py` | Feature | Paralleler Cluster-Start |
| `docker/docker-compose.yml` | Feature | Health Checks für alle 3 Services |
| `tools/ui/backend.py` | Feature | Differenz-basierte Telemetrie-Emission |
| `tools/ui/context/swarm_context.py` | Feature | Echte Reynolds-Boids in NED-Metern |
| `tools/ui/updater.py` | Feature | SHA256-Checksum-Verifikation |
| `tests/test_goto_cmd.py` | Test (neu) | 3 Regressionstests für goto()-Fix |
| `tests/test_swarm_formation_offby1.py` | Test (neu) | 5 Regressionstests für Formation-Fix |
| `tests/test_reconnect_fsm.py` | Test (neu) | 4 Regressionstests für FSM-Reconnect |
| `tests/test_frontier_ned.py` | Test (neu) | 4 Regressionstests für NED-Konvertierung |
| `tests/test_metrics_position_error.py` | Test (neu) | 3 Tests für neue Metrik |
| `tests/test_logger_jsonl.py` | Test (neu) | 2 Tests für JSONL-Logging |

**Gesamt: 21 Dateien, +2.146 / −615 Zeilen**

---

## 9. Test-Ergebnis

```
Platform: win32, Python 3.14.5, pytest 9.0.3
Collected: 138 tests

134 passed
  4 skipped  (rclpy nicht installiert — ROS2-Tests)
  0 failed
  0 errors

Laufzeit: 8.02s
```

Übersprungene Tests:
- `test_ros_context.py::TestRefcountSemantics::test_acquire_increments`
- `test_ros_context.py::TestRefcountSemantics::test_multiple_acquires_stack`
- `test_ros_context.py::TestRefcountSemantics::test_release_decrements`
- `test_ros_context.py::TestThreadSafety::test_balanced_concurrent_calls_end_at_zero`

Diese sind mit `# rclpy not installed` markiert und werden auf einem System mit ROS2-Installation automatisch aktiv.

---

## 10. Commit-Historie

```
43dadb7  test: regression tests for 4 fixed bugs + script sandbox + SQLite store
3f899c5  feat: UI improvements - diff-emit, boids NED, SHA256 verify, docker healthchecks
1beaa52  feat: core - reconnect backoff, connection validation, hybrid mission upload, parallel SITL
5df0c56  feat: SDK improvements - PX4 takeoff, swarm follow loop, position_error metric, logger flush+JSONL
751ae02  fix: four bugs found in deep analysis

─── Basis (ui-dashboard) ────────────────────────────────────────────────────
d59d681  ci: trigger build
```

---

## Kurzübersicht

| Kategorie | Anzahl | Details |
|-----------|--------|---------|
| Bug-Fixes | 4 | goto(), Formation Off-by-One, NED-Konvertierung, FSM-Reconnect |
| Core-SDK-Verbesserungen | 11 | Reconnect, Validierung, Mission-Handshake, PX4-Takeoff, Follow-Loop, Metrik, Flush, JSONL, SQLite, SITL-parallel, Sandbox |
| UI-Verbesserungen | 3 | Diff-Emit, Boids NED, SHA256 |
| Infrastruktur | 1 | Docker Health Checks |
| Neue Tests | 21 | 6 neue Testdateien mit 21 Testfällen |
| Geänderte Dateien | 21 | 15 Quelldateien + 6 neue Testdateien |
| Zeilen | +2.146 / −615 | Netto +1.531 Zeilen |
| Tests gesamt | 134 / 138 | 134 passed, 4 skipped (rclpy) |

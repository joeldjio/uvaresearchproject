# uavresearch gcs – Vollständige technische Analyse

> Detaillierte Beschreibung der Anwendung basierend auf vollständiger Code-Analyse  
> Stand: 2026-06-08  
> Autor: Technische Dokumentation nach Code-Review

---

## 🎯 Was ist uavresearch gcs?

**uavresearch gcs** ist eine **professionelle Ground Control Station für Drohnen-Schwärme**, die wissenschaftliche Forschung mit kommerzieller Software verbindet. Die Anwendung kombiniert:

1. **DroneResearch Backend** (Python) – Wissenschaftliches Framework für UAV-Forschung
2. **PyQt6/QML Frontend** – Moderne Desktop-UI mit Echtzeit-Visualisierung
3. **Kommerzielle Distribution** – Windows/Linux/macOS Installer mit Lizenzierung

---

## 🏗️ Vollständige Architektur

### Layer 1: Hardware-Abstraktion

```
ArduPilot/PX4 Flight Controller
    ↓ MAVLink / uXRCE-DDS
droneresearch.core.connection.MAVLinkConnection
    ├─ Heartbeat-Loop (1 Hz)
    ├─ Telemetry-Polling (10 Hz)
    └─ Command-Dispatch (ARM/DISARM/TAKEOFF/LAND/RTL/GOTO)
```

**Verbindungstypen**:
- Serial: `COM3:57600`, `/dev/ttyUSB0:57600`
- TCP: `tcp:127.0.0.1:5762` (ArduCopter SITL)
- UDP: `udp:127.0.0.1:14550` (PX4 SITL)

### Layer 2: SDK & Models

```
droneresearch.sdk.drone.Drone (Basis-API)
    ├─ connect() / disconnect()
    ├─ arm() / disarm() / takeoff() / land() / rtl()
    ├─ goto(lat, lon, alt)
    ├─ Event-System: on("altitude", callback)
    └─ TelemetryState (lat, lon, alt, armed, mode, battery, etc.)

droneresearch.models.GenericUAVModel (FSM-erweitert)
    ├─ StateMachine (10 Zustände)
    ├─ Swarm-Rollen: none/leader/follower/coordinator
    ├─ Formation-Offsets (north, east, alt in NED)
    └─ start() / stop() (FSM-gesteuert)

droneresearch.models.ObservationUAVModel (Gimbal-erweitert)
    ├─ gimbal_point(pitch, roll, yaw)
    ├─ gimbal_home()
    ├─ track_target(lat, lon)
    └─ start_stream(url)

droneresearch.models.CoordinatorUAVModel (Schwarm-Manager)
    ├─ register(drone_id, uav_model)
    ├─ set_leader(drone_id)
    ├─ set_formation("line"/"v"/"grid"/"circle"/"wedge", spacing)
    ├─ takeoff_all() / land_all() / rtl_all()
    └─ start_formation_follow() (20 Hz Loop)
```

### Layer 3: Sicherheitssysteme

```
droneresearch.safety.apf.APFSafetyFilter (20 Hz)
    ├─ Kollisionsvermeidung (min_separation: 2-5m)
    ├─ Geofencing (horizontal + vertikal)
    ├─ Kinematische Limits (max_speed: 3-5 m/s)
    ├─ Repulsion/Attraction Gains
    └─ filter(positions, desired) → safe_positions

Pose3D (x=North, y=East, z=altitude_above_ground)
    ├─ dist() / dist_2d()
    ├─ normalized() / clamp()
    └─ Operatoren: +, *, norm()
```

**APF-Algorithmus**:
```python
for each drone pair (i, j):
    distance = positions[i].dist(positions[j])
    if distance < min_separation:
        repulsion_force = (min_separation - distance) * repulsion_gain
        direction = (positions[i] - positions[j]).normalized()
        positions[i] += direction * repulsion_force

for each drone:
    attraction_force = (desired[i] - positions[i]) * attraction_gain
    positions[i] += attraction_force
    positions[i] = positions[i].clamp(max_speed)
    positions[i] = geofence.clip(positions[i])
```

### Layer 4: ROS2-Integration

```
droneresearch.ros.px4_bridge.PX4ROS2Bridge
    ├─ uXRCE-DDS (NICHT MAVLink-over-ROS)
    ├─ Frame-Konvertierung: NED ↔ ENU, FRD ↔ FLU
    ├─ Multi-Vehicle Namespaces (/uav_1/fmu/out/*, /uav_1/fmu/in/*)
    ├─ Offboard Mode (Position/Velocity Setpoints)
    └─ Vehicle Commands (ARM/DISARM/TAKEOFF/LAND/RTL)
```

**Topics**:
- ← `/fmu/out/vehicle_attitude` (Quaternion → Roll/Pitch/Yaw)
- ← `/fmu/out/vehicle_global_position` (GPS)
- ← `/fmu/out/vehicle_local_position` (NED)
- ← `/fmu/out/vehicle_status` (Armed, Nav State)
- ← `/fmu/out/battery_status`
- → `/fmu/in/vehicle_command`
- → `/fmu/in/offboard_control_mode`
- → `/fmu/in/trajectory_setpoint`

### Layer 5: UI Backend Bridge

```
tools.ui.backend.DroneBackend (pro Drohne)
    ├─ Lazy SDK-Import (erst bei connect())
    ├─ Telemetry-Polling (10 Hz) → pyqtSignal
    ├─ FSM-Transition-Callbacks → pyqtSignal
    ├─ Command-Wrapper (arm/disarm/takeoff/land/rtl/goto)
    ├─ Gimbal-Wrapper (nur ObservationUAV)
    └─ Swarm-Rollen (set_swarm_role, set_formation_offset)

tools.ui.backend.SwarmBackend (Flotten-Manager)
    ├─ add_drone(id, conn, type) → DroneBackend
    ├─ Aggregation (5 Hz) → swarm_telemetry_updated
    ├─ Bulk-Commands (arm_all, takeoff_all, land_all, rtl_all)
    └─ Signal-Forwarding (log_message, fsm_state_changed)
```

### Layer 6: QML Context-Objekte

```
tools.ui.context.swarm_context.SwarmContext
    ├─ @pyqtSlot-Wrapper für QML
    ├─ Mission-Management (runMission, cancelMission)
    ├─ Swarm-Algorithmen (Boids, Leader-Follower, Consensus, Behavior Trees)
    ├─ Formation-Berechnung (_formation_offsets, _calculate_formation_positions)
    └─ Signale: droneAdded, telemetryUpdated, fsmStateChanged, missionFinished
```

**Weitere Contexts**:
- `SafetyContext` – APF-Konfiguration
- `ROS2Context` – Bridge-Management
- `ExperimentContext` – Szenario-Runner
- `TelemetryModel` – ListModel für QML

### Layer 7: QML Frontend

```
tools/ui/qml/main.qml (Root Window)
    ├─ Tab-System (10 Tabs)
    ├─ Header (52px): Verbindung, Drone-Badges, Uhr, Emergency Stop
    ├─ InstrBar (110px): Artificial Horizon, Kompass, Quick Commands
    ├─ NavBar (70px): Icon-Seitenleiste
    └─ StatusBar (28px)
```

**Panels** (`tools/ui/qml/panels/`):
- `DashboardPanel` – FSM-State, KPIs, Batterie, GPS
- `SwarmPanel` – Drohnen hinzufügen, Waypoints, Rollen, Formation
- `SafetyPanel` – APF-Konfiguration, Geofence, Violations-Log
- `GimbalPanel` – Pitch/Roll/Yaw Slider, Presets
- `ROS2Panel` – Bridge-Status, Offboard Mode, uORB Topics
- `ExperimentPanel` – Python-Script / JSON-Szenario
- `FlightLogPanel` – CSV-Charts (Höhe, Geschwindigkeit, Batterie)
- `LogPanel` – Echtzeit-Log mit Filter
- `HelpPanel` – Feature-Übersicht, Updates, Lizenz

**MapView** (`tools/ui/qml/MapView.qml`):
- Leaflet.js (QtWebEngine)
- Drone-Marker mit Heading-Pfeil
- Waypoint-Pick-Modus
- HUD-Overlay (Attitude)

---

## 🔧 Kernfunktionen im Detail

### 1. FSM State Machine (10 Zustände)

```
IDLE ──arm()──→ ARMING ──ok──→ ARMED ──takeoff()──→ TAKEOFF ──ok──→ FLYING
                   │                                    │
                 [fail]                              [fail]
                   ↓                                    ↓
                 IDLE                              EMERGENCY

FLYING ──mission()──→ MISSION ──done──→ FLYING
       ──rtl()─────→ RTL ──landed──→ IDLE
       ──land()────→ LANDING ──landed──→ IDLE
       ──emergency()→ EMERGENCY

Any State ──emergency()──→ EMERGENCY ──reset──→ IDLE
```

**Implementierung**: `droneresearch/core/fsm.py`

**Airborne States**: `TAKEOFF`, `FLYING`, `MISSION`, `RTL`, `LANDING`  
**Safe States**: `IDLE`, `ARMED`

**Thread-Safety**: Alle Transitionen sind durch `threading.Lock()` geschützt

**Callbacks**:
```python
fsm.on_transition(lambda old, new: print(f"{old.name} → {new.name}"))
fsm.on_rejection(lambda cur, req: print(f"Rejected: {cur} → {req}"))
```

### 2. Swarm-Algorithmen (SwarmContext)

#### Boids (Reynolds-Regeln)
- **Separation**: Abstoßung bei zu geringer Distanz
- **Alignment**: Geschwindigkeits-Angleichung
- **Cohesion**: Anziehung zum Schwarm-Zentrum
- **Perception Radius**: 10-50m
- **Update Rate**: 5-20 Hz

**Implementierung**: `tools/ui/context/swarm_context.py:_update_boids()`

#### Leader-Follower
- **Formation Types**: `line`, `v`, `grid`, `circle`, `wedge`
- **Follow Distance**: 3-10m
- **Formation Size**: 2-20 Drohnen
- **Offsets**: NED (North, East, Alt)

**Implementierung**: `tools/ui/context/swarm_context.py:_update_leader_follower()`

**Formation-Offsets** (Beispiel V-Formation, 3 Drohnen, 5m Spacing):
```python
Leader:    (0.0,  0.0, 0.0)
Follower1: (-5.0, -5.0, 0.0)  # hinten links
Follower2: (-5.0,  5.0, 0.0)  # hinten rechts
```

#### Consensus (Byzantine Fault Tolerance)
- **Algorithmen**: `majority_vote`, `weighted_average`, `median`
- **Byzantine Tolerance**: 0-33%
- **Consensus State**: `voting`/`reached`/`failed`

**Implementierung**: `tools/ui/context/swarm_context.py:startConsensusVote()`

#### Behavior Trees
- **Mission Types**: `patrol`, `search`, `escort`, `formation`
- **Priority**: `low`/`medium`/`high`/`critical`
- **Status**: `idle`/`running`/`success`/`failure`

**Implementierung**: `tools/ui/context/swarm_context.py:executeBehaviorTreeMission()`

### 3. Mission-System

**Waypoint-Format**:
```json
[
  {"lat": 48.137, "lon": 11.575, "alt": 10},
  {"lat": 48.138, "lon": 11.576, "alt": 15}
]
```

**Mission-Ablauf**:
1. `runMission(drone_id, json)` → Thread-Start
2. FSM: `FLYING` → `MISSION`
3. Waypoint-Upload (MAVLink `MISSION_COUNT`/`MISSION_ITEM`)
4. Mission-Start (MAVLink `MISSION_START`)
5. Monitoring (`MISSION_CURRENT`, `MISSION_ITEM_REACHED`)
6. FSM: `MISSION` → `FLYING` (bei Completion)

**Multi-Drone-Mission**:
- `runMissionMulti(drone_ids_json, waypoints_json)`
- Lane-Offset pro Drohne (±5m lateral)
- Parallele Ausführung
- Individuelle Cancellation

**Implementierung**: `tools/ui/context/swarm_context.py:runMission()`, `runMissionMulti()`

### 4. APF Safety Filter (20 Hz)

**Parameter**:
- `min_separation`: 2.0-5.0m
- `max_speed`: 3.0-5.0 m/s
- `repulsion_gain`: 2.0-5.0
- `attraction_gain`: 0.5-2.0
- `geofence_radius`: 50-500m
- `geofence_alt`: (1.0, 30.0) m

**Implementierung**: `droneresearch/safety/apf.py:APFSafetyFilter`

**Verwendung**:
```python
from droneresearch.safety import APFSafetyFilter, Pose3D

apf = APFSafetyFilter(min_separation=3.0, max_speed=5.0)
positions = {"D1": Pose3D(0, 0, 10), "D2": Pose3D(1.5, 0, 10)}
desired = {"D1": Pose3D(0, 5, 10), "D2": Pose3D(3, 5, 10)}
safe = apf.filter(positions, desired)
```

### 5. Lizenzierung & Updates

#### Trial-System
- **Dauer**: 30 Tage ab erstem Start
- **State**: `%LOCALAPPDATA%\UAVResearch\uavresearch gcs\license.json`
- **Overlay**: `LicenseOverlay.qml` nach Ablauf

**Implementierung**: `tools/ui/license.py:LicenseManager`

#### License-Key-Format
```
UAVGCS-XXXX-XXXX-XXXX-YYYYMMDD
       └─12 Zeichen─┘ └─Expiry─┘
       base32(HMAC-SHA256(SECRET, "v1|YYYYMMDD"))
```

**Generierung**:
```bash
python tools/installer/gen_license.py --days 365 --customer "Acme Drones"
```

**Validierung**: Komplett offline, kein Server erforderlich

#### In-App-Updater
1. GET `https://api.github.com/repos/joeldjio/rz-gcs-releases/releases/latest`
2. Vergleich Tag-Version mit `tools/ui/_version.py:VERSION`
3. Asset-Suche: `uavresearch-gcs-setup-*.exe`
4. SHA256-Checksum-Verifikation
5. Silent Install: `/SILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS`

**Implementierung**: `tools/ui/updater.py:UpdaterContext`

---

## 📊 Datenfluss (Echtzeit)

```
Flight Controller (10 Hz MAVLink)
    ↓
MAVLinkConnection._poll_telemetry()
    ↓
TelemetryState.update(msg)
    ↓
Drone.on("telemetry", callback)
    ↓
DroneBackend._poll() (10 Hz)
    ↓ pyqtSignal
SwarmBackend._aggregate() (5 Hz)
    ↓ pyqtSignal
SwarmContext._on_telemetry()
    ↓ pyqtSignal
QML telemetryUpdated
    ↓
InstrBar / Dashboard / MapView (UI-Update)
```

**Polling-Raten**:
- MAVLink Heartbeat: 1 Hz
- Telemetry-Polling: 10 Hz (DroneBackend)
- Swarm-Aggregation: 5 Hz (SwarmBackend)
- APF Filter: 20 Hz (APFFilterLoop)
- Swarm-Algorithmen: 5-20 Hz (konfigurierbar)

---

## 🚀 Build & Distribution

### Build-Pipeline

**Schritte**:
1. `python tools/installer/icon/make_assets.py` (Branding)
2. `pyinstaller tools/installer/specs/uavresearch_gcs.spec` (Bundle)
3. `ISCC tools/installer/inno/uavresearch_gcs.iss` (Installer)
4. SHA256-Checksum
5. GitHub Release Upload

**Build-Zeit**: 4-8 Minuten (LZMA2 ultra64 Kompression)

### CI/CD (GitHub Actions)

**Workflow**: `.github/workflows/build-uavresearch-gcs.yml`

**Trigger**:
- Push `v*` Tag (z.B. `v0.3.2`)
- Manual Dispatch mit `publish = true`

**Matrix**:
- Windows (windows-latest)
- Linux (ubuntu-22.04)
- macOS (macos-latest)

**Output**:
- `uavresearch-gcs-setup-X.Y.Z.exe` + `.sha256`
- `uavresearch-gcs_X.Y.Z_amd64_jammy.deb` + `.sha256`
- `uavresearch-gcs-macos.tar.gz` + `.sha256`

**Publish**: `joeldjio/rz-gcs-releases` (öffentliches Repo)

### Installer-Features

**Windows (Inno Setup)**:
- LZMA2 ultra64 Kompression (~450 MB)
- Per-User Install (kein Admin erforderlich)
- Desktop-Shortcut
- Start-Menu-Gruppe
- In-Place-Upgrade (GUID-stabil)
- Clean Uninstall

**Linux (Debian Package)**:
- Installation: `/opt/uavresearch-gcs`
- Launcher: `uavresearch-gcs`
- Desktop Entry: `uavresearch-gcs.desktop`
- Icon: `/usr/share/icons/hicolor/256x256/apps/`

---

## 🔑 Wichtige Code-Pfade

### Backend (Python)

| Komponente | Pfad |
|------------|------|
| Drone SDK | `droneresearch/sdk/drone.py` |
| GenericUAV | `droneresearch/models/generic_uav.py` |
| ObservationUAV | `droneresearch/models/observation_uav.py` |
| CoordinatorUAV | `droneresearch/models/coordinator_uav.py` |
| FSM | `droneresearch/core/fsm.py` |
| MAVLink Connection | `droneresearch/core/connection.py` |
| Telemetry | `droneresearch/core/telemetry.py` |
| APF Filter | `droneresearch/safety/apf.py` |
| PX4 ROS2 Bridge | `droneresearch/ros/px4_bridge.py` |
| Mission Engine | `droneresearch/control/mission.py` |

### Frontend (PyQt6/QML)

| Komponente | Pfad |
|------------|------|
| App Entry | `tools/ui/app.py` |
| Backend Bridge | `tools/ui/backend.py` |
| SwarmContext | `tools/ui/context/swarm_context.py` |
| SafetyContext | `tools/ui/context/safety_context.py` |
| ROS2Context | `tools/ui/context/ros2_context.py` |
| Main Window | `tools/ui/qml/main.qml` |
| Dashboard Panel | `tools/ui/qml/panels/DashboardPanel.qml` |
| Swarm Panel | `tools/ui/qml/panels/SwarmPanel.qml` |
| Map View | `tools/ui/qml/MapView.qml` |
| License Manager | `tools/ui/license.py` |
| Updater | `tools/ui/updater.py` |

### Build & Distribution

| Komponente | Pfad |
|------------|------|
| Build Script (Windows) | `tools/installer/build.ps1` |
| Build Script (Linux) | `tools/installer/build_linux_deb.sh` |
| PyInstaller Spec (GCS) | `tools/installer/specs/uavresearch_gcs.spec` |
| Inno Setup Script | `tools/installer/inno/uavresearch_gcs.iss` |
| License Generator | `tools/installer/gen_license.py` |
| Version Bumper | `tools/installer/bump_version.py` |
| CI Workflow | `.github/workflows/build-uavresearch-gcs.yml` |

---

## 📚 Dokumentation

| Dokument | Pfad |
|----------|------|
| Projekt-Übersicht | `docs/project/overview.md` |
| UI-Dokumentation | `docs/ui/ui-documentation.md` |
| Installer-Pipeline | `docs/build/installer-pipeline.md` |
| CI-Workflow | `docs/build/ci-workflow.md` |
| Release-Checklist | `docs/release/checklist.md` |
| Release-Repo | `docs/release/releases-repo.md` |
| Installation | `docs/setup/installation.md` |
| PX4 SITL Setup | `docs/setup/px4-sitl.md` |
| Raspberry Pi | `docs/setup/raspberry-pi.md` |

---

## 🎯 Zusammenfassung

**uavresearch gcs** ist eine **vollständige Drohnen-Schwarm-GCS** mit:

✅ **Multi-Drohnen-Management** (Generic/Observation UAV)  
✅ **FSM State Machine** (10 Zustände, Thread-safe)  
✅ **Swarm-Algorithmen** (Boids, Leader-Follower, Consensus, Behavior Trees)  
✅ **APF Safety Filter** (20 Hz Kollisionsvermeidung)  
✅ **ROS2-Integration** (PX4 uXRCE-DDS, Offboard Mode)  
✅ **Mission-System** (Waypoint-Upload, Multi-Drone)  
✅ **Echtzeit-UI** (PyQt6/QML, 10 Tabs, Artificial Horizon, Leaflet-Karte)  
✅ **Lizenzierung** (30-Tage-Trial, Offline-Keys)  
✅ **Auto-Updates** (GitHub Releases, SHA256-Verifikation)  
✅ **Cross-Platform** (Windows/Linux/macOS Installer)

Die Anwendung verbindet wissenschaftliche Forschung (DroneResearch SDK) mit professioneller GCS-Software und ist bereit für kommerzielle Distribution.

---

## 📈 Technische Metriken

- **Codebase**: ~15.000 Zeilen Python + ~8.000 Zeilen QML
- **Test-Suite**: 172 Tests (hardware-frei, ~1s Laufzeit)
- **Build-Zeit**: 4-8 Minuten (LZMA2 Kompression)
- **Installer-Größe**: ~450 MB (PyQt6 + WebEngine + SDK)
- **RAM-Nutzung**: ~150-300 MB (abhängig von Drohnen-Anzahl)
- **Telemetrie-Rate**: 10 Hz (pro Drohne)
- **UI-Update-Rate**: 5 Hz (Swarm-Aggregation)
- **APF-Filter-Rate**: 20 Hz
- **Swarm-Algorithmen-Rate**: 5-20 Hz (konfigurierbar)

---

**Erstellt**: 2026-06-08  
**Basierend auf**: Vollständige Code-Analyse aller Frontend- und Backend-Komponenten
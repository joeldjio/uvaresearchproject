# PX4 Mission Status Monitoring

**Feature 2** der PX4-Optimierungen: Echtzeit-Überwachung von Mission-Status über uXRCE-DDS.

## Überblick

Das Mission-Status-Monitoring erweitert die Mission-Upload-Funktionalität um Echtzeit-Feedback:
- **Live-Status**: Aktuelle Mission-Phase (aktiv, abgeschlossen, fehlgeschlagen)
- **Fortschritt**: Aktueller Waypoint und Gesamtzahl
- **Callbacks**: Event-basierte Benachrichtigungen bei Status-Änderungen
- **UI-Integration**: Visuelles Feedback im ROS2 Panel

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                      ROS2 Panel (QML)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Mission Management                                   │   │
│  │  • Status Indicator (Green/Red/Gray)                 │   │
│  │  • Progress Bar (WP 2/5)                             │   │
│  │  • Control Buttons (START/PAUSE/CLEAR)               │   │
│  │  • Upload Dialog                                     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↕ Qt Slots/Signals
┌─────────────────────────────────────────────────────────────┐
│                    ROS2Context (Python)                     │
│  • getMissionStatus(drone_id) → dict                        │
│  • getMissionWaypoints(drone_id) → list                     │
│  • missionStatusChanged signal                              │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                   PX4ROS2Bridge (Python)                    │
│  • get_mission_status() → dict                              │
│  • get_mission_waypoints() → list                           │
│  • on_mission_status(callback)                              │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                PX4MissionUploader (Python)                  │
│  • Subscribes to /fmu/out/mission_result                    │
│  • Tracks: current_seq, total_count, finished, failure      │
│  • Stores uploaded waypoints                                │
│  • Triggers callbacks on status change                      │
└─────────────────────────────────────────────────────────────┘
                            ↕ uXRCE-DDS
┌─────────────────────────────────────────────────────────────┐
│                      PX4 Autopilot                          │
│  • Publishes MissionResult messages                         │
│  • Updates current waypoint during mission                  │
└─────────────────────────────────────────────────────────────┘
```

## Backend API

### PX4MissionUploader

```python
from droneresearch.ros.px4_mission import PX4MissionUploader

uploader = PX4MissionUploader(namespace="px4_1")

# Get current status
status = uploader.get_mission_status()
# Returns: {
#     "current_seq": 2,
#     "total_count": 5,
#     "finished": False,
#     "failure": False,
#     "active": True
# }

# Get uploaded waypoints
waypoints = uploader.get_mission_waypoints()
# Returns: [
#     {"lat": 47.397742, "lon": 8.545594, "alt": 15.0, "hold_time": 2.0},
#     {"lat": 47.397842, "lon": 8.545694, "alt": 20.0, "hold_time": 3.0},
#     ...
# ]

# Register callback for status changes
def on_status_change(status_dict):
    print(f"Mission status: WP {status_dict['current_seq']}/{status_dict['total_count']}")
    if status_dict['finished']:
        print("Mission complete!")

uploader.on_mission_status(on_status_change)
```

### PX4ROS2Bridge

```python
from droneresearch.ros.px4_bridge import PX4ROS2Bridge

bridge = PX4ROS2Bridge(namespace="px4_1")
bridge.start()

# Get mission status
status = bridge.get_mission_status()

# Get waypoints
waypoints = bridge.get_mission_waypoints()

# Register callback
bridge.on_mission_status(lambda s: print(f"Status: {s}"))
```

## UI Verwendung

### 1. ROS2 Panel öffnen
- Starte die UI: `python -m tools.ui`
- Navigiere zum **ROS2 Panel**
- Wähle Drohne aus Dropdown (z.B. `px4_1`)

### 2. Mission hochladen
- Klicke **⬆ UPLOAD MISSION**
- Im Dialog: **Upload Test Mission** (3 Waypoints, Zurich-Gebiet)
- Status zeigt "No Mission" → Upload bestätigt

### 3. Mission starten
- **ARM** Drohne (Vehicle Commands)
- **TAKEOFF** auf 10m
- Warte bis Takeoff abgeschlossen
- Klicke **▶ START** (Mission Management)

### 4. Status beobachten
- **Status-Indikator**:
  - 🟢 Pulsierend = Mission aktiv
  - 🟢 Solid = Mission abgeschlossen
  - 🔴 = Mission fehlgeschlagen
  - ⚪ = Keine Mission
- **Progress Bar**: Zeigt `WP 2/3` (aktueller/gesamt)
- Updates alle 500ms automatisch

### 5. Mission-Kontrolle
- **⏸ PAUSE**: Mission pausieren
- **▶ START**: Fortsetzen
- **✕ CLEAR**: Mission löschen

## Test-Workflow

### Automatischer Test mit UI
```bash
# Startet SITL + Gazebo + UI
python examples/test_mission_ui.py
```

Folge den Anweisungen im Terminal für interaktiven Test.

### Manueller Test
```bash
# Terminal 1: SITL starten
cd ~/PX4-Autopilot
make px4_sitl gz_x500

# Terminal 2: uXRCE-DDS Agent
MicroXRCEAgent udp4 -p 8888

# Terminal 3: UI starten
python -m tools.ui
```

## Status-Felder

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `current_seq` | int | Aktueller Waypoint-Index (0-basiert) |
| `total_count` | int | Gesamtzahl Waypoints |
| `finished` | bool | Mission erfolgreich abgeschlossen |
| `failure` | bool | Mission fehlgeschlagen |
| `active` | bool | Mission läuft gerade |

**Berechnung `active`:**
```python
active = (total_count > 0) and not finished and not failure
```

## Callback-System

Callbacks werden bei **jeder** `MissionResult`-Nachricht getriggert:
- Waypoint-Wechsel
- Mission-Start
- Mission-Ende (finished/failure)

```python
def my_callback(status):
    if status['finished']:
        print("✅ Mission complete!")
    elif status['failure']:
        print("❌ Mission failed!")
    else:
        progress = (status['current_seq'] / status['total_count']) * 100
        print(f"📍 Progress: {progress:.1f}%")

bridge.on_mission_status(my_callback)
```

## Troubleshooting

### Status bleibt bei "No Mission"
- **Ursache**: Mission nicht hochgeladen oder gelöscht
- **Lösung**: Upload erneut durchführen

### Progress Bar bewegt sich nicht
- **Ursache**: Mission nicht gestartet (nur hochgeladen)
- **Lösung**: ARM + TAKEOFF, dann START klicken

### Status zeigt "Mission Failed"
- **Ursache**: PX4 konnte Waypoint nicht erreichen (Timeout, Kollision, etc.)
- **Lösung**: Mission clearen, Parameter prüfen, neu hochladen

### Callbacks werden nicht getriggert
- **Ursache**: Bridge nicht gestartet oder Namespace falsch
- **Lösung**: `bridge.start()` aufrufen, Namespace prüfen (`/px4_1`, nicht `px4_1`)

## Integration mit anderen Features

### Mit Gazebo Auto-Setup (Feature 3)
```python
from droneresearch.simulation.px4_gazebo import PX4GazeboCluster
from droneresearch.ros.px4_bridge import PX4ROS2Bridge

# SITL starten
with PX4GazeboCluster(num_drones=1) as cluster:
    # Bridge verbinden
    bridge = PX4ROS2Bridge(namespace="px4_1")
    bridge.start()
    
    # Mission hochladen
    waypoints = [...]
    bridge.upload_mission(waypoints)
    
    # Status überwachen
    def on_status(s):
        print(f"WP {s['current_seq']}/{s['total_count']}")
    bridge.on_mission_status(on_status)
    
    # Mission starten
    bridge.arm()
    bridge.takeoff(10.0)
    time.sleep(5)
    bridge.start_mission()
    
    # Warten bis fertig
    while not bridge.get_mission_status()['finished']:
        time.sleep(1)
```

## Technische Details

### MissionResult Topic
- **Topic**: `/fmu/out/mission_result`
- **Type**: `px4_msgs/msg/MissionResult`
- **QoS**: Best Effort, Volatile
- **Rate**: ~1 Hz während Mission, sporadisch sonst

### Waypoint-Speicherung
Waypoints werden im Uploader gespeichert für:
- UI-Anzeige (Liste, Map-Overlay)
- Replay/Analyse
- Vergleich Soll/Ist-Position

Format:
```python
{
    "lat": float,      # Latitude (Grad)
    "lon": float,      # Longitude (Grad)
    "alt": float,      # Altitude MSL (Meter)
    "hold_time": float # Loiter-Zeit (Sekunden)
}
```

### Thread-Safety
- `get_mission_status()`: Thread-safe (Lock)
- `get_mission_waypoints()`: Thread-safe (Lock)
- Callbacks: Werden in ROS2 Executor-Thread ausgeführt

## Siehe auch
- [Mission Upload](px4-mission-upload.md) - Feature 1
- [Gazebo Auto-Setup](px4-sitl-automation.md) - Feature 3
- [PX4 uXRCE-DDS](https://docs.px4.io/main/en/middleware/uxrce_dds.html)
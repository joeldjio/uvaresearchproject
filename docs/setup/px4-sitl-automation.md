# PX4 SITL Automation

Automatisches Starten von PX4 SITL + Gazebo + XRCE-DDS Agent.

## 🎯 Übersicht

Dieses Feature automatisiert den manuellen 3-Terminal-Workflow für PX4 SITL:

**Vorher (Manuell)**:
```bash
# Terminal 1: XRCE-DDS Agent
MicroXRCEAgent udp4 -p 8888

# Terminal 2: PX4 SITL
source /opt/ros/humble/setup.bash
source /home/iruz/ws_sensor_combined/install/setup.bash
cd /home/iruz/PX4-Autopilot
PX4_UXRCE_DDS_NS=uav_1 make px4_sitl gz_x500

# Terminal 3: UI
python3 -m tools.ui.app
```

**Nachher (Automatisch)**:
- **Option 1**: Bash-Script
- **Option 2**: Python-Klasse
- **Option 3**: UI-Button

---

## 📋 Voraussetzungen

- Ubuntu 22.04 Jammy (oder kompatibel)
- ROS2 Humble installiert
- PX4-Autopilot Repository geklont
- Gazebo Ignition 8 installiert
- `micro-xrce-dds-agent` installiert: `pip install micro-xrce-dds-agent`
- `px4_msgs` in ROS2 Workspace gebaut

---

## 🚀 Verwendung

### Option 1: Bash-Script

```bash
# Mit Defaults (uav_1, x500, /home/iruz/PX4-Autopilot)
./tools/launch_px4_sitl.sh

# Mit Custom-Parametern
./tools/launch_px4_sitl.sh uav_2 iris /path/to/PX4-Autopilot

# Stoppen: Ctrl+C
```

**Features**:
- Startet XRCE-DDS Agent + PX4 SITL + Gazebo
- Sourced automatisch ROS2 Setups
- Farbige Ausgabe mit Status-Indikatoren
- Logs in `/tmp/xrce_agent_*.log` und `/tmp/px4_sitl_*.log`
- Graceful Shutdown bei Ctrl+C

---

### Option 2: Python-Klasse

```python
from droneresearch.simulation import PX4GazeboCluster

# Konfiguration
cluster = PX4GazeboCluster(
    num_drones=1,
    px4_dir="/home/iruz/PX4-Autopilot",
    model="x500",
    ros2_setups=[
        "/opt/ros/humble/setup.bash",
        "/home/iruz/ws_sensor_combined/install/setup.bash"
    ],
    namespace_prefix="uav"
)

# Starten
cluster.start()

# ... Deine Anwendung ...

# Stoppen
cluster.stop()
```

**Context Manager**:
```python
with PX4GazeboCluster(num_drones=1) as cluster:
    # SITL läuft
    bridge = PX4ROS2Bridge(namespace="uav_1")
    bridge.start()
    # ...
# Automatisches Cleanup
```

**Vollständiges Beispiel**:
```bash
python examples/px4_sitl_automation.py
```

---

### Option 3: UI-Button

1. **UI starten**:
   ```bash
   python3 -m tools.ui.app
   ```

2. **ROS2 Panel öffnen**

3. **SITL Steuerung konfigurieren**:
   - **PX4**: `/home/iruz/PX4-Autopilot` (anpassen!)
   - **Model**: `x500` (oder `iris`, `plane`, `standard_vtol`)
   - **NS**: `uav_1`

4. **"SITL starten" klicken**

5. **Warten** (~15 Sekunden für Gazebo-Start)

6. **Bridge starten**:
   - Namespace: `uav_1` (muss mit SITL NS übereinstimmen)
   - "Bridge starten" klicken

7. **Fertig!** Jetzt kannst du ARM, TAKEOFF, etc. verwenden

---

## 🔧 Konfiguration

### PX4 Directory

**Standard**: `/home/iruz/PX4-Autopilot`

**Anpassen**:
- **Bash**: `./tools/launch_px4_sitl.sh uav_1 x500 /path/to/PX4`
- **Python**: `px4_dir="/path/to/PX4"`
- **UI**: Feld "PX4" im SITL Steuerung Panel

### ROS2 Setups

**Standard**:
- `/opt/ros/humble/setup.bash`
- `/home/iruz/ws_sensor_combined/install/setup.bash`

**Anpassen in Python**:
```python
cluster = PX4GazeboCluster(
    ros2_setups=[
        "/opt/ros/humble/setup.bash",
        "/home/user/my_workspace/install/setup.bash"
    ]
)
```

**Anpassen in UI**:
- Wird aus `ros2_context.py` geladen
- Editiere `tools/ui/context/ros2_context.py` Zeile 82-86

### Modelle

Verfügbare Modelle:
- `x500` (Standard Quadcopter)
- `iris` (Kleinerer Quadcopter)
- `plane` (Fixed-Wing)
- `standard_vtol` (VTOL)

### Namespace

**Standard**: `uav_1`

**Multi-Drone**:
```python
cluster = PX4GazeboCluster(
    num_drones=3,
    namespace_prefix="uav"  # → uav_1, uav_2, uav_3
)
```

---

## 🐛 Troubleshooting

### XRCE-DDS Agent startet nicht

**Fehler**: `MicroXRCEAgent: command not found`

**Lösung**:
```bash
pip install micro-xrce-dds-agent
# Oder
pip install --user micro-xrce-dds-agent
```

### PX4 SITL startet nicht

**Fehler**: `PX4 directory not found`

**Lösung**:
- Prüfe PX4 Pfad: `ls /home/iruz/PX4-Autopilot`
- Passe Pfad an in UI oder Script

**Fehler**: `make: *** No rule to make target 'px4_sitl'`

**Lösung**:
```bash
cd /home/iruz/PX4-Autopilot
make distclean
make px4_sitl gz_x500
```

### Gazebo startet nicht

**Fehler**: `gz: command not found`

**Lösung**:
```bash
# Installiere Gazebo Ignition 8
sudo apt install gz-garden
```

### Bridge findet keine Topics

**Fehler**: `No topics on /uav_1/fmu/out/*`

**Lösung**:
1. Prüfe ob XRCE-DDS Agent läuft: `ps aux | grep MicroXRCE`
2. Prüfe ob PX4 läuft: `ps aux | grep px4`
3. Prüfe Namespace: Muss in SITL und Bridge identisch sein
4. Warte 5-10 Sekunden nach SITL-Start

### Port bereits belegt

**Fehler**: `Port 8888 already in use`

**Lösung**:
```bash
# Finde Prozess
lsof -i :8888

# Stoppe alten Agent
killall MicroXRCEAgent
```

---

## 📊 Logs

### Bash-Script Logs

```bash
# XRCE-DDS Agent
tail -f /tmp/xrce_agent_uav_1.log

# PX4 SITL
tail -f /tmp/px4_sitl_uav_1.log
```

### Python Logs

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### UI Logs

- Logs erscheinen im ROS2 Panel Log-Bereich
- Farben: INFO (grün), WARN (gelb), ERROR (rot)

---

## 🎓 Beispiele

### Einfacher Takeoff

```python
from droneresearch.simulation import PX4GazeboCluster
from droneresearch.ros.px4_bridge import PX4ROS2Bridge
import time

with PX4GazeboCluster(num_drones=1) as cluster:
    bridge = PX4ROS2Bridge(namespace="uav_1")
    bridge.start()
    time.sleep(5)  # Warte auf Telemetrie
    
    bridge.arm()
    time.sleep(2)
    
    bridge.takeoff(10.0)
    time.sleep(10)
    
    bridge.land()
    time.sleep(10)
```

### Multi-Drone Formation

```python
with PX4GazeboCluster(num_drones=3) as cluster:
    bridges = [
        PX4ROS2Bridge(namespace=f"uav_{i+1}")
        for i in range(3)
    ]
    
    for bridge in bridges:
        bridge.start()
    
    time.sleep(5)
    
    # Alle gleichzeitig armen
    for bridge in bridges:
        bridge.arm()
    
    # Formation takeoff
    for i, bridge in enumerate(bridges):
        bridge.takeoff(10.0 + i * 2)  # Gestaffelte Höhen
```

---

## 📝 Zusammenfassung

**3 Wege, SITL zu starten**:

1. **Bash-Script**: `./tools/launch_px4_sitl.sh`
   - ✅ Schnell und einfach
   - ✅ Keine Python-Abhängigkeiten
   - ❌ Weniger Flexibilität

2. **Python-Klasse**: `PX4GazeboCluster`
   - ✅ Programmatische Kontrolle
   - ✅ Multi-Drone Support
   - ✅ Context Manager
   - ❌ Erfordert Python-Code

3. **UI-Button**: ROS2 Panel
   - ✅ Keine Terminal-Befehle
   - ✅ Visuelles Feedback
   - ✅ Konfigurierbar
   - ❌ Erfordert UI

**Empfehlung**:
- **Entwicklung**: Python-Klasse oder Bash-Script
- **Endbenutzer**: UI-Button
- **CI/CD**: Bash-Script

---

## 🔗 Siehe auch

- [PX4 SITL Setup Guide](px4-sitl.md)
- [ROS2 Bridge Documentation](../ui/ui-documentation.md)
- [PX4 Optimierungen](../PX4_OPTIMIERUNGEN_UND_FEATURES.md)
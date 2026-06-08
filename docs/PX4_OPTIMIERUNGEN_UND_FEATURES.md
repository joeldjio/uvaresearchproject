# PX4 Optimierungen und neue Features

> Vorschläge für Verbesserungen und neue Features mit Fokus auf PX4 + ROS2 + Gazebo  
> Basierend auf: Ubuntu 22.04 Jammy, ROS2 Humble, Gazebo, PX4 v1.14+  
> Stand: 2026-06-08

---

## 🔴 Kritische Probleme (Mission fliegt nicht)

### Problem 1: Mission-Upload über uXRCE-DDS nicht implementiert

**Aktueller Stand**:
- `PX4ROS2Bridge` unterstützt nur **Offboard Mode** (TrajectorySetpoint)
- **Keine Mission-Upload-Funktion** über uXRCE-DDS
- MAVLink-basierte Mission funktioniert, aber nicht über ROS2

**Ursache**:
```python
# droneresearch/ros/px4_bridge.py hat KEINE Mission-Upload-Methode
# Nur: arm(), takeoff(), land(), rtl(), set_position_setpoint_*()
```

**Lösung 1: Mission über Offboard Mode emulieren**

```python
# Neue Methode in PX4ROS2Bridge
def fly_mission_offboard(self, waypoints: list, speed: float = 2.0):
    """
    Fliegt Mission-Waypoints über Offboard Mode.
    
    Args:
        waypoints: [{"lat": 48.137, "lon": 11.575, "alt": 10}, ...]
        speed: Fluggeschwindigkeit in m/s
    """
    self.set_offboard_mode()
    
    for i, wp in enumerate(waypoints):
        # GPS → NED Konvertierung (relativ zu Home)
        north, east = self._gps_to_ned(wp["lat"], wp["lon"])
        down = -wp["alt"]  # NED: Down ist negativ
        
        print(f"Flying to WP{i+1}: N={north:.1f} E={east:.1f} D={down:.1f}")
        self.set_position_setpoint_ned(north, east, down)
        
        # Warten bis Waypoint erreicht (Toleranz: 1m)
        while True:
            pos = self.telemetry.get("local_position", {})
            dist = math.sqrt(
                (pos.get("x", 0) - north)**2 +
                (pos.get("y", 0) - east)**2 +
                (pos.get("z", 0) - down)**2
            )
            if dist < 1.0:
                break
            time.sleep(0.1)
        
        print(f"  Reached WP{i+1}")
```

**Lösung 2: Hybrid-Ansatz (MAVLink Mission + ROS2 Monitoring)**

```python
# In SwarmContext oder ROS2Context
def upload_mission_mavlink_monitor_ros2(self, drone_id: str, waypoints: list):
    """
    Upload Mission via MAVLink, Monitor via ROS2.
    
    Nutzt MAVLink für Mission-Upload (funktioniert),
    aber ROS2 für Telemetrie-Monitoring (besser).
    """
    # 1. MAVLink Mission-Upload (existierender Code)
    backend = self._backend.get_backend(drone_id)
    if backend and backend.drone:
        backend.drone._mission.upload(waypoints)
        backend.drone._mission.start()
    
    # 2. ROS2 Bridge für Monitoring
    if drone_id in self._ros2_bridges:
        bridge = self._ros2_bridges[drone_id]
        # Monitor mission progress via /fmu/out/vehicle_status
        # mission_state field zeigt MISSION_STATE_ACTIVE
```

---

## 🟡 Wichtige Verbesserungen

### Feature 1: Mission-Upload über uXRCE-DDS (Native PX4)

**Implementierung**:

```python
# Neue Datei: droneresearch/ros/px4_mission.py

from px4_msgs.msg import VehicleMissionItem, VehicleMissionItemCount

class PX4MissionUploader:
    """
    Mission-Upload über uXRCE-DDS (PX4 v1.14+).
    
    Verwendet:
        - /fmu/in/vehicle_mission_item_count
        - /fmu/in/vehicle_mission_item
        - /fmu/out/vehicle_mission_ack
    """
    
    def __init__(self, node, namespace=""):
        self._node = node
        self._ns = f"/{namespace}" if namespace else ""
        
        # Publishers
        self._pub_count = node.create_publisher(
            VehicleMissionItemCount,
            f"{self._ns}/fmu/in/vehicle_mission_item_count",
            10
        )
        self._pub_item = node.create_publisher(
            VehicleMissionItem,
            f"{self._ns}/fmu/in/vehicle_mission_item",
            10
        )
        
        # Subscriber für ACK
        self._sub_ack = node.create_subscription(
            VehicleMissionAck,
            f"{self._ns}/fmu/out/vehicle_mission_ack",
            self._on_ack,
            10
        )
        
        self._ack_received = threading.Event()
        self._ack_result = None
    
    def upload(self, waypoints: list) -> bool:
        """
        Upload waypoints to PX4.
        
        Args:
            waypoints: [{"lat": 48.137, "lon": 11.575, "alt": 10}, ...]
        
        Returns:
            True if upload successful
        """
        # 1. Send count
        count_msg = VehicleMissionItemCount()
        count_msg.timestamp = int(time.time() * 1e6)
        count_msg.count = len(waypoints)
        self._pub_count.publish(count_msg)
        
        # 2. Send items
        for i, wp in enumerate(waypoints):
            item = VehicleMissionItem()
            item.timestamp = int(time.time() * 1e6)
            item.sequence = i
            item.frame = 3  # MAV_FRAME_GLOBAL_RELATIVE_ALT
            item.command = 16  # MAV_CMD_NAV_WAYPOINT
            item.latitude = wp["lat"]
            item.longitude = wp["lon"]
            item.altitude = wp["alt"]
            item.autocontinue = True
            self._pub_item.publish(item)
            time.sleep(0.05)
        
        # 3. Wait for ACK
        self._ack_received.wait(timeout=5.0)
        return self._ack_result == 0  # MAV_MISSION_ACCEPTED
    
    def _on_ack(self, msg):
        self._ack_result = msg.result
        self._ack_received.set()
```

**Integration in PX4ROS2Bridge**:

```python
# In droneresearch/ros/px4_bridge.py

from droneresearch.ros.px4_mission import PX4MissionUploader

class PX4ROS2Bridge:
    def __init__(self, ...):
        # ... existing code ...
        self._mission_uploader = None
    
    def start(self):
        # ... existing code ...
        self._mission_uploader = PX4MissionUploader(self._node, self._ns_prefix)
    
    def upload_mission(self, waypoints: list) -> bool:
        """Upload mission via uXRCE-DDS."""
        if not self._mission_uploader:
            return False
        return self._mission_uploader.upload(waypoints)
    
    def start_mission(self):
        """Start uploaded mission."""
        self._send_vehicle_command(VehicleCommandId.MISSION_START, 0, 0)
```

---

### Feature 2: Erweiterte Mission-Diagnostik im ROS2 Panel

**UI-Erweiterung** (`tools/ui/qml/panels/ROS2Panel.qml`):

```qml
// Neuer Abschnitt: Mission Status
Rectangle {
    width: parent.width
    height: 200
    color: "#1a1d24"
    
    Column {
        spacing: 10
        
        Text {
            text: "Mission Status"
            font.pixelSize: 16
            font.bold: true
            color: "#e2e8f0"
        }
        
        Row {
            spacing: 20
            
            Text {
                text: "State: " + (ros2.missionState(selectedDroneId) || "—")
                color: "#94a3b8"
            }
            
            Text {
                text: "Current WP: " + (ros2.currentWaypoint(selectedDroneId) || "—")
                color: "#94a3b8"
            }
            
            Text {
                text: "Total WPs: " + (ros2.totalWaypoints(selectedDroneId) || "—")
                color: "#94a3b8"
            }
        }
        
        ProgressBar {
            width: parent.width - 40
            value: ros2.missionProgress(selectedDroneId) || 0
            from: 0
            to: 1.0
        }
        
        Row {
            spacing: 10
            
            Button {
                text: "Upload Mission"
                onClicked: {
                    // Waypoints aus globalMissionWaypoints
                    var wps = []
                    for (var i = 0; i < globalMissionWaypoints.count; i++) {
                        var w = globalMissionWaypoints.get(i)
                        wps.push({lat: w.lat, lon: w.lon, alt: w.alt})
                    }
                    ros2.uploadMission(selectedDroneId, JSON.stringify(wps))
                }
            }
            
            Button {
                text: "Start Mission"
                onClicked: ros2.startMission(selectedDroneId)
            }
            
            Button {
                text: "Pause Mission"
                onClicked: ros2.pauseMission(selectedDroneId)
            }
            
            Button {
                text: "Clear Mission"
                onClicked: ros2.clearMission(selectedDroneId)
            }
        }
    }
}
```

**Backend** (`tools/ui/context/ros2_context.py`):

```python
@pyqtSlot(str, str)
def uploadMission(self, drone_id: str, waypoints_json: str):
    """Upload mission via uXRCE-DDS."""
    bridge = self._bridges.get(drone_id)
    if not bridge:
        self.ros2LogMessage.emit("ERROR", f"[{drone_id}] No active bridge")
        return
    
    waypoints = json.loads(waypoints_json)
    ok = bridge.upload_mission(waypoints)
    if ok:
        self.ros2LogMessage.emit("INFO", f"[{drone_id}] Mission uploaded ({len(waypoints)} WPs)")
    else:
        self.ros2LogMessage.emit("ERROR", f"[{drone_id}] Mission upload failed")

@pyqtSlot(str)
def startMission(self, drone_id: str):
    """Start uploaded mission."""
    bridge = self._bridges.get(drone_id)
    if bridge:
        bridge.start_mission()
        self.ros2LogMessage.emit("INFO", f"[{drone_id}] Mission started")

@pyqtSlot(str, result=str)
def missionState(self, drone_id: str) -> str:
    """Get current mission state."""
    bridge = self._bridges.get(drone_id)
    if not bridge:
        return "—"
    state = bridge.telemetry.get("mission_state", 0)
    states = {0: "IDLE", 1: "ACTIVE", 2: "PAUSED", 3: "COMPLETE"}
    return states.get(state, "UNKNOWN")

@pyqtSlot(str, result=int)
def currentWaypoint(self, drone_id: str) -> int:
    """Get current waypoint index."""
    bridge = self._bridges.get(drone_id)
    if not bridge:
        return 0
    return bridge.telemetry.get("mission_current", 0)
```

---

### Feature 3: Gazebo-Integration mit automatischer Drone-Erkennung

**Problem**: Manuelles Starten von SITL + Gazebo + uXRCE-DDS Agent

**Lösung**: Automatisiertes Setup-Script

```python
# Neue Datei: droneresearch/simulation/px4_gazebo.py

import subprocess
import time
import os

class PX4GazeboCluster:
    """
    Automatisches Setup für PX4 SITL + Gazebo + uXRCE-DDS.
    
    Startet:
        1. Micro XRCE-DDS Agent (Port 8888)
        2. PX4 SITL Instanzen mit Gazebo
        3. Wartet auf uXRCE-DDS Verbindung
    """
    
    def __init__(
        self,
        num_drones: int = 1,
        px4_dir: str = "~/PX4-Autopilot",
        model: str = "x500",
        world: str = "default",
    ):
        self.num_drones = num_drones
        self.px4_dir = os.path.expanduser(px4_dir)
        self.model = model
        self.world = world
        self._processes = []
    
    def start(self):
        """Start XRCE-DDS Agent + PX4 SITL instances."""
        # 1. Start XRCE-DDS Agent
        print("Starting Micro XRCE-DDS Agent...")
        agent_proc = subprocess.Popen(
            ["MicroXRCEAgent", "udp4", "-p", "8888"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._processes.append(agent_proc)
        time.sleep(2)
        
        # 2. Start PX4 SITL instances
        for i in range(self.num_drones):
            instance_id = i
            namespace = f"uav_{i+1}"
            
            print(f"Starting PX4 SITL instance {instance_id} (namespace: {namespace})...")
            
            env = os.environ.copy()
            env["PX4_SIM_MODEL"] = self.model
            env["PX4_GZ_WORLD"] = self.world
            env["PX4_UXRCE_DDS_NS"] = namespace
            
            sitl_proc = subprocess.Popen(
                ["make", "px4_sitl", f"gz_{self.model}"],
                cwd=self.px4_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self._processes.append(sitl_proc)
            time.sleep(5)  # Wait for SITL to initialize
        
        print(f"All {self.num_drones} drones started.")
        print("Waiting for uXRCE-DDS connections...")
        time.sleep(5)
    
    def stop(self):
        """Stop all processes."""
        for proc in self._processes:
            proc.terminate()
            proc.wait(timeout=5)
        self._processes.clear()
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()
```

**Verwendung**:

```python
from droneresearch.simulation import PX4GazeboCluster
from droneresearch.ros.px4_bridge import PX4ROS2Bridge

# Start 3 drones in Gazebo
with PX4GazeboCluster(num_drones=3) as cluster:
    # Connect bridges
    bridges = [
        PX4ROS2Bridge(namespace=f"uav_{i+1}")
        for i in range(3)
    ]
    
    for bridge in bridges:
        bridge.start()
    
    # Fly mission...
```

---

### Feature 4: Verbesserte Frame-Konvertierung mit Visualisierung

**Problem**: NED ↔ ENU Konvertierung ist fehleranfällig

**Lösung**: Debug-Visualisierung im ROS2 Panel

```qml
// In ROS2Panel.qml
Rectangle {
    width: parent.width
    height: 300
    color: "#1a1d24"
    
    Column {
        Text {
            text: "Frame Conversion Debug"
            font.pixelSize: 16
            font.bold: true
        }
        
        Row {
            spacing: 20
            
            // NED (PX4)
            Column {
                Text { text: "NED (PX4)"; color: "#ef4444" }
                Text { text: "N: " + ros2.nedNorth(selectedDroneId).toFixed(2); color: "#94a3b8" }
                Text { text: "E: " + ros2.nedEast(selectedDroneId).toFixed(2); color: "#94a3b8" }
                Text { text: "D: " + ros2.nedDown(selectedDroneId).toFixed(2); color: "#94a3b8" }
            }
            
            Text { text: "⟷"; font.pixelSize: 24; color: "#64748b" }
            
            // ENU (ROS2)
            Column {
                Text { text: "ENU (ROS2)"; color: "#22c55e" }
                Text { text: "E: " + ros2.enuEast(selectedDroneId).toFixed(2); color: "#94a3b8" }
                Text { text: "N: " + ros2.enuNorth(selectedDroneId).toFixed(2); color: "#94a3b8" }
                Text { text: "U: " + ros2.enuUp(selectedDroneId).toFixed(2); color: "#94a3b8" }
            }
        }
        
        // 3D Visualisierung (Canvas)
        Canvas {
            width: parent.width - 40
            height: 200
            
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                
                // Draw NED axes (red)
                ctx.strokeStyle = "#ef4444"
                ctx.beginPath()
                ctx.moveTo(width/2, height/2)
                ctx.lineTo(width/2, height/2 - 50)  // North
                ctx.stroke()
                
                // Draw ENU axes (green)
                ctx.strokeStyle = "#22c55e"
                ctx.beginPath()
                ctx.moveTo(width/2, height/2)
                ctx.lineTo(width/2 + 50, height/2)  // East
                ctx.stroke()
                
                // Draw drone position
                var nedN = ros2.nedNorth(selectedDroneId) * 5
                var nedE = ros2.nedEast(selectedDroneId) * 5
                ctx.fillStyle = "#2563eb"
                ctx.beginPath()
                ctx.arc(width/2 + nedE, height/2 - nedN, 5, 0, 2*Math.PI)
                ctx.fill()
            }
        }
    }
}
```

---

## 🟢 Nice-to-Have Features

### Feature 5: Multi-Vehicle Formation mit PX4

```python
# Neue Datei: droneresearch/ros/px4_formation.py

class PX4FormationController:
    """
    Formation-Control für PX4 Swarm via uXRCE-DDS.
    
    Verwendet Offboard Mode für alle Follower.
    """
    
    def __init__(self, bridges: list, leader_id: str):
        self.bridges = {b.namespace: b for b in bridges}
        self.leader_id = leader_id
        self._running = False
        self._thread = None
    
    def set_formation(self, formation: str, spacing: float):
        """
        Set formation geometry.
        
        Args:
            formation: "line", "v", "grid", "circle"
            spacing: Distance between drones (m)
        """
        from droneresearch.sdk.formations import formation_offsets
        
        follower_ids = [id for id in self.bridges if id != self.leader_id]
        offsets = list(formation_offsets(formation, len(follower_ids), spacing))
        
        self._offsets = dict(zip(follower_ids, offsets))
    
    def start(self):
        """Start formation-following loop (20 Hz)."""
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
    
    def _loop(self):
        while self._running:
            # Get leader position
            leader = self.bridges[self.leader_id]
            leader_pos = leader.telemetry.get("local_position", {})
            leader_n = leader_pos.get("x", 0)
            leader_e = leader_pos.get("y", 0)
            leader_d = leader_pos.get("z", 0)
            
            # Update follower setpoints
            for follower_id, (offset_n, offset_e) in self._offsets.items():
                follower = self.bridges[follower_id]
                target_n = leader_n + offset_n
                target_e = leader_e + offset_e
                target_d = leader_d  # Same altitude
                
                follower.set_position_setpoint_ned(target_n, target_e, target_d)
            
            time.sleep(0.05)  # 20 Hz
```

---

### Feature 6: ROS2 Bag Recording Integration

```python
# In ROS2Context
@pyqtSlot(str, str)
def startRecording(self, drone_id: str, bag_path: str):
    """Start ROS2 bag recording for drone."""
    bridge = self._bridges.get(drone_id)
    if not bridge:
        return
    
    # Start ros2 bag record in subprocess
    topics = [
        f"{bridge._ns_prefix}/fmu/out/vehicle_attitude",
        f"{bridge._ns_prefix}/fmu/out/vehicle_global_position",
        f"{bridge._ns_prefix}/fmu/out/vehicle_local_position",
        f"{bridge._ns_prefix}/fmu/out/vehicle_status",
    ]
    
    cmd = ["ros2", "bag", "record", "-o", bag_path] + topics
    proc = subprocess.Popen(cmd)
    self._recording_procs[drone_id] = proc
    self.ros2LogMessage.emit("INFO", f"[{drone_id}] Recording to {bag_path}")

@pyqtSlot(str)
def stopRecording(self, drone_id: str):
    """Stop ROS2 bag recording."""
    proc = self._recording_procs.pop(drone_id, None)
    if proc:
        proc.terminate()
        proc.wait()
        self.ros2LogMessage.emit("INFO", f"[{drone_id}] Recording stopped")
```

---

## 📋 Implementierungs-Prioritäten

### Phase 1: Kritische Fixes (1-2 Wochen)
1. ✅ **Mission-Upload über uXRCE-DDS** (`PX4MissionUploader`)
2. ✅ **Offboard-Mission-Emulation** (`fly_mission_offboard()`)
3. ✅ **Mission-Status-Monitoring** (ROS2 Panel Erweiterung)
4. ✅ **Debug-Logging** (Frame-Konvertierung, Mission-State)

### Phase 2: Wichtige Verbesserungen (2-3 Wochen)
5. ✅ **Gazebo-Auto-Setup** (`PX4GazeboCluster`)
6. ✅ **Erweiterte Diagnostik** (Frame-Visualisierung)
7. ✅ **Multi-Vehicle-Formation** (`PX4FormationController`)
8. ✅ **Hybrid MAVLink/ROS2** (Mission-Upload MAVLink, Monitoring ROS2)

### Phase 3: Nice-to-Have (3-4 Wochen)
9. ⬜ **ROS2 Bag Recording** (UI-Integration)
10. ⬜ **Parameter-Tuning** (PX4 Parameter über uXRCE-DDS)
11. ⬜ **Collision Avoidance** (APF + ROS2 Offboard)
12. ⬜ **Vision-based Navigation** (VIO/SLAM Integration)

---

## 🧪 Test-Setup für Ubuntu Jammy + ROS2 Humble + Gazebo

### Schritt 1: PX4 SITL + Gazebo starten

```bash
# Terminal 1: XRCE-DDS Agent
MicroXRCEAgent udp4 -p 8888

# Terminal 2: PX4 SITL mit Gazebo
cd ~/PX4-Autopilot
PX4_UXRCE_DDS_NS=uav_1 make px4_sitl gz_x500

# Terminal 3: ROS2 Topic-Check
source ~/ros2_ws/install/setup.bash
ros2 topic list | grep fmu
```

### Schritt 2: uavresearch gcs starten

```bash
# Terminal 4: GCS
cd ~/uavresearchproject
source ~/ros2_ws/install/setup.bash
python -m tools.ui
```

### Schritt 3: Mission testen

1. **ROS2 Panel öffnen**
2. **Bridge starten**: Namespace = `uav_1`
3. **ARM + TAKEOFF** über ROS2 Panel
4. **Mission hochladen**:
   - Waypoints in Map-Tab setzen
   - "Upload Mission" klicken
5. **Mission starten**: "Start Mission" klicken
6. **Monitoring**: Mission-Status beobachten

### Schritt 4: Debug bei Problemen

```bash
# Terminal 5: ROS2 Topic Echo
ros2 topic echo /uav_1/fmu/out/vehicle_status

# Terminal 6: PX4 Console
pxh> commander status
pxh> mission status
pxh> listener vehicle_local_position
```

---

## 📝 Zusammenfassung

**Hauptproblem**: Mission-Upload über uXRCE-DDS fehlt komplett

**Schnellste Lösung**: Offboard-Mission-Emulation (1-2 Tage)

**Beste Lösung**: Native Mission-Upload über uXRCE-DDS (1 Woche)

**Empfehlung**: 
1. Implementiere **Offboard-Mission-Emulation** sofort (Quick-Fix)
2. Parallel entwickle **Native Mission-Upload** (Langfristig)
3. Erweitere **ROS2 Panel** mit Mission-Diagnostik
4. Automatisiere **Gazebo-Setup** für einfacheres Testen

Alle Features sind **kompatibel** mit Ubuntu 22.04 Jammy + ROS2 Humble + Gazebo + PX4 v1.14+.
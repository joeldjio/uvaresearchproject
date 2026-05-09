# DroneResearch Platform

**ROS2-based UAV Research Middleware Platform**

> A modular, scriptable, simulation-first research framework for autonomous drone experiments and swarm coordination.

**Author:** Joel Djio  
**License:** MIT  
**Repository:** https://github.com/joeldjio/uavresearchproject

---

## Table of Contents

1. [What it is](#what-it-is)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Module Documentation](#module-documentation)
   - [autopilot — Hardware Abstraction](#autopilot--hardware-abstraction)
   - [core — FSM & Connection](#core--fsm--connection)
   - [models — UAV Classes](#models--uav-classes)
   - [simulation — SITL & Replay](#simulation--sitl--replay)
   - [experiment — Scenarios & Metrics](#experiment--scenarios--metrics)
   - [safety — APF Filter](#safety--apf-filter)
   - [llm — Swarm Commander](#llm--swarm-commander)
   - [ros — PX4 ROS2 Bridge](#ros--px4-ros2-bridge)
   - [exploration — Frontier & vswarm](#exploration--frontier--vswarm)
   - [data — Telemetry Logging](#data--telemetry-logging)
   - [sdk — Public API](#sdk--public-api)
   - [cli — Command Line](#cli--command-line)
6. [Raspberry Pi Deployment](#raspberry-pi-deployment)
7. [Docker](#docker)
8. [Examples](#examples)
9. [Research Background](#research-background)
10. [Hardware](#hardware)

---

## What it is

DroneResearch is a **ROS2-based UAV Research Middleware Platform** — not a GCS, not a UI tool. It is a Python framework designed for:

- **Reproducible drone experiments** with quantitative metrics
- **Simulation-first development** (SITL → real hardware, same code)
- **Heterogeneous UAV swarm coordination** (leader-follower, formations)
- **Natural language swarm control** via LLM integration
- **Autonomous exploration** via frontier planning and vision-based flocking
- **Raspberry Pi 1 deployment** (stdlib-only HTTP server, ~20MB RAM)

This platform follows the architecture described in:
> *"Modular and Scalable System Architecture for Heterogeneous UAV Swarms"* (2025)  
> *"SkySim: ROS2-based Simulation for Natural Language Control of Drone Swarms"* (Shibu et al., arXiv:2602.01226)

---

## Architecture

```
DroneResearch/
├── droneresearch/
│   ├── autopilot/          Hardware abstraction layer
│   │   ├── base.py         AutopilotBackend ABC (interface)
│   │   ├── mavlink/        ArduPilot + PX4 via pymavlink
│   │   ├── ardupilot/      ArduPilot-specific extensions
│   │   └── px4/            PX4 native via uXRCE-DDS (ROS2 native)
│   │
│   ├── core/               Low-level connection & state
│   │   ├── connection.py   MAVLink connection manager
│   │   ├── fsm.py          Drone Finite State Machine
│   │   └── telemetry.py    Telemetry state container
│   │
│   ├── models/             UAV model classes (paper architecture)
│   │   ├── generic_uav.py       GenericUAVModel (base)
│   │   ├── observation_uav.py   ObservationUAVModel (gimbal/camera)
│   │   └── coordinator_uav.py   CoordinatorUAVModel (leader-follower)
│   │
│   ├── simulation/         Simulation-first tooling
│   │   ├── sitl.py         SITL launcher (ArduPilot + PX4 Gazebo)
│   │   └── replay.py       Telemetry replay (.csv/.json/.bin)
│   │
│   ├── experiment/         Reproducible research experiments
│   │   ├── manager.py      Experiment (grid-search, export)
│   │   ├── scenario.py     Scenario + ScenarioRunner
│   │   └── metrics.py      MetricsCollector (8 flight metrics)
│   │
│   ├── safety/             Real-time safety systems
│   │   └── apf.py          APF filter (20Hz), Geofence, Pose3D
│   │
│   ├── llm/                Natural language control
│   │   └── swarm_commander.py  SwarmCommander (Gemini/OpenAI/Ollama/Mock)
│   │
│   ├── ros/                ROS2 integration
│   │   ├── px4_bridge.py   PX4 native via uXRCE-DDS
│   │   └── bridge.py       MAVLink telemetry → ROS2 topics
│   │
│   ├── exploration/        Autonomous exploration
│   │   ├── frontier_bridge.py  larics frontier planner bridge
│   │   └── vswarm_bridge.py    EPFL LIS vswarm flocking bridge
│   │
│   ├── data/               Telemetry storage
│   │   ├── logger.py       CSV + JSON + ROS bag logging
│   │   └── store.py        Ring-buffer telemetry store
│   │
│   ├── sdk/                Public Python API
│   │   ├── drone.py        Drone class
│   │   └── swarm_api.py    Swarm class
│   │
│   └── cli/                Command-line interface
│       └── main.py         droneresearch CLI
│
├── pi/                     Raspberry Pi 1 optimized server
│   ├── server.py           Lightweight HTTP REST API (stdlib only)
│   ├── requirements_pi.txt Minimal deps (pymavlink + pyserial)
│   ├── droneresearch.service  systemd autostart
│   ├── install.sh          One-shot Pi setup script
│   └── README_PI.md        Pi-specific documentation
│
├── docker/                 Multi-platform containers
│   ├── Dockerfile.pi       ARMv6/7/8 (Raspberry Pi)
│   ├── Dockerfile.jetson   AArch64 + CUDA (Nvidia Jetson)
│   ├── Dockerfile.x86      x86_64 simulation / GCS
│   └── docker-compose.yml  3-agent heterogeneous swarm
│
└── examples/               Ready-to-run scripts
    ├── hover.py
    ├── event_based.py
    ├── speed_experiment.py
    ├── swarm_circle.py
    ├── coordinator_demo.py
    ├── autonomous_exploration.py
    ├── vswarm_flocking.py
    ├── px4_ros2_offboard.py
    ├── px4_multi_vehicle.py
    ├── llm_swarm_control.py
    └── full_research_pipeline.py
```

---

## Installation

```bash
git clone https://github.com/joeldjio/uavresearchproject.git
cd uavresearchproject
pip install -e .

# With ROS2 support (install ROS2 Humble first)
pip install -e ".[ros]"

# With UI (PySide6)
pip install -e ".[ui]"

# Full install
pip install -e ".[full]"
```

**Requirements:**
- Python 3.10+
- `pymavlink >= 2.4.40`
- `pyserial >= 3.5`
- ROS2 Humble/Jazzy (optional, for ROS2 features)
- `px4_msgs` ROS2 package (optional, for PX4 uXRCE-DDS)

---

## Quick Start

```bash
# SITL simulation (no hardware needed)
python examples/hover.py --port tcp:127.0.0.1:5760

# LLM swarm control (offline, no API key)
python examples/llm_swarm_control.py --backend mock --interactive

# Full research pipeline demo
python examples/full_research_pipeline.py --demo

# CLI
droneresearch connect --port tcp:127.0.0.1:5760
droneresearch arm
droneresearch takeoff --alt 10
droneresearch status
```

---

## Module Documentation

### autopilot — Hardware Abstraction

**`droneresearch/autopilot/base.py`**

Abstract base class `AutopilotBackend` defines the hardware interface. Every autopilot implementation must implement this interface — swap backends without changing mission code.

```python
from droneresearch.autopilot import get_backend

# ArduPilot or PX4 via MAVLink
backend = get_backend("mavlink")
backend.connect("tcp:127.0.0.1:5760")
backend.arm()
backend.takeoff(10.0)

# ArduPilot with extended features (parameters, fences)
backend = get_backend("ardupilot")
backend.connect("/dev/ttyUSB0", baud=57600)
backend.set_parameter("WPNAV_SPEED", 500)

# PX4 native via uXRCE-DDS
backend = get_backend("px4")
```

`TelemetrySnapshot` — shared telemetry contract:

| Field | Type | Description |
|---|---|---|
| `lat`, `lon`, `alt` | float | GPS position |
| `alt_rel` | float | Altitude above home (m) |
| `roll`, `pitch`, `yaw` | float | Attitude (degrees) |
| `vx`, `vy`, `vz` | float | Velocity (m/s) |
| `groundspeed` | float | Horizontal speed (m/s) |
| `armed` | bool | Motors armed |
| `flight_mode` | str | Current mode name |
| `battery_v`, `battery_pct` | float | Battery voltage / percent |
| `gps_fix`, `satellites` | int | GPS quality |

---

### core — FSM & Connection

**`droneresearch/core/fsm.py`** — Thread-safe Finite State Machine

```
IDLE → ARMING → ARMED → TAKEOFF → FLYING → MISSION
                                      ↓         ↓
                               EMERGENCY      RTL
                                      ↓         ↓
                                   LANDING ← ───┘
                                      ↓
                                    IDLE
```

States: `IDLE`, `ARMING`, `ARMED`, `TAKEOFF`, `FLYING`, `MISSION`, `RTL`, `LANDING`, `EMERGENCY`, `HOVER`

```python
from droneresearch.core.fsm import StateMachine, DroneState

fsm = StateMachine()
fsm.on_transition(lambda old, new: print(f"{old.name} → {new.name}"))
fsm.transition(DroneState.ARMING)
print(fsm.state)          # DroneState.ARMING
print(fsm.is_airborne)    # False
```

---

### models — UAV Classes

Based on: *"Modular and Scalable System Architecture for Heterogeneous UAV Swarms"* (2025)

#### `GenericUAVModel` — Base UAV

Wraps `Drone` SDK + `StateMachine`. Suitable for any UAV role.

```python
from droneresearch.models import GenericUAVModel

uav = GenericUAVModel("UAV_1", "tcp:127.0.0.1:5760")
uav.connect()
uav.arm()
uav.takeoff(10.0)

# Swarm roles
uav.set_role("follower")
uav.formation_offset = (3.0, 0.0, 0.0)   # 3m right of leader
```

#### `ObservationUAVModel` — Camera + Gimbal UAV

Extends `GenericUAVModel` with:
- Gimbal control (pitch/yaw/roll)
- GPS target tracking
- Video stream start/stop
- Object detection callback hook
- ROS2 video publishing

```python
from droneresearch.models import ObservationUAVModel

obs = ObservationUAVModel("OBS_1", "tcp:127.0.0.1:5761")
obs.connect()
obs.takeoff(15.0)

obs.point_gimbal(pitch=-45, yaw=0)
obs.track_target(lat=48.137, lon=11.575)
obs.start_stream("rtsp://192.168.1.10:8554/stream")
obs.on_detection = lambda det: print(f"Detected: {det}")
```

#### `CoordinatorUAVModel` — Swarm Coordinator

Leader-follower swarm management. Can run on-vehicle (leader UAV) or as a ground station.

```python
from droneresearch.models import CoordinatorUAVModel, GenericUAVModel

# Ground station mode
coord = CoordinatorUAVModel.as_ground_station()

d1 = GenericUAVModel("D1", "tcp:127.0.0.1:5760")
d2 = GenericUAVModel("D2", "tcp:127.0.0.1:5770")

coord.register("D1", d1)
coord.register("D2", d2)
coord.assign_leader("D1")

# Formations: "line", "v", "grid", "circle", "wedge"
coord.set_formation("v", spacing=4.0)

coord.takeoff_all(altitude=10.0)
coord.start_formation_follow()
```

**Supported formations:**

| Formation | Description |
|---|---|
| `line` | Single-file line |
| `v` | V-shape (wedge) |
| `grid` | N×M rectangular grid |
| `circle` | Circle around leader |
| `wedge` | Asymmetric wedge |

---

### simulation — SITL & Replay

**`droneresearch/simulation/sitl.py`**

```python
from droneresearch.simulation import SITLInstance, SITLCluster

# Single vehicle
with SITLInstance(autopilot="ardupilot", speedup=3.0) as sitl:
    drone = Drone(sitl.connection_string)
    drone.connect()
    # ... experiment ...

# Multi-vehicle cluster (3 drones, spaced 5m apart)
with SITLCluster(count=3, speedup=3.0) as cluster:
    for i, conn in enumerate(cluster.connection_strings):
        print(f"UAV {i}: {conn}")
```

**`SITLConfig` parameters:**

| Parameter | Default | Description |
|---|---|---|
| `autopilot` | `"ardupilot"` | `"ardupilot"` or `"px4"` |
| `vehicle` | `"copter"` | `"copter"`, `"plane"`, `"rover"` |
| `home_lat/lon` | Munich | Home location |
| `speedup` | `1.0` | Simulation speed multiplier |
| `base_port` | `5760` | TCP base port (ArduPilot) |

**`droneresearch/simulation/replay.py`**

```python
from droneresearch.simulation import TelemetryReplay

replay = TelemetryReplay("logs/flight_2025-01-01.csv")
replay.load()
print(f"{replay.frame_count} frames, {replay.duration:.1f}s")

# Replay at 5x speed
for frame in replay.play(speed=5.0):
    print(f"alt={frame.snapshot.alt_rel:.1f}m")
```

Supported formats: `.csv`, `.json`, `.bin` (ArduPilot DataFlash)

---

### experiment — Scenarios & Metrics

**`droneresearch/experiment/scenario.py`**

Fully serializable, reproducible experiment definition with automatic SITL lifecycle and grid-search over parameters.

```python
from droneresearch.experiment import Scenario, ScenarioRunner

scenario = Scenario(
    name       = "hover_altitude_test",
    autopilot  = "ardupilot",
    description= "Compare hover stability at different altitudes",
    tags       = ["hover", "stability"],
    mission    = [
        {"cmd": "takeoff", "alt": 10},
        {"cmd": "hover",   "duration": 30},
        {"cmd": "land"},
    ],
    params  = {"alt": [5, 10, 15, 20]},      # 4 runs
    metrics = ["hover_stability", "battery_drain", "flight_time"],
    speedup = 5.0,
)

# Save scenario for archiving/sharing
scenario.save("scenarios/hover_test.json")

# Run all 4 altitude combinations
runner = ScenarioRunner(scenario, results_dir="results")
results = runner.run()

for r in results:
    print(f"alt={r.params['alt']}m → stability={r.metrics['hover_stability_m']:.3f}m")
```

**`droneresearch/experiment/metrics.py`** — `MetricsCollector`

| Metric | Field | Unit |
|---|---|---|
| `flight_time` | `flight_time_s` | seconds |
| `battery_drain` | `battery_drain_pct` | % |
| `max_altitude` | `max_altitude_m` | meters |
| `avg_groundspeed` | `avg_groundspeed_ms` | m/s |
| `dist_traveled` | `dist_traveled_m` | meters |
| `hover_stability` | `hover_stability_m` | meters (std-dev) |
| `gps_quality` | `gps_fix_pct` | % with 3D fix |

---

### safety — APF Filter

**`droneresearch/safety/apf.py`**

Based on: *SkySim* (Shibu et al., 2025). Artificial Potential Field safety filter running at 20 Hz. Prevents drone-to-drone collisions, enforces geofencing, and clips to kinematic limits.

```python
from droneresearch.safety import APFSafetyFilter, APFFilterLoop, Pose3D

apf = APFSafetyFilter(
    min_separation=2.0,     # meters between drones
    max_speed=3.0,          # m/s max per update step
    geofence_radius=50.0,   # horizontal radius (m)
    geofence_alt=(1.0, 30.0),
    repulsion_gain=2.0,
    attraction_gain=1.0,
)

# One-shot filtering
positions = {"D1": Pose3D(0, 0, 10), "D2": Pose3D(1.5, 0, 10)}  # too close!
desired   = {"D1": Pose3D(0, 5, 10), "D2": Pose3D(3,   5, 10)}
safe      = apf.filter(positions, desired)
# D1 and D2 will be pushed apart before moving toward desired

# Check separation violations
violations = apf.check_separation(positions)
# → [("D1", "D2", 1.5)]  # 1.5m < 2.0m min

# Continuous 20Hz loop
loop = APFFilterLoop(
    apf=apf,
    get_positions=lambda: current_positions,
    get_desired=lambda: mission_waypoints,
    on_safe=lambda safe: send_to_drones(safe),
    on_violation=lambda v: print(f"WARNING: {v}"),
    hz=20.0,
)
loop.start()
```

**`Pose3D`** — position in local ENU (x=North, y=East, z=altitude above ground):

```python
p = Pose3D(10.0, 5.0, 15.0)   # 10m North, 5m East, 15m altitude
d = p.dist(Pose3D(0, 0, 0))   # Euclidean distance
```

---

### llm — Swarm Commander

**`droneresearch/llm/swarm_commander.py`**

Based on: *SkySim* (Shibu et al., 2025). Translates natural language commands into per-drone waypoints using an LLM, then passes them through the APF safety filter.

```python
from droneresearch.llm import SwarmCommander
from droneresearch.safety import APFSafetyFilter, Pose3D

commander = SwarmCommander(
    backend="gemini",           # "gemini" | "openai" | "ollama" | "mock"
    api_key="YOUR_API_KEY",     # or set DRONE_LLM_API_KEY env var
    apf=APFSafetyFilter(),
)

commander.update_state({
    "D1": Pose3D(0, 0, 10),
    "D2": Pose3D(3, 0, 10),
    "D3": Pose3D(6, 0, 10),
})

result = commander.command("Form a circle with 5 meter radius at 15m altitude")
print(result.explanation)       # LLM's description
print(result.waypoints)         # {drone_id: Pose3D} — APF-filtered
print(result.latency_ms)        # round-trip time in ms
```

**Supported backends:**

| Backend | Requirement | Notes |
|---|---|---|
| `mock` | None | Offline, deterministic — for testing |
| `gemini` | `pip install google-generativeai` + API key | Gemini 1.5 Pro |
| `openai` | `pip install openai` + API key | GPT-4o |
| `ollama` | Ollama running locally | `ollama pull llama3` |

**Mock backend recognized commands** (no API key needed):
`circle`, `line`, `v formation`, `wedge`, `grid`, `north/south/east/west`, `up/climb`, `land`, `hover/hold`

```bash
# Interactive offline demo
python examples/llm_swarm_control.py --backend mock --interactive
```

---

### ros — PX4 ROS2 Bridge

**`droneresearch/ros/px4_bridge.py`**

Native PX4 ↔ ROS2 integration via **uXRCE-DDS** (correct for PX4 v1.14+).  
**Not MAVLink-over-ROS. Not FastRTPS.** Direct uORB topic access.

```
PX4 FC (v1.14+)
  └─ uxrce_dds_client start -n uav_1 -t udp -h <companion_ip> -p 8888
                              │
Companion Computer
  └─ MicroXRCEAgent udp4 -p 8888
                              │
DroneResearch PX4ROS2Bridge
  subscribe: /uav_1/fmu/out/vehicle_attitude
             /uav_1/fmu/out/vehicle_status
             /uav_1/fmu/out/vehicle_global_position
             /uav_1/fmu/out/battery_status
  publish:   /uav_1/fmu/in/vehicle_command
             /uav_1/fmu/in/trajectory_setpoint
             /uav_1/fmu/in/offboard_control_mode
```

```python
from droneresearch.ros.px4_bridge import PX4ROS2Bridge

bridge = PX4ROS2Bridge(namespace="uav_1", publish_hz=20.0)
bridge.start()

bridge.arm()
bridge.takeoff(altitude=10.0)
bridge.set_offboard_mode()

# Position setpoint in ENU (auto-converted to PX4 NED)
bridge.set_position_setpoint_enu(east=5.0, north=5.0, up=10.0)

# Velocity setpoint in NED
bridge.set_velocity_setpoint_ned(vn=1.0, ve=0.0, vd=0.0)

print(bridge.telemetry)
bridge.land()
bridge.stop()
```

**Frame conventions (critical):**

| Frame | Used by | Convention |
|---|---|---|
| NED (North-East-Down) | PX4 natively | x=North, y=East, z=Down |
| ENU (East-North-Up) | ROS2 standard | x=East, y=North, z=Up |
| FRD (Forward-Right-Down) | PX4 body | Roll/Pitch/Yaw |
| FLU (Forward-Left-Up) | ROS2 body | Roll/Pitch/Yaw |

All conversions handled automatically by `ned_to_enu()`, `enu_to_ned()`, `frd_to_flu()`.

**Prerequisites:**
```bash
# 1. Install Micro XRCE-DDS Agent on companion
pip3 install --user micro-xrce-dds-agent
MicroXRCEAgent udp4 -p 8888

# 2. On FC (via MAVLink shell or at boot)
uxrce_dds_client start -t udp -h 192.168.1.10 -p 8888 -n uav_1

# 3. Install px4_msgs in ROS2 workspace
cd ~/ros2_ws/src && git clone https://github.com/PX4/px4_msgs
cd ~/ros2_ws && colcon build --packages-select px4_msgs
source install/setup.bash

# 4. SITL testing
PX4_UXRCE_DDS_NS=uav_1 make px4_sitl gz_x500
```

---

### exploration — Frontier & vswarm

#### Frontier-based 3D Exploration

**`droneresearch/exploration/frontier_bridge.py`**

Bridge to **larics Multi-Resolution Frontier-Based Planner** (IEEE RA-L 2021).  
GitHub: https://github.com/larics/uav_frontier_exploration_3d

```python
from droneresearch import Drone
from droneresearch.exploration import FrontierExplorationBridge

drone = Drone("tcp:127.0.0.1:5760")
drone.connect()
drone.arm()
drone.takeoff(5.0)

bridge = FrontierExplorationBridge(
    drone,
    point_cloud_topic="/camera/depth/points",
    on_volume_update=lambda v: print(f"Explored: {v['explored_pct']:.1f}%"),
)
bridge.start()
bridge.exploration_start()
bridge.wait_until_done(timeout=600)
bridge.save_octomap("/tmp/map")
drone.rtl()
```

**ROS2 topic mapping:**

| DroneResearch → | Explorer expects |
|---|---|
| `/exploration/odometry` | `nav_msgs/Odometry` |
| `/exploration/cloud_in` | `sensor_msgs/PointCloud2` |
| `/exploration/carrot_pose` | `geometry_msgs/PoseStamped` |
| ← `/exploration/point_reached` | `std_msgs/Bool` |
| ← `/exploration/octomap_volume` | `std_msgs/Float64MultiArray` |

#### Vision-based Swarm Flocking

**`droneresearch/exploration/vswarm_bridge.py`**

Bridge to **vswarm** (EPFL LIS, IEEE RA-L 2021).  
GitHub: https://github.com/lis-epfl/vswarm  
Decentralized, communication-free flocking via CNN + Reynolds rules.

```python
from droneresearch import Drone
from droneresearch.exploration import VSwarmBridge

drone = Drone("tcp:127.0.0.1:5760")
drone.connect()
drone.arm()
drone.takeoff(2.5)

bridge = VSwarmBridge(
    drone,
    camera_topic="/camera/image_raw",
    gain=0.5,   # velocity-to-position gain
)
bridge.start()
bridge.start_flocking()
```

---

### data — Telemetry Logging

**`droneresearch/data/logger.py`** — `TelemetryLogger`

Automatically logs all flights:
- `logs/YYYYMMDD_HHMMSS_telemetry.csv` — full telemetry at configured rate
- `logs/YYYYMMDD_HHMMSS_events.json` — arm/disarm/mode changes
- `logs/YYYYMMDD_HHMMSS.bag` — ROS bag (if ROS2 available)

**`droneresearch/data/store.py`** — `TelemetryStore`

Ring-buffer storing the last N telemetry snapshots in memory for real-time analysis.

```python
from droneresearch.data import TelemetryStore

store = TelemetryStore(maxlen=1000)
# Latest 10 altitude values
alts = [s.alt_rel for s in store.recent(10)]
```

---

### sdk — Public API

**`droneresearch/sdk/drone.py`** — `Drone`

```python
from droneresearch import Drone

drone = Drone("tcp:127.0.0.1:5760")
drone.connect()

drone.arm()
drone.takeoff(altitude=10)
drone.goto(lat=48.137, lon=11.575, alt=15)
drone.set_speed(3.0)
drone.rtl()
drone.land()
drone.disarm()
drone.disconnect()

# Event callbacks
@drone.on("altitude")
def on_alt(value):
    if value > 20:
        drone.rtl()

@drone.on("battery")
def on_bat(pct):
    if pct < 20:
        drone.land()

# Telemetry
t = drone.telemetry
print(f"{t.lat:.6f}, {t.lon:.6f}, {t.alt_rel:.1f}m")
```

**`droneresearch/sdk/swarm_api.py`** — `Swarm`

```python
from droneresearch import Swarm

swarm = Swarm()
swarm.add("D1", "tcp:127.0.0.1:5760")
swarm.add("D2", "tcp:127.0.0.1:5770")
swarm.connect_all()
swarm.arm_all()
swarm.takeoff_all(altitude=10)
swarm.formation("circle", spacing=5.0)
swarm.land_all()
```

---

### cli — Command Line

```bash
# Connect
droneresearch connect --port tcp:127.0.0.1:5760
droneresearch connect --port /dev/ttyUSB0 --baud 57600

# Flight commands
droneresearch arm
droneresearch takeoff --alt 10
droneresearch goto --lat 48.137 --lon 11.575 --alt 15
droneresearch rtl
droneresearch land

# Status
droneresearch status
droneresearch telemetry

# Experiment
droneresearch experiment run scenarios/hover_test.json
```

---

## Raspberry Pi Deployment

The `pi/` directory contains a resource-optimized server for **Raspberry Pi 1** (~700MHz ARM, 512MB RAM).

```bash
# One-shot install
chmod +x pi/install.sh
./pi/install.sh

# Manual start
python3 pi/server.py --port /dev/ttyAMA0 --baud 57600 --http-port 8080

# Autostart via systemd
sudo systemctl enable droneresearch
sudo systemctl start droneresearch
```

**REST API endpoints:**

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/telemetry` | Full telemetry JSON |
| GET | `/api/status` | Connection + armed status |
| POST | `/api/arm` | Arm motors |
| POST | `/api/disarm` | Disarm motors |
| POST | `/api/takeoff` | Takeoff `{"alt": 10}` |
| POST | `/api/land` | Land |
| POST | `/api/rtl` | Return to Launch |
| GET | `/api/logs` | Last 100 log lines |
| GET | `/` | Web dashboard |

**Resource profile:**
- RAM: ~20MB
- CPU: ~5% (Raspberry Pi 1 @ 700MHz)
- Dependencies: `pymavlink`, `pyserial` only (stdlib HTTP server)

See [`pi/README_PI.md`](pi/README_PI.md) for full Pi documentation.

---

## Docker

Three platform-specific containers + a multi-agent compose file.

```bash
# Build and run heterogeneous swarm simulation
cd docker
docker-compose up

# Individual containers
docker build -f Dockerfile.pi    -t droneresearch:pi      .
docker build -f Dockerfile.jetson -t droneresearch:jetson  .
docker build -f Dockerfile.x86   -t droneresearch:x86     .
```

**`docker-compose.yml`** spins up:
- `gcs` — x86 ground station coordinator
- `uav_generic` — Pi-style generic agent
- `uav_observation` — Jetson-style observation agent

---

## Examples

| Script | Description |
|---|---|
| `hover.py` | Connect, arm, hover at 10m, land |
| `event_based.py` | Event-driven altitude + battery monitoring |
| `speed_experiment.py` | Grid-search over cruise speeds |
| `swarm_circle.py` | 3-drone circle formation via `Swarm` API |
| `coordinator_demo.py` | Leader-follower V-formation with `CoordinatorUAVModel` |
| `autonomous_exploration.py` | Frontier-based 3D map building |
| `vswarm_flocking.py` | Camera-only Reynolds flocking |
| `px4_ros2_offboard.py` | PX4 offboard circle via uXRCE-DDS |
| `px4_multi_vehicle.py` | 3-drone PX4 formation via ROS2 namespaces |
| `llm_swarm_control.py` | Natural language → swarm waypoints |
| `full_research_pipeline.py` | Complete stack: SITL + FSM + APF + LLM + Metrics + Replay |

```bash
# All examples work offline with SITL or mock mode
python examples/llm_swarm_control.py --backend mock --interactive
python examples/full_research_pipeline.py --demo
python examples/coordinator_demo.py  # needs ArduPilot SITL
```

---

## Research Background

This platform implements and integrates concepts from recent UAV research:

| Paper | Integration |
|---|---|
| *Modular and Scalable System Architecture for Heterogeneous UAV Swarms* (2025) | `models/` — GenericUAV, ObservationUAV, CoordinatorUAV; FSM; Docker setup |
| *SkySim: ROS2 Simulation for Natural Language Control* (Shibu et al., arXiv:2602.01226) | `safety/apf.py` — APF filter; `llm/swarm_commander.py` — LLM→waypoints |
| *Multi-Resolution Frontier-Based 3D Exploration* (larics, IEEE RA-L 2021) | `exploration/frontier_bridge.py` |
| *Vision-based Swarm Flocking* (EPFL LIS, IEEE RA-L 2021) | `exploration/vswarm_bridge.py` |
| PX4 ROS2 User Guide (docs.px4.io/main/en/ros2) | `ros/px4_bridge.py` — uXRCE-DDS, frame conventions, multi-vehicle namespaces |

---

## Hardware

**Tested / supported:**

| Platform | Role | Notes |
|---|---|---|
| Raspberry Pi 1 (700MHz) | Companion computer | `pi/server.py` — stdlib only |
| Raspberry Pi 4/5 | Full stack | All features |
| Nvidia Jetson Orin NX | Observation UAV | GPU inference, ROS2 |
| x86 Linux / Windows | Development / GCS | Full simulation support |

**Autopilots:**
- ArduPilot (Copter 4.x+) via MAVLink
- PX4 v1.14+ via uXRCE-DDS (ROS2)

---

## Contributing

This is a research platform. Contributions welcome.

```bash
git clone https://github.com/joeldjio/uavresearchproject.git
cd uavresearchproject
pip install -e .

# Run a demo to verify setup
python examples/full_research_pipeline.py --demo
```

- See `examples/` for how to write experiments
- See `droneresearch/experiment/scenario.py` for the Scenario API
- See `droneresearch/autopilot/base.py` to add a new autopilot backend

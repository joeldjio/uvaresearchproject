# UAVResearch - Advanced Drone Research Platform

**Open-Source Ground Control Station with Modern Architecture**

[![Tests](https://github.com/joeldjio/uavresearchproject/workflows/Tests/badge.svg)](https://github.com/joeldjio/uavresearchproject/actions)
[![Coverage](https://codecov.io/gh/joeldjio/uavresearchproject/branch/main/graph/badge.svg)](https://codecov.io/gh/joeldjio/uavresearchproject)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/UI-PySide6%20%2F%20QML-green.svg)](https://doc.qt.io/qtforpython/)

> Professional drone control platform with declarative QML UI, real-time telemetry, swarm coordination, and advanced safety systems.

**Author:** Joel Djio  
**License:** MIT (Core) + LGPL v3 (UI)  
**Repository:** https://github.com/joeldjio/uavresearchproject

---

## 🚀 Technology Stack

### Core Platform
- **Python 3.10+** - Modern async/await, type hints, dataclasses
- **MAVLink Protocol** - Industry-standard drone communication
- **pymavlink** - MAVLink Python bindings (LGPL v3)
- **pyserial** - Serial/USB communication (BSD-3)

### User Interface
- **PySide6 (Qt for Python)** - Professional UI framework (LGPL v3)
- **QML** - Declarative UI language with hardware acceleration
- **Qt Quick** - Fluid animations and responsive layouts
- **Leaflet.js** - Interactive mapping with OpenStreetMap
- **Qt WebEngine** - Embedded web content

### Robotics Integration
- **ROS2 (Humble/Iron)** - Robot Operating System 2 (Apache 2.0)
- **rclpy** - ROS2 Python client library
- **px4_msgs** - PX4 message definitions (BSD-3)
- **uXRCE-DDS** - PX4 ROS2 bridge protocol

### Safety & Control
- **APF (Artificial Potential Field)** - Collision avoidance at 20Hz
- **Collision Predictor** - Time-to-collision estimation
- **Battery Monitor** - Real-time power management
- **Geofencing** - Polygon-based boundary enforcement

### Research Tools
- **Experiment Framework** - Reproducible scenario execution
- **Field Coverage Planner** - Multi-drone area coverage
- **Solar Inspection** - Automated panel inspection
- **Mission Engine** - Waypoint mission management

---

## ✨ Key Capabilities

### 🎯 Multi-Drone Swarm Control
- **Formation Flying** - 6 pre-defined formations (Line, V, Circle, Grid, Wedge, Custom)
- **Leader-Follower** - Coordinator-based swarm control
- **Distributed Allocation** - Auction-based task assignment
- **Collision Avoidance** - APF filter with configurable forces
- **Real-time Coordination** - 10Hz telemetry updates

### 🗺️ Advanced Mapping
- **Interactive Map** - OpenStreetMap with Leaflet.js
- **Real-time Tracking** - Multi-drone position visualization
- **Click-to-Goto** - Waypoint planning with map clicks
- **Flight Path History** - Trajectory visualization
- **Geofence Editor** - Polygon drawing and editing
- **Multi-layer Support** - Satellite, terrain, street views

### 📊 Telemetry & Monitoring
- **Position** - GPS coordinates, altitude (MSL & relative)
- **Velocity** - Groundspeed, climb rate, 3D velocity vector
- **Attitude** - Roll, pitch, yaw (Euler angles)
- **Battery** - Voltage, current, percentage, time remaining
- **GPS** - Fix type, satellite count, HDOP, VDOP
- **Flight Mode** - GUIDED, AUTO, LOITER, RTL, LAND
- **System Health** - Sensor status, calibration, errors

### 🔒 Safety Systems
- **APF Filter** ([`apf.py`](droneresearch/safety/apf.py))
  - Artificial Potential Field collision avoidance
  - 20Hz update rate
  - Configurable repulsion/attraction forces
  - Adaptive safety margins based on velocity
  
- **Collision Predictor** ([`collision_predictor.py`](droneresearch/safety/collision_predictor.py))
  - Predictive collision detection
  - Time-to-collision (TTC) estimation
  - Velocity-based risk assessment
  - Multi-drone conflict resolution

- **Battery Monitor** ([`battery_monitor.py`](droneresearch/safety/battery_monitor.py))
  - Real-time battery tracking
  - Low battery alerts (configurable thresholds)
  - Automatic RTL on critical level
  - Battery persistence across sessions

- **Geofencing**
  - Polygon-based boundaries
  - Altitude limits (min/max)
  - Automatic RTL on breach
  - Visual feedback in UI

### 🧪 Research Framework
- **Experiment Manager** ([`experiment/manager.py`](droneresearch/experiment/manager.py))
  - YAML-based scenario definition
  - Automated execution
  - Real-time metrics collection
  - Data export (CSV, JSON, ROS2 bags)

- **Field Coverage Planner** ([`field_coverage.py`](droneresearch/control/field_coverage.py))
  - Multi-drone area coverage
  - Boustrophedon pattern generation
  - Optimized waypoint allocation
  - Overlap configuration

- **Solar Inspection** ([`solar_inspection.py`](droneresearch/control/solar_inspection.py))
  - Automated solar panel inspection
  - Thermal camera integration
  - Defect detection
  - Grid-based flight patterns

- **Mission Engine** ([`mission.py`](droneresearch/control/mission.py))
  - Waypoint mission management
  - Async mission upload (non-blocking UI)
  - Mission validation
  - Progress monitoring

---

## 🏗️ Architecture

### Layered Design

```
┌─────────────────────────────────────────────────────────────┐
│                   QML UI Layer (Declarative)                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Dashboard │  │   Map    │  │  Swarm   │  │Experiment│   │
│  │  Panel   │  │  Panel   │  │  Panel   │  │  Panel   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Safety  │  │  Gimbal  │  │FlightLog │  │   Help   │   │
│  │  Panel   │  │  Panel   │  │  Panel   │  │  Panel   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                             ↕ Qt Signals/Properties
┌─────────────────────────────────────────────────────────────┐
│              Context Layer (Qt QObject Bridge)              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Telemetry │  │  Swarm   │  │Experiment│  │  Safety  │   │
│  │ Context  │  │ Context  │  │ Context  │  │ Context  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                             ↕ Python API
┌─────────────────────────────────────────────────────────────┐
│                   Backend Layer (Python)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Drone   │  │  Swarm   │  │  Safety  │  │ Mission  │   │
│  │   SDK    │  │   API    │  │   APF    │  │  Engine  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │   FSM    │  │Connection│  │Telemetry │                 │
│  │  Engine  │  │ Manager  │  │  Store   │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
                             ↕ MAVLink/ROS2
┌─────────────────────────────────────────────────────────────┐
│                 Communication Layer                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │ MAVLink  │  │  ROS2    │  │  Serial  │                 │
│  │(pymavlink│  │ (rclpy)  │  │(pyserial)│                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
                             ↕ TCP/UDP/Serial
┌─────────────────────────────────────────────────────────────┐
│                      Drone Hardware                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │ArduPilot │  │   PX4    │  │  Custom  │                 │
│  │  SITL    │  │  SITL    │  │Autopilot │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Input (QML) → Qt Signal → Context → Backend → MAVLink → Drone
                                            ↓
Drone → MAVLink → Backend → Qt Signal → Context → QML Property Update
```

### Thread Safety

- **UI Thread** - QML rendering, user input
- **Worker Threads** - Mission upload, file I/O, network requests
- **Telemetry Thread** - MAVLink message processing (10Hz)
- **Safety Thread** - APF filter, collision detection (20Hz)

All cross-thread communication uses Qt signals/slots for thread safety.

---

## 🚀 Quick Start

### Download Pre-built Binaries

**Latest Release:** [Download from GitHub Releases](https://github.com/joeldjio/rz-gcs-releases/releases/latest)

| Platform | Download | Installation |
|----------|----------|--------------|
| **Windows** | [uavresearch-gcs-setup-*.exe](https://github.com/joeldjio/rz-gcs-releases/releases/latest) | Run the installer |
| **macOS** | [uavresearch-gcs-macos.tar.gz](https://github.com/joeldjio/rz-gcs-releases/releases/latest) | Extract and drag to Applications |
| **Linux (Ubuntu 22.04)** | [*.deb](https://github.com/joeldjio/rz-gcs-releases/releases/latest) | `sudo dpkg -i *.deb` |

> **Note:** Windows Defender / macOS Gatekeeper may warn about unsigned binaries. Click *More info → Run anyway* (Windows) or right-click → Open (macOS).

### Install from Source

```bash
# Clone repository
git clone https://github.com/joeldjio/uavresearchproject.git
cd uavresearchproject

# Install core package
pip install -e .

# Install UI dependencies (PySide6 + QML)
pip install -r requirements.txt

# Optional: ROS2 support
pip install -e ".[ros]"
```

### Launch UI

```bash
# Start QML UI
python -m tools.ui

# With debug logging
python -m tools.ui --debug

# Profile startup performance
python tools/ui/startup_profiler.py
```

### Connect to Drone

```bash
# ArduPilot SITL (default port 5762)
sim_vehicle.py -v ArduCopter

# PX4 SITL with Gazebo (port 14540)
make px4_sitl gazebo

# Connect in UI: tcp:127.0.0.1:5762 (ArduPilot) or udp:127.0.0.1:14540 (PX4)
```

---

## 💻 Code Examples

### Basic Flight Control

```python
from droneresearch.sdk import Drone

# Connect to drone
drone = Drone("tcp:127.0.0.1:5762")
drone.connect()

# Arm and takeoff
drone.arm()
drone.takeoff(altitude=10)

# Goto waypoint
drone.goto(lat=47.397742, lon=8.545594, alt=15)

# Land
drone.land()
```

### Swarm Formation

```python
from droneresearch.sdk import Swarm

# Create swarm
swarm = Swarm([
    "tcp:127.0.0.1:5762",
    "tcp:127.0.0.1:5772",
    "tcp:127.0.0.1:5782"
])

# Connect and arm all
swarm.connect_all()
swarm.arm_all()
swarm.takeoff_all(altitude=10)

# Form V-formation with 5m spacing
swarm.set_formation("v", spacing=5.0)

# Move formation north 20m
swarm.move_formation(north=20)

# Land all
swarm.land_all()
```

### Field Coverage Planning

```python
from droneresearch.control import FieldCoveragePlanner

# Define field boundary (lat/lon polygon)
boundary = [
    (47.397742, 8.545594),
    (47.397742, 8.546594),
    (47.398742, 8.546594),
    (47.398742, 8.545594)
]

# Create planner
planner = FieldCoveragePlanner(
    boundary=boundary,
    altitude=15,
    overlap=0.2,  # 20% overlap
    num_drones=3
)

# Generate waypoints
missions = planner.plan()

# Upload to drones
for drone_id, mission in missions.items():
    drone = swarm.get_drone(drone_id)
    drone.upload_mission(mission)
    drone.start_mission()
```

### Safety Systems

```python
from droneresearch.safety import APFFilter, BatteryMonitor

# Configure APF filter
apf = APFFilter(
    repulsion_gain=2.0,
    attraction_gain=1.0,
    safety_radius=5.0,
    update_rate=20  # Hz
)

# Start APF filter
apf.start()

# Configure battery monitor
battery = BatteryMonitor(
    low_threshold=30.0,  # 30%
    critical_threshold=15.0,  # 15%
    rtl_on_critical=True
)

# Start monitoring
battery.start()
```

---

## 🧪 Testing

### Test Coverage

| Component | Coverage | Tests | Description |
|-----------|----------|-------|-------------|
| **UI Contexts** | **100%** | **71** | QML-Python bridge |
| Core (FSM, Connection) | 85% | 25 | State machine, MAVLink |
| Control (Mission, Coverage) | 80% | 18 | Mission planning |
| Safety (APF, Collision) | 90% | 15 | Safety systems |
| SDK (Drone, Swarm) | 75% | 22 | High-level API |
| ROS2 (Bridge, Bag) | 70% | 12 | ROS2 integration |

### Run Tests

```bash
# All tests (~1 second, hardware-free)
pytest tests/

# UI context tests
pytest tests/ -k "context"

# Safety system tests
pytest tests/ -k "apf or collision or battery"

# E2E UI tests (requires display)
pytest tests/e2e/ -m e2e

# With coverage report
pytest tests/ --cov=droneresearch --cov=tools.ui --cov-report=html

# Fast tests only (skip slow markers)
pytest tests/ -m "not slow"
```

---

## 📚 Documentation

### Technical Documentation

| Document | Description |
|----------|-------------|
| [**Software Documentation**](docs/SOFTWARE_DOCUMENTATION.md) | Complete technical reference |
| [API Reference](docs/api/reference.md) | Full API documentation |
| [Core API](docs/api/core.md) | FSM, Connection, Telemetry |
| [Control API](docs/api/control.md) | Mission, Coverage, Solar |
| [Safety API](docs/api/safety.md) | APF, Collision, Battery |

### Feature Documentation

| Document | Description |
|----------|-------------|
| [Field Coverage Planning](docs/features/field-coverage-planning.md) | Multi-drone area coverage |
| [Swarm Coordination](docs/features/swarm-coordination.md) | Formation flying |
| [Solar Inspection](docs/features/solar-inspection.md) | Automated panel inspection |
| [Battery Monitoring](docs/features/battery-monitoring.md) | Power management |
| [Collision Prediction](docs/features/collision-prediction.md) | Safety systems |
| [Async Mission Upload](docs/features/async-mission-upload.md) | Non-blocking UI |

### Setup Guides

| Document | Description |
|----------|-------------|
| [Installation Guide](docs/setup/installation.md) | Setup instructions |
| [PX4 Hardware Setup](docs/setup/px4-hardware-setup.md) | PX4 configuration |
| [Frame Conventions](docs/setup/frame-conventions.md) | NED/ENU coordinates |
| [PX4 Mission Upload](docs/setup/px4-mission-upload.md) | Mission protocol |

### UI Documentation

| Document | Description |
|----------|-------------|
| [UI Documentation](docs/ui/ui-documentation.md) | Complete UI reference |
| [Formation Preview](docs/ui/formation-preview.md) | 2D Canvas visualization |
| [Escape UI Integration](docs/ui/escape-ui-integration-guide.md) | ESCAPE framework |

---

## 📄 License & Commercial Use

### Project License

**UAVResearch** is licensed under the **MIT License**, allowing:
- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Private use
- ✅ Sublicensing

See [`LICENSE`](LICENSE) for full terms.

### Third-Party Components

| Component | License | Commercial Use | Notes |
|-----------|---------|----------------|-------|
| **PySide6** | LGPL v3 | ✅ Yes | Qt for Python (dynamically linked) |
| **pymavlink** | LGPL v3+ | ✅ Yes | MAVLink protocol library |
| **pyserial** | BSD-3-Clause | ✅ Yes | Serial communication |
| **psutil** | BSD-3-Clause | ✅ Yes | System monitoring |
| **ROS2** | Apache 2.0 | ✅ Yes | Optional dependency |
| **pytest** | MIT | ✅ Yes | Development only |

**Full license texts:** [`THIRD_PARTY_LICENSES.txt`](THIRD_PARTY_LICENSES.txt)  
**Copyright notices:** [`NOTICE.txt`](NOTICE.txt)

### PySide6 Migration (2026-06)

Migrated from PyQt6 (GPL v3) to PySide6 (LGPL v3) for commercial compatibility.

**Benefits:**
- ✅ Commercial closed-source distribution allowed
- ✅ No license fees
- ✅ No source code disclosure required
- ✅ LGPL compliance via dynamic linking

**Details:** [`docs/security/LICENSE_AUDIT_2026-06.md`](docs/security/LICENSE_AUDIT_2026-06.md)

### Research Paper Citations

Algorithms implemented from:
- **APF Safety Filter:** Shibu et al., "SkySim" (arXiv:2602.01226, 2025)
- **Vision-based Flocking:** Schilling et al., IEEE RA-L 2021
- **Frontier Exploration:** Batinovic et al., IEEE RA-L 2021

---

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone and install
git clone https://github.com/joeldjio/uavresearchproject.git
cd uavresearchproject
pip install -r requirements.txt
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run UI
python -m tools.ui --debug
```

### QML Development

```bash
# Edit QML files in tools/ui/qml/
# Changes are hot-reloaded (no restart needed)

# Test UI workflows
pytest tests/e2e/test_ui_workflows.py -v

# Profile UI performance
python tools/ui/startup_profiler.py
```

---

## 🗺️ Roadmap

### Current (v0.3.x)
- ✅ PySide6/QML UI with declarative design
- ✅ Interactive map with Leaflet.js
- ✅ Swarm coordination with 6 formations
- ✅ Real-time telemetry (10Hz)
- ✅ Safety systems (APF 20Hz, collision prediction, battery monitor)
- ✅ 100% UI test coverage
- ✅ Commercial-friendly licensing (MIT + LGPL v3)
- ✅ Field coverage planning
- ✅ Solar inspection
- ✅ ROS2 integration

### Next (v0.4.x)
- ⏳ 3D visualization with Qt3D
- ⏳ Video streaming integration
- ⏳ Mission planner with drag-and-drop
- ⏳ Multi-language support (EN, DE, FR)
- ⏳ Mobile companion app

### Future (v0.5.x)
- ⏳ Web-based UI (React/Vue)
- ⏳ Cloud integration
- ⏳ AI-powered flight planning
- ⏳ VR/AR support

---

## 📞 Support

- **Documentation:** [`docs/`](docs/)
- **Issues:** [GitHub Issues](https://github.com/joeldjio/uavresearchproject/issues)
- **Discussions:** [GitHub Discussions](https://github.com/joeldjio/uavresearchproject/discussions)

---

## 🙏 Acknowledgments

- **ArduPilot Team** - MAVLink protocol and pymavlink library
- **Qt Company** - PySide6 (Qt for Python)
- **Open Source Robotics Foundation** - ROS2 framework
- **Research Community** - Papers and algorithms

---

**Made with ❤️ for drone research**

**⭐ Star us on GitHub if you find this project useful!**

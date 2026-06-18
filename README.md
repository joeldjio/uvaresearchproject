# UAVResearch Ground Control Station

**Professional Drone Control Software with Modern UI**

[![Tests](https://github.com/joeldjio/uavresearchproject/workflows/Tests/badge.svg)](https://github.com/joeldjio/uavresearchproject/actions)
[![Coverage](https://codecov.io/gh/joeldjio/uavresearchproject/branch/main/graph/badge.svg)](https://codecov.io/gh/joeldjio/uavresearchproject)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> Modern ground control station for drone research with intuitive UI, real-time 3D visualization, and advanced swarm coordination.

**Author:** Joel Djio  
**License:** MIT  
**Repository:** https://github.com/joeldjio/uavresearchproject

---

## 🎯 What is UAVResearch GCS?

**UAVResearch GCS** is a professional ground control station designed for researchers, developers, and drone enthusiasts who need:

- 🖥️ **Modern Desktop UI** - PySide6/QML interface with dark theme and 3D visualization
- 🗺️ **Interactive Map** - Real-time drone tracking on OpenStreetMap with Leaflet.js
- 🤖 **Swarm Control** - Manage multiple drones with formation flying and coordination
- 📊 **Live Telemetry** - Real-time monitoring of position, battery, GPS, and flight mode
- 🔒 **Safety Systems** - Built-in collision avoidance and geofencing
- 🧪 **Experiment Framework** - Run reproducible research scenarios with metrics
- 🌐 **Multi-Platform** - Works with ArduPilot, PX4, and supports ROS2 integration

---

## 🖼️ User Interface

### Main Dashboard

The GCS features a modern, dark-themed interface with multiple panels:

**Dashboard Panel** - Live telemetry and drone status
- Real-time position (GPS coordinates, altitude)
- Battery level and voltage monitoring
- Flight mode and armed status
- GPS fix quality and satellite count
- Connection status indicator

**Map Panel** - Interactive drone tracking
- OpenStreetMap integration with Leaflet.js
- Real-time drone position markers
- Flight path visualization
- Waypoint planning and editing
- Geofence visualization
- Multi-drone tracking

**Swarm Panel** - Multi-drone coordination
- Formation selection (Line, V, Circle, Grid, Wedge, Custom)
- Formation preview with 2D visualization
- Individual drone control
- Swarm-wide commands (arm, takeoff, land, RTL)
- Leader-follower coordination

**Experiment Panel** - Research workflow
- Scenario definition and execution
- Real-time metrics collection
- Data export (CSV, JSON)
- Experiment replay

**Safety Panel** - Collision avoidance
- APF (Artificial Potential Field) filter
- Geofence monitoring
- Obstacle detection
- Safety parameter configuration

**ROS2 Panel** - ROS2 integration
- Bag recording controls
- Topic monitoring
- PX4 uXRCE-DDS bridge status
- Frame conversion (NED ↔ ENU)

**Log Panel** - System monitoring
- Real-time log viewer
- Log level filtering
- Telemetry export
- Session recording

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/joeldjio/uavresearchproject.git
cd uavresearchproject

# Install with UI dependencies
pip install -e .
pip install -r requirements.txt

# With ROS2 support (optional)
pip install -e ".[ros]"
```

### Launch Ground Control Station

```bash
# Start the UI
python -m tools.ui

# Or use the launcher script
python tools/ui/app.py
```

### Connect to Drone

1. **Start SITL** (for simulation):
   ```bash
   # ArduPilot SITL
   sim_vehicle.py -v ArduCopter
   
   # PX4 SITL with Gazebo
   make px4_sitl gazebo
   ```

2. **Connect in UI**:
   - Open Dashboard panel
   - Click "Connect" button
   - Default: `tcp:127.0.0.1:5762` (ArduPilot SITL)
   - For PX4: `udp:127.0.0.1:14540`

3. **Fly**:
   - Arm drone
   - Takeoff to desired altitude
   - Monitor telemetry in real-time
   - View position on map
   - Land when finished

---

## ✨ Key Features

### 🎨 Modern UI/UX

- **Dark Theme** - Professional, eye-friendly interface
- **Responsive Layout** - Adapts to different screen sizes
- **Real-time Updates** - 10Hz telemetry refresh rate
- **Smooth Animations** - Fluid transitions and interactions
- **Keyboard Shortcuts** - Efficient workflow
- **Status Indicators** - Clear visual feedback

### 🗺️ Interactive Mapping

- **OpenStreetMap** - High-quality base maps
- **Leaflet.js Integration** - Smooth pan and zoom
- **Drone Markers** - Color-coded by ID
- **Flight Trails** - Historical path visualization
- **Waypoint Editor** - Click to add/edit waypoints
- **Geofence Drawing** - Define safe zones
- **Multi-layer Support** - Satellite, terrain, street views

### 🤖 Swarm Coordination

- **6 Formation Types**:
  - **Line** - Drones in a straight line
  - **V-Formation** - Classic V-shape
  - **Circle** - Circular pattern
  - **Grid** - Rectangular grid
  - **Wedge** - Tactical wedge formation
  - **Custom** - User-defined positions

- **Formation Preview** - 2D visualization before execution
- **Dynamic Scaling** - Adjust spacing and size
- **Leader-Follower** - Coordinator-based control
- **Collision Avoidance** - APF filter integration

### 📊 Telemetry Monitoring

Real-time display of:
- **Position**: Latitude, Longitude, Altitude (MSL & Relative)
- **Velocity**: Groundspeed, Climb rate
- **Attitude**: Roll, Pitch, Yaw
- **Battery**: Voltage, Current, Percentage
- **GPS**: Fix type, Satellite count, HDOP
- **Flight Mode**: GUIDED, AUTO, LOITER, RTL, etc.
- **System**: Armed status, Connection quality

### 🔒 Safety Systems

- **APF Filter** - Artificial Potential Field collision avoidance
  - Runs at 20Hz
  - Configurable repulsion/attraction forces
  - Real-time obstacle detection
  
- **Geofencing** - Define safe operating zones
  - Polygon-based boundaries
  - Altitude limits
  - Automatic RTL on breach

- **Pre-flight Checks** - Automated safety verification
  - GPS fix quality
  - Battery level
  - Sensor health
  - Calibration status

### 🧪 Research Tools

- **Experiment Framework**:
  - Define scenarios with YAML
  - Automated execution
  - Metrics collection (position error, timing, battery)
  - Data export (CSV, JSON, ROS2 bags)
  
- **Replay System**:
  - Playback recorded flights
  - Variable speed control
  - Frame-by-frame analysis
  
- **LLM Integration**:
  - Natural language commands
  - "Form a circle with 5 meter radius"
  - "Move north 10 meters"
  - Supports Gemini, OpenAI, Ollama

---

## 🎮 Usage Examples

### Basic Flight

```python
from droneresearch.sdk import Drone

# Connect to drone
drone = Drone("tcp:127.0.0.1:5762")
drone.connect()

# Arm and takeoff
drone.arm()
drone.takeoff(altitude=10)

# Hover for 10 seconds
import time
time.sleep(10)

# Land
drone.land()
```

### Swarm Formation

```python
from droneresearch.sdk import Swarm

# Create swarm with 3 drones
swarm = Swarm([
    "tcp:127.0.0.1:5762",
    "tcp:127.0.0.1:5772",
    "tcp:127.0.0.1:5782"
])

# Connect all
swarm.connect_all()

# Arm and takeoff
swarm.arm_all()
swarm.takeoff_all(altitude=10)

# Form V-formation
swarm.set_formation("v", spacing=5.0)

# Move formation north
swarm.move_formation(north=20)

# Land all
swarm.land_all()
```

### Natural Language Control

```python
from droneresearch.llm import SwarmCommander

# Initialize with Gemini API
commander = SwarmCommander(
    api_key="your-api-key",
    provider="gemini"
)

# Execute natural language commands
commander.execute("Form a circle with 5 meter radius")
commander.execute("Move the formation north 10 meters")
commander.execute("Land all drones safely")
```

---

## 📚 Documentation

### User Guides

| Guide | Description |
|-------|-------------|
| [**UI Documentation**](docs/ui/ui-documentation.md) | Complete UI reference |
| [Installation Guide](docs/setup/installation.md) | Setup instructions |
| [PX4 Setup](docs/setup/px4-sitl.md) | PX4 SITL configuration |
| [Raspberry Pi](docs/setup/raspberry-pi.md) | Pi deployment |

### Feature Documentation

| Document | Description |
|----------|-------------|
| [Formation Preview](docs/ui/formation-preview.md) | 2D formation visualization |
| [Bag Playback](docs/ui/bag-playback-controls.md) | ROS2 bag replay |
| [Async Mission Upload](docs/features/async-mission-upload.md) | Non-blocking UI |
| [Memory Profiling](docs/development/memory-profiling.md) | Qt memory optimization |

### Developer Documentation

| Document | Description |
|----------|-------------|
| [**Software Documentation**](docs/SOFTWARE_DOCUMENTATION.md) | Technical reference |
| [Contributing Guide](CONTRIBUTING.md) | Development workflow |
| [Test Strategy](docs/testing/test-strategy.md) | Testing best practices |
| [CI/CD Guide](docs/testing/ci-cd-guide.md) | GitHub Actions |

---

## 🏗️ Architecture

### UI Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      PyQt6/QML UI Layer                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Dashboard │  │   Map    │  │  Swarm   │  │Experiment│   │
│  │  Panel   │  │  Panel   │  │  Panel   │  │  Panel   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │  Safety  │  │  ROS2    │  │   Log    │                 │
│  │  Panel   │  │  Panel   │  │  Panel   │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                    Context Layer (Qt)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Telemetry │  │  Swarm   │  │Experiment│  │  Safety  │   │
│  │ Context  │  │ Context  │  │ Context  │  │ Context  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                   Backend Layer (Python)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Drone   │  │  Swarm   │  │  Safety  │  │   LLM    │   │
│  │   SDK    │  │   API    │  │   APF    │  │Commander │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Input → Qt Signal → Context → Backend → MAVLink → Drone
                                      ↓
Drone → MAVLink → Backend → Qt Signal → Context → UI Update
```

---

## 🧪 Testing

### Test Coverage

| Component | Coverage | Tests |
|-----------|----------|-------|
| **UI Contexts** | **100%** | **71** |
| Core (FSM, Connection) | 85% | 25 |
| Control (Mission) | 80% | 18 |
| Safety (APF) | 90% | 15 |
| SDK (Drone, Swarm) | 75% | 22 |
| ROS2 (Bridge, Bag) | 70% | 12 |

### Run Tests

```bash
# All tests
pytest tests/

# UI tests only
pytest tests/ -m ui

# E2E tests (requires display)
pytest tests/e2e/ -m e2e

# With coverage
pytest tests/ --cov=droneresearch --cov=tools.ui
```

---

## 🎨 UI Customization

### Theme Configuration

The UI uses a dark theme by default. Customize in `tools/ui/style.py`:

```python
# Colors
BACKGROUND = "#1e1e1e"
FOREGROUND = "#ffffff"
ACCENT = "#0078d4"
SUCCESS = "#4caf50"
WARNING = "#ff9800"
ERROR = "#f44336"

# Fonts
FONT_FAMILY = "Segoe UI"
FONT_SIZE = 10
```

### Layout Configuration

Adjust panel sizes and positions in `tools/ui/main_window.py`:

```python
# Panel sizes
DASHBOARD_WIDTH = 400
MAP_HEIGHT = 600

# Update rates
TELEMETRY_RATE = 10  # Hz
MAP_UPDATE_RATE = 5  # Hz
```

---

## 🐳 Docker Deployment

Run the GCS in a container:

```bash
# Build image
docker build -f docker/Dockerfile.x86 -t uavresearch-gcs .

# Run with X11 forwarding (Linux)
docker run -it --rm \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  uavresearch-gcs

# Run with VNC (headless)
docker run -it --rm \
  -p 5900:5900 \
  uavresearch-gcs
```

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### UI Development

1. **Setup**:
   ```bash
   pip install -e .
   pip install -r requirements.txt
   ```

2. **Run in development mode**:
   ```bash
   python -m tools.ui --debug
   ```

3. **Make changes** to QML files in `tools/ui/qml/`

4. **Test**:
   ```bash
   pytest tests/e2e/ -m ui
   ```

5. **Submit PR** with screenshots/GIFs

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Qt Framework** - Cross-platform UI framework
- **Leaflet.js** - Interactive mapping library
- **PyQt6** - Python bindings for Qt
- **MAVLink** - Micro Air Vehicle communication protocol
- **PX4** - Open-source flight control software
- **ArduPilot** - Versatile autopilot software

---

## 📞 Support

- **Documentation:** [docs/](docs/)
- **Issues:** [GitHub Issues](https://github.com/joeldjio/uavresearchproject/issues)
- **Discussions:** [GitHub Discussions](https://github.com/joeldjio/uavresearchproject/discussions)

---

## 🗺️ Roadmap

### Current (v0.3.x)
- ✅ Modern PyQt6/QML UI
- ✅ Interactive map with Leaflet.js
- ✅ Swarm coordination with formations
- ✅ Real-time telemetry monitoring
- ✅ Safety systems (APF, geofencing)
- ✅ 100% UI test coverage

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

**Made with ❤️ for the drone research community**

**⭐ Star us on GitHub if you find this project useful!**


---

## 📄 License & Commercial Use

### Project License

**UAVResearch GCS** is licensed under the **MIT License**, allowing:
- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Private use
- ✅ Sublicensing

See [`LICENSE`](LICENSE) for full terms.

### Third-Party Components

This project uses the following open-source components:

| Component | License | Commercial Use | Notes |
|-----------|---------|----------------|-------|
| **PySide6** | LGPL v3 | ✅ Yes | Qt for Python (dynamically linked) |
| **pymavlink** | LGPL v3+ | ✅ Yes | MAVLink protocol library |
| **pyserial** | BSD-3-Clause | ✅ Yes | Serial communication |
| **psutil** | BSD-3-Clause | ✅ Yes | System monitoring |
| **ROS2** | Apache 2.0 | ✅ Yes | Optional dependency |
| **pytest** | MIT | ✅ Yes | Development only |

**Full license texts:** See [`THIRD_PARTY_LICENSES.txt`](THIRD_PARTY_LICENSES.txt)  
**Copyright notices:** See [`NOTICE.txt`](NOTICE.txt)

### PySide6 Migration (2026-06)

The project migrated from PyQt6 (GPL v3) to PySide6 (LGPL v3) to enable commercial use without GPL restrictions.

**Key Benefits:**
- ✅ Commercial closed-source distribution allowed
- ✅ No license fees (LGPL v3 is free)
- ✅ No source code disclosure required
- ✅ LGPL compliance via dynamic linking (standard in Python)

**Migration Details:** See [`docs/security/PYSIDE6_MIGRATION_GUIDE.md`](docs/security/PYSIDE6_MIGRATION_GUIDE.md)  
**License Audit:** See [`docs/security/LICENSE_AUDIT_2026-06.md`](docs/security/LICENSE_AUDIT_2026-06.md)

### LGPL Compliance

PySide6 and pymavlink are used under LGPL v3, which requires:

1. **Dynamic Linking** ✅ - Python naturally uses dynamic linking
2. **User Replacement** ✅ - Users can replace via `pip install PySide6`
3. **License Notice** ✅ - Included in `THIRD_PARTY_LICENSES.txt`
4. **No Modifications** ✅ - No changes made to LGPL libraries

### Research Paper Citations

This project implements algorithms from:

- **APF Safety Filter:** Shibu et al., "SkySim" (arXiv:2602.01226, 2025)
- **Vision-based Flocking:** Schilling et al., IEEE RA-L 2021
- **Frontier Exploration:** Batinovic et al., IEEE RA-L 2021

### Commercial Distribution Checklist

When distributing UAVResearch GCS commercially:

- [x] Include `LICENSE` (MIT)
- [x] Include `THIRD_PARTY_LICENSES.txt`
- [x] Include `NOTICE.txt`
- [x] Document PySide6 dynamic linking
- [x] Provide instructions for replacing PySide6/pymavlink
- [x] No modifications to LGPL libraries

**Legal Disclaimer:** This is not legal advice. Consult a lawyer for commercial distribution.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone repository
git clone https://github.com/joeldjio/uavresearchproject.git
cd uavresearchproject

# Install dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run UI
python -m tools.ui
```

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
- **Research Community** - Papers and algorithms implemented

---

**Made with ❤️ for drone research**

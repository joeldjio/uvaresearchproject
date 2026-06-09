# DroneResearch Platform

**Enterprise-Grade UAV Research Middleware with ROS2 Integration**

[![Tests](https://github.com/joeldjio/uavresearchproject/workflows/Tests/badge.svg)](https://github.com/joeldjio/uavresearchproject/actions)
[![Coverage](https://codecov.io/gh/joeldjio/uavresearchproject/branch/main/graph/badge.svg)](https://codecov.io/gh/joeldjio/uavresearchproject)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue.svg)](https://docs.ros.org/en/humble/)

> A modular, scriptable, simulation-first research framework for autonomous drone experiments, swarm coordination, and natural language control.

**Author:** Joel Djio  
**License:** MIT  
**Repository:** https://github.com/joeldjio/uavresearchproject

---

## 🎯 What is DroneResearch?

DroneResearch is a **professional UAV research middleware platform** designed for:

- ✅ **Reproducible Experiments** - Quantitative metrics, scenario definitions, grid-search
- ✅ **Simulation-First** - SITL → Real hardware, same code
- ✅ **Heterogeneous Swarms** - Leader-follower, formations, multi-role coordination
- ✅ **Natural Language Control** - LLM-powered swarm commands (Gemini/OpenAI/Ollama)
- ✅ **Autonomous Exploration** - Frontier planning, vision-based flocking
- ✅ **Enterprise Testing** - 235 tests, 70% coverage, CI/CD pipeline
- ✅ **Production Ready** - Raspberry Pi deployment, Docker containers, ROS2 integration

### Key Features

| Feature | Description |
|---------|-------------|
| **Hardware Abstraction** | Unified API for ArduPilot, PX4 (MAVLink + uXRCE-DDS) |
| **State Machine** | Thread-safe FSM with 10 states, event callbacks |
| **Safety Systems** | APF filter (20Hz), geofencing, collision avoidance |
| **Swarm Coordination** | 6 formations (Line/V/Circle/Grid/Wedge/Custom) |
| **ROS2 Native** | PX4 uXRCE-DDS bridge, bag recording, frame conversions |
| **LLM Integration** | Natural language → waypoints via Gemini/OpenAI/Ollama |
| **Experiment Framework** | Scenario definitions, metrics collection, replay |
| **Desktop UI** | PyQt6/QML dashboard with 3D visualization |
| **Raspberry Pi** | Optimized server (~20MB RAM, stdlib-only) |
| **Testing** | 235 tests (Unit/Integration/UI/System/E2E), 70% coverage |

---

## 📊 Project Status

| Metric | Value | Status |
|--------|-------|--------|
| **Tests** | 235 (95% passing) | ✅ |
| **Coverage** | 70% overall, 100% UI | ✅ |
| **CI/CD** | 8 jobs, <10min runtime | ✅ |
| **Documentation** | 5000+ lines | ✅ |
| **Python** | 3.10, 3.11, 3.12 | ✅ |
| **ROS2** | Humble, Jazzy | ✅ |
| **Autopilots** | ArduPilot 4.x, PX4 v1.14+ | ✅ |

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/joeldjio/uavresearchproject.git
cd uavresearchproject

# Install core package
pip install -e .

# With ROS2 support (requires ROS2 Humble/Jazzy)
pip install -e ".[ros]"

# With test dependencies
pip install -e ".[test]"

# Install pre-commit hooks (recommended)
pip install pre-commit
pre-commit install
```

### First Flight (SITL)

```bash
# Start ArduPilot SITL (default: tcp:127.0.0.1:5762)
# In separate terminal: sim_vehicle.py -v ArduCopter

# Run hover example
python examples/hover.py

# Or use CLI
droneresearch connect
droneresearch arm
droneresearch takeoff --alt 10
droneresearch status
droneresearch land
```

### LLM Swarm Control (Offline Demo)

```bash
# No API key needed - uses mock backend
python examples/llm_swarm_control.py --backend mock --interactive

# Commands:
# > "Form a circle with 5 meter radius"
# > "Move north 10 meters"
# > "Land all drones"
```

### Run Tests

```bash
# Fast tests (unit + integration, ~4s)
make test-fast

# All tests
make test-all

# With coverage report
make test-coverage
# Opens htmlcov/index.html
```

---

## 📚 Documentation

### Core Documentation

| Document | Description |
|----------|-------------|
| [**Software Documentation**](docs/SOFTWARE_DOCUMENTATION.md) | Complete technical reference |
| [Installation Guide](docs/setup/installation.md) | Setup instructions |
| [Contributing Guide](CONTRIBUTING.md) | Development workflow |
| [Changelog](CHANGELOG.md) | Version history |

### Feature Guides

| Guide | Description |
|-------|-------------|
| [PX4 SITL Setup](docs/setup/px4-sitl.md) | PX4 Gazebo simulation |
| [PX4 Hardware Setup](docs/setup/px4-hardware-setup.md) | Real PX4 flight controller |
| [Raspberry Pi Deployment](docs/setup/raspberry-pi.md) | Pi 1/4/5 setup |
| [Formation Preview](docs/ui/formation-preview.md) | 2D formation visualization |
| [Bag Playback](docs/ui/bag-playback-controls.md) | ROS2 bag replay |
| [Async Mission Upload](docs/features/async-mission-upload.md) | Non-blocking UI |

### Testing & Development

| Document | Description |
|----------|-------------|
| [Test Strategy](docs/testing/test-strategy.md) | Test pyramid, best practices |
| [CI/CD Guide](docs/testing/ci-cd-guide.md) | GitHub Actions, Codecov |
| [E2E Setup](docs/testing/e2e-setup.md) | End-to-end UI testing |
| [UI Audit](docs/ui/ui-audit-2026-06.md) | UI/UX analysis |
| [Memory Profiling](docs/development/memory-profiling.md) | Qt memory leak detection |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   CLI    │  │ Desktop  │  │  Python  │  │   REST   │   │
│  │          │  │    UI    │  │   SDK    │  │   API    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                   Middleware Layer                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Swarm   │  │  Safety  │  │   LLM    │  │Experiment│   │
│  │Coordinator│  │   APF    │  │Commander │  │ Manager  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Mission  │  │   FSM    │  │Telemetry │  │  Logger  │   │
│  │ Engine   │  │          │  │  Store   │  │          │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                Hardware Abstraction Layer                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ MAVLink  │  │   PX4    │  │  ROS2    │  │   SITL   │   │
│  │ Backend  │  │ uXRCE-DDS│  │  Bridge  │  │ Launcher │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Hardware Layer                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ArduPilot │  │   PX4    │  │Raspberry │  │  Gazebo  │   │
│  │   FC     │  │   FC     │  │    Pi    │  │   SITL   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧪 Testing

### Test Pyramid

```
        /\
       /E2E\      10 tests  (~10min, Qt UI workflows)
      /------\
     /System \    33 tests  (~5min, SITL integration)
    /----------\
   /Integration\  71 tests  (~3s, Fake connections)
  /--------------\
 /     Unit      \ 111 tests (~1s, Pure logic)
/------------------\
```

### Run Tests

```bash
# Fast tests (unit + integration)
make test-fast

# Specific categories
make test-unit          # Unit tests only
make test-integration   # Integration tests
make test-ui            # UI tests (PyQt6/QML)
make test-system        # System tests (requires SITL)
make test-e2e           # E2E tests (Qt workflows)

# With coverage
make test-coverage
```

### Coverage by Component

| Component | Coverage | Tests |
|-----------|----------|-------|
| Core (FSM, Connection) | 85% | 25 |
| Control (Mission) | 80% | 18 |
| Safety (APF) | 90% | 15 |
| SDK (Drone, Swarm) | 75% | 22 |
| ROS2 (Bridge, Bag) | 70% | 12 |
| **UI (Contexts)** | **100%** | **71** |
| Data (Logger) | 80% | 14 |
| Simulation (SITL) | 60% | 8 |
| Experiment | 65% | 10 |

---

## 🔧 Development

### Setup Development Environment

```bash
# Install with test dependencies
pip install -e ".[test]"

# Install pre-commit hooks
pre-commit install

# Run linters
make lint

# Auto-format code
make format
```

### Makefile Commands

```bash
# Installation
make install          # Core package
make install-test     # With test dependencies
make install-ros      # With ROS2 support

# Testing
make test-fast        # Fast tests (~4s)
make test-all         # All tests
make test-coverage    # With HTML report

# Code Quality
make lint             # Run all linters
make format           # Auto-format code
make clean            # Clean build artifacts

# CI/CD
make ci-test          # Simulate CI tests
make ci-lint          # Simulate CI linting
make ci-build         # Build package
```

### Pre-commit Hooks

Automatically run on every commit:

- ✅ **black** - Code formatting
- ✅ **isort** - Import sorting
- ✅ **ruff** - Fast linting
- ✅ **trailing-whitespace** - Cleanup
- ✅ **check-yaml/json/toml** - Syntax validation
- ✅ **bandit** - Security checks
- ✅ **pydocstyle** - Docstring style
- ✅ **commitizen** - Commit message format

---

## 📦 Modules

### Core Modules

| Module | Description |
|--------|-------------|
| `droneresearch.core` | FSM, Connection, Telemetry |
| `droneresearch.control` | Mission engine, Script runner |
| `droneresearch.safety` | APF filter, Geofencing |
| `droneresearch.sdk` | Drone, Swarm, Formations API |

### Advanced Modules

| Module | Description |
|--------|-------------|
| `droneresearch.ros` | PX4 ROS2 bridge, Bag recorder |
| `droneresearch.llm` | LLM swarm commander |
| `droneresearch.experiment` | Scenario manager, Metrics |
| `droneresearch.simulation` | SITL launcher, Replay |

### Hardware Support

| Module | Description |
|--------|-------------|
| `droneresearch.autopilot.mavlink` | ArduPilot + PX4 via MAVLink |
| `droneresearch.autopilot.px4` | PX4 native via uXRCE-DDS |
| `pi/server.py` | Raspberry Pi HTTP server |

---

## 🎮 Examples

| Example | Description |
|---------|-------------|
| `hover.py` | Basic hover at 10m |
| `swarm_circle.py` | 3-drone circle formation |
| `coordinator_demo.py` | Leader-follower V-formation |
| `llm_swarm_control.py` | Natural language control |
| `autonomous_exploration.py` | Frontier-based 3D mapping |
| `px4_ros2_offboard.py` | PX4 offboard control via ROS2 |
| `px4_multi_vehicle.py` | Multi-vehicle PX4 formation |
| `full_research_pipeline.py` | Complete research workflow |

```bash
# Run examples (requires SITL on tcp:127.0.0.1:5762)
python examples/hover.py
python examples/swarm_circle.py

# LLM demo (offline, no API key)
python examples/llm_swarm_control.py --backend mock --interactive
```

---

## 🐳 Docker

Multi-platform containers for heterogeneous swarms:

```bash
# Build all containers
cd docker
docker-compose build

# Run 3-agent swarm
docker-compose up

# Individual containers
docker build -f Dockerfile.pi -t droneresearch:pi .
docker build -f Dockerfile.jetson -t droneresearch:jetson .
docker build -f Dockerfile.x86 -t droneresearch:x86 .
```

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make changes and add tests
4. Run tests: `make test-fast`
5. Format code: `make format`
6. Commit: `git commit -m "feat: your feature"`
7. Push and create Pull Request

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new feature
fix: fix bug
docs: update documentation
test: add tests
refactor: refactor code
perf: improve performance
style: format code
chore: update build tools
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

This platform implements and integrates concepts from:

- **SkySim** (Shibu et al., arXiv:2602.01226) - APF filter, LLM control
- **larics Multi-Resolution Frontier Planner** (IEEE RA-L 2021) - 3D exploration
- **EPFL LIS vswarm** (IEEE RA-L 2021) - Vision-based flocking
- **PX4 ROS2 User Guide** - uXRCE-DDS integration

---

## 📞 Support

- **Documentation:** [docs/](docs/)
- **Issues:** [GitHub Issues](https://github.com/joeldjio/uavresearchproject/issues)
- **Discussions:** [GitHub Discussions](https://github.com/joeldjio/uavresearchproject/discussions)

---

## 🗺️ Roadmap

### Q3 2026
- ✅ 70% test coverage
- ✅ 100% UI coverage
- ✅ CI/CD pipeline
- ⏳ Visual regression tests
- ⏳ Performance benchmarks

### Q4 2026
- ⏳ 75% test coverage
- ⏳ Hardware-in-the-loop tests
- ⏳ Multi-language support
- ⏳ Web-based UI

---

**Made with ❤️ by the DroneResearch Team**

**⭐ Star us on GitHub if you find this project useful!**

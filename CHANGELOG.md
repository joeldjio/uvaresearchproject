# Changelog

All notable changes to the DroneResearch Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Complete CI/CD pipeline with GitHub Actions
- Comprehensive test suite (225 tests, 95% passing, 70% coverage)
- Test pyramid: Unit, Integration, UI, System, E2E tests
- Codecov integration with component-based tracking
- Makefile with 25+ development commands
- Pre-commit hooks configuration
- pytest.ini with test markers and coverage settings
- Contributing guidelines (CONTRIBUTING.md)
- GitHub issue templates (bug report, feature request)
- Pull request template
- CI/CD documentation (docs/testing/ci-cd-guide.md)
- Test strategy documentation (docs/testing/test-strategy.md)
- UI audit report (docs/ui/ui-audit-2026-06.md)

### Changed
- README.md updated with comprehensive testing section
- Test coverage improved to 70% overall, 100% for UI components

### Fixed
- UI tests: Fixed missing bagPlayback service registration (18 errors → 18 passing)

## [0.3.1] - 2025-01-15

### Added
- ROS2 bag recording and playback functionality
- Bag compression support (zstd, lz4)
- Formation preview in UI
- Async mission upload (non-blocking UI)
- Memory profiling tools for UI
- Reconnect logic for ROS2 bridges

### Fixed
- Memory leaks in Qt/QML components
- ROS2 bridge stability issues

## [0.3.0] - 2025-01-01

### Added
- PX4 ROS2 native support via uXRCE-DDS
- Multi-vehicle PX4 support with namespaces
- Frame conversion helpers (NED↔ENU, FRD↔FLU)
- PX4 Gazebo SITL integration
- PX4 formation flight examples
- Hardware setup documentation for PX4

### Changed
- Improved ROS2 context management
- Enhanced PX4 bridge with offboard control

## [0.2.0] - 2024-12-01

### Added
- Natural language swarm control via LLM (Gemini, OpenAI, Ollama)
- APF safety filter (20Hz, separation + geofence)
- Swarm formations (Line, V, Circle, Grid, Wedge)
- Coordinator UAV model for leader-follower swarms
- Observation UAV model with gimbal control
- Frontier-based 3D exploration bridge
- Vision-based swarm flocking bridge (vswarm)
- Experiment framework with scenario definitions
- Metrics collector (8 flight metrics)
- Telemetry replay from CSV/JSON/BIN
- SITL cluster support (multi-vehicle)

### Changed
- Refactored UAV models into modular architecture
- Improved FSM with more states and transitions
- Enhanced mission upload protocol

## [0.1.0] - 2024-11-01

### Added
- Initial release
- Core FSM (Finite State Machine)
- MAVLink connection manager
- Telemetry state container
- Mission upload and execution
- Basic Drone SDK
- CLI interface
- ArduPilot SITL support
- Hardware-free test suite
- Raspberry Pi deployment support
- Docker containers (Pi, Jetson, x86)

### Features
- Hardware abstraction layer (AutopilotBackend)
- Connection string resolution (tcp/udp/serial)
- Event-based telemetry callbacks
- CSV/JSON logging
- Basic formations (line, circle)

---

## Version History

| Version | Release Date | Highlights |
|---------|--------------|------------|
| **Unreleased** | TBD | CI/CD, 225 tests, 70% coverage |
| **0.3.1** | 2025-01-15 | ROS2 bags, Formation preview, Async mission |
| **0.3.0** | 2025-01-01 | PX4 ROS2 native, Multi-vehicle, Gazebo |
| **0.2.0** | 2024-12-01 | LLM control, APF safety, Swarm formations |
| **0.1.0** | 2024-11-01 | Initial release, Core FSM, MAVLink |

---

## Upgrade Guide

### From 0.3.1 to Unreleased

No breaking changes. New features:
- Run tests with `make test-fast`
- Use pre-commit hooks: `pre-commit install`
- Check coverage: `make test-coverage`

### From 0.3.0 to 0.3.1

No breaking changes. New features:
- ROS2 bag recording: `BagRecorder` class
- Bag playback: `BagPlaybackContext` in UI
- Formation preview: `FormationPreview` component

### From 0.2.0 to 0.3.0

**Breaking Changes:**
- PX4 bridge now uses uXRCE-DDS instead of MAVLink-over-ROS
- Frame conventions changed: Use `ned_to_enu()` helpers

**Migration:**
```python
# Old (0.2.0)
from droneresearch.ros import MAVLinkROS2Bridge
bridge = MAVLinkROS2Bridge()

# New (0.3.0)
from droneresearch.ros import PX4ROS2Bridge
bridge = PX4ROS2Bridge(namespace="uav_1")
```

### From 0.1.0 to 0.2.0

**Breaking Changes:**
- UAV models refactored: `GenericUAVModel`, `ObservationUAVModel`, `CoordinatorUAVModel`
- FSM states expanded: Added `HOVER`, `EMERGENCY`

**Migration:**
```python
# Old (0.1.0)
from droneresearch import Drone
drone = Drone("tcp:127.0.0.1:5760")

# New (0.2.0) - Still works, but models recommended
from droneresearch.models import GenericUAVModel
uav = GenericUAVModel("UAV_1", "tcp:127.0.0.1:5760")
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on contributing to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
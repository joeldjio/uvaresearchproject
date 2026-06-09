# Contributing to DroneResearch Platform

Thank you for your interest in contributing to the DroneResearch Platform! This document provides guidelines and instructions for contributing.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Testing](#testing)
5. [Code Style](#code-style)
6. [Commit Messages](#commit-messages)
7. [Pull Request Process](#pull-request-process)
8. [Project Structure](#project-structure)

---

## Code of Conduct

This project follows a professional code of conduct. Be respectful, constructive, and collaborative.

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- (Optional) ROS2 Humble/Jazzy for ROS2 features
- (Optional) ArduPilot or PX4 SITL for testing

### Setup Development Environment

```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/uavresearchproject.git
cd uavresearchproject

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# 3. Install in editable mode with test dependencies
pip install -e ".[test]"

# 4. Install pre-commit hooks (recommended)
pip install pre-commit
pre-commit install

# 5. Verify setup
make test-fast
```

### Optional: Install ROS2 Support

```bash
# Install ROS2 Humble first (see docs/setup/installation.md)
pip install -e ".[ros]"
```

---

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### Branch Naming Convention

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `test/` - Test additions/improvements
- `refactor/` - Code refactoring
- `perf/` - Performance improvements

### 2. Make Your Changes

- Write clean, readable code
- Follow the [Code Style](#code-style) guidelines
- Add tests for new functionality
- Update documentation as needed

### 3. Run Tests Locally

```bash
# Fast tests (unit + integration)
make test-fast

# All tests
make test-all

# With coverage
make test-coverage

# Specific test file
pytest tests/test_your_feature.py -v
```

### 4. Run Linters

```bash
# Run all linters
make lint

# Auto-format code
make format

# Or use pre-commit (runs automatically on commit)
pre-commit run --all-files
```

### 5. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature description"
```

See [Commit Messages](#commit-messages) for format guidelines.

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

---

## Testing

### Test Pyramid

We follow a test pyramid approach:

```
        /\
       /E2E\      10 tests  (~10min, Playwright)
      /------\
     /System \    33 tests  (~5min, SITL)
    /----------\
   /Integration\  71 tests  (~3s, Fake connections)
  /--------------\
 /     Unit      \ 111 tests (~1s, No dependencies)
/------------------\
```

### Writing Tests

#### Unit Tests

```python
# tests/test_your_module.py
import pytest
from droneresearch.your_module import YourClass

@pytest.mark.unit
def test_your_function():
    """Test description."""
    result = YourClass().your_method()
    assert result == expected_value
```

#### Integration Tests

```python
@pytest.mark.integration
def test_with_fake_connection(fake_conn):
    """Test with mocked MAVLink connection."""
    drone = Drone(fake_conn)
    drone.connect()
    assert drone.connected
```

#### UI Tests

```python
@pytest.mark.ui
def test_ui_component(qapp, wired_locator):
    """Test UI component."""
    context = wired_locator.get("swarm")
    assert context is not None
```

### Test Markers

Use pytest markers to categorize tests:

- `@pytest.mark.unit` - Fast, no dependencies
- `@pytest.mark.integration` - Uses fake connections
- `@pytest.mark.ui` - PyQt6/QML tests
- `@pytest.mark.system` - Requires SITL
- `@pytest.mark.e2e` - End-to-end UI tests
- `@pytest.mark.slow` - Tests taking >1s
- `@pytest.mark.sitl` - Requires ArduPilot SITL
- `@pytest.mark.px4` - Requires PX4 SITL
- `@pytest.mark.ros2` - Requires ROS2

### Running Specific Test Categories

```bash
# Only unit tests
pytest tests/ -m unit -v

# Skip slow tests
pytest tests/ -m "not slow" -v

# Only UI tests
pytest tests/test_ui_*.py -v

# System tests (requires SITL)
pytest tests/ -m system -v
```

### Coverage Requirements

- **New code:** Aim for 80%+ coverage
- **Critical paths:** 90%+ coverage (FSM, Safety, Control)
- **UI components:** 100% coverage (already achieved!)

Check coverage:

```bash
make test-coverage
# Opens htmlcov/index.html
```

---

## Code Style

### Python Style Guide

We follow **PEP 8** with some modifications:

- **Line length:** 100 characters (not 79)
- **Imports:** Sorted with `isort` (black-compatible profile)
- **Formatting:** Automated with `black`
- **Linting:** Enforced with `ruff`

### Automatic Formatting

```bash
# Format all code
make format

# Or manually
black droneresearch/ tools/ tests/
isort droneresearch/ tools/ tests/
```

### Type Hints

Use type hints for public APIs:

```python
from typing import Optional, List, Dict
from droneresearch.core.telemetry import TelemetrySnapshot

def process_telemetry(
    snapshot: TelemetrySnapshot,
    threshold: float = 10.0
) -> Optional[Dict[str, float]]:
    """Process telemetry snapshot.
    
    Args:
        snapshot: Telemetry data
        threshold: Altitude threshold in meters
        
    Returns:
        Processed data or None if below threshold
    """
    if snapshot.alt_rel < threshold:
        return None
    return {"altitude": snapshot.alt_rel}
```

### Docstrings

Use **Google-style docstrings**:

```python
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two GPS coordinates.
    
    Uses Haversine formula for great-circle distance.
    
    Args:
        lat1: Latitude of first point (degrees)
        lon1: Longitude of first point (degrees)
        lat2: Latitude of second point (degrees)
        lon2: Longitude of second point (degrees)
        
    Returns:
        Distance in meters
        
    Example:
        >>> distance = calculate_distance(48.137, 11.575, 48.138, 11.576)
        >>> print(f"{distance:.1f}m")
        123.4m
    """
    # Implementation...
```

### Import Order

1. Standard library
2. Third-party packages
3. Local imports (absolute)

```python
# Standard library
import time
import threading
from typing import Optional

# Third-party
import pytest
from pymavlink import mavutil

# Local
from droneresearch.core.fsm import StateMachine
from droneresearch.core.telemetry import TelemetrySnapshot
```

### Naming Conventions

- **Classes:** `PascalCase` (e.g., `StateMachine`, `APFSafetyFilter`)
- **Functions/Methods:** `snake_case` (e.g., `connect()`, `get_telemetry()`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `DEFAULT_PORT`, `MAX_RETRIES`)
- **Private:** Prefix with `_` (e.g., `_internal_method()`)
- **Fixtures:** `snake_case` (e.g., `fake_conn`, `snap_factory`)

---

## Commit Messages

We follow **Conventional Commits** format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `style:` - Code style changes (formatting)
- `chore:` - Build/tooling changes
- `ci:` - CI/CD changes

### Examples

```bash
# Feature
git commit -m "feat(safety): add geofence altitude limits"

# Bug fix
git commit -m "fix(fsm): prevent invalid EMERGENCY→MISSION transition"

# Documentation
git commit -m "docs(readme): update installation instructions"

# Test
git commit -m "test(apf): add separation violation tests"

# With body
git commit -m "feat(ros2): add PX4 multi-vehicle support

- Add namespace parameter to PX4ROS2Bridge
- Support multiple drones via /uav_N/ topics
- Add frame conversion helpers (NED↔ENU)

Closes #123"
```

### Commit Message Rules

1. **Subject line:**
   - Max 72 characters
   - Lowercase after type
   - No period at end
   - Imperative mood ("add" not "added")

2. **Body (optional):**
   - Wrap at 72 characters
   - Explain *what* and *why*, not *how*
   - Separate from subject with blank line

3. **Footer (optional):**
   - Reference issues: `Closes #123`, `Fixes #456`
   - Breaking changes: `BREAKING CHANGE: description`

---

## Pull Request Process

### Before Submitting

1. ✅ All tests pass: `make test-fast`
2. ✅ Code is formatted: `make format`
3. ✅ Linters pass: `make lint`
4. ✅ Coverage maintained/improved
5. ✅ Documentation updated
6. ✅ Commit messages follow convention

### PR Template

When creating a PR, include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass locally
- [ ] No new warnings

## Related Issues
Closes #123
```

### Review Process

1. **Automated checks:** CI/CD runs all tests
2. **Code review:** Maintainer reviews code
3. **Feedback:** Address review comments
4. **Approval:** Maintainer approves PR
5. **Merge:** Squash and merge to main

### CI/CD Checks

Your PR must pass:

- ✅ Unit & Integration Tests (Python 3.9, 3.10, 3.11)
- ✅ UI Tests (Xvfb headless)
- ✅ Linting (ruff, black, isort, mypy)
- ✅ License Check
- ✅ Build & Package

---

## Project Structure

```
droneresearch/
├── autopilot/          # Hardware abstraction layer
│   ├── base.py         # AutopilotBackend ABC
│   ├── mavlink/        # MAVLink implementation
│   ├── ardupilot/      # ArduPilot extensions
│   └── px4/            # PX4 native (uXRCE-DDS)
│
├── core/               # Core functionality
│   ├── connection.py   # MAVLink connection
│   ├── fsm.py          # State machine
│   └── telemetry.py    # Telemetry container
│
├── control/            # Control primitives
│   ├── mission.py      # Mission upload/execution
│   └── script_runner.py # Script execution
│
├── models/             # UAV model classes
│   ├── generic_uav.py
│   ├── observation_uav.py
│   └── coordinator_uav.py
│
├── safety/             # Safety systems
│   └── apf.py          # APF filter + geofence
│
├── sdk/                # Public API
│   ├── drone.py        # Drone class
│   ├── swarm_api.py    # Swarm class
│   └── formations.py   # Formation primitives
│
├── ros/                # ROS2 integration
│   ├── px4_bridge.py   # PX4 uXRCE-DDS bridge
│   ├── bridge.py       # MAVLink→ROS2 bridge
│   └── context.py      # ROS2 context manager
│
├── simulation/         # Simulation tools
│   ├── sitl.py         # SITL launcher
│   └── replay.py       # Telemetry replay
│
├── experiment/         # Research experiments
│   ├── manager.py      # Experiment manager
│   ├── scenario.py     # Scenario definition
│   └── metrics.py      # Metrics collector
│
├── data/               # Data logging
│   ├── logger.py       # Telemetry logger
│   └── store.py        # Ring buffer store
│
├── llm/                # LLM integration
│   └── swarm_commander.py # Natural language control
│
├── exploration/        # Autonomous exploration
│   ├── frontier_bridge.py # Frontier planner
│   └── vswarm_bridge.py   # Vision-based flocking
│
└── cli/                # Command-line interface
    └── main.py         # CLI entry point
```

### Adding New Modules

1. Create module in appropriate directory
2. Add `__init__.py` with public exports
3. Write tests in `tests/test_your_module.py`
4. Update documentation
5. Add to `pyproject.toml` if needed

---

## Questions?

- **Documentation:** See `docs/` directory
- **Examples:** See `examples/` directory
- **Issues:** Open a GitHub issue
- **Discussions:** Use GitHub Discussions

---

**Thank you for contributing to DroneResearch Platform! 🚁**
# DroneResearch Platform - Complete Software Documentation

**Version:** 0.3.1+  
**Last Updated:** 2026-06-09  
**Author:** Joel Djio

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Architecture](#2-system-architecture)
3. [Installation & Setup](#3-installation--setup)
4. [Core Modules](#4-core-modules)
5. [Advanced Features](#5-advanced-features)
6. [Hardware Integration](#6-hardware-integration)
7. [Testing & Quality Assurance](#7-testing--quality-assurance)
8. [Development Guide](#8-development-guide)
9. [Deployment](#9-deployment)
10. [API Reference](#10-api-reference)
11. [Troubleshooting](#11-troubleshooting)
12. [Appendix](#12-appendix)

---

## 1. Introduction

### 1.1 What is DroneResearch?

DroneResearch is an **enterprise-grade UAV research middleware platform** designed for reproducible drone experiments, swarm coordination, and autonomous operations. It provides a unified API for multiple autopilot systems (ArduPilot, PX4) and integrates with ROS2 for advanced robotics applications.

### 1.2 Key Features

- **Hardware Abstraction:** Unified API for ArduPilot and PX4 (MAVLink + uXRCE-DDS)
- **State Management:** Thread-safe FSM with 10 states and event callbacks
- **Safety Systems:** APF filter (20Hz), geofencing, collision avoidance
- **Swarm Coordination:** 6 formations, leader-follower, multi-role UAVs
- **ROS2 Integration:** Native PX4 support, bag recording, frame conversions
- **LLM Control:** Natural language → waypoints via Gemini/OpenAI/Ollama
- **Experiment Framework:** Scenario definitions, metrics collection, replay
- **Desktop UI:** PyQt6/QML dashboard with 3D visualization
- **Testing:** 235 tests (70% coverage), CI/CD pipeline
- **Production Ready:** Raspberry Pi deployment, Docker containers

### 1.3 Design Philosophy

1. **Simulation-First:** Develop in SITL, deploy to hardware with same code
2. **Modular Architecture:** Swap backends, add features without breaking changes
3. **Reproducible Research:** Scenario definitions, quantitative metrics, replay
4. **Hardware-Free Testing:** Mock all external dependencies for fast iteration
5. **Enterprise Quality:** CI/CD, code coverage, linting, security checks

### 1.4 Use Cases

- **Academic Research:** Reproducible experiments with quantitative metrics
- **Swarm Robotics:** Multi-drone coordination, formations, leader-follower
- **Autonomous Exploration:** Frontier planning, vision-based navigation
- **Natural Language Control:** LLM-powered swarm commands
- **Hardware Testing:** SITL → Real hardware validation
- **Education:** Learn drone programming with safe simulation

---

## 2. System Architecture

### 2.1 Layered Architecture

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

### 2.2 Module Overview

| Module | Purpose | Key Files |
|--------|---------|-----------|
| `droneresearch.core` | FSM, Connection, Telemetry | `fsm.py`, `connection.py`, `telemetry.py` |
| `droneresearch.control` | Mission, Script execution | `mission.py`, `script_runner.py` |
| `droneresearch.safety` | APF filter, Geofencing | `apf.py` |
| `droneresearch.sdk` | Public API | `drone.py`, `swarm_api.py`, `formations.py` |
| `droneresearch.ros` | ROS2 integration | `px4_bridge.py`, `bag_recorder.py` |
| `droneresearch.llm` | LLM swarm commander | `swarm_commander.py` |
| `droneresearch.experiment` | Scenario manager | `manager.py`, `scenario.py`, `metrics.py` |
| `droneresearch.simulation` | SITL launcher, Replay | `sitl.py`, `replay.py` |
| `droneresearch.data` | Logger, Store | `logger.py`, `store.py` |
| `droneresearch.cli` | Command-line interface | `main.py` |
| `tools.ui` | Desktop UI | `main_window.py`, `qml/` |
| `pi.server` | Raspberry Pi server | `server.py` |

---

**For complete documentation, see:**

- [Installation Guide](setup/installation.md)
- [PX4 Setup](setup/px4-sitl.md)
- [Test Strategy](testing/test-strategy.md)
- [CI/CD Guide](testing/ci-cd-guide.md)
- [E2E Testing](testing/e2e-setup.md)
- [UI Documentation](ui/ui-documentation.md)
- [Contributing Guide](../CONTRIBUTING.md)

---

**This is a living document. For the latest version, see the [GitHub repository](https://github.com/joeldjio/uavresearchproject).**
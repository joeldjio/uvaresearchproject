# DroneResearch Platform

**An open, scriptable research platform for drone experiments.**

> Not a better QGroundControl — a programmable research tool.

**Author:** Joel Djio

---

## What it is

DroneResearch is a lightweight, Raspberry Pi-compatible platform for autonomous drone research. It connects to real drones via MAVLink (ArduPilot + PX4), exposes a clean Python API, integrates with ROS2, and provides an Experiment Manager for reproducible flight experiments.

## What it is NOT

- Not a full-featured GCS (no calibration wizard, no firmware flashing)
- Not a fancy UI showpiece
- Not limited to one use case

---

## Architecture

```
DroneResearch/
├── core/        # MAVLink connection layer (ArduPilot + PX4)
├── data/        # Telemetry store + CSV/JSON/ROS logging
├── control/     # Python drone API + Mission engine + Script runner
├── swarm/       # Multi-drone management + Formation flying
├── ros/         # ROS2 bridge (optional, graceful fallback)
├── experiment/  # Experiment manager: save, replay, evaluate
├── ui/          # Minimal PySide6 UI (runs on Raspberry Pi)
├── cli/         # Command-line interface
├── sdk/         # Public Python API (importable as library)
└── examples/    # Ready-to-run experiment scripts
```

---

## Quick Start

```bash
pip install -e .

# Connect to drone and hover at 10m
python examples/hover.py --port /dev/ttyUSB0

# Run an experiment
python -m droneresearch experiment run examples/speed_test.yaml

# CLI
droneresearch connect --port tcp:127.0.0.1:5760
droneresearch takeoff --alt 10
droneresearch status
```

---

## Python API

```python
from droneresearch import Drone

drone = Drone("tcp:127.0.0.1:5760")
drone.connect()
drone.arm()
drone.takeoff(altitude=10)

# Event-based logic
@drone.on("altitude")
def on_altitude(value):
    if value > 15:
        drone.set_speed(3.0)

drone.wait_for_landing()
drone.disconnect()
```

---

## Swarm API

```python
from droneresearch.swarm import Swarm

swarm = Swarm()
swarm.add("D1", "tcp:127.0.0.1:5760")
swarm.add("D2", "tcp:127.0.0.1:5761")
swarm.connect_all()
swarm.arm_all()
swarm.takeoff_all(altitude=10)
swarm.formation("circle", spacing=5.0)
```

---

## Experiment Manager

```python
from droneresearch.experiment import Experiment

exp = Experiment("speed_comparison")
exp.param("speed", [2.0, 4.0, 6.0])
exp.param("altitude", 10.0)
exp.run(lambda drone, params: drone.fly_mission("square", **params))
exp.export("results/speed_comparison.csv")
```

---

## Autonomous 3D Exploration

DroneResearch integrates with the **larics Multi-Resolution Frontier-Based Planner**
([GitHub](https://github.com/larics/uav_frontier_exploration_3d), IEEE RA-L 2021).

The bridge handles:
- MAVLink telemetry → ROS2 `nav_msgs/Odometry` + `geometry_msgs/PoseStamped`
- Forwarding of external `sensor_msgs/PointCloud2` (depth cam / LiDAR) to the explorer
- Receiving frontier goals from the explorer → `drone.goto()`
- Volume tracking + automatic done detection

```python
from droneresearch import Drone
from droneresearch.exploration import FrontierExplorationBridge

drone = Drone("tcp:127.0.0.1:5760")
drone.connect()
drone.arm()
drone.takeoff(altitude=5.0)

bridge = FrontierExplorationBridge(
    drone,
    point_cloud_topic="/camera/depth/points",   # from your depth cam
    on_volume_update=lambda v: print(f"Explored: {v['explored_pct']:.1f}%"),
)
bridge.start()
bridge.exploration_start()
bridge.wait_until_done(timeout=600)
bridge.save_octomap(filename="result", file_path="/tmp")
drone.rtl()
```

**Topic mapping:**

| DroneResearch publishes | Explorer expects |
|---|---|
| `/exploration/odometry` | `nav_msgs/Odometry` |
| `/exploration/cloud_in` | `sensor_msgs/PointCloud2` |
| `/exploration/carrot_pose` | `geometry_msgs/PoseStamped` |
| ← `/exploration/point_reached` | `std_msgs/Bool` |
| ← `/exploration/octomap_volume` | `std_msgs/Float64MultiArray` |

**Prerequisites:**
```bash
# 1. Clone and build the larics explorer
cd ~/ros2_ws/src
git clone https://github.com/larics/uav_frontier_exploration_3d
cd ~/ros2_ws && colcon build
source ~/ros2_ws/install/setup.bash

# 2. Run the explorer node
ros2 launch uav_frontier_exploration_3d frontier_server.launch.py

# 3. Run DroneResearch bridge
python examples/autonomous_exploration.py --port tcp:127.0.0.1:5760 \
    --cloud /camera/depth/points
```

## Vision-based Swarm Flocking (vswarm)

DroneResearch integrates with **vswarm** (EPFL LIS, IEEE RA-L 2021)
([GitHub](https://github.com/lis-epfl/vswarm)) — decentralized, communication-free
drone flocking using only a camera.

Each drone runs independently:
1. CNN detects neighboring drones from omnidirectional camera images
2. Relative localizer estimates 3D positions of neighbors
3. Multi-target tracker (RFS filter) estimates positions + velocities
4. Reynolds-inspired flocking controller outputs `cmd_vel`
5. DroneResearch converts `cmd_vel` → MAVLink `goto` commands

**No inter-drone communication. No fiducial markers. Camera only.**

```python
from droneresearch import Drone
from droneresearch.exploration import VSwarmBridge

drone = Drone("tcp:127.0.0.1:5760")
drone.connect()
drone.arm()
drone.takeoff(altitude=2.5)

bridge = VSwarmBridge(
    drone,
    camera_topic="/camera/image_raw",
    on_cmd_vel=lambda vx, vy, vz, yr: print(f"vx={vx:.2f} vy={vy:.2f}"),
)
bridge.start()
bridge.start_flocking()
# drone now flocks with neighbors autonomously
```

**Topic mapping:**

| DroneResearch publishes | vswarm expects |
|---|---|
| `/vswarm/odometry` | `nav_msgs/Odometry` |
| `/vswarm/image` | `sensor_msgs/Image` (forwarded from camera) |
| `/vswarm/camera_info` | `sensor_msgs/CameraInfo` |
| ← `/vswarm/cmd_vel` | `geometry_msgs/Twist` (flocking velocity) |

**Prerequisites:**
```bash
# vswarm runs on ROS1 Melodic — use ros1_bridge for ROS2
cd ~/catkin_ws/src
git clone https://github.com/lis-epfl/vswarm
cd ~/catkin_ws && catkin_make
source devel/setup.bash

# Download detection model (see vswarm/docs/installation.md)

# Launch vswarm per drone
roslaunch vswarm vswarm_onboard.launch

# Run DroneResearch bridge per drone
python examples/vswarm_flocking.py --port tcp:127.0.0.1:5760 \
    --camera /camera/image_raw --duration 120
```

## ROS2 Integration

```bash
# Telemetry as ROS topics
ros2 topic echo /droneresearch/attitude
ros2 topic echo /droneresearch/gps
ros2 topic echo /droneresearch/battery

# Send commands via ROS
ros2 topic pub /droneresearch/cmd/mode std_msgs/String "data: GUIDED"
```

---

## Logging

All flights are automatically logged:

- `logs/YYYYMMDD_HHMMSS_telemetry.csv` — full telemetry
- `logs/YYYYMMDD_HHMMSS_events.json` — arm/disarm/mode changes
- `logs/YYYYMMDD_HHMMSS.bag` — ROS bag (if ROS2 available)

---

## Hardware

Tested on:
- Raspberry Pi 4 (2GB RAM)
- Raspberry Pi 5
- x86 Linux / Windows (development)

Requirements:
- Python 3.10+
- PySide6 (UI, optional)
- pymavlink
- ROS2 Humble/Jazzy (optional)

---

## Contributing

This is a research platform — contributions welcome.
See `examples/` for how to write experiments.
See `sdk/` for the public API reference.

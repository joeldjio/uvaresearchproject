# PX4 SITL Startup Guide

This guide shows how to start PX4 SITL with Ignition/Gazebo and connect it to the DroneResearch ROS2 bridge.

## Preconditions

- Linux with `gz` Ignition 8 installed (`gz gui --versions` shows `8.4.0`)
- PX4 Firmware source or build environment available
- ROS2 Humble (or compatible) installed
- `px4_msgs` built and sourced in your ROS2 workspace
- `micro-xrce-dds-agent` installed

## 1. Build and source ROS2 + px4_msgs

```bash
cd ~/ros2_ws/src
git clone https://github.com/PX4/px4_msgs.git
cd ~/ros2_ws
colcon build --packages-select px4_msgs
source install/setup.bash
```

## 2. Install and start the XRCE-DDS agent

```bash
python3 -m pip install --user micro-xrce-dds-agent
MicroXRCEAgent udp4 -p 8888
```

Leave this terminal open. The agent listens for PX4 uXRCE-DDS packets and forwards them to ROS2.

## 3. Start PX4 SITL with Ignition

Open a second terminal and run:

```bash
cd ~/Firmware
export PX4_UXRCE_DDS_NS=uav_1
    make px4_sitl gz_x500
```
oder 
'''
source /opt/ros/humble/setup.bash
source /home/iruz/ws_sensor_combined/install/setup.bash
cd /home/iruz/PX4-Autopilot
PX4_UXRCE_DDS_NS=uav_1 make px4_sitl gz_x500
'''

This starts PX4 SITL using the `gz_x500` model and sets the PX4 XRCE namespace.

> If you want a single-vehicle default namespace, use `PX4_UXRCE_DDS_NS=` (empty) or omit the variable.

## 4. Start the DroneResearch PX4 ROS2 example

Open a third terminal and source ROS2 again:

```bash
cd ~/ros2_ws
source install/setup.bash
cd ~/path/to/uavresearchproject
python3 examples/px4_ros2_offboard.py
```

The example will:
- start the ROS2 bridge
- arm the vehicle
- execute takeoff
- switch to OFFBOARD mode
- fly a simple trajectory
- land

## 5. Optional: use the DroneResearch UI

If you want the QML UI instead of the example script:

```bash
cd ~/path/to/uavresearchproject
python3 -m tools.ui.app
```
oder
'''
source /opt/ros/humble/setup.bash
source /home/iruz/ws_sensor_combined/install/setup.bash
cd /home/iruz/dorneresearch/uavresearchproject
python3 -m tools.ui.app
'''

Then open the ROS2 tab, set namespace `uav_1`, and click `Bridge starten`.

## Troubleshooting

### Takeoff stops at ~5m or drone doesn't climb

This is usually a **geofence limit** or **preflight disarm** in PX4. Check:

1. **Run diagnostics:**
   ```bash
   python3 examples/diagnose_px4_env.py
   ```
   This checks Gazebo models, PX4 parameters, and suggests fixes.

2. **Run takeoff debug script:**
   ```bash
   python3 examples/debug_px4_takeoff.py --altitude 20
   ```
   Watch live telemetry during climb. If it stops abruptly, you'll see the exact altitude and flight mode.

3. **Check PX4 parameters in nsh:**
   If you have access to the PX4 nsh console (via serial, MAVLink, or SITL):
   ```bash
   param show | grep -E "MPC_Z_MAX|GEO_FENCE|ALT|COM_DISARM"
   ```
   Look for:
   - `MPC_Z_MAX` — max climb rate (should be >1)
   - `GEO_FENCE_*` — geofence limits
   - `COM_DISARM_PREFLT` — preflight disarm timeout (increase if too short)

### Mission doesn't navigate / waypoints not reached

1. **Run mission debug script:**
   ```bash
   python3 examples/debug_px4_mission.py --lat-offset 0.0001 --altitude 15
   ```
   This flies 3 small waypoints and logs distance to each one.

2. **Check that GUIDED mode is supported:**
   PX4 SITL may require `OFFBOARD` mode for ROS2 control. Our code auto-selects it for PX4.
   If waypoints still don't work:
   - Verify `goto()` sends correct MAVLink message: `SET_POSITION_TARGET_GLOBAL_INT`
   - Check that PX4 is in `GUIDED` or `AUTO` mode (not `ACRO`, `MANUAL`, etc.)

3. **Increase timeout if waypoint is far away:**
   ```python
   drone.goto(lat, lon, alt, timeout=300.0)  # 5 minutes instead of 1
   ```

### Gazebo world is empty (white plane, no ground)

Make sure the world is loaded:
```bash
cd ~/Firmware  # or ~/PX4-Autopilot
export PX4_UXRCE_DDS_NS=uav_1
make px4_sitl gz_x500
```

The `gz_x500` target loads the correct world model with terrain.

- If PX4 reports `NACK DO_SET_MODE`, make sure the `MicroXRCEAgent` is running before starting PX4.
- If the ROS2 bridge does not see PX4 telemetry, confirm that `px4_msgs` is sourced in the same shell that starts the example or UI.
- For multi-vehicle setups, use unique namespaces like `uav_1`, `uav_2`, etc. and start one PX4 instance per namespace.

## Notes

- This guide assumes the PX4 Firmware repository is available at `~/Firmware`.
- Use Ignition 8/Gazebo Classic only if your PX4 build supports `gz_x500`.
- The `examples/px4_ros2_offboard.py` script is the recommended starting point for validating the PX4 ROS2 bridge.

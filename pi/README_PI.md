# DroneResearch on Raspberry Pi 1

Optimized for: **Raspberry Pi 1 Model B/B+**
CPU: 700MHz ARM11 | RAM: 512MB | No hardware float acceleration

## Resource profile

| Component        | RAM      | CPU (idle) |
|------------------|----------|------------|
| Python 3 runtime | ~12 MB   | —          |
| pymavlink        | ~4 MB    | <1%        |
| HTTP server      | ~2 MB    | <1%        |
| MAVLink RX loop  | ~1 MB    | 2–4%       |
| **Total**        | **~20 MB** | **<5%**  |

Compared to PySide6 UI: ~180 MB RAM, unusable on Pi 1.

## What runs on Pi 1

- MAVLink connection (serial or TCP/UDP)
- Full telemetry parsing at 2–4 Hz
- REST API on port 8080
- Web dashboard (open on laptop/phone browser)
- Command execution (ARM, DISARM, TAKEOFF, LAND, RTL, GOTO, MODE)
- Log ring buffer (last 200 entries)

## What does NOT run on Pi 1

- PySide6 / Qt UI → use web dashboard instead
- ROS2 → needs Pi 3+ minimum
- vswarm CNN → needs GPU (Jetson TX2 recommended)
- Frontier exploration → needs Pi 3+ with OctoMap

## Install

```bash
# On the Pi (Raspberry Pi OS Lite recommended)
git clone https://github.com/yourname/DroneResearch ~/DroneResearch
cd ~/DroneResearch
bash pi/install.sh
```

## Run

```bash
# Serial (most common)
python3 pi/server.py --port /dev/ttyUSB0 --baud 57600

# SITL over TCP
python3 pi/server.py --port tcp:127.0.0.1:5760

# Demo mode (no drone needed — for testing)
python3 pi/server.py --demo

# Custom HTTP port
python3 pi/server.py --port /dev/ttyAMA0 --baud 115200 --http 80
```

## Web Dashboard

Open in browser on any device on the same network:

```
http://<raspberry-pi-ip>:8080
```

Features:
- Live telemetry (0.5s update)
- Mini map with flight trail
- ARM / DISARM / TAKEOFF / LAND / RTL buttons
- Mode switching
- Log viewer

## REST API

```bash
# Telemetry
curl http://pi-ip:8080/api/telemetry

# Send command
curl -X POST http://pi-ip:8080/api/command \
     -H "Content-Type: application/json" \
     -d '{"cmd": "TAKEOFF", "params": {"alt": 10}}'

# Log
curl http://pi-ip:8080/api/log?n=20
```

Available commands:
| cmd | params |
|---|---|
| `ARM` | `{"force": false}` |
| `DISARM` | `{"force": false}` |
| `TAKEOFF` | `{"alt": 10.0}` |
| `LAND` | — |
| `RTL` | — |
| `MODE` | `{"mode": "LOITER"}` |
| `GOTO` | `{"lat": 48.1, "lon": 11.5, "alt": 10}` |

## Autostart with systemd

```bash
sudo systemctl start droneresearch
sudo systemctl status droneresearch
sudo journalctl -u droneresearch -f    # live logs
```

## MAVLink stream rates (Pi 1 optimized)

Reduced from defaults to save CPU:

| Stream | Rate |
|---|---|
| POSITION (GPS) | 2 Hz |
| ATTITUDE | 4 Hz |
| VFR_HUD | 2 Hz |
| SYS_STATUS | 1 Hz |

To increase: edit `_request_streams()` in `pi/server.py`.

## Tuning for even less RAM

```bash
# Disable swap (wear-leveling for SD card)
sudo dphys-swapfile swapoff
sudo systemctl disable dphys-swapfile

# Use Raspberry Pi OS Lite (no desktop)
# Python 3 slim — no pip extras

# Reduce log buffer in server.py:
_log: deque = deque(maxlen=50)   # was 200
```

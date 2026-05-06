"""
Full Research Pipeline — demonstrating the complete DroneResearch architecture.

This example shows the full stack:
    1. SITL  — simulation-first, reproducible
    2. Autopilot backend — hardware abstraction
    3. FSM UAV models — paper-based architecture
    4. APF safety filter — collision avoidance
    5. LLM swarm commander — natural language control
    6. Scenario + Metrics — quantitative research output
    7. Replay — post-hoc analysis

Run:
    python3 examples/full_research_pipeline.py --demo
    python3 examples/full_research_pipeline.py --sitl
"""
import argparse
import time

parser = argparse.ArgumentParser()
parser.add_argument("--demo",  action="store_true", help="No SITL, no hardware")
parser.add_argument("--sitl",  action="store_true", help="Auto-start ArduPilot SITL")
parser.add_argument("--port",  default="tcp:127.0.0.1:5760")
args = parser.parse_args()

# ── 1. Scenario definition ────────────────────────────────────────────────────
from droneresearch.experiment import Scenario, ScenarioRunner, MetricsCollector

scenario = Scenario(
    name        = "swarm_circle_formation",
    autopilot   = "ardupilot",
    vehicle     = "copter",
    description = "3-drone circle formation with LLM commander and APF safety",
    tags        = ["swarm", "formation", "llm", "apf"],
    mission     = [
        {"cmd": "takeoff", "alt": 10},
        {"cmd": "hover",   "duration": 5},
        {"cmd": "land"},
    ],
    params      = {"alt": [8, 10, 12]},
    metrics     = ["flight_time", "battery_drain", "dist_traveled", "hover_stability"],
    speedup     = 3.0,
)

print(f"Scenario: {scenario.name}")
print(f"Param combinations: {len(scenario.param_combinations())}")
scenario.save("results/swarm_circle_formation.json")

# ── 2. Safety filter ──────────────────────────────────────────────────────────
from droneresearch.safety import APFSafetyFilter, Pose3D

apf = APFSafetyFilter(
    min_separation=2.0,
    max_speed=3.0,
    geofence_radius=30.0,
    geofence_alt=(1.0, 20.0),
)

# ── 3. LLM swarm commander ────────────────────────────────────────────────────
from droneresearch.llm import SwarmCommander

commander = SwarmCommander(backend="mock", apf=apf)
commander.update_state({
    "D1": Pose3D(0, 0, 10),
    "D2": Pose3D(3, 0, 10),
    "D3": Pose3D(6, 0, 10),
})

print("\n── LLM Swarm Commands ──")
for cmd_text in ["Form a circle 5m", "Move north 8 meters", "V formation"]:
    result = commander.command(cmd_text)
    print(f"  '{cmd_text}' → {result.explanation} ({result.latency_ms:.0f}ms)")

# ── 4. SITL + Autopilot backend ───────────────────────────────────────────────
if args.sitl:
    from droneresearch.simulation import SITLInstance
    print("\n── Starting SITL ──")
    sitl = SITLInstance(autopilot="ardupilot", speedup=3.0)
    sitl.start()
    sitl.wait_ready()
    connection = sitl.connection_string
elif args.demo:
    connection = None
    print("\n── Demo mode (no hardware) ──")
else:
    connection = args.port

# ── 5. UAV Models + Coordinator ───────────────────────────────────────────────
from droneresearch.models import GenericUAVModel, CoordinatorUAVModel
from droneresearch.core.fsm import DroneState

coord = CoordinatorUAVModel.as_ground_station()

if connection:
    d1 = GenericUAVModel("D1", connection)
    coord.register("D1", d1)
    print(f"\n── Connecting D1 to {connection} ──")
    if d1.connect():
        print(f"  Connected. FSM: {d1.fsm.state.name}")
        print(f"  Autopilot: {d1._conn._backend.autopilot_type if hasattr(d1._conn, '_backend') else 'unknown'}")

# ── 6. Metrics collection (offline demo) ─────────────────────────────────────
print("\n── Metrics example ──")
print("Available metrics:", scenario.metrics)
print("Scenario saved to: results/swarm_circle_formation.json")

# ── 7. Replay demo ────────────────────────────────────────────────────────────
from droneresearch.simulation.replay import TelemetryReplay
import os

log_files = []
for root, _, files in os.walk("logs"):
    for f in files:
        if f.endswith(".csv"):
            log_files.append(os.path.join(root, f))

if log_files:
    print(f"\n── Replay: {log_files[0]} ──")
    replay = TelemetryReplay(log_files[0])
    replay.load()
    print(f"  {replay.frame_count} frames, {replay.duration:.1f}s duration")
    for frame in list(replay.play(speed=0))[:5]:
        print(f"  t={frame.timestamp:.1f} lat={frame.snapshot.lat:.6f} alt={frame.snapshot.alt_rel:.1f}m")
else:
    print("\n── No log files found for replay demo ──")

# ── Cleanup ───────────────────────────────────────────────────────────────────
if args.sitl and 'sitl' in dir():
    sitl.stop()

print("\n── Architecture Summary ──")
print("  autopilot/   → MAVLink | ArduPilot | PX4 (uXRCE-DDS)")
print("  models/      → GenericUAV | ObservationUAV | CoordinatorUAV + FSM")
print("  simulation/  → SITL launcher | Replay (.csv/.json/.bin)")
print("  experiment/  → Scenario | ScenarioRunner | MetricsCollector")
print("  safety/      → APF filter | Geofence | Separation checks")
print("  llm/         → SwarmCommander (Gemini/OpenAI/Ollama/Mock)")
print("  ros/         → PX4 uXRCE-DDS bridge | vswarm | frontier")
print("  exploration/ → FrontierBridge (larics) | VSwarmBridge (EPFL)")
print("  pi/          → Lightweight HTTP server for Raspberry Pi 1")
print("  docker/      → Dockerfile.pi | Dockerfile.jetson | Dockerfile.x86")

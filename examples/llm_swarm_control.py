"""
Example: Natural language swarm control via LLM + APF safety filter.

Based on: SkySim (Shibu et al., 2025) arXiv:2602.01226

Demonstrates the full pipeline:
    User text → LLM → waypoints → APF filter → drone.goto()

Run offline (mock LLM, no API key needed):
    python3 examples/llm_swarm_control.py --backend mock

Run with Gemini:
    export DRONE_LLM_API_KEY=your_key
    python3 examples/llm_swarm_control.py --backend gemini

Run with local Ollama:
    ollama pull llama3
    python3 examples/llm_swarm_control.py --backend ollama
"""
import argparse
import time
from droneresearch.safety import APFSafetyFilter, Pose3D
from droneresearch.llm import SwarmCommander

parser = argparse.ArgumentParser()
parser.add_argument("--backend", default="mock",
                    choices=["mock", "gemini", "openai", "ollama"])
parser.add_argument("--api-key", default=None)
parser.add_argument("--interactive", action="store_true",
                    help="Interactive REPL mode")
args = parser.parse_args()

# Setup APF safety filter
apf = APFSafetyFilter(
    min_separation=2.0,
    max_speed=3.0,
    geofence_radius=30.0,
    geofence_alt=(1.0, 20.0),
    repulsion_gain=2.5,
)

# Setup swarm commander
commander = SwarmCommander(
    backend=args.backend,
    api_key=args.api_key,
    apf=apf,
)

# Simulated initial swarm state (3 drones, line formation at 10m alt)
state = {
    "D1": Pose3D( 0.0, 0.0, 10.0),
    "D2": Pose3D( 3.0, 0.0, 10.0),
    "D3": Pose3D( 6.0, 0.0, 10.0),
}
commander.update_state(state)

def run_command(text: str):
    print(f"\n> {text}")
    result = commander.command(text)
    if result.success:
        print(f"  [{args.backend}] {result.explanation}")
        print(f"  Latency: {result.latency_ms:.0f}ms")
        print("  Waypoints:")
        for did, wp in result.waypoints.items():
            raw = result.raw_waypoints.get(did)
            moved = raw and (
                abs(wp.x - raw.x) > 0.01 or
                abs(wp.y - raw.y) > 0.01 or
                abs(wp.z - raw.z) > 0.01
            )
            apf_note = " [APF adjusted]" if moved else ""
            print(f"    {did}: ({wp.x:.2f}, {wp.y:.2f}, {wp.z:.2f}){apf_note}")
        # Update simulated state
        state.update(result.waypoints)
        commander.update_state(state)
    else:
        print(f"  ERROR: {result.error}")

if args.interactive:
    print(f"SwarmCommander [{args.backend}] — interactive mode")
    print("Type drone commands in natural language. Ctrl+C to exit.\n")
    print("Initial state:")
    for did, p in state.items():
        print(f"  {did}: {p}")
    while True:
        try:
            text = input("\nCommand: ").strip()
            if text:
                run_command(text)
        except KeyboardInterrupt:
            print("\nBye.")
            break
else:
    print(f"SwarmCommander [{args.backend}] — demo sequence\n")
    print("Initial state:")
    for did, p in state.items():
        print(f"  {did}: {p}")

    demo_commands = [
        "Form a circle with 5 meter radius",
        "Move the swarm 8 meters north",
        "V formation with 3m spacing",
        "Grid formation",
        "Hover in place",
        "Line up facing east",
        "Climb to 15 meters",
        "Land all drones",
    ]

    for cmd in demo_commands:
        run_command(cmd)
        time.sleep(0.2)

    print("\n\nCommand history:")
    for entry in commander.history():
        print(f"  [{entry['t']:.0f}] {entry['command']} → {entry['result']}")

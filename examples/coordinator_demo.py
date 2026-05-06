"""
Example: CoordinatorUAVModel — leader-follower formation with FSM.

Demonstrates the paper architecture:
    D1 = CoordinatorUAVModel (leader)
    D2 = GenericUAVModel (follower)
    D3 = GenericUAVModel (follower)

Run with SITL:
    python examples/coordinator_demo.py
"""
import time
from droneresearch.models import GenericUAVModel, CoordinatorUAVModel

# Create coordinator as ground station
coord = CoordinatorUAVModel.as_ground_station()

# Create UAVs
d1 = GenericUAVModel("D1", "tcp:127.0.0.1:5760")
d2 = GenericUAVModel("D2", "tcp:127.0.0.1:5761")
d3 = GenericUAVModel("D3", "tcp:127.0.0.1:5762")

# Register with coordinator
coord.register("D1", d1)
coord.register("D2", d2)
coord.register("D3", d3)

# Connect all
for uav in [d1, d2, d3]:
    print(f"Connecting {uav.id}...")
    uav.connect()

# Set leader
coord.set_leader("D1")

# Set V-formation, 5m spacing
coord.set_formation("v", spacing=5.0)

print("FSM states before start:")
for uav in [d1, d2, d3]:
    print(f"  {uav.id}: {uav.fsm.state.name}")

# Staggered takeoff
print("\nTaking off all drones...")
coord.takeoff_all(altitude=10.0, stagger_s=2.0)

print("\nFSM states after takeoff:")
for uav in [d1, d2, d3]:
    print(f"  {uav.id}: {uav.fsm.state.name}")

# Start formation following (followers track leader position)
coord.start_formation_follow(update_hz=2.0)

print("\nSwarm status:")
import json
print(json.dumps(coord.swarm_status(), indent=2, default=str))

# Fly leader in a square — followers maintain formation
print("\nFlying leader in square mission...")
leader_wp = [
    {"lat": 48.1380, "lon": 11.5760, "alt": 10.0},
    {"lat": 48.1390, "lon": 11.5770, "alt": 10.0},
    {"lat": 48.1390, "lon": 11.5760, "alt": 10.0},
    {"lat": 48.1380, "lon": 11.5750, "alt": 10.0},
]
d1.run_mission_fsm(leader_wp, timeout=120)

print("\nLanding all...")
coord.stop_formation_follow()
coord.land_all()

print("\nFSM states after landing:")
for uav in [d1, d2, d3]:
    print(f"  {uav.id}: {uav.fsm.state.name}")
    print(f"  History: {uav.fsm.history()}")

for uav in [d1, d2, d3]:
    uav.disconnect()
print("Done.")

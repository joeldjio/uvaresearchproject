"""
Example: 3-drone circle formation.

Run:
    python examples/swarm_circle.py
"""
from droneresearch import Swarm

swarm = Swarm()
swarm.add("D1", "tcp:127.0.0.1:5760")
swarm.add("D2", "tcp:127.0.0.1:5761")
swarm.add("D3", "tcp:127.0.0.1:5762")

print("Connecting all drones ...")
results = swarm.connect_all(timeout=15.0)
for did, ok in results.items():
    print(f"  {did}: {'OK' if ok else 'FAILED'}")

print("Arming all ...")
swarm.arm_all()

print("Takeoff all to 10m ...")
swarm.takeoff_all(altitude=10.0)

print("Circle formation, 5m spacing ...")
swarm.formation("circle", spacing=5.0, leader="D1")

import time
time.sleep(20)

print("Landing all ...")
swarm.land_all()
swarm.disconnect_all()
print("Done.")

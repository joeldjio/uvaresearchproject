"""
Example: Simple hover at 10m for 15 seconds, then land.

Run:
    python examples/hover.py --port tcp:127.0.0.1:5760
"""
import argparse
from droneresearch import Drone

parser = argparse.ArgumentParser()
parser.add_argument("--port", default="tcp:127.0.0.1:5760")
parser.add_argument("--alt",  type=float, default=10.0)
parser.add_argument("--hold", type=float, default=15.0)
args = parser.parse_args()

drone = Drone(args.port)

print(f"Connecting to {args.port} ...")
if not drone.connect():
    raise SystemExit("Could not connect.")

print(f"Arming ...")
drone.arm()

print(f"Taking off to {args.alt}m ...")
drone.takeoff(altitude=args.alt)

print(f"Hovering for {args.hold}s ...")
drone.wait(args.hold)

print("Landing ...")
drone.land()
drone.disconnect()
print("Done.")

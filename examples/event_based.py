"""
Example: Event-based control — react to altitude and battery changes.

Run:
    python examples/event_based.py --port tcp:127.0.0.1:5760
"""
import argparse
from droneresearch import Drone

parser = argparse.ArgumentParser()
parser.add_argument("--port", default="tcp:127.0.0.1:5760")
args = parser.parse_args()

drone = Drone(args.port)

@drone.on("altitude")
def on_altitude(alt):
    if alt > 18.0:
        print(f"[event] altitude {alt:.1f}m — reducing speed")
        drone.set_speed(2.0)
    elif alt > 12.0:
        drone.set_speed(5.0)

@drone.on("battery")
def on_battery(pct):
    if 0 < pct < 20:
        print(f"[event] battery low ({pct:.0f}%) — RTL")
        drone.rtl()

@drone.on("mode")
def on_mode(mode):
    print(f"[event] mode changed → {mode}")

@drone.on("statustext")
def on_status(text, severity):
    if severity <= 4:
        print(f"[FC] {text}")

drone.connect()
drone.arm()
drone.takeoff(altitude=15.0)
drone.wait(30.0)
drone.land()
drone.disconnect()

"""
Example: Experiment — compare energy use at different speeds.

Flies a fixed-distance leg at 3 speeds, logs battery consumption per trial.

Run:
    python examples/speed_experiment.py --port tcp:127.0.0.1:5760
"""
import argparse
from droneresearch import Drone
from droneresearch.experiment import Experiment

parser = argparse.ArgumentParser()
parser.add_argument("--port", default="tcp:127.0.0.1:5760")
args = parser.parse_args()

drone = Drone(args.port)
drone.connect()

exp = Experiment("speed_energy")
exp.param("speed",    [2.0, 4.0, 6.0])
exp.param("altitude", 10.0)
exp.param("distance", 30.0)   # meters to fly forward


def run_trial(drone, params):
    battery_start = drone.battery

    drone.takeoff(altitude=params["altitude"])
    drone.set_speed(params["speed"])

    # Fly forward (north) by moving to offset waypoint
    import math
    dlat = params["distance"] / 111320.0
    drone.goto(drone.lat + dlat, drone.lon, params["altitude"])

    drone.land()

    battery_used = battery_start - drone.battery
    return {
        "battery_start": round(battery_start, 1),
        "battery_used":  round(battery_used, 1),
        "final_speed":   round(drone.groundspeed, 2),
    }


exp.on_trial_done(lambda r: print(f"  result: {r}"))
exp.run(drone, run_trial, repeat=1)
exp.export("results/speed_energy.csv")
print(exp.summary())

drone.disconnect()

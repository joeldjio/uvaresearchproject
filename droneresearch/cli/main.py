"""
DroneResearch CLI

Usage:
    droneresearch connect --port tcp:127.0.0.1:5760
    droneresearch status
    droneresearch arm
    droneresearch disarm
    droneresearch takeoff --alt 10
    droneresearch land
    droneresearch rtl
    droneresearch mode LOITER
    droneresearch goto --lat 48.137 --lon 11.575 --alt 20
    droneresearch run script.py
    droneresearch experiment run exp.yaml
    droneresearch log tail
"""
import argparse
import json
import os
import sys
import time


def main():
    parser = argparse.ArgumentParser(
        prog="droneresearch",
        description="DroneResearch CLI — scriptable drone research platform",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # connect
    p_con = sub.add_parser("connect", help="Connect to drone")
    p_con.add_argument("--port", required=True, help="Connection string e.g. tcp:127.0.0.1:5760")
    p_con.add_argument("--id",   default="drone", help="Drone ID")
    p_con.add_argument("--timeout", type=float, default=15.0)

    # status
    sub.add_parser("status", help="Print telemetry snapshot")

    # arm / disarm
    p_arm = sub.add_parser("arm",    help="Arm drone")
    p_arm.add_argument("--force", action="store_true")
    p_dis = sub.add_parser("disarm", help="Disarm drone")
    p_dis.add_argument("--force", action="store_true")

    # takeoff
    p_to = sub.add_parser("takeoff", help="Takeoff")
    p_to.add_argument("--alt", type=float, default=10.0)

    # land / rtl
    sub.add_parser("land", help="Land in place")
    sub.add_parser("rtl",  help="Return to launch")

    # mode
    p_mode = sub.add_parser("mode", help="Set flight mode")
    p_mode.add_argument("mode_name", help="e.g. LOITER, GUIDED, AUTO")

    # goto
    p_goto = sub.add_parser("goto", help="Fly to GPS position")
    p_goto.add_argument("--lat", type=float, required=True)
    p_goto.add_argument("--lon", type=float, required=True)
    p_goto.add_argument("--alt", type=float, required=True)

    # run script
    p_run = sub.add_parser("run", help="Execute Python script")
    p_run.add_argument("script", help="Path to .py script")
    p_run.add_argument("--port", default=os.environ.get("DRONE_PORT", "tcp:127.0.0.1:5760"))

    # experiment
    p_exp = sub.add_parser("experiment", help="Experiment manager")
    exp_sub = p_exp.add_subparsers(dest="exp_cmd")
    p_exp_run = exp_sub.add_parser("run")
    p_exp_run.add_argument("config", help="Path to .yaml experiment config")
    p_exp_run.add_argument("--port", default=os.environ.get("DRONE_PORT", "tcp:127.0.0.1:5760"))

    # ui
    sub.add_parser("ui", help="Launch the graphical UI")

    args = parser.parse_args()

    if args.command == "ui":
        _launch_ui()
        return

    if args.command == "run":
        _run_script(args)
        return

    if args.command == "experiment":
        _run_experiment(args)
        return

    # All other commands need a persistent connection session
    _run_command(args)


def _run_command(args):
    from droneresearch import Drone

    port = os.environ.get("DRONE_PORT", "tcp:127.0.0.1:5760")
    drone_id = getattr(args, "id", "drone")
    drone = Drone(port, drone_id=drone_id, auto_log=False)

    print(f"Connecting to {port} ...")
    if not drone.connect(timeout=getattr(args, "timeout", 10.0)):
        print("ERROR: Could not connect.", file=sys.stderr)
        sys.exit(1)
    print(f"Connected. Autopilot: {drone.telemetry.autopilot}")
    time.sleep(1.0)

    try:
        cmd = args.command
        if cmd == "connect":
            print(json.dumps(drone.telemetry.snapshot(), indent=2))
        elif cmd == "status":
            t = drone.telemetry
            print(f"  Armed:    {t.armed}")
            print(f"  Mode:     {t.flight_mode}")
            print(f"  Pos:      {t.lat:.6f}, {t.lon:.6f}, {t.alt_rel:.1f}m")
            print(f"  Battery:  {t.battery_pct:.0f}% ({t.battery_v:.2f}V)")
            print(f"  Speed:    {t.groundspeed:.1f} m/s")
        elif cmd == "arm":
            print("Arming...")
            ok = drone.arm(force=args.force)
            print("Armed." if ok else "Arm failed.")
        elif cmd == "disarm":
            print("Disarming...")
            ok = drone.disarm(force=args.force)
            print("Disarmed." if ok else "Disarm failed.")
        elif cmd == "takeoff":
            print(f"Taking off to {args.alt}m ...")
            ok = drone.takeoff(altitude=args.alt)
            print("Airborne." if ok else "Takeoff failed.")
        elif cmd == "land":
            print("Landing...")
            drone.land()
        elif cmd == "rtl":
            print("RTL...")
            drone.rtl()
        elif cmd == "mode":
            print(f"Setting mode {args.mode_name}...")
            ok = drone.set_mode(args.mode_name)
            print("OK" if ok else "Failed")
        elif cmd == "goto":
            print(f"Going to {args.lat}, {args.lon}, {args.alt}m ...")
            drone.goto(args.lat, args.lon, args.alt)
    finally:
        drone.disconnect()


def _run_script(args):
    from droneresearch import Drone
    from droneresearch.control.script_runner import ScriptRunner

    drone = Drone(args.port, auto_log=True)
    print(f"Connecting to {args.port} ...")
    if not drone.connect():
        print("ERROR: Could not connect.", file=sys.stderr)
        sys.exit(1)
    runner = ScriptRunner(drone)
    runner.on_output(print)
    runner.on_error(lambda t: print(f"ERROR: {t}", file=sys.stderr))
    runner.run_file(args.script, blocking=True)
    drone.disconnect()


def _run_experiment(args):
    print(f"[experiment] Loading {args.config} ...")
    try:
        import yaml
    except ImportError:
        print("pip install pyyaml required for experiment configs", file=sys.stderr)
        sys.exit(1)
    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    from droneresearch import Drone
    from droneresearch.experiment import Experiment
    from droneresearch.control.script_runner import ScriptRunner

    exp = Experiment(cfg.get("name", "experiment"))
    for k, v in cfg.get("params", {}).items():
        exp.param(k, v)

    script_path = cfg.get("script")
    if not script_path:
        print("ERROR: experiment config must have 'script' field", file=sys.stderr)
        sys.exit(1)

    drone = Drone(args.port)
    drone.connect()
    runner = ScriptRunner(drone)
    runner.on_output(print)

    def run_trial(d, params):
        code = open(script_path).read()
        import io, sys as _sys
        env = {"drone": d, "params": params, "log": print}
        exec(compile(code, script_path, "exec"), env)

    exp.run(drone, run_trial)
    out = cfg.get("output", "results/experiment.csv")
    exp.export(out)
    print(exp.summary())
    drone.disconnect()


def _launch_ui():
    try:
        from droneresearch.ui.app import main as ui_main
        ui_main()
    except ImportError:
        print("UI requires PySide6: pip install PySide6", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

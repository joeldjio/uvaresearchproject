"""
SITL Launcher — starts ArduPilot or PX4 SITL as a subprocess.

Provides a Python API to:
    - Start/stop SITL instances
    - Configure vehicle type, home location, speed-up factor
    - Multi-vehicle SITL (multiple instances on different ports)
    - Wait for SITL to be ready before connecting DroneResearch

ArduPilot SITL:
    https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html
    Default port: TCP 5760 (instance 0), 5770 (instance 1), ...

PX4 SITL (Gazebo):
    https://docs.px4.io/main/en/simulation/
    Default port: UDP 14550 (instance 0)

Usage:
    from droneresearch.simulation import SITLInstance, SITLCluster

    # Single ArduPilot SITL
    sitl = SITLInstance(autopilot="ardupilot", vehicle="copter")
    sitl.start()
    sitl.wait_ready()
    drone = Drone(sitl.connection_string)
    drone.connect()
    ...
    sitl.stop()

    # 3-vehicle PX4 cluster
    cluster = SITLCluster(autopilot="px4", count=3)
    cluster.start()
    connections = cluster.connection_strings  # list of 3 strings
"""
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SITLConfig:
    autopilot:  str   = "ardupilot"    # "ardupilot" | "px4"
    vehicle:    str   = "copter"       # "copter" | "plane" | "rover"
    instance:   int   = 0
    home_lat:   float = 48.1374        # Munich default
    home_lon:   float = 11.5754
    home_alt:   float = 519.0          # meters MSL
    home_yaw:   float = 0.0
    speedup:    float = 1.0            # simulation speed multiplier
    base_port:  int   = 5760           # ArduPilot TCP base port
    udp_port:   int   = 14550          # PX4 UDP base port
    extra_args: List[str] = field(default_factory=list)


class SITLInstance:
    """Single SITL vehicle instance."""

    def __init__(self, config: Optional[SITLConfig] = None, **kwargs):
        self.config = config or SITLConfig(**kwargs)
        self._proc: Optional[subprocess.Popen] = None

    @property
    def connection_string(self) -> str:
        if self.config.autopilot == "ardupilot":
            port = self.config.base_port + self.config.instance * 10
            return f"tcp:127.0.0.1:{port}"
        else:
            port = self.config.udp_port + self.config.instance
            return f"udp:127.0.0.1:{port}"

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self) -> bool:
        if self.is_running:
            return True
        if self.config.autopilot == "ardupilot":
            return self._start_ardupilot()
        elif self.config.autopilot == "px4":
            return self._start_px4()
        return False

    def stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None
        print(f"[sitl:{self.config.instance}] Stopped.")

    def wait_ready(self, timeout: float = 30.0) -> bool:
        """Wait until SITL is accepting connections."""
        import socket
        if self.config.autopilot == "ardupilot":
            host, port = "127.0.0.1", self.config.base_port + self.config.instance * 10
        else:
            return True   # PX4 UDP doesn't need port check
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                with socket.create_connection((host, port), timeout=1.0):
                    print(f"[sitl:{self.config.instance}] Ready on {self.connection_string}")
                    return True
            except (ConnectionRefusedError, OSError):
                time.sleep(0.5)
        print(f"[sitl:{self.config.instance}] Timeout waiting for SITL")
        return False

    def _start_ardupilot(self) -> bool:
        sitl_bin = shutil.which("arducopter") or shutil.which("arducopter-SITL")
        if not sitl_bin:
            # Try common install paths
            candidates = [
                os.path.expanduser("~/ardupilot/build/sitl/bin/arducopter"),
                "/usr/local/bin/arducopter",
            ]
            sitl_bin = next((c for c in candidates if os.path.isfile(c)), None)
        if not sitl_bin:
            print("[sitl] arducopter not found. Install ArduPilot SITL:")
            print("  https://ardupilot.org/dev/docs/building-setup-linux.html")
            return False

        home = f"{self.config.home_lat},{self.config.home_lon},{self.config.home_alt},{self.config.home_yaw}"
        port = self.config.base_port + self.config.instance * 10
        cmd  = [
            sitl_bin,
            "--home",    home,
            "--model",   "+",
            "--speedup", str(self.config.speedup),
            "--port",    str(port),
            "--instance",str(self.config.instance),
        ] + self.config.extra_args

        print(f"[sitl:{self.config.instance}] Starting ArduPilot SITL on port {port}")
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True

    def _start_px4(self) -> bool:
        px4_dir = os.environ.get("PX4_DIR", os.path.expanduser("~/PX4-Autopilot"))
        if not os.path.isdir(px4_dir):
            print(f"[sitl] PX4-Autopilot not found at {px4_dir}")
            print("  Set PX4_DIR env var or clone: https://github.com/PX4/PX4-Autopilot")
            return False

        env = os.environ.copy()
        env["PX4_UXRCE_DDS_NS"] = f"uav_{self.config.instance + 1}"
        if self.config.instance > 0:
            env["PX4_SIM_PORT_OFFSET"] = str(self.config.instance * 10)

        cmd = ["make", "px4_sitl", "gz_x500"]
        print(f"[sitl:{self.config.instance}] Starting PX4 SITL (Gazebo)")
        self._proc = subprocess.Popen(
            cmd, cwd=px4_dir, env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True

    def __enter__(self):
        self.start()
        self.wait_ready()
        return self

    def __exit__(self, *_):
        self.stop()


class SITLCluster:
    """
    Multi-vehicle SITL cluster.

    Usage:
        with SITLCluster(count=3) as cluster:
            for conn in cluster.connection_strings:
                drone = Drone(conn)
                drone.connect()
    """

    def __init__(
        self,
        count:      int   = 3,
        autopilot:  str   = "ardupilot",
        vehicle:    str   = "copter",
        home_lat:   float = 48.1374,
        home_lon:   float = 11.5754,
        spacing_m:  float = 5.0,
        speedup:    float = 1.0,
    ):
        import math
        self.instances = []
        for i in range(count):
            # Offset each drone slightly east
            lon_offset = (i * spacing_m) / (111320.0 * math.cos(math.radians(home_lat)))
            cfg = SITLConfig(
                autopilot=autopilot,
                vehicle=vehicle,
                instance=i,
                home_lat=home_lat,
                home_lon=home_lon + lon_offset,
                speedup=speedup,
            )
            self.instances.append(SITLInstance(cfg))

    @property
    def connection_strings(self) -> List[str]:
        return [inst.connection_string for inst in self.instances]

    def start(self, stagger_s: float = 2.0):
        for inst in self.instances:
            inst.start()
            time.sleep(stagger_s)

    def wait_ready(self, timeout: float = 60.0):
        for inst in self.instances:
            inst.wait_ready(timeout=timeout)

    def stop(self):
        for inst in self.instances:
            inst.stop()

    def __enter__(self):
        self.start()
        self.wait_ready()
        return self

    def __exit__(self, *_):
        self.stop()

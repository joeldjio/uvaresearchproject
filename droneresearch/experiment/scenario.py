"""
Scenario — reproducible, declarative experiment definition.

A Scenario defines everything needed to reproduce an experiment:
    - SITL config (autopilot, vehicle, home location)
    - Mission / script to execute
    - Parameters to vary (grid search)
    - Metrics to collect
    - Success criteria

Scenarios are serializable to JSON/YAML for archiving and sharing.

Usage:
    from droneresearch.experiment import Scenario, run_scenario

    scenario = Scenario(
        name="hover_stability_test",
        autopilot="ardupilot",
        mission=[
            {"cmd": "takeoff", "alt": 10},
            {"cmd": "hover",   "duration": 30},
            {"cmd": "land"},
        ],
        params={"speed": [1, 3, 5]},
        metrics=["position_error", "battery_drain", "flight_time"],
    )
    results = run_scenario(scenario)
    results.save("results/hover_stability.json")
"""
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from droneresearch.experiment.metrics import MetricsCollector


@dataclass
class Scenario:
    """
    Fully-reproducible experiment definition.
    Serialize with .to_dict() / .save() and reload with .load().
    """
    name:       str
    autopilot:  str   = "ardupilot"          # "ardupilot" | "px4"
    vehicle:    str   = "copter"
    home_lat:   float = 48.1374
    home_lon:   float = 11.5754
    home_alt:   float = 519.0
    speedup:    float = 1.0                   # SITL speed multiplier
    mission:    List[dict] = field(default_factory=list)
    params:     Dict[str, List[Any]] = field(default_factory=dict)
    metrics:    List[str] = field(default_factory=list)
    timeout_s:  float = 300.0
    description: str  = ""
    tags:       List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        import dataclasses
        return dataclasses.asdict(self)

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "Scenario":
        with open(path) as f:
            data = json.load(f)
        return cls(**data)

    def param_combinations(self) -> List[Dict[str, Any]]:
        """Generate all parameter combinations (grid search)."""
        if not self.params:
            return [{}]
        import itertools
        keys   = list(self.params.keys())
        values = list(self.params.values())
        return [
            dict(zip(keys, combo))
            for combo in itertools.product(*values)
        ]


@dataclass
class ScenarioResult:
    """Result of a single scenario run."""
    scenario_name: str
    run_id:        str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    params:        dict = field(default_factory=dict)
    metrics:       dict = field(default_factory=dict)
    success:       bool = False
    error:         str  = ""
    start_time:    float = field(default_factory=time.time)
    end_time:      float = 0.0
    log_path:      str  = ""

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    def to_dict(self) -> dict:
        import dataclasses
        return dataclasses.asdict(self)

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


class ScenarioRunner:
    """
    Runs a Scenario — handles SITL lifecycle, mission execution,
    metric collection, and result export.

    For each param combination, a fresh SITL instance is started.
    """

    def __init__(
        self,
        scenario:   Scenario,
        results_dir: str = "results",
        on_result:  Optional[Callable[[ScenarioResult], None]] = None,
        use_sitl:   bool = True,
    ):
        self.scenario     = scenario
        self.results_dir  = Path(results_dir)
        self._on_result   = on_result
        self._use_sitl    = use_sitl
        self.results:     List[ScenarioResult] = []

    def run(self) -> List[ScenarioResult]:
        """Run all parameter combinations."""
        combos = self.scenario.param_combinations()
        print(f"[scenario:{self.scenario.name}] "
              f"Running {len(combos)} combination(s)")
        for combo in combos:
            result = self._run_single(combo)
            self.results.append(result)
            if self._on_result:
                self._on_result(result)
        self._save_summary()
        return self.results

    def _run_single(self, params: dict) -> ScenarioResult:
        result = ScenarioResult(
            scenario_name=self.scenario.name,
            params=params,
        )
        print(f"  params={params}")
        if self._use_sitl:
            from droneresearch.simulation import SITLInstance, SITLConfig
            sitl_cfg = SITLConfig(
                autopilot=self.scenario.autopilot,
                vehicle=self.scenario.vehicle,
                home_lat=self.scenario.home_lat,
                home_lon=self.scenario.home_lon,
                home_alt=self.scenario.home_alt,
                speedup=self.scenario.speedup,
            )
            sitl = SITLInstance(sitl_cfg)
        else:
            sitl = None

        metrics = MetricsCollector(self.scenario.metrics)
        try:
            if sitl:
                sitl.start()
                sitl.wait_ready(timeout=30)
                conn_str = sitl.connection_string
            else:
                conn_str = "tcp:127.0.0.1:5760"

            from droneresearch.autopilot import get_backend
            backend = get_backend(self.scenario.autopilot)
            backend.connect(conn_str)
            metrics.attach(backend)
            metrics.start()

            self._execute_mission(backend, params)

            result.success = True
        except Exception as e:
            result.error   = str(e)
            result.success = False
            print(f"  ERROR: {e}")
        finally:
            metrics.stop()
            result.metrics  = metrics.summary()
            result.end_time = time.time()
            if sitl:
                sitl.stop()

        log_path = self.results_dir / self.scenario.name / f"{result.run_id}.json"
        result.log_path = str(log_path)
        result.save(str(log_path))
        return result

    def _execute_mission(self, backend, params: dict):
        """Execute mission steps with param substitution."""
        for step in self.scenario.mission:
            cmd = step.get("cmd", "").lower()
            if cmd == "takeoff":
                alt = params.get("alt", step.get("alt", 10.0))
                backend.takeoff(float(alt))
                time.sleep(5)
            elif cmd == "hover":
                dur = params.get("duration", step.get("duration", 10.0))
                time.sleep(float(dur))
            elif cmd == "land":
                backend.land()
                time.sleep(5)
            elif cmd == "rtl":
                backend.rtl()
                time.sleep(10)
            elif cmd == "goto":
                backend.goto(step["lat"], step["lon"],
                             params.get("alt", step.get("alt", 10.0)))
                time.sleep(step.get("wait", 5))
            elif cmd == "set_mode":
                backend.set_mode(step["mode"])
            elif cmd == "wait":
                time.sleep(float(step.get("seconds", 1)))

    def _save_summary(self):
        summary_path = self.results_dir / self.scenario.name / "summary.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "scenario": self.scenario.name,
            "total":    len(self.results),
            "success":  sum(1 for r in self.results if r.success),
            "results":  [r.to_dict() for r in self.results],
        }
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"[scenario] Summary: {summary_path}")

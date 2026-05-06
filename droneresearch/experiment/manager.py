"""
Experiment Manager — define, run, and evaluate repeatable drone experiments.

Usage:
    from droneresearch.experiment import Experiment

    exp = Experiment("speed_comparison")
    exp.param("speed", [2.0, 4.0, 6.0])
    exp.param("altitude", 10.0)

    def run_trial(drone, params):
        drone.takeoff(params["altitude"])
        drone.set_speed(params["speed"])
        drone.wait(10)
        drone.land()

    exp.run(drone, run_trial)
    exp.export("results/speed_comparison.csv")
    print(exp.summary())
"""
import csv
import itertools
import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union


class Experiment:
    def __init__(self, name: str):
        self.name    = name
        self._params: Dict[str, Any] = {}
        self._results: List[dict]    = []
        self._on_trial_start: Optional[Callable] = None
        self._on_trial_done:  Optional[Callable] = None

    # ── Parameter definition ──────────────────────────────────────────────

    def param(self, name: str, value: Union[Any, List]):
        """
        Define a parameter.
        - Single value  → used in every trial
        - List of values → one trial per combination
        """
        self._params[name] = value

    def param_space(self) -> List[dict]:
        """Return all parameter combinations (grid search)."""
        lists = {}
        fixed = {}
        for k, v in self._params.items():
            if isinstance(v, list):
                lists[k] = v
            else:
                fixed[k] = v
        if not lists:
            return [dict(fixed)]
        keys   = list(lists.keys())
        combos = list(itertools.product(*[lists[k] for k in keys]))
        result = []
        for combo in combos:
            p = dict(fixed)
            p.update(dict(zip(keys, combo)))
            result.append(p)
        return result

    # ── Run ───────────────────────────────────────────────────────────────

    def run(self, drone, fn: Callable, repeat: int = 1):
        """
        Run all parameter combinations.

        fn(drone, params) → optional dict of metrics
        """
        trials = self.param_space()
        total  = len(trials) * repeat
        print(f"[experiment] '{self.name}' — {total} trials")
        for trial_idx, params in enumerate(trials):
            for rep in range(repeat):
                print(f"[experiment] trial {trial_idx+1}/{len(trials)} rep {rep+1}/{repeat}: {params}")
                if self._on_trial_start:
                    self._on_trial_start(trial_idx, params)
                t_start = time.time()
                metrics = {}
                try:
                    result = fn(drone, dict(params))
                    if isinstance(result, dict):
                        metrics = result
                except Exception as e:
                    metrics["error"] = str(e)
                    print(f"[experiment] trial error: {e}")
                duration = time.time() - t_start
                record = {
                    "trial":    trial_idx,
                    "rep":      rep,
                    "duration": round(duration, 3),
                    **params,
                    **metrics,
                }
                self._results.append(record)
                if self._on_trial_done:
                    self._on_trial_done(record)

    # ── Callbacks ─────────────────────────────────────────────────────────

    def on_trial_start(self, cb: Callable):
        self._on_trial_start = cb

    def on_trial_done(self, cb: Callable):
        self._on_trial_done = cb

    # ── Export ────────────────────────────────────────────────────────────

    def export(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        if path.endswith(".json"):
            with open(path, "w") as f:
                json.dump({"name": self.name, "results": self._results}, f, indent=2)
        else:
            if not self._results:
                return
            fields = list(self._results[0].keys())
            with open(path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                w.writerows(self._results)
        print(f"[experiment] exported to {path}")

    def summary(self) -> str:
        if not self._results:
            return "No results yet."
        lines = [f"Experiment: {self.name}",
                 f"Trials: {len(self._results)}"]
        durations = [r.get("duration", 0) for r in self._results]
        lines.append(f"Avg duration: {sum(durations)/len(durations):.1f}s")
        errors = [r for r in self._results if "error" in r]
        if errors:
            lines.append(f"Errors: {len(errors)}")
        return "\n".join(lines)

    @property
    def results(self) -> List[dict]:
        return list(self._results)

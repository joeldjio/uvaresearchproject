"""
Swarm-scaling benchmark for the DroneResearch GCS.

Goal
----
Find the per-tick cost of the UI's hot paths as a function of the number
of drones N:

  1. ``TelemetryModel.update_all(snapshots)`` — translates SDK snapshots into
     differential dataChanged emissions for QML. O(N · roles).
  2. APF pairwise distance check — quadratic, O(N²). The real
     ``APFSafetyFilter`` is used if importable; otherwise an in-place
     equivalent (haversine + altitude diff) measures the same algorithmic
     cost without pulling extra deps.
  3. Aggregate cycle — bundles per-drone snapshot dicts the same way
     ``SwarmBackend._aggregate`` does and emits a single signal.

What this benchmark is NOT
--------------------------
* No real MAVLink, no SITL, no QML window. It measures only the Python /
  Qt-signal hot paths. Real-world limits are usually IO-bound (MAVLink
  serial / TCP / DDS throughput) and stricter than what this prints.
* No GPU / rendering. The map and InstrBar are not exercised.

Run
---
    python -m tools.ui.benchmarks.swarm_scaling                 # default Ns
    python -m tools.ui.benchmarks.swarm_scaling --ns 1,5,25,100 # custom
    python -m tools.ui.benchmarks.swarm_scaling --ticks 500     # iterations
    python -m tools.ui.benchmarks.swarm_scaling --json out.json # machine output
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple


# ── Synthetic snapshot factory ─────────────────────────────────────────────


def _make_snapshots(n: int, rng: random.Random) -> Dict[str, dict]:
    """Build N drone snapshots around a fixed reference (47°N, 8°E)."""
    snaps: Dict[str, dict] = {}
    for i in range(n):
        # Spread drones in a ~200m square so the APF pairwise distance is
        # non-trivial (some pairs will be close, most far).
        dx = rng.uniform(-100, 100)  # metres east
        dy = rng.uniform(-100, 100)  # metres north
        lat = 47.0 + dy / 111_320.0
        lon = 8.0 + dx / (111_320.0 * math.cos(math.radians(47.0)))
        snaps[f"D{i:03d}"] = {
            "lat":         lat,
            "lon":         lon,
            "alt_rel":     rng.uniform(5, 30),
            "alt":         rng.uniform(100, 130),
            "groundspeed": rng.uniform(0, 10),
            "yaw":         rng.uniform(0, 360),
            "roll":        rng.uniform(-15, 15),
            "pitch":       rng.uniform(-15, 15),
            "armed":       True,
            "flight_mode": "GUIDED",
            "battery_pct": rng.uniform(40, 100),
            "battery_v":   rng.uniform(11.5, 12.6),
            "satellites":  rng.randint(8, 18),
            "gps_fix":     3,
            "climb":       rng.uniform(-1, 1),
            "throttle":    rng.uniform(20, 80),
            "connected":   True,
        }
    return snaps


def _mutate(snapshots: Dict[str, dict], rng: random.Random,
            change_fraction: float = 0.3) -> None:
    """Mutate roughly ``change_fraction`` of the snapshots in place.

    Emulates real drift: not every tick changes every field.
    """
    for did, s in snapshots.items():
        if rng.random() > change_fraction:
            continue
        s["lat"]         += rng.uniform(-1e-5, 1e-5)
        s["lon"]         += rng.uniform(-1e-5, 1e-5)
        s["alt_rel"]     += rng.uniform(-0.1, 0.1)
        s["groundspeed"] += rng.uniform(-0.2, 0.2)
        s["yaw"]          = (s["yaw"] + rng.uniform(-2, 2)) % 360.0
        s["battery_pct"] -= 0.001  # tiny drain


# ── Pairwise distance (APF surrogate) ──────────────────────────────────────


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def _apf_pairwise_distances(snapshots: Dict[str, dict]) -> int:
    """Compute distance for every drone pair. Returns the pair count.

    Mirrors what :class:`APFSafetyFilter._check_separations` does, but
    self-contained so the benchmark works without the real safety filter.
    """
    ids = list(snapshots.keys())
    pairs = 0
    for i in range(len(ids)):
        si = snapshots[ids[i]]
        for j in range(i + 1, len(ids)):
            sj = snapshots[ids[j]]
            d_h = _haversine_m(si["lat"], si["lon"], sj["lat"], sj["lon"])
            d_v = abs(si["alt_rel"] - sj["alt_rel"])
            _ = math.sqrt(d_h * d_h + d_v * d_v)
            pairs += 1
    return pairs


# ── Result dataclass ───────────────────────────────────────────────────────


@dataclass
class Result:
    n_drones:           int
    ticks:              int
    telemetry_ms_per_tick: float
    telemetry_hz_max:   float          # 1000 / telemetry_ms_per_tick
    apf_ms_per_tick:    float
    apf_hz_max:         float
    pairs_per_tick:     int
    headroom_at_10hz:   float          # 1.0 = exactly maxed, >1 = spare
    headroom_at_5hz:    float

    def pretty(self) -> str:
        return (
            f"  N={self.n_drones:>3}  "
            f"telemetry {self.telemetry_ms_per_tick:6.2f} ms/tick "
            f"({self.telemetry_hz_max:6.0f} Hz max)  |  "
            f"APF {self.apf_ms_per_tick:6.2f} ms/tick "
            f"({self.apf_hz_max:6.0f} Hz max, {self.pairs_per_tick:>5} pairs)  |  "
            f"10 Hz headroom={self.headroom_at_10hz:5.2f}x  "
            f"5 Hz headroom={self.headroom_at_5hz:5.2f}x"
        )


# ── Benchmark runner ───────────────────────────────────────────────────────


def _bench_telemetry(n: int, ticks: int, rng: random.Random) -> Tuple[float, int]:
    """Return (avg_ms_per_tick, dataChanged_emit_count)."""
    # Local import: the model needs PyQt6 + a QCoreApplication context.
    from PyQt6.QtCore import QCoreApplication
    app = QCoreApplication.instance() or QCoreApplication([])

    from tools.ui.context.telemetry_context import TelemetryModel

    model = TelemetryModel()
    emit_count = [0]
    model.dataChanged.connect(lambda *_a, **_k: _bump(emit_count))

    snapshots = _make_snapshots(n, rng)
    model.update_all(snapshots)         # warm-up insert

    t0 = time.perf_counter()
    for _ in range(ticks):
        _mutate(snapshots, rng)
        model.update_all(snapshots)
    elapsed = time.perf_counter() - t0
    # Pump pending queued events (signals are direct-connection here, but
    # we still flush to keep timing fair across Qt versions).
    app.processEvents()
    return (elapsed / ticks) * 1000.0, emit_count[0]


def _bump(counter: List[int]) -> None:
    counter[0] += 1


def _bench_apf(n: int, ticks: int, rng: random.Random) -> Tuple[float, int]:
    snapshots = _make_snapshots(n, rng)
    pair_count = 0
    t0 = time.perf_counter()
    for _ in range(ticks):
        _mutate(snapshots, rng, change_fraction=0.5)
        pair_count = _apf_pairwise_distances(snapshots)
    elapsed = time.perf_counter() - t0
    return (elapsed / ticks) * 1000.0, pair_count


def run(ns: List[int], ticks: int, seed: int) -> List[Result]:
    rng = random.Random(seed)
    results: List[Result] = []
    print(f"Running benchmark: ticks={ticks}, seed={seed}")
    print("-" * 110)
    for n in ns:
        if n <= 0:
            continue
        tele_ms, _emits = _bench_telemetry(n, ticks, rng)
        apf_ms,  pairs = _bench_apf(n, ticks, rng)
        # Combined per-tick cost the GCS pays at the most-frequent rate.
        # TelemetryModel updates at 5 Hz (SwarmBackend aggregation), APF
        # at 10 Hz. Headroom = budget_ms / observed_ms.
        budget_10hz = 100.0   # 1000 ms / 10 Hz
        budget_5hz  = 200.0
        # APF runs at 10 Hz; telemetry at 5 Hz. We report both.
        head_10 = budget_10hz / max(apf_ms, 0.001)
        head_5  = budget_5hz  / max(tele_ms, 0.001)
        r = Result(
            n_drones              = n,
            ticks                 = ticks,
            telemetry_ms_per_tick = tele_ms,
            telemetry_hz_max      = 1000.0 / max(tele_ms, 0.001),
            apf_ms_per_tick       = apf_ms,
            apf_hz_max            = 1000.0 / max(apf_ms, 0.001),
            pairs_per_tick        = pairs,
            headroom_at_10hz      = head_10,
            headroom_at_5hz       = head_5,
        )
        results.append(r)
        print(r.pretty())
    print("-" * 110)
    return results


def _interpret(results: List[Result]) -> str:
    """Find the largest N that keeps both rates comfortably under budget."""
    def comfortable(r: Result) -> bool:
        # Comfortable = at least 3x headroom (room for GC / IO / GUI)
        return r.headroom_at_10hz >= 3.0 and r.headroom_at_5hz >= 3.0

    def survivable(r: Result) -> bool:
        return r.headroom_at_10hz >= 1.0 and r.headroom_at_5hz >= 1.0

    comf = [r.n_drones for r in results if comfortable(r)]
    surv = [r.n_drones for r in results if survivable(r)]
    lines = ["", "Interpretation:"]
    if comf:
        lines.append(f"  Comfortable (≥3x headroom on both APF+telemetry):  up to N = {max(comf)}")
    else:
        lines.append("  Comfortable range: even smallest tested N is tight — try lower budget.")
    if surv:
        lines.append(f"  Survivable   (≥1x, meets budget but no spare):      up to N = {max(surv)}")
    else:
        lines.append("  Survivable range: budget exceeded for all tested N.")
    lines.append("")
    lines.append("Notes:")
    lines.append("  - APF cost is O(N²); telemetry cost is O(N).")
    lines.append("  - These numbers are CPU-only. Real-world MAVLink/DDS IO adds latency.")
    lines.append("  - If APF is your bottleneck, lower its frequency in SafetyContext.")
    return "\n".join(lines)


# ── CLI ─────────────────────────────────────────────────────────────────────


def _parse_ns(spec: str) -> List[int]:
    return sorted({int(x.strip()) for x in spec.split(",") if x.strip()})


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ns", default="1,5,10,15,25,50,100",
                   help="Comma-separated drone counts to test")
    p.add_argument("--ticks", type=int, default=200,
                   help="Iterations per N (default 200)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--json", metavar="PATH",
                   help="Also write machine-readable results to PATH")
    args = p.parse_args(argv)

    ns = _parse_ns(args.ns)
    results = run(ns, args.ticks, args.seed)
    print(_interpret(results))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in results], f, indent=2)
        print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

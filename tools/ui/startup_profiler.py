"""
Startup profiler — measures cold-start phases so we can track regressions.

Usage:
    from tools.ui.startup_profiler import profiler
    profiler.mark("phase_name")
    profiler.report()    # at end of run()
"""
import time
import os
from typing import List, Tuple


class StartupProfiler:
    def __init__(self) -> None:
        self._start: float = time.perf_counter()
        self._marks: List[Tuple[str, float]] = []
        self._enabled: bool = os.environ.get("GCS_PROFILE", "1") != "0"

    def mark(self, name: str) -> None:
        if not self._enabled:
            return
        t = time.perf_counter() - self._start
        self._marks.append((name, t))

    def report(self) -> None:
        if not self._enabled or not self._marks:
            return
        prev = 0.0
        print("\n[STARTUP PROFILER]")
        print(f"  {'Phase':<32} {'Δ ms':>8} {'Total':>9}")
        print(f"  {'-'*32} {'-'*8} {'-'*9}")
        for name, t in self._marks:
            delta_ms = (t - prev) * 1000
            total_ms = t * 1000
            print(f"  {name:<32} {delta_ms:>8.1f} {total_ms:>8.1f}ms")
            prev = t
        print(f"  {'-'*32} {'-'*8} {'-'*9}")
        print(f"  {'Total cold-start':<32} {'':>8} {self._marks[-1][1]*1000:>8.1f}ms\n")


profiler = StartupProfiler()

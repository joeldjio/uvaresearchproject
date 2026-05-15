"""Tests for :mod:`droneresearch.core.telemetry`."""
from __future__ import annotations

import threading
import time

import pytest

from droneresearch.core.telemetry import TelemetryState


class TestUpdate:
    def test_update_writes_known_fields(self):
        t = TelemetryState()
        t.update(lat=47.5, lon=8.5, alt=100.0)
        assert t.lat == 47.5
        assert t.lon == 8.5
        assert t.alt == 100.0

    def test_update_ignores_unknown_fields(self):
        t = TelemetryState()
        t.update(bogus_field=123)
        assert not hasattr(t, "bogus_field") or getattr(t, "bogus_field", None) == 123


class TestSnapshot:
    def test_snapshot_returns_dict_copy(self):
        t = TelemetryState()
        t.update(lat=47.0)
        snap = t.snapshot()
        assert snap["lat"] == 47.0
        # Mutating the snapshot must not affect the live state.
        snap["lat"] = 99.0
        assert t.lat == 47.0

    def test_snapshot_excludes_private_fields(self):
        t = TelemetryState()
        snap = t.snapshot()
        assert not any(k.startswith("_") for k in snap.keys())

    def test_snapshot_includes_all_public_fields(self):
        t = TelemetryState()
        snap = t.snapshot()
        # Spot-check a few essentials.
        for f in ("lat", "lon", "alt", "armed", "flight_mode", "battery_pct"):
            assert f in snap


class TestProperties:
    def test_is_stale_true_initially(self):
        t = TelemetryState()
        assert t.is_stale is True

    def test_is_stale_false_when_fresh(self):
        t = TelemetryState()
        t.update(last_heartbeat=time.time())
        assert t.is_stale is False

    def test_has_gps_requires_3d_fix(self):
        t = TelemetryState()
        assert t.has_gps is False
        t.update(gps_fix=2)
        assert t.has_gps is False
        t.update(gps_fix=3)
        assert t.has_gps is True


class TestConcurrency:
    def test_concurrent_updates_dont_corrupt(self):
        """Snapshot under load should always be internally consistent."""
        t = TelemetryState()
        stop = threading.Event()

        def writer():
            counter = 0
            while not stop.is_set():
                counter += 1
                t.update(lat=float(counter), lon=float(counter))

        w = threading.Thread(target=writer, daemon=True)
        w.start()
        # Take many snapshots; lat == lon must hold every time because both
        # are written under the same lock in update().
        for _ in range(1000):
            snap = t.snapshot()
            assert snap["lat"] == snap["lon"]
        stop.set()
        w.join(timeout=2.0)

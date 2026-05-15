"""Tests for :mod:`droneresearch.data.logger`."""
from __future__ import annotations

import csv
import time
from pathlib import Path
from queue import Queue

import pytest

from droneresearch.data.logger import TelemetryLogger


@pytest.fixture
def logger(tmp_path: Path):
    lg = TelemetryLogger(log_dir=str(tmp_path))
    yield lg
    if lg._running:
        lg.stop()


class TestLifecycle:
    def test_start_creates_csv_with_header(self, logger: TelemetryLogger, tmp_path: Path):
        logger.start(drone_id="UNIT")
        logger.log({"lat": 47.0, "lon": 8.0})
        logger.stop()
        # Find the CSV file just created.
        csvs = list(tmp_path.glob("*_UNIT_telemetry.csv"))
        assert len(csvs) == 1
        rows = list(csv.DictReader(open(csvs[0])))
        assert len(rows) == 1
        assert rows[0]["lat"] == "47.0"
        assert rows[0]["drone_id"] == "UNIT"

    def test_log_before_start_is_ignored(self, logger: TelemetryLogger):
        logger.log({"lat": 1.0})   # not running -> no crash, no queue entry
        assert logger._queue.qsize() == 0

    def test_double_start_is_idempotent(self, logger: TelemetryLogger):
        logger.start(drone_id="X")
        logger.start(drone_id="X")   # second call should be a no-op
        logger.stop()

    def test_log_event_recorded(self, logger: TelemetryLogger, tmp_path: Path):
        logger.start(drone_id="E")
        logger.log_event("takeoff", {"alt": 10})
        logger.stop()
        events = list(tmp_path.glob("*_E_events.json"))
        assert len(events) == 1
        import json
        data = json.loads(events[0].read_text())
        assert data[0]["event"] == "takeoff"
        assert data[0]["data"]["alt"] == 10


class TestDropAccounting:
    def test_dropped_count_starts_at_zero(self, logger: TelemetryLogger):
        assert logger.dropped_count == 0

    def test_full_queue_increments_drop_counter(self, logger: TelemetryLogger):
        logger.start(drone_id="DROP")
        # Shrink the queue so we can saturate it deterministically and the
        # writer thread can't drain fast enough.
        logger._queue = Queue(maxsize=2)
        for i in range(50):
            logger.log({"x": i})
        logger.stop()
        assert logger.dropped_count > 0

    def test_warning_is_rate_limited(self, logger: TelemetryLogger, capsys):
        logger.start(drone_id="RL")
        logger._queue = Queue(maxsize=1)
        logger._DROP_WARN_EVERY_S = 5.0
        for i in range(200):
            logger.log({"x": i})
        out = capsys.readouterr().out
        warns = [ln for ln in out.splitlines() if "queue full" in ln]
        # 200 drops but the rate-limit should emit at most ~2 lines per second.
        assert 1 <= len(warns) <= 3
        logger.stop()

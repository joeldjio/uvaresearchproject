"""
TelemetryLogger — writes telemetry to CSV + JSON event log.

ROS bag support: if rclpy is available, also writes .bag file.

Usage:
    logger = TelemetryLogger("logs/")
    logger.start(drone_id="D1")
    logger.log(telemetry_snapshot)
    logger.stop()
"""
import csv
import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from queue import Empty, Full, Queue
from typing import Optional


class TelemetryLogger:
    CSV_FIELDS = [
        "timestamp", "drone_id",
        "lat", "lon", "alt", "alt_rel",
        "roll", "pitch", "yaw",
        "vx", "vy", "vz", "groundspeed", "airspeed", "climb",
        "battery_v", "battery_pct", "current_a",
        "armed", "flight_mode",
        "gps_fix", "satellites",
        "throttle",
    ]

    def __init__(self, log_dir: str = "logs"):
        self.log_dir   = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._queue    = Queue(maxsize=10000)
        self._thread: Optional[threading.Thread] = None
        self._running  = False
        self._csv_file = None
        self._csv_writer = None
        self._json_events = []
        self._session_start = 0.0
        self._drone_id = "unknown"
        self._session_path = ""
        # Drop accounting — used to surface backpressure that previously
        # vanished silently into a bare ``except: pass`` block.
        self._dropped: int       = 0
        self._last_drop_warn: float = 0.0
        self._DROP_WARN_EVERY_S: float = 5.0

    def start(self, drone_id: str = "drone"):
        if self._running:
            return
        self._drone_id = drone_id
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = self.log_dir / f"{ts}_{drone_id}"
        self._session_path = str(base)
        self._session_start = time.time()
        self._json_events = []
        # Open CSV
        csv_path = f"{base}_telemetry.csv"
        self._csv_file = open(csv_path, "w", newline="")
        self._csv_writer = csv.DictWriter(self._csv_file, fieldnames=self.CSV_FIELDS)
        self._csv_writer.writeheader()
        # Start writer thread
        self._running = True
        self._thread = threading.Thread(target=self._writer, daemon=True, name=f"logger-{drone_id}")
        self._thread.start()
        print(f"[logger] Logging to {csv_path}")

    def log(self, snapshot: dict):
        if not self._running:
            return
        snapshot["timestamp"] = time.time()
        snapshot["drone_id"]  = self._drone_id
        try:
            self._queue.put_nowait(snapshot)
        except Full:
            # Queue is saturated — the writer thread can't keep up. Count
            # the drop and log at most once every DROP_WARN_EVERY_S so we
            # don't drown the console while still letting the operator
            # notice the data loss.
            self._dropped += 1
            now = time.time()
            if now - self._last_drop_warn >= self._DROP_WARN_EVERY_S:
                self._last_drop_warn = now
                print(
                    f"[logger:{self._drone_id}] WARN: queue full — dropped "
                    f"{self._dropped} samples so far (writer thread too slow?)"
                )
        except Exception as e:
            # Anything other than Full is a real bug — surface it.
            print(f"[logger:{self._drone_id}] ERROR: log enqueue failed: {e}")

    def log_event(self, event: str, data: dict = None):
        entry = {
            "timestamp": time.time(),
            "drone_id":  self._drone_id,
            "event":     event,
            "data":      data or {},
        }
        self._json_events.append(entry)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
        if self._dropped:
            print(
                f"[logger:{self._drone_id}] Session dropped {self._dropped} "
                f"telemetry sample(s) due to writer backpressure."
            )
        # Flush remaining
        while not self._queue.empty():
            try:
                row = self._queue.get_nowait()
                self._write_row(row)
            except Empty:
                break
        if self._csv_file:
            self._csv_file.close()
        # Write events JSON
        if self._json_events and self._session_path:
            json_path = f"{self._session_path}_events.json"
            with open(json_path, "w") as f:
                json.dump(self._json_events, f, indent=2)
            print(f"[logger] Events saved to {json_path}")

    def _writer(self):
        while self._running:
            try:
                row = self._queue.get(timeout=0.5)
                self._write_row(row)
            except Empty:
                continue

    @property
    def dropped_count(self) -> int:
        """Total samples dropped due to queue backpressure this session."""
        return self._dropped

    def _write_row(self, snapshot: dict):
        if not self._csv_writer:
            return
        row = {f: snapshot.get(f, "") for f in self.CSV_FIELDS}
        self._csv_writer.writerow(row)

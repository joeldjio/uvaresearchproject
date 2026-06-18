from __future__ import annotations

import json
import os

import pytest


@pytest.fixture(scope="module")
def qcoreapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def test_run_mission_multi_applies_lane_offsets(qcoreapp, monkeypatch):
    from tools.ui.context.swarm_context import SwarmContext

    ctx = SwarmContext()
    dispatched: list[tuple[str, list[dict]]] = []

    def fake_run(drone_id: str, waypoints_json: str) -> None:
        dispatched.append((drone_id, json.loads(waypoints_json)))

    monkeypatch.setattr(ctx, "runMission", fake_run)

    ids = ["drone1", "drone2", "drone3"]
    wps = [
        {"lat": 47.0, "lon": 8.0, "alt": 10.0},
        {"lat": 47.001, "lon": 8.0, "alt": 10.0},
    ]

    ctx.runMissionMulti(json.dumps(ids), json.dumps(wps))

    assert [did for did, _ in dispatched] == ids
    left = dispatched[0][1]
    center = dispatched[1][1]
    right = dispatched[2][1]
    assert center == wps
    assert left != wps
    assert right != wps
    assert left[0]["lon"] != right[0]["lon"]


def test_run_mission_multi_stops_active_algorithms(qcoreapp, monkeypatch):
    from tools.ui.context.swarm_context import SwarmContext

    ctx = SwarmContext()
    calls: list[str] = []
    monkeypatch.setattr(
        ctx, "runMission", lambda drone_id, waypoints_json: calls.append(drone_id)
    )

    stopped = {"value": False}

    def fake_stop() -> None:
        stopped["value"] = True
        ctx._swarm_algorithms_active = False

    monkeypatch.setattr(ctx, "stopSwarmAlgorithms", fake_stop)
    ctx._swarm_algorithms_active = True
    ctx._boids_enabled = True

    ctx.runMissionMulti(
        json.dumps(["drone1", "drone2"]),
        json.dumps([{"lat": 47.0, "lon": 8.0, "alt": 10.0}]),
    )

    assert stopped["value"] is True
    assert calls == ["drone1", "drone2"]

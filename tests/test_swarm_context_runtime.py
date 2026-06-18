from __future__ import annotations

import os
import threading

import pytest


@pytest.fixture(scope="module")
def qcoreapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def test_remove_drone_clears_runtime_state(qcoreapp):
    from tools.ui.context.swarm_context import SwarmContext

    ctx = SwarmContext()
    ctx._backend.add_drone("drone1", "udp:127.0.0.1:14540")
    ctx._mission_active["drone1"] = threading.Event()
    ctx._mission_threads["drone1"] = threading.Thread(target=lambda: None)
    ctx._formation_launched.add("drone1")
    ctx._formation_cmd_ts["drone1"] = 123.0
    ctx._leader_drone_id = "drone1"

    ctx.removeDrone("drone1")

    assert ctx._backend.get_backend("drone1") is None
    assert "drone1" not in ctx._mission_active
    assert "drone1" not in ctx._mission_threads
    assert "drone1" not in ctx._formation_launched
    assert "drone1" not in ctx._formation_cmd_ts
    assert ctx._leader_drone_id == ""


def test_duplicate_drone_id_is_refused(qcoreapp, monkeypatch):
    from tools.ui.context.swarm_context import SwarmContext

    ctx = SwarmContext()
    first = ctx._backend.add_drone("drone1", "udp:127.0.0.1:14540")
    messages: list[tuple[str, str]] = []
    ctx.logMessage.connect(lambda level, text: messages.append((level, text)))

    def fail_start(self):
        raise AssertionError("duplicate add must not start a connect thread")

    monkeypatch.setattr(threading.Thread, "start", fail_start)

    ctx.addDroneTyped("drone1", "udp:127.0.0.1:14541", "generic")

    assert ctx._backend.get_backend("drone1") is first
    assert any(
        level == "WARN" and "duplicate drone id refused" in text
        for level, text in messages
    )

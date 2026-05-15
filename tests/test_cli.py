"""
Tests for droneresearch.cli.main.

Covers the pure-Python parts of the CLI without actually opening a drone
connection or spawning the UI. We exercise:

  - Argparse: every subcommand parses without error
  - ``_resolve_port`` precedence: --port  >  $DRONE_PORT  >  default
  - The UI subcommand routes to tools.ui.app:run (not the dead
    droneresearch.ui.app path) and surfaces a friendly error on missing deps
"""
from __future__ import annotations

import argparse
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from droneresearch.cli import main as cli_main


# ── _resolve_port precedence ────────────────────────────────────────────────


def test_resolve_port_prefers_explicit_arg(monkeypatch):
    monkeypatch.setenv("DRONE_PORT", "tcp:1.2.3.4:5762")
    args = SimpleNamespace(port="udp:127.0.0.1:14550")
    assert cli_main._resolve_port(args) == "udp:127.0.0.1:14550"


def test_resolve_port_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("DRONE_PORT", "tcp:1.2.3.4:5762")
    args = SimpleNamespace(port=None)
    assert cli_main._resolve_port(args) == "tcp:1.2.3.4:5762"


def test_resolve_port_default_is_5762(monkeypatch):
    monkeypatch.delenv("DRONE_PORT", raising=False)
    args = SimpleNamespace(port=None)
    assert cli_main._resolve_port(args) == "tcp:127.0.0.1:5762"


def test_resolve_port_missing_attr_is_safe(monkeypatch):
    """Subparsers without --port (e.g. legacy ones) must not crash."""
    monkeypatch.delenv("DRONE_PORT", raising=False)
    assert cli_main._resolve_port(SimpleNamespace()) == "tcp:127.0.0.1:5762"


# ── Argparse smoke tests ────────────────────────────────────────────────────


def _build_parser_via_main(argv: list[str]) -> argparse.Namespace:
    """Reuse ``cli_main.main`` to build args but stop before any side effects.

    We can't call ``main()`` directly without it actually trying to open
    a MAVLink connection. Instead we patch the dispatch helpers so the
    parser runs to completion and we capture ``args`` from the closure.
    """
    captured: dict = {}

    def _capture(args):
        captured["args"] = args

    with patch.object(cli_main, "_run_command",    _capture), \
         patch.object(cli_main, "_run_script",     _capture), \
         patch.object(cli_main, "_run_experiment", _capture), \
         patch.object(cli_main, "_launch_ui",      lambda: captured.update(args=SimpleNamespace(command="ui"))), \
         patch.object(sys, "argv", ["droneresearch", *argv]):
        cli_main.main()
    return captured["args"]


@pytest.mark.parametrize("argv, expected_cmd", [
    (["connect", "--port", "tcp:127.0.0.1:5762"],          "connect"),
    (["status"],                                            "status"),
    (["arm", "--force"],                                    "arm"),
    (["disarm"],                                            "disarm"),
    (["takeoff", "--alt", "15"],                            "takeoff"),
    (["land"],                                              "land"),
    (["rtl"],                                               "rtl"),
    (["mode", "LOITER"],                                    "mode"),
    (["goto", "--lat", "47.5", "--lon", "8.5", "--alt", "20"], "goto"),
    (["run", "scripts/hover.py"],                           "run"),
    (["experiment", "run", "exp.yaml"],                     "experiment"),
])
def test_subcommand_parses(argv, expected_cmd):
    args = _build_parser_via_main(argv)
    assert args.command == expected_cmd


def test_connect_port_is_captured():
    args = _build_parser_via_main(["connect", "--port", "udp:127.0.0.1:14550"])
    assert args.port == "udp:127.0.0.1:14550"


def test_takeoff_alt_is_parsed_as_float():
    args = _build_parser_via_main(["takeoff", "--alt", "12.5"])
    assert args.alt == pytest.approx(12.5)


def test_goto_requires_all_three_coords():
    """Missing --alt must cause argparse to exit with code 2."""
    with pytest.raises(SystemExit) as exc_info, \
         patch.object(sys, "argv", ["droneresearch", "goto", "--lat", "1", "--lon", "2"]):
        cli_main.main()
    assert exc_info.value.code == 2


def test_no_subcommand_is_error():
    with pytest.raises(SystemExit), \
         patch.object(sys, "argv", ["droneresearch"]):
        cli_main.main()


# ── UI launcher ─────────────────────────────────────────────────────────────


def test_launch_ui_imports_tools_ui_app(monkeypatch):
    """The launcher must use the real UI path (tools.ui.app), not the
    long-dead droneresearch.ui.app."""
    called = {"n": 0}

    def fake_run() -> int:
        called["n"] += 1
        return 0

    # Inject a fake module so the launcher's `from tools.ui.app import run`
    # finds something importable even on systems without PyQt6 wired up.
    import types
    fake_pkg = types.ModuleType("tools.ui.app")
    fake_pkg.run = fake_run
    monkeypatch.setitem(sys.modules, "tools.ui.app", fake_pkg)

    with pytest.raises(SystemExit) as exc_info:
        cli_main._launch_ui()
    assert exc_info.value.code == 0
    assert called["n"] == 1


def test_launch_ui_reports_helpful_error_when_pyqt_missing(monkeypatch, capsys):
    """If the import fails (PyQt6 not installed), the user must see a
    PyQt6-flavoured hint, not the old PySide6 message."""
    import builtins
    real_import = builtins.__import__

    def boom(name, *a, **kw):
        if name.startswith("tools.ui"):
            raise ImportError("No module named 'PyQt6'")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", boom)
    with pytest.raises(SystemExit) as exc_info:
        cli_main._launch_ui()
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "PyQt6" in err
    assert "PySide6" not in err

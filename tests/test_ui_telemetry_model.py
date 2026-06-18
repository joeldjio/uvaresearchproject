"""
Tests for tools.ui.context.telemetry_context.TelemetryModel.

Covers:
  - row insertion / removal as drones come and go
  - role mapping (snapshot keys → QML role names)
  - differential dataChanged emission
  - snapshotFor() lookup
  - count property + countChanged signal
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QModelIndex, Qt

from tools.ui.context.telemetry_context import TelemetryModel, _ROLES


# ── Helpers ─────────────────────────────────────────────────────────────────


def _role_id(role_name: bytes) -> int:
    """Return the integer role id for a given role-name bytes literal."""
    for rid, name in _ROLES.items():
        if name == role_name:
            return rid
    raise KeyError(role_name)


def _data(model: TelemetryModel, row: int, role_name: bytes):
    return model.data(model.index(row, 0), _role_id(role_name))


# ── rowCount / roleNames ────────────────────────────────────────────────────


def test_empty_model_has_zero_rows(qapp):
    m = TelemetryModel()
    assert m.rowCount() == 0
    assert m.count == 0


def test_role_names_contain_expected_keys(qapp):
    m = TelemetryModel()
    role_bytes = set(m.roleNames().values())
    for expected in (b"droneId", b"lat", b"lon", b"altRel", b"armed",
                     b"flightMode", b"batteryPct", b"heading", b"connected"):
        assert expected in role_bytes


# ── update_all: insertion ───────────────────────────────────────────────────


def test_update_all_inserts_rows_for_new_drones(qapp, snap_factory):
    m = TelemetryModel()
    m.update_all({
        "D1": snap_factory(lat=47.1),
        "D2": snap_factory(lat=47.2),
    })
    assert m.rowCount() == 2
    assert m.count == 2


def test_update_all_sorts_added_ids_deterministically(qapp, snap_factory):
    """Newly added drones go into the model sorted by id (per impl)."""
    m = TelemetryModel()
    m.update_all({"Z": snap_factory(), "A": snap_factory(), "M": snap_factory()})
    ids = [_data(m, r, b"droneId") for r in range(m.rowCount())]
    assert ids == ["A", "M", "Z"]


def test_count_changed_fires_on_insert(qapp, snap_factory):
    m = TelemetryModel()
    fired = []
    m.countChanged.connect(lambda: fired.append(m.count))
    m.update_all({"D1": snap_factory()})
    assert fired == [1]


# ── update_all: role values ─────────────────────────────────────────────────


def test_data_maps_snapshot_keys_to_qml_roles(qapp, snap_factory):
    m = TelemetryModel()
    m.update_all({"D1": snap_factory(
        lat=47.5, lon=8.5, alt_rel=12.3, yaw=270.0,
        armed=True, flight_mode="LOITER", battery_pct=88.0,
        satellites=15, gps_fix=4,
    )})
    assert _data(m, 0, b"droneId")     == "D1"
    assert _data(m, 0, b"lat")         == pytest.approx(47.5)
    assert _data(m, 0, b"lon")         == pytest.approx(8.5)
    assert _data(m, 0, b"altRel")      == pytest.approx(12.3)
    # heading role maps to snap['yaw'] (see _SNAP_MAP)
    assert _data(m, 0, b"heading")     == pytest.approx(270.0)
    assert _data(m, 0, b"armed")       is True
    assert _data(m, 0, b"flightMode")  == "LOITER"
    assert _data(m, 0, b"batteryPct")  == pytest.approx(88.0)
    assert _data(m, 0, b"satellites")  == 15
    assert _data(m, 0, b"gpsFix")      == 4


def test_data_returns_default_when_snapshot_key_missing(qapp):
    """Missing keys must not crash; numeric → 0, flightMode → 'UNKNOWN'."""
    m = TelemetryModel()
    m.update_all({"D1": {}})  # empty snapshot
    assert _data(m, 0, b"lat")        == 0
    assert _data(m, 0, b"flightMode") == "UNKNOWN"


def test_data_invalid_index_returns_none(qapp, snap_factory):
    m = TelemetryModel()
    m.update_all({"D1": snap_factory()})
    # Out-of-range row
    assert m.data(m.index(99, 0), _role_id(b"lat")) is None
    # Default invalid index
    assert m.data(QModelIndex(), _role_id(b"lat")) is None


# ── update_all: removal ─────────────────────────────────────────────────────


def test_update_all_removes_disappearing_drone(qapp, snap_factory):
    m = TelemetryModel()
    m.update_all({"D1": snap_factory(), "D2": snap_factory()})
    assert m.rowCount() == 2

    m.update_all({"D1": snap_factory()})  # D2 vanished
    assert m.rowCount() == 1
    assert _data(m, 0, b"droneId") == "D1"


def test_count_changed_fires_on_remove(qapp, snap_factory):
    m = TelemetryModel()
    m.update_all({"D1": snap_factory(), "D2": snap_factory()})
    fired = []
    m.countChanged.connect(lambda: fired.append(m.count))
    m.update_all({"D1": snap_factory()})
    assert fired == [1]  # one removal


# ── Differential update ─────────────────────────────────────────────────────


def test_data_changed_emits_only_changed_roles(qapp, snap_factory):
    """The model must skip unchanged roles to avoid binding churn."""
    m = TelemetryModel()
    m.update_all({"D1": snap_factory(lat=47.0, lon=8.0, battery_pct=100.0)})

    seen_roles: list = []

    def _on_changed(top_left, bottom_right, roles):
        seen_roles.append(list(roles))

    m.dataChanged.connect(_on_changed)
    # Change only the battery
    m.update_all({"D1": snap_factory(lat=47.0, lon=8.0, battery_pct=80.0)})

    assert len(seen_roles) == 1
    changed = seen_roles[0]
    assert _role_id(b"batteryPct") in changed
    # lat / lon must NOT be in the changed-roles list
    assert _role_id(b"lat") not in changed
    assert _role_id(b"lon") not in changed


def test_data_changed_not_emitted_when_nothing_changed(qapp, snap_factory):
    m = TelemetryModel()
    snap = snap_factory(lat=47.0)
    m.update_all({"D1": snap})

    fired = []
    m.dataChanged.connect(lambda *a: fired.append(a))
    # Identical snapshot
    m.update_all({"D1": snap_factory(lat=47.0)})
    assert fired == []


# ── snapshotFor ─────────────────────────────────────────────────────────────


def test_snapshot_for_returns_stored_dict(qapp, snap_factory):
    m = TelemetryModel()
    snap = snap_factory(lat=47.9, armed=True)
    m.update_all({"D1": snap})
    out = m.snapshotFor("D1")
    assert out["lat"] == pytest.approx(47.9)
    assert out["armed"] is True


def test_snapshot_for_unknown_drone_returns_empty(qapp):
    m = TelemetryModel()
    assert m.snapshotFor("DOES_NOT_EXIST") == {}

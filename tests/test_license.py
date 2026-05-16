"""Regression tests for the offline trial + license-key system."""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

# Make sure license imports work even when PyQt6 isn't on the path
# (LicenseManager test sets QT_QPA_PLATFORM=offscreen below).
from tools.ui import license as lic


# ──────────────────────────────────────────────────────────────────────
#  Pure-function tests (no Qt required)
# ──────────────────────────────────────────────────────────────────────
def test_generate_and_validate_roundtrip():
    exp = date(2027, 1, 31)
    key = lic.generate_key(exp)
    assert key.startswith("RZGCS-")
    assert key.endswith("20270131")
    assert lic.validate_key(key) == exp


def test_validate_rejects_tampered_hash():
    key = lic.generate_key(date(2027, 1, 31))
    # Flip one character in the hash section.
    bad = key[:-9] + "X" + key[-8:]
    assert lic.validate_key(bad) is None


def test_validate_rejects_tampered_expiry():
    key = lic.generate_key(date(2027, 1, 31))
    # Change the date but keep the hash.
    bad = key[:-8] + "21001231"
    assert lic.validate_key(bad) is None


@pytest.mark.parametrize("garbage", [
    "",
    "not a key",
    "RZGCS-AAAA-BBBB-CCCC",                  # missing date
    "OTHER-Q3D7-ZKN5-FHFT-20270516",         # wrong prefix
    "RZGCS-Q3D7-ZKN5-FHFT-2027ABCD",         # non-numeric date
    "RZGCS-Q3D7-ZKN5-FHFT-20279999",         # invalid calendar date
])
def test_validate_rejects_garbage(garbage):
    assert lic.validate_key(garbage) is None


def test_case_insensitive():
    key = lic.generate_key(date(2027, 1, 31))
    assert lic.validate_key(key.lower()) == date(2027, 1, 31)


# ──────────────────────────────────────────────────────────────────────
#  LicenseManager state machine (needs offscreen Qt)
# ──────────────────────────────────────────────────────────────────────
@pytest.fixture
def manager(tmp_path, monkeypatch):
    """Yield a fresh LicenseManager with isolated storage."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtCore import QCoreApplication, QStandardPaths
    if QCoreApplication.instance() is None:
        QCoreApplication([])  # singleton, kept by Qt
    monkeypatch.setattr(
        QStandardPaths, "writableLocation",
        staticmethod(lambda _loc: str(tmp_path)),
    )
    from tools.ui.license import LicenseManager
    yield LicenseManager()


def test_first_launch_is_trial(manager):
    assert manager.state == "trial"
    assert manager.daysLeft > 0
    assert manager.expiryDate == ""


def test_trial_expires_after_window(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtCore import QCoreApplication, QStandardPaths
    if QCoreApplication.instance() is None:
        QCoreApplication([])
    monkeypatch.setattr(
        QStandardPaths, "writableLocation",
        staticmethod(lambda _loc: str(tmp_path)),
    )

    # Stamp an install time 100 days ago.
    state_path = Path(tmp_path) / "license.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    past = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
    state_path.write_text(json.dumps({"installed_at": past, "key": ""}))

    from tools.ui.license import LicenseManager
    m = LicenseManager()
    assert m.state == "expired"
    assert m.daysLeft == 0


def test_activate_valid_key_unlocks(manager):
    key = lic.generate_key(date.today() + timedelta(days=180))
    assert manager.activate(key) is True
    assert manager.state == "licensed"
    assert manager.daysLeft >= 179
    assert manager.expiryDate != ""


def test_activate_invalid_key_rejected(manager):
    assert manager.activate("RZGCS-AAAA-BBBB-CCCC-20270101") is False
    assert manager.state == "trial"
    assert manager.lastError != ""


def test_activate_expired_key_rejected(manager):
    yesterday = date.today() - timedelta(days=1)
    key = lic.generate_key(yesterday)
    assert manager.activate(key) is False
    assert manager.state in ("trial", "expired")
    assert "abgelaufen" in manager.lastError.lower()


def test_state_persists_across_instances(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtCore import QCoreApplication, QStandardPaths
    if QCoreApplication.instance() is None:
        QCoreApplication([])
    monkeypatch.setattr(
        QStandardPaths, "writableLocation",
        staticmethod(lambda _loc: str(tmp_path)),
    )
    from tools.ui.license import LicenseManager

    key = lic.generate_key(date.today() + timedelta(days=365))
    m1 = LicenseManager()
    assert m1.activate(key) is True
    assert m1.state == "licensed"

    m2 = LicenseManager()  # second launch
    assert m2.state == "licensed"
    assert m2.daysLeft >= 364

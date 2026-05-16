"""
RZ GCS — offline trial + license-key system.

Concept
-------
* On first launch the app stamps an install timestamp into
  ``%LOCALAPPDATA%\\RZ Solutions\\RZ GCS\\license.json``.
* For ``TRIAL_DAYS`` days the app is fully unlocked (state = "trial").
* After that the app still starts but ``LicenseManager.state`` flips
  to "expired" — QML covers the entire window with ``LicenseOverlay``
  which blocks all interaction until a valid key is entered.
* A valid key flips state to "licensed" and the overlay disappears.

Key format
----------
``RZGCS-XXXX-XXXX-XXXX-YYYYMMDD``

* ``YYYYMMDD`` = expiry date (inclusive).
* ``XXXXXXXXXXXX`` = first 12 chars of
  ``base32(HMAC-SHA256(LICENSE_SECRET, "v1|YYYYMMDD"))``.

The key is verified entirely **offline** — no internet, no server.

Security note
-------------
The HMAC secret is embedded in the shipped binary. A determined
reverse-engineer can extract it and mint their own keys. This is
deliberate ("casual protection" to match the rest of the bundle —
see ``tools/installer/README.md``). For stronger protection a
server-side activation API would be required.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import (
    QObject, QStandardPaths, pyqtProperty, pyqtSignal, pyqtSlot,
)

from tools.ui._version import LICENSE_CONTACT, LICENSE_SECRET, TRIAL_DAYS


KEY_PREFIX = "RZGCS"


# ──────────────────────────────────────────────────────────────────────
#  Pure functions — also used by tools/installer/gen_license.py
# ──────────────────────────────────────────────────────────────────────
def _hash(expiry_yyyymmdd: str) -> str:
    """First 12 chars of base32(HMAC-SHA256(SECRET, "v1|<expiry>"))."""
    sig = hmac.new(
        LICENSE_SECRET.encode("utf-8"),
        f"v1|{expiry_yyyymmdd}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b32encode(sig).decode("ascii").rstrip("=")[:12]


def generate_key(expiry: date) -> str:
    """Mint a license key valid through (and including) ``expiry``."""
    exp = expiry.strftime("%Y%m%d")
    h = _hash(exp)
    return f"{KEY_PREFIX}-{h[0:4]}-{h[4:8]}-{h[8:12]}-{exp}"


def validate_key(key: str) -> Optional[date]:
    """
    Verify ``key`` signature and return its expiry date, or ``None``
    if the key is malformed / has been tampered with.

    The caller is responsible for comparing the returned date against
    ``date.today()`` to decide "valid right now" vs "valid but expired".
    """
    parts = key.strip().upper().split("-")
    if len(parts) != 5 or parts[0] != KEY_PREFIX:
        return None
    exp = parts[4]
    if len(exp) != 8 or not exp.isdigit():
        return None
    expected = _hash(exp)
    actual = (parts[1] + parts[2] + parts[3])[:12]
    if not hmac.compare_digest(expected, actual):
        return None
    try:
        return datetime.strptime(exp, "%Y%m%d").date()
    except ValueError:
        return None


# ──────────────────────────────────────────────────────────────────────
#  Qt-facing manager
# ──────────────────────────────────────────────────────────────────────
class LicenseManager(QObject):
    """
    QObject exposed to QML as ``licenseManager``.

    Properties
    ----------
    state          str   — "trial" / "expired" / "licensed"
    daysLeft       int   — trial days remaining, OR days until key expiry
    expiryDate     str   — ISO date of the active license (empty in trial)
    lastError      str   — set by ``activate()`` when a key is rejected
    contactInfo    str   — vendor contact shown by the overlay
    trialDays      int   — configured trial length (for UI)

    Slots
    -----
    activate(key)  bool  — try to install a key; returns success
    deactivate()         — wipe stored key (for testing only)
    """

    stateChanged      = pyqtSignal()
    daysLeftChanged   = pyqtSignal()
    expiryDateChanged = pyqtSignal()
    lastErrorChanged  = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._state:        str  = "trial"
        self._days_left:    int  = 0
        self._expiry_date:  str  = ""
        self._last_error:   str  = ""
        self._installed_at: Optional[datetime] = None
        self._stored_key:   str  = ""

        self._path = self._license_path()
        self._load()
        self._evaluate()

    # ── Filesystem ───────────────────────────────────────────────────
    def _license_path(self) -> Path:
        base = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation
        )
        path = Path(base) if base else Path.home() / ".rz_gcs"
        path.mkdir(parents=True, exist_ok=True)
        return path / "license.json"

    def _load(self) -> None:
        if not self._path.exists():
            self._installed_at = datetime.now(timezone.utc)
            self._save()
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            ts = data.get("installed_at")
            if ts:
                self._installed_at = datetime.fromisoformat(ts)
            else:
                self._installed_at = datetime.now(timezone.utc)
            self._stored_key = data.get("key", "")
        except Exception:
            self._installed_at = datetime.now(timezone.utc)
            self._stored_key = ""
            self._save()

    def _save(self) -> None:
        try:
            self._path.write_text(
                json.dumps(
                    {
                        "installed_at": (self._installed_at or datetime.now(timezone.utc)).isoformat(),
                        "key": self._stored_key,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except OSError:
            # Best-effort. Don't crash the app for a read-only disk.
            pass

    # ── State machine ────────────────────────────────────────────────
    def _evaluate(self) -> None:
        # 1. Stored key wins if still valid.
        if self._stored_key:
            exp = validate_key(self._stored_key)
            if exp is not None and exp >= date.today():
                self._update(
                    state="licensed",
                    days_left=(exp - date.today()).days,
                    expiry=exp.isoformat(),
                )
                return

        # 2. Otherwise fall back to the trial window.
        if self._installed_at:
            elapsed = (datetime.now(timezone.utc) - self._installed_at).days
            days_left = max(0, TRIAL_DAYS - elapsed)
        else:
            days_left = 0

        if days_left > 0:
            self._update(state="trial", days_left=days_left, expiry="")
        else:
            self._update(state="expired", days_left=0, expiry="")

    def _update(self, state: str, days_left: int, expiry: str) -> None:
        if state != self._state:
            self._state = state
            self.stateChanged.emit()
        if days_left != self._days_left:
            self._days_left = days_left
            self.daysLeftChanged.emit()
        if expiry != self._expiry_date:
            self._expiry_date = expiry
            self.expiryDateChanged.emit()

    # ── Properties ───────────────────────────────────────────────────
    @pyqtProperty(str, notify=stateChanged)
    def state(self) -> str:
        return self._state

    @pyqtProperty(int, notify=daysLeftChanged)
    def daysLeft(self) -> int:
        return self._days_left

    @pyqtProperty(str, notify=expiryDateChanged)
    def expiryDate(self) -> str:
        return self._expiry_date

    @pyqtProperty(str, notify=lastErrorChanged)
    def lastError(self) -> str:
        return self._last_error

    @pyqtProperty(str, constant=True)
    def contactInfo(self) -> str:
        return LICENSE_CONTACT

    @pyqtProperty(int, constant=True)
    def trialDays(self) -> int:
        return TRIAL_DAYS

    # ── Slots ────────────────────────────────────────────────────────
    @pyqtSlot(str, result=bool)
    def activate(self, key: str) -> bool:
        exp = validate_key(key)
        if exp is None:
            self._last_error = "Ungültiger Schlüssel. Format: RZGCS-XXXX-XXXX-XXXX-YYYYMMDD"
            self.lastErrorChanged.emit()
            return False
        if exp < date.today():
            self._last_error = f"Schlüssel abgelaufen am {exp.isoformat()}."
            self.lastErrorChanged.emit()
            return False
        self._stored_key = key.strip().upper()
        self._last_error = ""
        self.lastErrorChanged.emit()
        self._save()
        self._evaluate()
        return self._state == "licensed"

    @pyqtSlot()
    def deactivate(self) -> None:
        """Testing helper: clear stored key and reset trial baseline."""
        self._stored_key = ""
        self._installed_at = datetime.now(timezone.utc)
        self._save()
        self._evaluate()

"""
uavresearch gcs — In-app update checker.

What this gives the user
------------------------
* "Check for Updates" button in the Help panel.
* Optional silent check on startup (off by default; user opts in once).
* If a newer release exists on GitHub, a non-blocking banner appears
  with the new version + release notes excerpt + "Download & Install"
  action.
* "Download & Install" fetches the matching ``uavresearch-gcs-setup-x.y.z.exe``
  asset to ``%TEMP%`` and launches it with Inno-Setup's silent-upgrade
  flags. The current process exits cleanly so the installer can replace
  ``_internal/`` files.

What this does NOT do
---------------------
* No auto-applying updates without user consent.
* No download of arbitrary code from anywhere else than the configured
  GitHub repo (see ``_version.py:GITHUB_REPO``).
* No telemetry / analytics. The only network request is a GET to the
  GitHub Releases API.

All network I/O happens on a worker QThread so the UI never blocks.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from PySide6.QtCore import (
    QObject,
    QThread,
    QTimer,
    Property,
    Signal,
    Slot,
)
from PySide6.QtWidgets import QApplication

from tools.ui._version import GITHUB_REPO, INSTALLER_ASSET_PREFIX, VERSION

RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE_URL = f"https://github.com/{GITHUB_REPO}/releases"

# Windows CreateProcess flag: detached process — child survives parent exit.
_DETACHED_PROCESS = 0x00000008


def _parse_semver(s: str) -> tuple[int, ...]:
    """Lenient 'x.y.z' tuple. Returns (0,) on garbage so it loses any compare."""
    cleaned = s.lstrip("v").split("-", 1)[0].split("+", 1)[0]
    parts: list[int] = []
    for chunk in cleaned.split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            return (0,)
    return tuple(parts) if parts else (0,)


def _is_newer(remote: str, local: str) -> bool:
    return _parse_semver(remote) > _parse_semver(local)


# ──────────────────────────────────────────────────────────────────────
# Worker objects — run on a QThread, NEVER touch UI directly.
# ──────────────────────────────────────────────────────────────────────
class _CheckWorker(QObject):
    found = Signal(str, str, str, str)  # version, asset_url, notes, sha256_url
    uptodate = Signal()
    failed = Signal(str)
    finished = Signal()

    @Slot()
    def run(self) -> None:
        try:
            req = urllib.request.Request(
                RELEASES_API_URL,
                headers={
                    "User-Agent": f"uavresearch-gcs-Updater/{VERSION}",
                    "Accept": "application/vnd.github+json",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            self.failed.emit(f"GitHub returned HTTP {exc.code}.")
            self.finished.emit()
            return
        except Exception as exc:  # network down, DNS, JSON, …
            self.failed.emit(f"Could not reach GitHub: {exc}")
            self.finished.emit()
            return

        latest_tag = str(payload.get("tag_name") or "").strip()
        notes = str(payload.get("body") or "").strip()
        assets = payload.get("assets") or []

        asset_url: Optional[str] = None
        sha256_url: Optional[str] = None
        for a in assets:
            name = str(a.get("name") or "")
            if name.startswith(INSTALLER_ASSET_PREFIX) and name.lower().endswith(
                ".exe"
            ):
                asset_url = a.get("browser_download_url")
            elif name.endswith(".sha256") and INSTALLER_ASSET_PREFIX in name:
                sha256_url = a.get("browser_download_url")

        if not latest_tag:
            self.failed.emit("Latest release has no tag.")
        elif not _is_newer(latest_tag, VERSION):
            self.uptodate.emit()
        elif asset_url is None:
            self.failed.emit(
                f"Release {latest_tag} has no '{INSTALLER_ASSET_PREFIX}*.exe' asset."
            )
        else:
            self.found.emit(latest_tag.lstrip("v"), asset_url, notes, sha256_url or "")

        self.finished.emit()


class _DownloadWorker(QObject):
    progress = Signal(int)  # 0..100
    completed = Signal(str)  # local path
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self, url: str, sha256_url: str = "", parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)
        self._url = url
        self._sha256_url = sha256_url

    @Slot()
    def run(self) -> None:
        try:
            target = Path(tempfile.gettempdir()) / Path(self._url).name
            req = urllib.request.Request(
                self._url,
                headers={"User-Agent": f"uavresearch-gcs-Updater/{VERSION}"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = int(resp.headers.get("Content-Length") or 0)
                done = 0
                with open(target, "wb") as fh:
                    last_pct = -1
                    while True:
                        chunk = resp.read(64 * 1024)
                        if not chunk:
                            break
                        fh.write(chunk)
                        done += len(chunk)
                        if total > 0:
                            pct = int(done * 100 / total)
                            if pct != last_pct:
                                self.progress.emit(pct)
                                last_pct = pct
            self.progress.emit(100)

            # Verify SHA256 checksum if a .sha256 asset was provided.
            if self._sha256_url:
                try:
                    sha_req = urllib.request.Request(
                        self._sha256_url,
                        headers={"User-Agent": f"uavresearch-gcs-Updater/{VERSION}"},
                    )
                    with urllib.request.urlopen(sha_req, timeout=10) as sha_resp:
                        expected = sha_resp.read().decode("utf-8")
                    if not self._verify_sha256(str(target), expected):
                        target.unlink(missing_ok=True)
                        self.failed.emit(
                            "SHA256 checksum mismatch — download may be corrupt."
                        )
                        return
                except Exception as exc:
                    self.failed.emit(f"SHA256 verification failed: {exc}")
                    return

            self.completed.emit(str(target))
        except Exception as exc:
            self.failed.emit(f"Download failed: {exc}")
        finally:
            self.finished.emit()

    def _verify_sha256(self, file_path: str, expected_sha256: str) -> bool:
        import hashlib

        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        actual = sha.hexdigest().lower()
        expected = expected_sha256.strip().lower().split()[0]  # "abc123  filename.exe"
        return actual == expected


# ──────────────────────────────────────────────────────────────────────
# Public facade — register this in the ServiceLocator as ``updater``.
# ──────────────────────────────────────────────────────────────────────
class UpdaterContext(QObject):
    """
    QObject exposed to QML as ``updater``.

    Properties (QML bindings)
    -------------------------
    * ``currentVersion``    str   — what is running right now.
    * ``state``             str   — one of:
        ``"idle"``, ``"checking"``, ``"available"``, ``"uptodate"``,
        ``"error"``, ``"downloading"``, ``"ready"``.
    * ``latestVersion``     str   — populated when state == ``available``.
    * ``releaseNotes``      str   — populated when state == ``available``.
    * ``progress``          int   — 0..100 when downloading.
    * ``errorMessage``      str   — populated when state == ``error``.

    Methods (callable from QML)
    ---------------------------
    * ``check()``                  — kick off an async update check.
    * ``downloadAndInstall()``     — fetch the installer and launch it.
    * ``openReleasesPage()``       — open the GitHub releases page in
                                     the default browser as a fallback.
    """

    stateChanged = Signal()
    latestVersionChanged = Signal()
    releaseNotesChanged = Signal()
    progressChanged = Signal()
    errorMessageChanged = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._state = "idle"
        self._latest_version = ""
        self._asset_url = ""
        self._sha256_url = ""
        self._release_notes = ""
        self._error_message = ""
        self._progress = 0

        # Keep references so QThread isn't garbage-collected mid-run.
        self._check_thread: Optional[QThread] = None
        self._check_worker: Optional[_CheckWorker] = None
        self._download_thread: Optional[QThread] = None
        self._download_worker: Optional[_DownloadWorker] = None

    # ── QML-facing properties ────────────────────────────────────────
    @Property(str, constant=True)
    def currentVersion(self) -> str:
        return VERSION

    @Property(str, notify=stateChanged)
    def state(self) -> str:
        return self._state

    @Property(str, notify=latestVersionChanged)
    def latestVersion(self) -> str:
        return self._latest_version

    @Property(str, notify=releaseNotesChanged)
    def releaseNotes(self) -> str:
        return self._release_notes

    @Property(int, notify=progressChanged)
    def progress(self) -> int:
        return self._progress

    @Property(str, notify=errorMessageChanged)
    def errorMessage(self) -> str:
        return self._error_message

    # ── State helpers ────────────────────────────────────────────────
    def _set_state(self, new: str) -> None:
        if new != self._state:
            self._state = new
            self.stateChanged.emit()

    # ── Slots callable from QML ──────────────────────────────────────
    @Slot()
    def check(self) -> None:
        if self._state == "checking":
            return  # already running
        self._error_message = ""
        self.errorMessageChanged.emit()
        self._set_state("checking")

        self._check_thread = QThread(self)
        self._check_worker = _CheckWorker()
        self._check_worker.moveToThread(self._check_thread)
        self._check_thread.started.connect(self._check_worker.run)
        self._check_worker.found.connect(self._on_check_found)
        self._check_worker.uptodate.connect(self._on_check_uptodate)
        self._check_worker.failed.connect(self._on_check_failed)
        self._check_worker.finished.connect(self._check_thread.quit)
        self._check_thread.finished.connect(self._check_thread.deleteLater)
        self._check_thread.start()

    @Slot()
    def downloadAndInstall(self) -> None:
        if self._state != "available" or not self._asset_url:
            return
        self._progress = 0
        self.progressChanged.emit()
        self._set_state("downloading")

        self._download_thread = QThread(self)
        self._download_worker = _DownloadWorker(self._asset_url, self._sha256_url)
        self._download_worker.moveToThread(self._download_thread)
        self._download_thread.started.connect(self._download_worker.run)
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.completed.connect(self._on_download_completed)
        self._download_worker.failed.connect(self._on_download_failed)
        self._download_worker.finished.connect(self._download_thread.quit)
        self._download_thread.finished.connect(self._download_thread.deleteLater)
        self._download_thread.start()

    @Slot()
    def openReleasesPage(self) -> None:
        import webbrowser

        webbrowser.open(RELEASES_PAGE_URL)

    # ── Worker callbacks ─────────────────────────────────────────────
    @Slot(str, str, str, str)
    def _on_check_found(
        self, version: str, url: str, notes: str, sha256_url: str = ""
    ) -> None:
        self._latest_version = version
        self._asset_url = url
        self._sha256_url = sha256_url
        # Trim very long release notes for the UI; full text on GitHub.
        self._release_notes = notes[:1000] + ("\u2026" if len(notes) > 1000 else "")
        self.latestVersionChanged.emit()
        self.releaseNotesChanged.emit()
        self._set_state("available")

    @Slot()
    def _on_check_uptodate(self) -> None:
        self._set_state("uptodate")

    @Slot(str)
    def _on_check_failed(self, msg: str) -> None:
        self._error_message = msg
        self.errorMessageChanged.emit()
        self._set_state("error")

    @Slot(int)
    def _on_download_progress(self, pct: int) -> None:
        self._progress = pct
        self.progressChanged.emit()

    @Slot(str)
    def _on_download_completed(self, path: str) -> None:
        self._set_state("ready")
        self._launch_installer(path)

    @Slot(str)
    def _on_download_failed(self, msg: str) -> None:
        self._error_message = msg
        self.errorMessageChanged.emit()
        self._set_state("error")

    # ── Installer launch ─────────────────────────────────────────────
    def _launch_installer(self, installer_path: str) -> None:
        """
        Launch the freshly downloaded installer with Inno Setup's
        upgrade flags, then quit this app so the installer can replace
        in-use files in ``_internal/``.

        Flags:
          /SILENT              minimal UI, still shows progress
          /CLOSEAPPLICATIONS   gracefully ask the running app to exit
          /RESTARTAPPLICATIONS relaunch after upgrade
          /NORESTART           never reboot Windows even if needed
        """
        if not os.path.isfile(installer_path):
            self._error_message = f"Installer not found at {installer_path}"
            self.errorMessageChanged.emit()
            self._set_state("error")
            return

        try:
            subprocess.Popen(
                [
                    installer_path,
                    "/SILENT",
                    "/CLOSEAPPLICATIONS",
                    "/RESTARTAPPLICATIONS",
                    "/NORESTART",
                ],
                creationflags=_DETACHED_PROCESS if sys.platform == "win32" else 0,
                close_fds=True,
            )
        except OSError as exc:
            self._error_message = f"Could not launch installer: {exc}"
            self.errorMessageChanged.emit()
            self._set_state("error")
            return

        # Give the installer a moment to start before this process exits.
        QTimer.singleShot(800, QApplication.quit)

"""
Single source of truth for the RZ GCS application version.

Read at runtime by:
  - tools.ui.app           (QApplication.setApplicationVersion)
  - tools.ui.updater       (compare against GitHub Releases API)

Read at build time by:
  - tools/installer/inno/rz_gcs.iss (#define AppVersion)
  - tools/installer/build.ps1       (output filename)

Update procedure
----------------
1. Bump VERSION here.
2. Update tools/installer/inno/rz_gcs.iss line ``#define AppVersion``.
3. Tag the release: ``git tag v0.3.0 && git push --tags``.
4. Run ``tools\installer\build.ps1``.
5. Upload the produced installer to the GitHub release as an asset
   whose name starts with ``RZ-GCS-Setup-`` and ends with ``.exe``.
   (The updater downloads any asset matching that pattern.)
"""
from __future__ import annotations

VERSION: str = "0.3.0"

# Asset-name prefix the in-app updater looks for when scanning a
# GitHub release. Must match ``OutputBaseFilename`` in the .iss file.
INSTALLER_ASSET_PREFIX: str = "RZ-GCS-Setup-"

# GitHub repo (owner/name) the updater queries.
GITHUB_REPO: str = "joeldjio/rz-gcs-releases"

# ─────────────────────────────────────────────────────────────────────
#  Licensing — used by tools/ui/license.py
# ─────────────────────────────────────────────────────────────────────
# Free-trial duration starting at first launch, in days.
TRIAL_DAYS: int = 30

# HMAC-SHA256 secret used to sign license keys. ROTATE this string
# before shipping to customers; anyone with both the secret and the
# key-generation tool can mint valid keys. Keep it private (don't
# commit a real production secret to the public repo).
#
# A key minted with one secret is NOT accepted by builds carrying a
# different secret, which lets you "revoke" all keys by rotating the
# secret + shipping a new installer.
LICENSE_SECRET: str = "rz-solutions-dev-secret-CHANGE-ME-before-shipping"

# Vendor contact shown in the activation overlay.
LICENSE_CONTACT: str = "djiojoel2@gmail.com"

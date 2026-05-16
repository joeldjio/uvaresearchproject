# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — RZ GCS (RZ Solutions ground control station).

Full graphical build: PyQt6 + QtQuick + QtWebEngine + pyqtgraph +
the entire QML tree under tools/ui/qml/ (including 3D mesh assets).

Build with:
    pyinstaller tools/installer/specs/rz_gcs.spec --noconfirm
Output:
    dist/RZGCS/RZ GCS.exe   (+ _internal/ folder)

Notes
-----
- One-folder mode is intentional: one-file would re-extract ~280 MB
  to %TEMP% on every launch (slow and flaky on locked-down machines).
- console=False → no flickering cmd.exe window when launching from
  the Start Menu shortcut.
- QML files are bundled under ``tools/ui/qml/`` to mirror the source
  layout; ``tools/ui/app.py:_resolve_qml_root()`` understands both
  frozen and source layouts.
- ``optimize=2`` strips ``assert`` statements and ``__doc__`` strings
  from all bundled .pyc files. Casual code-protection only; bytecode
  can still be decompiled with public tools.
"""
import os
import sys
from pathlib import Path

# Apply the Python 3.10.0-3.10.3 dis._get_const_info workaround
# (bpo-45757) before PyInstaller starts scanning bytecode.
sys.path.insert(0, str(Path(SPECPATH).resolve()))
import _dis_patch  # noqa: F401

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

PROJECT_ROOT = Path(SPECPATH).resolve().parent.parent.parent
ASSETS_DIR   = PROJECT_ROOT / "tools" / "installer" / "assets"
QML_ROOT     = PROJECT_ROOT / "tools" / "ui" / "qml"

block_cipher = None


# ── Data: QML + 3D assets ────────────────────────────────────────────
def _collect_qml() -> list[tuple[str, str]]:
    """Mirror tools/ui/qml/** into the bundle, preserving directory layout."""
    out: list[tuple[str, str]] = []
    for path in QML_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix == ".bak":
            continue
        rel_dir = path.parent.relative_to(PROJECT_ROOT)
        out.append((str(path), str(rel_dir).replace(os.sep, "/")))
    return out


qml_datas = _collect_qml()
print(f"[gcs.spec] bundling {len(qml_datas)} QML / asset files")


# ── Hidden imports ───────────────────────────────────────────────────
hidden = (
    collect_submodules("droneresearch")
    + collect_submodules("tools.ui")
    + collect_submodules("pymavlink")
    + [
        "serial", "serial.tools.list_ports",
        "pyqtgraph",
        # WebEngine bits PyInstaller occasionally misses
        "PyQt6.QtWebEngineCore",
        "PyQt6.QtWebEngineQuick",
        "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtQuick3D",
        "PyQt6.QtPositioning",
        "PyQt6.QtLocation",
    ]
)


a = Analysis(
    [str(PROJECT_ROOT / "tools" / "ui" / "__main__.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=qml_datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyQt5", "PySide6", "PySide2",
        "tkinter", "matplotlib", "scipy", "pandas", "IPython",
        "test", "unittest",
        # See droneresearch_cli.spec for the rationale.
        "lxml", "cv2", "google", "grpc", "cryptography",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=2,                  # -OO: strip asserts + docstrings
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RZ GCS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,               # GUI app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ASSETS_DIR / "rz_icon.ico"),
    version=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="RZGCS",
)

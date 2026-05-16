# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — DroneResearch CLI (droneresearch.exe).

Headless build: SDK + CLI + safety + experiment runner. PyQt6 and
QtWebEngine are explicitly excluded so the bundle stays small (~40 MB
instead of ~280 MB).

Build with:
    pyinstaller tools/installer/specs/droneresearch_cli.spec --noconfirm
Output:
    dist/DroneResearchCLI/droneresearch.exe   (+ _internal/ folder)
"""
import sys
from pathlib import Path

# Apply the Python 3.10.0-3.10.3 dis._get_const_info workaround
# (bpo-45757) before PyInstaller starts scanning bytecode.
sys.path.insert(0, str(Path(SPECPATH).resolve()))
import _dis_patch  # noqa: F401

from PyInstaller.utils.hooks import collect_submodules

PROJECT_ROOT = Path(SPECPATH).resolve().parent.parent.parent
ASSETS_DIR   = PROJECT_ROOT / "tools" / "installer" / "assets"

block_cipher = None


a = Analysis(
    [str(PROJECT_ROOT / "droneresearch" / "cli" / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=(
        collect_submodules("droneresearch")
        + collect_submodules("pymavlink")
        + ["serial", "serial.tools.list_ports"]
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Hard-exclude UI / heavy stacks: this is the headless build.
        "PyQt6", "PyQt5", "PySide6", "PySide2",
        "tools.ui",
        "matplotlib", "scipy", "pandas", "IPython",
        "tkinter", "test", "unittest",
        # lxml's isoschematron has bytecode that confuses Python 3.10's
        # ``dis`` module (PyInstaller issue #7689). The CLI does not
        # need any XML schema processing.
        "lxml",
        # Optional heavy deps pulled in transitively by some pymavlink
        # extras / google api libs that we do not use in the CLI.
        "cv2", "google", "grpc", "cryptography",
        # pkg_resources / setuptools are not used at runtime by the
        # droneresearch package and pull in optional ``appdirs`` /
        # ``jaraco`` deps that may not be installed.
        "pkg_resources", "setuptools._vendor",
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
    name="droneresearch",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,                # CLI = console window stays
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
    name="DroneResearchCLI",
)

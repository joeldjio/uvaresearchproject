# Windows Installer Build Pipeline

End-to-end build of two self-contained Windows installers:

| Installer | What it bundles | Approx. size |
|---|---|---|
| `DroneResearch-CLI-Setup-X.Y.Z.exe` | `droneresearch.exe` + SDK + safety + experiment runner. Headless, no PyQt6. | ~40 MB |
| `DroneResearch-GCS-Setup-X.Y.Z.exe` | `DroneResearch.exe` (QML dashboard) + everything from CLI + PyQt6 + WebEngine + pyqtgraph + 3D mesh assets. | ~280 MB |

Both installers ship **all** runtime dependencies — end users do **not** need a separate Python install.

---

## Layout

```
tools/installer/
├── README.md                       ← this file
├── build.ps1                       ← orchestrator (run this)
├── requirements_build.txt          ← build-time deps (PyInstaller, Pillow, …)
│
├── icon/
│   └── make_assets.py              ← generates the RZ branding assets
│
├── assets/                         ← (generated, gitignored)
│   ├── rz_icon.ico                    multi-res Windows icon
│   ├── rz_logo_256.png                preview / debugging
│   ├── wizard_large.bmp               164×314 Inno wizard image
│   └── wizard_small.bmp               55×55 Inno wizard image
│
├── specs/
│   ├── droneresearch_cli.spec      ← PyInstaller spec — CLI
│   └── droneresearch_gcs.spec      ← PyInstaller spec — GCS
│
├── inno/
│   ├── droneresearch_cli.iss       ← Inno Setup script — CLI
│   └── droneresearch_gcs.iss       ← Inno Setup script — GCS
│
└── out/                            ← (generated, gitignored)
    ├── DroneResearch-CLI-Setup-0.2.0.exe
    └── DroneResearch-GCS-Setup-0.2.0.exe
```

---

## Prerequisites (one-time)

1. **Python 3.10+** on PATH.
2. **Inno Setup 6** (free, MIT/Mozilla-style licence): https://jrsoftware.org/isinfo.php  
   Default install path is `C:\Program Files (x86)\Inno Setup 6\`. The build script picks `ISCC.exe` from there automatically; override with `-InnoCompiler <path>` if needed.
3. **Build-time Python deps:**
   ```powershell
   pip install -r tools\installer\requirements_build.txt
   ```

---

## One-shot build

From the repository root:

```powershell
.\tools\installer\build.ps1
```

This will:

1. Regenerate `assets/rz_icon.ico`, the wizard BMPs, and the preview PNG.
2. Run PyInstaller for the CLI bundle  → `dist\DroneResearchCLI\`.
3. Run PyInstaller for the GCS bundle  → `dist\DroneResearchGCS\`.
4. Compile both Inno Setup scripts     → `tools\installer\out\*.exe`.

Typical full build: 4–8 minutes on a modern desktop, dominated by the GCS bundle compression (LZMA2 ultra64).

### Targeted builds

```powershell
# Only the CLI installer
.\tools\installer\build.ps1 -Target cli

# Only the GCS installer
.\tools\installer\build.ps1 -Target gcs

# Re-compile installers without re-running PyInstaller
# (useful when you only changed the .iss script or branding)
.\tools\installer\build.ps1 -SkipBundle
```

---

## What the installers do

### Modern wizard UX

Both installers use Inno Setup's `WizardStyle=modern` with custom RZ branding:

- Welcome page with the 164×314 RZ wizard image on the left
- License agreement (`LICENSE` from the repo root)
- Optional installation directory selection
- Component / task selection (see below)
- Progress page with LZMA2-decompressed file installation
- Finish page with optional "launch now" checkbox

### Per-installer tasks

**CLI installer:**
- ✅ Add `droneresearch.exe` to user `%PATH%` (default: on)
- ⬜ Create a desktop shortcut that opens `cmd.exe /K droneresearch --help` (default: off)
- Start-menu group `DroneResearch` with `DroneResearch CLI` and `Uninstall`

**GCS installer:**
- ✅ Desktop shortcut (default: on)
- ⬜ Quick Launch shortcut (default: off)
- ⬜ Associate `.drscenario` files with the GCS (default: off)
- Start-menu group with `DroneResearch GCS`, `… (Legacy Widget UI)`, `Documentation`, `Uninstall`

### No admin required

Both installers default to `PrivilegesRequired=lowest` (per-user install under `%LOCALAPPDATA%\Programs\…`). Users can opt up to a system-wide install through Inno's standard UAC prompt.

### Clean uninstall

Each installer registers a proper uninstaller in *Apps & features* / *Programs and Features*. Uninstalling removes everything under `{app}\` (including the PyInstaller `_internal\` extraction directory) and any `%PATH%` / file-association registry entries it added.

---

## Branding

The RZ logo is **generated**, not committed:

- `tools/installer/icon/make_assets.py` draws a rounded square with a vertical blue gradient (`#2563eb → #1d4ed8`, matches the QML `Theme.qml` accent colour) and bold white "RZ" centred on top.
- 7 ICO resolutions (16, 24, 32, 48, 64, 128, 256) are stored in a single `rz_icon.ico` so Windows picks the best size for taskbar / Start menu / file-explorer / alt-tab automatically.
- Wizard images are exported as 24-bit BMP (Inno requirement; PNG is not supported on the wizard pages).

To customise: edit `make_assets.py` and re-run the build. Both `.iss` scripts pick the regenerated assets up automatically.

---

## Troubleshooting

**`pyinstaller : term not recognized`**  
Run `pip install -r tools\installer\requirements_build.txt` inside the same Python environment you launch PowerShell with.

**Missing `ISCC.exe`**  
Either install Inno Setup 6 to the default location, or pass `-InnoCompiler 'D:\path\to\ISCC.exe'`.

**GCS installer huge / extraction takes minutes on first run**  
Expected. PyQt6 + WebEngine alone is ~150 MB after LZMA2 compression. We use one-folder mode on purpose so subsequent launches do **not** re-extract anything.

**`ImportError: failed to load tools.ui.app` at runtime**  
Re-run with `--clean` (the build script already does). If it persists, add the missing module name to `hiddenimports=[…]` in `tools/installer/specs/droneresearch_gcs.spec`.

**QML files not found at runtime**  
Verify the path layout under `dist\DroneResearchGCS\_internal\tools\ui\qml\`. If it is missing, the `_collect_qml()` helper in the GCS spec did not find them — check that you're running the build from the repo root.

---

## CI integration (future)

The build is fully scriptable. A typical GitHub Actions matrix entry:

```yaml
- name: Build Windows installers
  if: runner.os == 'Windows'
  run: |
    pip install -r tools/installer/requirements_build.txt
    choco install innosetup -y
    pwsh tools/installer/build.ps1
- uses: actions/upload-artifact@v4
  with:
    name: installers-windows
    path: tools/installer/out/*.exe
```

# Windows Installer Build Pipeline

End-to-end build of two self-contained Windows installers:

| Installer | Product | What it bundles | Approx. size |
|---|---|---|---|
| `DroneResearch-CLI-Setup-X.Y.Z.exe` | DroneResearch (research backend, headless) | `droneresearch.exe` + SDK + safety + experiment runner. No PyQt6, no QtWebEngine. | ~86 MB |
| `RZ-GCS-Setup-X.Y.Z.exe` | **RZ GCS** (RZ Solutions ground control station) | `RZ GCS.exe` (QML dashboard) + the DroneResearch backend + PyQt6 + WebEngine + pyqtgraph + 3D mesh assets. | ~450 MB |

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
│   ├── rz_gcs.spec                 ← PyInstaller spec — RZ GCS
│   └── _dis_patch.py               ← bpo-45757 build-time workaround
│
├── inno/
│   ├── droneresearch_cli.iss       ← Inno Setup script — CLI
│   └── rz_gcs.iss                  ← Inno Setup script — RZ GCS
│
└── out/                            ← (generated, gitignored)
    ├── DroneResearch-CLI-Setup-0.2.0.exe
    └── RZ-GCS-Setup-0.2.0.exe
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
Re-run with `--clean` (the build script already does). If it persists, add the missing module name to `hiddenimports=[…]` in `tools/installer/specs/rz_gcs.spec`.

**QML files not found at runtime**  
Verify the path layout under `dist\RZGCS\_internal\tools\ui\qml\`. If it is missing, the `_collect_qml()` helper in the GCS spec did not find them — check that you're running the build from the repo root.

---

## Update flow (RZ GCS)

The installed RZ GCS application can fetch its own updates from GitHub
Releases. The flow lives in `tools/ui/updater.py` (`UpdaterContext`)
and is wired to the QML UI as an `UpdateBanner` component shown at the
top of the Help panel.

How users see it:

1. Open Help tab → banner shows the currently installed version.
2. Click **Nach Updates suchen** → GET to `api.github.com/.../releases/latest`.
3. If the latest tag is newer than `tools/ui/_version.py:VERSION`,
   the banner turns amber, shows the new version and release notes,
   and offers **Herunterladen & Installieren**.
4. Click it → the matching `RZ-GCS-Setup-*.exe` asset is downloaded to
   `%TEMP%`, then launched with `/SILENT /CLOSEAPPLICATIONS
   /RESTARTAPPLICATIONS /NORESTART`. The app exits cleanly, Inno Setup
   replaces the files (the GUID-stable `AppId` triggers an in-place
   upgrade), and the new version restarts automatically.

What the maintainer (you) needs to do for each release:

1. Bump `VERSION` in `tools/ui/_version.py`.
2. Mirror it in `tools/installer/inno/rz_gcs.iss` (`#define AppVersion`).
3. `git tag v0.3.0 && git push --tags`
4. Run `tools\installer\build.ps1`.
5. Create a GitHub Release for the tag and upload the produced
   `tools\installer\out\RZ-GCS-Setup-0.3.0.exe` as a release asset.
   The filename **must** start with `RZ-GCS-Setup-` and end with `.exe`
   so the updater can find it.

That's it — every running RZ GCS instance picks the update up on the
next time the user clicks "Nach Updates suchen".

Network access: a single GET to `api.github.com`. No telemetry,
no analytics, no auto-apply without explicit user click.

---

## Distribution to testers / customers

For every person who should try / buy RZ GCS you ship **one file**:

```
tools\installer\out\RZ-GCS-Setup-X.Y.Z.exe
```

Typical channels: WeTransfer, OneDrive / Google Drive share link, USB stick. The recipient:

1. Double-clicks the installer.
2. Walks through the Inno Setup wizard (License → Path → Shortcuts → Install).
3. Launches **RZ GCS** from the Start Menu.

No Python, no PyQt6, no admin rights required (per-user install by default; the wizard offers a system-wide option for admins).

---

## Trial + license-key flow

RZ GCS ships with a built-in **30-day free trial**. Every fresh install starts the clock on first launch; the trial state is stored in:

```
%LOCALAPPDATA%\RZ Solutions\RZ GCS\license.json
```

### What the tester sees

| Stage | UI behaviour |
|---|---|
| **Day 1 … 29** | Full feature set. Help panel shows a blue "Test-Phase · noch *N* Tage" banner with a `Lizenz aktivieren…` button. |
| **Day 30** | App still launches but a centred, non-dismissable amber overlay appears (`LicenseOverlay.qml`). It blocks every panel and asks for an activation key. The user can either type one in or close the app. |
| **Any time** | A valid key flips the banner green: "Lizenziert · gültig bis YYYY-MM-DD" and unlocks the app permanently (until the key's own expiry). |

The trial length is configured in `tools/ui/_version.py:TRIAL_DAYS`.

### How you mint a key

Run the tiny offline generator from the repo root:

```powershell
# Hand-pick an expiry date (inclusive)
python tools\installer\gen_license.py 2027-01-31

# Or use a duration relative to today
python tools\installer\gen_license.py --days 365

# Tag the output with a customer label (record-keeping only, not embedded)
python tools\installer\gen_license.py --customer "Acme Drones" --days 365
```

Output:

```
┌────────────────────────────────────────────────────────────┐
│  RZ GCS license key                                        │
├────────────────────────────────────────────────────────────┤
│  Customer : Acme Drones
│  Expires  : 2027-05-16  (inclusive)
│  Key      : RZGCS-XXXX-XXXX-XXXX-20270516
└────────────────────────────────────────────────────────────┘
```

Send the customer just the `Key` line. They paste it into the activation banner (Help tab) or into the post-expiry overlay → click **Aktivieren** → done. Verification is **purely offline** (HMAC-SHA256) — no server, no internet required at activation time.

### Rotating / revoking keys

Keys are signed with the `LICENSE_SECRET` constant in `tools/ui/_version.py`. To invalidate every key ever issued:

1. Change `LICENSE_SECRET` to a new random string.
2. Rebuild the installer (`tools\installer\build.ps1`).
3. Ship the new installer; mint fresh keys.

Old installs continue to honour their old keys — only newly-installed builds reject keys signed with the old secret.

> ⚠️ **Before shipping the first paid copy**, change the default `LICENSE_SECRET` (`rz-solutions-dev-secret-CHANGE-ME-before-shipping`). The CLI generator prints a warning while the default is still in place.

### Security caveat

Both the key-validation logic and the HMAC secret live inside the shipped binary. A determined reverse-engineer can extract the secret and mint their own keys. This is **casual protection** — perfect for paying-customer accounting, *not* hard DRM. If you need server-validated activations (one-key-per-machine, online check-in, kill-switch), say the word and I'll bolt that on; expect ~1 day of work.

---

## Source code protection

PyInstaller bundles **bytecode only**, not your `.py` source files. The
compiled DroneResearch + tools.ui code lives inside a PYZ archive
embedded into `_internal/`; the only `.py` files in the install
directory are tiny PyQt6 Designer plug-in descriptors.

Both specs build with `optimize=2`, which strips `assert` statements
and `__doc__` strings from the bundled bytecode.

⚠️ **This is "casual protection" only.** Python bytecode can still be
decompiled back to (roughly) readable source with public tools
(`pyinstxtractor` + `decompyle3`). If you need stronger protection
(commercial IP, licensing keys, etc.), the standard upgrade paths are:

| Tool       | Approach                                | Effort |
|------------|-----------------------------------------|--------|
| PyArmor    | Encrypted bytecode loaded at runtime    | low    |
| Nuitka     | Compile selected modules to C `.pyd`    | medium |
| Cython     | AOT-compile hot modules to C extensions | high   |

None of these are wired up today; ask if you want one added.

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

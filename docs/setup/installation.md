# Installation & Entwicklungsumgebung

## Voraussetzungen

- Python 3.10+
- Git
- Windows 10/11 (für GCS-Build), Ubuntu 22.04 (für Linux-Build)

## Repository klonen

```bash
git clone https://github.com/joeldjio/uavresearchproject.git
cd uavresearchproject
```

## Python-Abhängigkeiten installieren

```bash
pip install -e .
```

Mit Entwicklungstools:
```bash
pip install -e ".[dev]"
```

## GCS (UI) starten

```bash
pip install -r tools/installer/requirements_build.txt
python -m tools.ui
```

## Tests ausführen

```bash
python -m pytest -q
```

## Build-Abhängigkeiten (für Installer)

```bash
pip install -r tools/installer/requirements_build.txt
```

Enthält: PyInstaller, Pillow, PyQt6, PyQt6-WebEngine, pyqtgraph, pymavlink, pyserial, requests.

## Inno Setup (Windows Installer)

Download: https://jrsoftware.org/isinfo.php  
Standard-Installationspfad: `C:\Program Files (x86)\Inno Setup 6\`

## Vollständigen Build lokal ausführen

```powershell
# GCS Installer (Windows)
powershell -ExecutionPolicy Bypass -File tools/installer/build.ps1 -Target gcs

# CLI Installer (Windows)
powershell -ExecutionPolicy Bypass -File tools/installer/build.ps1 -Target cli

# Beide
powershell -ExecutionPolicy Bypass -File tools/installer/build.ps1 -Target all
```

Output: `tools/installer/out/uavresearch-gcs-setup-X.Y.Z.exe`

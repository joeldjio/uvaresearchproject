# Ubuntu 22.04 / Jammy Build Guide

This document explains how to build `uavresearch gcs` directly on Linux.

## Target platform

Supported packaging target:

- Ubuntu 22.04 LTS (Jammy)
- `amd64`
- Output package: `uavresearch-gcs_<VERSION>_amd64_jammy.deb`

## Why build on Linux

Build the Jammy package on Linux, ideally on Ubuntu 22.04 itself.

Reasons:

- PyInstaller bundles platform-native binaries.
- Qt / WebEngine dependencies are Linux-specific.
- Debian packaging tools like `dpkg-deb` are native to Linux.
- Building the Linux package on Windows is not recommended.

## Prerequisites

Install system packages:

```bash
sudo apt-get update
sudo apt-get install -y \
  python3 python3-pip python3-venv \
  build-essential \
  dpkg-dev \
  libegl1 libgl1 libxkbcommon-x11-0 libdbus-1-3 \
  libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
  libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
  libxcb-xinerama0 libxcb-xfixes0
```

Optional but recommended: build in a fresh virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Install Python build dependencies from the repository root:

```bash
python -m pip install -r tools/installer/requirements_build.txt
python -m pip install . requests
```

## Direct build

From the repository root:

```bash
chmod +x tools/installer/build_linux_deb.sh
./tools/installer/build_linux_deb.sh
```

This does the following:

1. Generates branding assets in `tools/installer/assets/`
2. Builds the Linux PyInstaller bundle in `dist/UAVResearchGCS/`
3. Creates a Debian package in `tools/installer/out/`

Expected output:

```text
tools/installer/out/uavresearch-gcs_<VERSION>_amd64_jammy.deb
```

## Repackage without rebuilding PyInstaller

If `dist/UAVResearchGCS/` already exists and you only changed metadata or packaging:

```bash
./tools/installer/build_linux_deb.sh --skip-bundle
```

## Install locally for testing

```bash
sudo apt install ./tools/installer/out/uavresearch-gcs_0.3.1_amd64_jammy.deb
```

Run it via:

```bash
uavresearch-gcs
```

## Remove again

```bash
sudo apt remove uavresearch-gcs
```

## CI / GitHub Actions

The repository workflow already builds the Jammy package on:

- `ubuntu-22.04`

Artifact name in GitHub Actions:

```text
uavresearch-gcs-linux-jammy
```

## Release checklist for Linux

1. Bump `tools/ui/_version.py`
2. Run the Jammy build script on Ubuntu 22.04
3. Verify the `.deb` installs and starts
4. Upload the `.deb` to the GitHub Release
5. Keep the Windows `.exe` asset too, because the in-app updater uses that

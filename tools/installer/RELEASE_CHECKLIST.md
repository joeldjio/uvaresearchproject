# Release Checklist

Use this checklist for each `uavresearch gcs` release.

## 1. Prepare version

- [ ] Update `tools/ui/_version.py`
- [ ] Update `tools/installer/inno/uavresearch_gcs.iss`
- [ ] Add or update release notes in `tools/installer/RELEASE_NOTES_vX.Y.Z.md`
- [ ] Review `tools/installer/README.md` if the packaging flow changed
- [ ] Review `PROJECT_OVERVIEW.md` if release commands or asset names changed

## 2. Validate code

- [ ] Run tests:

```bash
python -m pytest -q
```

- [ ] Regenerate branding assets if installer visuals changed:

```bash
python tools/installer/icon/make_assets.py
```

## 3. Build Windows installer

Run on Windows:

```powershell
.\tools\installer\build.ps1
```

Expected output:

```text
tools\installer\out\uavresearch-gcs-setup-X.Y.Z.exe
```

## 4. Build Ubuntu 22.04 / Jammy package

Run on Ubuntu 22.04:

```bash
chmod +x tools/installer/build_linux_deb.sh
./tools/installer/build_linux_deb.sh
```

Expected output:

```text
tools/installer/out/uavresearch-gcs_X.Y.Z_amd64_jammy.deb
```

## 5. Commit and tag

```bash
git add -A
git commit -m "release: vX.Y.Z"
git tag -a vX.Y.Z -m "uavresearch gcs X.Y.Z"
git push origin HEAD --tags
```

## 6. Publish GitHub release

Create the release with the Windows installer first:

```bash
gh release create vX.Y.Z \
  tools/installer/out/uavresearch-gcs-setup-X.Y.Z.exe \
  --title "uavresearch gcs X.Y.Z" \
  --notes-file tools/installer/RELEASE_NOTES_vX.Y.Z.md
```

Then upload the Jammy package:

```bash
gh release upload vX.Y.Z \
  tools/installer/out/uavresearch-gcs_X.Y.Z_amd64_jammy.deb
```

## 7. Final verification

- [ ] Confirm the GitHub Release contains both assets
- [ ] Confirm the Windows asset name still matches `uavresearch-gcs-setup-*.exe`
- [ ] Test Windows in-app updater against the published release
- [ ] Test local install of the Jammy `.deb`
- [ ] Archive any customer-facing release notes or delivery notes

## Current release target

For the current prepared release state in this repository:

- Version: `0.3.1`
- Windows asset: `uavresearch-gcs-setup-0.3.1.exe`
- Linux asset: `uavresearch-gcs_0.3.1_amd64_jammy.deb`

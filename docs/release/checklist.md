# Release Checklist

Checkliste für jeden `uavresearch gcs` Release.

---

## 1. Version bumpen

```bash
python tools/installer/bump_version.py X.Y.Z
```

Das Script aktualisiert automatisch:
- `tools/ui/_version.py`
- `tools/installer/inno/uavresearch_gcs.iss`

Dann manuell:
- [ ] Release Notes erstellen: `docs/release/notes-vX.Y.Z.md`
- [ ] `docs/README.md` — neue Release-Notes-Zeile in der Tabelle ergänzen

---

## 2. Code validieren

```bash
# Tests ausführen
python -m pytest -q

# Branding-Assets neu generieren (nur wenn sich Logos/Farben geändert haben)
python tools/installer/icon/make_assets.py
```

---

## 3. Committen & taggen

```bash
git add tools/ui/_version.py tools/installer/inno/uavresearch_gcs.iss
git add docs/release/notes-vX.Y.Z.md docs/README.md
git commit -m "Bump version to X.Y.Z"
git tag vX.Y.Z
git push origin ui-dashboard --tags
```

→ GitHub Actions baut automatisch alle 3 Plattformen und veröffentlicht den Release.

---

## 4. Release prüfen

- [ ] GitHub Actions Build erfolgreich: `https://github.com/joeldjio/uavresearchproject/actions`
- [ ] Release sichtbar: `https://github.com/joeldjio/rz-gcs-releases/releases`
- [ ] Windows `.exe` + `.sha256` vorhanden
- [ ] macOS `.tar.gz` + `.sha256` vorhanden
- [ ] Linux `.deb` + `.sha256` vorhanden

---

## 5. In-App-Updater testen

- [ ] GCS starten (alte Version installiert)
- [ ] Help-Panel → "Check for Updates" klicken
- [ ] Update-Banner erscheint mit neuer Versionsnummer
- [ ] "Download & Install" ausführen → Installer startet

---

## Asset-Naming-Konvention

Der In-App-Updater sucht nach Assets die:
- mit `uavresearch-gcs-setup-` beginnen
- auf `.exe` enden

**Korrekt:** `uavresearch-gcs-setup-0.3.2.exe`  
**Falsch:** `setup.exe`, `GCS-Setup.exe`, `installer.exe`

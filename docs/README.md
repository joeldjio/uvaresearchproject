# UAVResearch GCS — Dokumentation

Vollständige Dokumentation des UAVResearch GCS Projekts.

---

## Inhaltsverzeichnis

### Projekt
| Dokument | Beschreibung |
|----------|-------------|
| [project/overview.md](project/overview.md) | Projektarchitektur, Komponenten, Roadmap |
| [project/improvements.md](project/improvements.md) | Bugfixes & Verbesserungen (Code-Review) |

### Setup & Installation
| Dokument | Beschreibung |
|----------|-------------|
| [setup/installation.md](setup/installation.md) | Entwicklungsumgebung einrichten |
| [setup/px4-sitl.md](setup/px4-sitl.md) | PX4 SITL mit Gazebo starten |
| [setup/raspberry-pi.md](setup/raspberry-pi.md) | Raspberry Pi Deployment |

### Build & CI
| Dokument | Beschreibung |
|----------|-------------|
| [build/installer-pipeline.md](build/installer-pipeline.md) | Windows / Linux Installer bauen |
| [build/linux-jammy.md](build/linux-jammy.md) | Ubuntu 22.04 `.deb` Build-Guide |
| [build/ci-workflow.md](build/ci-workflow.md) | GitHub Actions Workflow erklärt |

### Release
| Dokument | Beschreibung |
|----------|-------------|
| [release/checklist.md](release/checklist.md) | Checkliste für jeden Release |
| [release/releases-repo.md](release/releases-repo.md) | Public Release-Repo (`rz-gcs-releases`) |
| [release/notes-v0.3.1.md](release/notes-v0.3.1.md) | Release Notes v0.3.1 |
| [release/notes-v0.3.0.md](release/notes-v0.3.0.md) | Release Notes v0.3.0 |

### UI
| Dokument | Beschreibung |
|----------|-------------|
| [ui/ui-documentation.md](ui/ui-documentation.md) | Alle Panels, Komponenten, QML-Architektur |

---

## Schnellstart — neuen Release veröffentlichen

```bash
# 1. Version bumpen (aktualisiert _version.py + .iss automatisch)
python tools/installer/bump_version.py 0.4.0

# 2. Committen, taggen und pushen
git add tools/ui/_version.py tools/installer/inno/uavresearch_gcs.iss
git commit -m "Bump version to 0.4.0"
git tag v0.4.0
git push origin ui-dashboard --tags
```

→ GitHub Actions baut automatisch alle Plattformen und veröffentlicht den Release unter  
`https://github.com/joeldjio/rz-gcs-releases/releases`

---

## Branch-Strategie

```
main           → stabiler, releasefähiger Stand
ui-dashboard   → aktive GCS / UI Entwicklung
feature/*      → einzelne Features / Optimierungen
```

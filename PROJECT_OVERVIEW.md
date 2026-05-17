# RZ GCS — Projekt-Überblick (für mich)

> Persönliches Briefing-Dokument. Kein Marketing, kein Kunde-zeigen.
> Hier steht **was wir gebaut haben, wie es zusammenhängt, und was als Nächstes ansteht.**
>
> Stand: 2026-05-16

---

## 1. Was ist RZ GCS?

Eine **Ground Control Station für Drohnen-Schwärme**, die als Windows-Installer
(später auch Mac/Linux) ausgeliefert wird. Der eigentliche Code ist das
`droneresearch`-Forschungs-Backend (CLI + Python-SDK), das `tools/ui` ist die
PyQt6/QML-Oberfläche darauf.

**Markenstruktur:**

| Komponente | Branding | Wer sieht das? |
|---|---|---|
| `droneresearch` (Backend, CLI, SDK) | DroneResearch | Forscher, CLI-User, SDK-User |
| `tools/ui` (Desktop-App) | **RZ GCS** / RZ Solutions | Endkunden, Tester |

→ Der wissenschaftliche Forschungs-Stack heißt weiter „DroneResearch"
(Repo-Name, Python-Imports, Logo). Nur die kommerzielle Desktop-App
ist „RZ GCS".

---

## 2. Was wir heute gebaut haben (2026-05-16)

### 2.1 Rebrand
- App-Titel, QApplication name/org, Status-Bar-Texte → **RZ GCS / RZ Solutions**
- Installer-Dateinamen → `RZ-GCS-Setup-X.Y.Z.exe`
- Inno-`AppId` auf eine stabile, dedizierte GUID rotiert — damit Upgrades funktionieren
- Spec/Inno-Dateien umbenannt: `rz_gcs.spec`, `rz_gcs.iss`

### 2.2 In-App-Updater  (`tools/ui/updater.py`)
- `UpdaterContext` als Qt-Singleton, registriert im ServiceLocator als `updater`
- Prüft auf Klick gegen GitHub Releases API
  (`https://api.github.com/repos/joeldjio/rz-gcs-releases/releases/latest`)
- Sucht ein Asset mit Präfix `RZ-GCS-Setup-` und Endung `.exe`
- Vergleicht Tag-Version mit eingebauter `_version.VERSION`
- QML-Banner im Help-Tab zeigt: idle / checking / available / uptodate / error / downloading
- Download nach `%TEMP%`, dann silent install: `/SILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS`
- Inno setzt `CloseApplications=force` und `RestartApplications=yes` → in-place Upgrade ohne User-Interaktion
- Code-Repo `joeldjio/uavresearchproject` ist privat; öffentliches Update-/Release-Repo ist `joeldjio/rz-gcs-releases`

### 2.3 Trial + License-Keys  (`tools/ui/license.py`)
- `LicenseManager` als Qt-Singleton, registriert als `licenseManager`
- **30 Tage Free Trial** ab erstem Start, Zeitstempel in
  `%LOCALAPPDATA%\RZ Solutions\RZ GCS\license.json`
- **Key-Format:** `RZGCS-XXXX-XXXX-XXXX-YYYYMMDD`
  - `XXXXXXXXXXXX` = erste 12 Zeichen von `base32(HMAC-SHA256(SECRET, "v1|YYYYMMDD"))`
  - Validierung **komplett offline**, kein Server
- **3 Zustände:** `trial`, `licensed`, `expired`
- **`LicenseOverlay.qml`** — Vollbild-Modal nach Trial-Ablauf, sperrt UI
- **`LicenseStatusBanner.qml`** — Banner im Help-Tab, zeigt Status + erlaubt proaktive Aktivierung
- **CLI-Generator:** `python tools/installer/gen_license.py --days 365 --customer "X"`

### 2.4 Code-Schutz
- Beide PyInstaller-Specs (`rz_gcs.spec`, `droneresearch_cli.spec`) bauen mit `optimize=2`
  → `assert`-Statements + `__doc__`-Strings werden aus dem Bytecode gestrippt
- Source-Dateien werden **nicht** mit ausgeliefert, nur `.pyc` im PYZ-Archiv
- `pkg_resources` und `setuptools._vendor` ausgeschlossen
  (sonst krachte der CLI-Build wegen `appdirs`-Imports)

### 2.5 Dokumentation
- `tools/installer/README.md` komplett überarbeitet:
  Distribution-Flow, Trial+License-Cookbook, Key-Rotation, Update-Mechanik
- `PROJECT_OVERVIEW.md` (das hier)

### 2.6 Tests
- `tests/test_license.py`: 16 Tests
  - Key-Round-Trip, Tampering rejection, garbage rejection, case-insensitive
  - Trial-State-Machine (first launch, expiration after window)
  - Activation success/failure, expired key rejection
  - Cross-instance Persistence
- **Gesamt-Suite:** 172 passed, 4 skipped (rclpy)

### 2.7 Git
- Branch: `ui-dashboard`
- Commit `d553c32`: alles oben drin, gepusht
- Tag `v0.2.0` gesetzt + gepusht (für GitHub Release)
- Remote: `https://github.com/joeldjio/uavresearchproject.git`

---

## 3. Wie das alles zusammenpasst (System-Diagramm)

```
┌────────────────────── DroneResearch (SDK / CLI) ──────────────────────┐
│                                                                       │
│   droneresearch/                                                      │
│     ├─ core/connection.py     ← MAVLinkConnection (Heartbeat-Loop)    │
│     ├─ autopilot/mavlink/     ← Stream-Rates, AP-Detection (APM/PX4)  │
│     ├─ control/mission.py     ← Waypoint-Engine                       │
│     ├─ data/logger.py         ← CSV-Logger pro Drohne                 │
│     └─ sdk/drone.py + swarm.py ← Public API                           │
│                                                                       │
└────────────────────────────────┬──────────────────────────────────────┘
                                 │ Python Imports
┌────────────────────────────────▼──────────────────────────────────────┐
│   tools/ui/  (RZ GCS Desktop)                                         │
│                                                                       │
│   service_locator.py — registriert als Qt-Singletons:                 │
│     • swarm           SwarmContext (mehrere Drohnen + FSM)            │
│     • telemetryModel  TelemetryModel (10 Hz Polling pro Drohne)       │
│     • experiment      ExperimentContext                               │
│     • safety          SafetyContext (APF-Visualisierung)              │
│     • ros2            ROS2Context (optional, nur mit rclpy)           │
│     • updater         UpdaterContext         ← NEU                    │
│     • licenseManager  LicenseManager         ← NEU                    │
│                                                                       │
│   qml/main.qml + panels/ — UI                                         │
│     [Map] [Dashboard] [Swarm] [Safety] [Gimbal] [ROS2]                │
│     [Experiment] [FlightLog] [Help] [Log]                             │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 4. Hardware-Support: Was funktioniert, was nicht (Audit-Ergebnis)

### 4.1 Verbindungsarten (alle bereits unterstützt durch pymavlink)

| Transport | Connection-String-Beispiel | Status |
|---|---|---|
| ArduPilot SITL | `tcp:127.0.0.1:5760` | ✅ getestet |
| PX4 SITL | `udp:127.0.0.1:14550` | ✅ getestet |
| Serial (USB-FTDI, telemetry-radio) | `COM3` (Windows) oder `/dev/ttyUSB0` (Linux) | ⚠️ ungetestet aber implementiert |
| Telemetry-Radio (SiK / RFD900) | `COM5:57600` | ⚠️ ungetestet |
| ELRS-Modul (siehe 4.5) | `COM7:420000` | ⚠️ ungetestet |
| UDP forward (z.B. Mission Planner shared) | `udpin:0.0.0.0:14550` | ⚠️ ungetestet |
| TCP-Bridge (Custom Companion-Computer) | `tcp:192.168.1.42:5760` | ⚠️ ungetestet |

**Aktion:** Beim ersten Echt-Hardware-Test mit Tester einen Termin machen,
einen Smoke-Test durchgehen.

### 4.2 Werden COM-Ports beim Start gescannt?

**Ja.** Im Header der App wird beim Start `swarm.availableSerialPorts()`
aufgerufen. Intern nutzt das `serial.tools.list_ports.comports()`.

Zusätzlich gibt es neben dem Port-Feld ein Refresh-Symbol `⟳`. Wenn man
darauf klickt, werden die COM-Ports erneut gescannt und als Liste angezeigt.

Wichtig: Wenn Windows keinen COM-Port meldet, kann die App auch keinen Port
anzeigen. Dann im Geräte-Manager prüfen, ob der Flight Controller oder das
Telemetrie-Modul wirklich als COM-Port erkannt wurde.

### 4.3 Wird Telemetrie abgefragt?

**Ja, vollständig.** Nach dem Heartbeat schickt `_request_streams()`
`REQUEST_DATA_STREAM` für alle relevanten Streams:

```
RAW_SENSORS  (1)   → 4 Hz
EXTENDED_STATUS (2) → 4 Hz   ← Battery, GPS-Status
RC_CHANNELS  (3)   → 2 Hz   ← RC-Inputs (auch von ELRS!)
POSITION (6)       → 4 Hz   ← GPS lat/lon
EXTRA1 (10)        → 10 Hz  ← Attitude
EXTRA2 (11)        → 4 Hz   ← VFR_HUD
EXTRA3 (12)        → 2 Hz   ← AHRS, Wind
```

Geparst werden: HEARTBEAT, GLOBAL_POSITION_INT, GPS_RAW_INT, ATTITUDE,
VFR_HUD, BATTERY_STATUS, SYS_STATUS, RAW_IMU, HOME_POSITION, STATUSTEXT,
COMMAND_ACK.

→ Battery, GPS, Attitude, Mode, Armed-State, Position — alles da.

### 4.4 Wird der Autopilot erkannt?

**Ja, halb.** `_detect_autopilot(heartbeat)` setzt `telemetry.autopilot`
auf `"ardupilot"`, `"px4"` oder `"unknown"`, basierend auf
`heartbeat.autopilot`-Feld (3 = APM, 12 = PX4).

**Jetzt auch in der UI sichtbar.** Im Swarm-Tab gibt es eine
**SYSTEM INFO**-Karte für die ausgewählte Drohne.

Angezeigt werden:
- Autopilot-Typ (`ardupilot`, `px4`, `unknown`)
- Vehicle-Type / Copter-Art aus `HEARTBEAT.type`, z. B. `QUADROTOR`
- Firmware-Version aus `AUTOPILOT_VERSION`, wenn der Flight Controller antwortet
- Board-Version
- Vendor-ID / Product-ID
- System-Status
- Flight-Mode
- FSM-State
- Connection-String

Wichtig: Firmware/Board erscheinen erst, wenn der echte Flight Controller
die MAVLink-Nachricht `AUTOPILOT_VERSION` beantwortet. SITL oder manche
Controller können diese Felder leer lassen.

### 4.5 Pre-Arm-Checks?

**Nicht von uns gemacht — vom Autopilot.** ArduPilot/PX4 führen ihre eigenen
Pre-Arm-Checks server-seitig durch. Wenn ein Check fehlschlägt:

1. Autopilot sendet `STATUSTEXT` mit der Fehlermeldung
   („PreArm: GPS HDOP too high")
2. Wir empfangen den `STATUSTEXT` → emittieren als `log_message`
3. Erscheint im **Log-Tab** und im **Status-Bar** (rot blinkend bei ERROR)
4. Wenn der `arm()`-Command nicht akzeptiert wird → `COMMAND_ACK` mit `result != 0`
5. Wir parsen den NACK → loggen als `WARN`: `NACK COMPONENT_ARM_DISARM → DENIED`

→ Der User sieht **immer** warum nicht gearmt werden kann, im Log und im Status-Bar.

### 4.6 Werden Verbindungs-Probleme im Log angezeigt?

**Ja:**

| Event | Log-Level | Quelle |
|---|---|---|
| `🔄 Connecting (...) to {conn_str}...` | INFO | `swarm_context.addDroneTyped` |
| `✅ Connected successfully` | INFO | `_on_connection_changed` |
| `❌ Connection lost or failed` | ERROR | `_on_connection_changed` |
| `Connection timed out` | ERROR | `DroneBackend.connect` (15s timeout) |
| `Connection error: {exception}` | ERROR | `MAVLinkConnection.connect` |
| Pre-Arm-Failures (STATUSTEXT) | WARN/ERROR | Autopilot-seitig |

Das Log-Panel hat einen Filter pro Drohne und pro Severity.

---

## 5. ELRS / Radiomaster Ranger Micro 2.4GHz — Wird das funktionieren?

### Kurz: **Ja, mit dem richtigen Setup.** Aber wir müssen es testen.

### Was ELRS ist
ExpressLRS ist ein offenes Funkprotokoll für RC-Steuerung (TX → Drohne).
Das **Radiomaster Ranger Micro** ist ein TX-Modul das man auf einen
Sender (z.B. Radiomaster Boxer) steckt, und auf der Drohne sitzt ein
ELRS-Empfänger.

### Was wir aus GCS-Sicht brauchen
RZ GCS spricht **nicht direkt** mit dem ELRS-Modul. Wir reden nur
**MAVLink** mit dem Flight Controller. Der FC kriegt RC-Inputs vom
Empfänger über CRSF/SBUS.

→ Für **RC-Steuerung allein**: ELRS macht das ohne GCS-Beteiligung.
   Pilot fliegt mit dem Sender, GCS sieht nur die Telemetrie.

### Wenn Telemetrie über ELRS zurückkommen soll
ELRS unterstützt **MAVLink-over-CRSF** (auch genannt
„MAVLink-tunneling"). Setup auf der Drohnen-Seite:

1. Im FC: `SERIAL1_PROTOCOL = 2` (MAVLink2) auf dem Port wo der ELRS-Empfänger hängt
2. Im ELRS-Empfänger: MAVLink-Modus aktivieren (Lua-Script auf dem Sender)
3. Im ELRS-TX-Modul (Ranger Micro): MAVLink-Output über USB aktivieren

Aus PC-Sicht: das Ranger Micro erscheint dann als **virtueller COM-Port**
und sendet MAVLink-Frames mit ~420000 Baud.

### Connection-String den der Tester eingeben würde
```
COM7              ← einfach, nimmt 57600 Baud (default)
serial:COM7:420000  ← explizit für ELRS
```

### Was noch nicht getestet ist
- Ob `pymavlink` mit ELRS-Latenz und Paketverlust gut klarkommt
  (im Vergleich zu SiK das stabil ist)
- Ob bei 2.4 GHz die Bandbreite für alle Streams reicht
  (bei 50–150 kbps ELRS-Packet-Rate könnte das knapp werden,
   eventuell Stream-Rates runtersetzen)

### Empfehlung
1. Beim ersten Hardware-Test: SiK / RFD900 / direkt USB-FTDI nutzen
   (das ist der zuverlässige Pfad, sicher funktioniert)
2. ELRS als „Premium-Feature" später separat verifizieren — kann 1–2 Tage
   Tuning brauchen (Stream-Rates anpassen, ggf. eigenen ELRS-Mode)

---

## 6. Distribution: Wie kommt das zum Kunden?

### 6.1 Build-Pipeline

```
git push                       (was du tust)
         │
         ▼
.\tools\installer\build.ps1    (was du tust, ~5 Min)
         │
         ▼
tools\installer\out\
  └── RZ-GCS-Setup-0.2.0.exe   (eine Datei, ~270 MB)
         │
         ▼
GitHub Release erstellen        (Web-UI oder gh CLI)
  + .exe als Asset hochladen
         │
         ▼
WeTransfer / Mail / Download-Link an Kunde
         │
         ▼
Kunde: Doppelklick → installiert → 30 Tage Trial
         │
         ▼ (wenn er kaufen will)
Du: python tools\installer\gen_license.py --days 365
         │
         ▼
Key per Mail an Kunde → er paste rein → entsperrt
```

### 6.2 Voraussetzungen

| Wer | Was muss installiert sein |
|---|---|
| **Du (Build)** | Python 3.10, PyInstaller, Inno Setup 6 |
| **Du (Release)** | git + optional GitHub CLI (`gh`) |
| **Kunde (Install)** | Nichts. Wirklich gar nichts. |

### 6.3 Auf welchen Branch pushen?

**Workflow den ich empfehle:**

```
main (stable, getaggte Releases)
  │
  └── ui-dashboard (aktive Entwicklung) ← du bist hier
        │
        ├── feature/sysinfo-panel (große Features)
        ├── feature/com-port-scan
        └── fix/foo (Bugfixes)
```

- **Kleine Änderung (Bugfix, README-Update, Tweak):**
  direkt auf `ui-dashboard` committen + pushen.
- **Großes Feature (neue Funktion, Refactor):**
  Branch von `ui-dashboard` machen → entwickeln → mergen.
- **Release zur Auslieferung:**
  `ui-dashboard` → `main` mergen → Tag setzen → bauen → GitHub Release.

```powershell
# Beispiel: kleines Update
git add -A
git commit -m "fix: status bar font size"
git push origin ui-dashboard

# Beispiel: großes Feature
git checkout -b feature/com-port-scan
# ... Code ...
git push origin feature/com-port-scan
# Pull Request auf GitHub → mergen in ui-dashboard
```

---

## 7. Versions-Workflow (für jeden Release)

```powershell
# 1. Versionen synchron hochzählen
#    tools/ui/_version.py            : VERSION = "0.3.0"
#    tools/installer/inno/rz_gcs.iss  : #define AppVersion "0.3.0"

# 2. Commit + Tag
git add -A
git commit -m "release: v0.3.0"
git tag -a v0.3.0 -m "RZ GCS 0.3.0"
git push origin ui-dashboard --tags

# 3. Bauen (~5 Min)
.\tools\installer\build.ps1

# 4. Release auf GitHub
gh release create v0.3.0 `
  tools\installer\out\RZ-GCS-Setup-0.3.0.exe `
  --title "RZ GCS 0.3.0" `
  --notes "Was neu ist..."

# 5. Bestehende Kunden klicken im Help-Tab auf "Updates suchen" → Update läuft auto.
```

---

## 7A. Release, Tags, privates Repo, Updates und Lizenz — alles Wichtige

### 7A.1 Kann ein Kunde die Release direkt von GitHub herunterladen?

**Ja, wenn das GitHub-Repo oder der Release öffentlich ist.**

Wenn du auf GitHub einen Release mit Asset hochlädst:

```text
RZ-GCS-Setup-0.3.0.exe
```

dann kann jeder, der Zugriff auf die Release-Seite hat, diese `.exe`
herunterladen.

Wenn das Repo **public** ist, kann jeder Releases, Tags, Release-Assets und
den Source-Code sehen. Wenn das Repo **private** ist, können nur eingeladene
GitHub-User diese Dinge sehen.

### 7A.2 Kann jemand den Tag sehen?

**Ja, wenn das Repo öffentlich ist.**

Ein Git-Tag wie `v0.2.0` ist ein Marker auf einen Commit. Wenn das Repo
public ist, sieht jeder diesen Tag und kann den dazugehörigen Code-Stand sehen.

### 7A.3 Soll ich das Repo privat machen?

**Ja, für dein Geschäftsmodell empfehle ich: Repo privat machen.**

Grund:
- Im Repo liegt der komplette Quellcode.
- Im Code liegt aktuell auch `LICENSE_SECRET`.
- Wer den echten Secret kennt, kann eigene gültige Keys generieren.
- PyInstaller schützt nur den ausgelieferten Installer halbwegs, aber nicht ein öffentliches GitHub-Repo.

Vor echter Kundenauslieferung:
1. Repo privat machen.
2. `LICENSE_SECRET` ändern.
3. Neue Version bauen.
4. Nur den Installer an Kunden geben, nicht das Repo.

### 7A.4 Funktioniert der Updater noch, wenn das Repo privat ist?

**Ja, weil der Updater jetzt nicht mehr das private Code-Repo benutzt.**

Das Code-Repo `joeldjio/uavresearchproject` ist privat. Der Updater fragt
stattdessen das öffentliche Release-Repo ab:

```text
https://api.github.com/repos/joeldjio/rz-gcs-releases/releases/latest
```

Die Einstellung steht in `tools/ui/_version.py`:

```python
GITHUB_REPO = "joeldjio/rz-gcs-releases"
```

Wichtig: In das Release-Repo kommen **nur Installer und Release Notes**,
kein Source-Code und kein `LICENSE_SECRET`.

### 7A.5 Wie mache ich eine neue Release?

```powershell
# 1. Versionen anpassen:
# tools/ui/_version.py -> VERSION = "0.3.0"
# tools/installer/inno/rz_gcs.iss -> AppVersion "0.3.0"

# 2. Commit + Tag
git status
git add -A
git commit -m "release: v0.3.0"
git tag -a v0.3.0 -m "RZ GCS 0.3.0"
git push origin ui-dashboard --tags

# 3. Installer bauen
.\tools\installer\build.ps1

# 4. GitHub Release erstellen
gh release create v0.3.0 `
  tools\installer\out\RZ-GCS-Setup-0.3.0.exe `
  --title "RZ GCS 0.3.0" `
  --notes "Neue Version mit Bugfixes und Verbesserungen."
```

Wenn du ein separates Release-Repo verwendest, muss der Release dort erstellt
werden, nicht im privaten Code-Repo.

### 7A.6 Wie mache ich einen neuen Lizenz-Key?

Für einen Key mit Laufzeit in Tagen:

```powershell
python tools\installer\gen_license.py --days 365 --customer "Kunde Name"
```

Für einen Key mit festem Ablaufdatum:

```powershell
python tools\installer\gen_license.py --expires 2027-05-17 --customer "Kunde Name"
```

Der Kunde bekommt einen Key im Format:

```text
RZGCS-XXXX-XXXX-XXXX-YYYYMMDD
```

Lizenz-Anfragen gehen an:

```text
djiojoel2@gmail.com
```

### 7A.7 Sind alle Keys im Code gespeichert?

**Nein. Es gibt keine Liste mit allen Keys im Code.**

Die Software prüft nicht gegen eine Datenbank. Sie prüft eine Signatur:

1. Im Code gibt es ein geheimes Passwort: `LICENSE_SECRET`.
2. Beim Generieren wird aus Ablaufdatum + Secret eine HMAC-SHA256-Signatur gebaut.
3. Die ersten 12 Zeichen dieser Signatur kommen in den Key.
4. In der App wird dieselbe Signatur nochmal berechnet.
5. Wenn die Signatur passt, ist der Key echt.
6. Danach prüft die App, ob das Ablaufdatum noch in der Zukunft liegt.

Beispiel:

```text
RZGCS-ABCD-EFGH-IJKL-20270517
                         └ Ablaufdatum
       └ Signatur aus SECRET + Ablaufdatum
```

### 7A.8 Wo wird die Lizenz beim Kunden gespeichert?

Die App speichert Trial/Lizenz hier:

```text
%LOCALAPPDATA%\RZ Solutions\RZ GCS\license.json
```

Darin steht:
- `installed_at` = wann die Trial gestartet ist
- `key` = aktivierter Lizenz-Key, falls vorhanden

Wenn kein Key vorhanden ist, läuft die App 30 Tage im Trial-Modus. Nach Ablauf
startet die App noch, aber das Lizenz-Overlay blockiert die Bedienung.

### 7A.9 Wird die Lizenz auch gebraucht, wenn ich mit `python -m tools.ui` starte?

**Ja.**

Die Lizenzlogik steckt in der App selbst, nicht nur im Installer:
- `tools/ui/license.py`
- `LicenseOverlay.qml`
- `LicenseStatusBanner.qml`
- Qt-Singleton `licenseManager`

Also nutzt auch:

```powershell
python -m tools.ui
```

dieselbe Trial-/License-Logik wie der gebaute Installer.

### 7A.10 Was passiert, wenn ich `LICENSE_SECRET` ändere?

Dann werden alte Keys für neue Builds ungültig, weil die Signatur nicht mehr
passt.

Das ist gut für Key-Rotation vor Kundenauslieferung oder im Notfall. Aber:
Kunden mit altem Key brauchen dann einen neuen Key, sobald sie eine App-Version
mit neuem Secret installieren.

### 7A.11 Was muss ich vor dem ersten echten Kunden machen?

Pflicht:
1. Repo privat machen.
2. Separates public Release-Repo oder eigenen Update-Server entscheiden.
3. `LICENSE_SECRET` in `tools/ui/_version.py` ersetzen.
4. `GITHUB_REPO` ggf. auf Release-Repo ändern.
5. Version erhöhen.
6. Installer neu bauen.
7. Test-Key generieren.
8. Auf frischem Windows-PC testen:
   - Trial startet
   - Key akzeptiert
   - abgelaufener Key wird abgelehnt
   - Update-Check findet Release

---

## 8. Was als Nächstes ansteht (Roadmap nach Priorität)

### 8.1 Erledigt in dieser Session
- [x] **Sysinfo-Detail-Pane im Swarm-Tab** — Autopilot/Frame/FW-Version anzeigen
- [x] **COM-Port-Scan/Refresh geprüft** — pyserial `list_ports.comports()` wird im Header genutzt
- [x] **GitHub Actions Workflow** — Mac/Linux/Windows-Builds automatisch

### 8.2 Vor erstem Echt-Hardware-Test
- [ ] Auto-Detect Baudrate für serial connections (115200/57600/420000 trying)
- [ ] „Test connection"-Button vor permanentem Add-Drone
- [ ] Better connection-string parser (Mission-Planner-kompatible Strings akzeptieren)

### 8.3 Vor erster bezahlter Auslieferung
- [ ] **`LICENSE_SECRET` rotieren** (aktuell `rz-solutions-dev-secret-CHANGE-ME-before-shipping`)
- [ ] Code-Signing-Zertifikat (sonst SmartScreen-Warnung beim Tester)
- [x] Echter `LICENSE_CONTACT` in `_version.py`: `djiojoel2@gmail.com`
- [ ] Entscheiden: privates Code-Repo + öffentliches Release-Repo oder eigener Update-Server

### 8.4 Nice-to-have (Backlog)
- [ ] „Skip this version"-Button im Update-Banner
- [ ] Automatischer Update-Check beim Start (mit Opt-Out)
- [ ] License-Aktivierung bindet Maschine (Hardware-ID-Hash) → Anti-Sharing
- [ ] Server-validierte Aktivierung (echte DRM, ~1 Tag Aufwand)
- [ ] ELRS-Tuning-Profile (reduzierte Stream-Rates für 2.4 GHz)

---

## 9. Nützliche Pfade & Dateien

```
tools/ui/_version.py              VERSION + LICENSE_SECRET + Vendor-Konstanten
tools/ui/license.py               LicenseManager + Key-Sign/Verify
tools/ui/updater.py               UpdaterContext (GitHub-Polling)
tools/ui/qml/components/
  ├── LicenseOverlay.qml          Vollbild-Modal nach Trial-Ablauf
  ├── LicenseStatusBanner.qml     Help-Tab Banner mit inline-Aktivierung
  └── UpdateBanner.qml            Help-Tab Banner für Updates
tools/installer/
  ├── build.ps1                   One-Shot-Builder
  ├── gen_license.py              Key-Generator-CLI
  ├── specs/
  │   ├── rz_gcs.spec             PyInstaller-Spec für GCS
  │   └── droneresearch_cli.spec  PyInstaller-Spec für CLI
  ├── inno/
  │   ├── rz_gcs.iss              Inno-Setup-Skript für GCS
  │   └── droneresearch_cli.iss   Inno-Setup-Skript für CLI
  └── README.md                   Detaillierte Build- + Distribution-Doku
tests/test_license.py             Regression-Tests für Trial+Keys
```

---

## 10. „Spickzettel" für tägliche Tasks

### Neue Version bauen + ausliefern
```powershell
.\tools\installer\build.ps1
```

### Lizenz-Key für Kunden generieren
```powershell
python tools\installer\gen_license.py --days 365 --customer "Name"
```

### Vollständige Test-Suite laufen lassen
```powershell
python -m pytest tests\ -q
```

### Trial reset (zum Testen — in installierter App)
```powershell
Remove-Item "$env:LOCALAPPDATA\RZ Solutions\RZ GCS\license.json"
```

### Eigene Lizenz für Dev-Tests aktivieren
```powershell
python tools\installer\gen_license.py --days 30
# Output-Key in der App eingeben (Help-Tab → Lizenz aktivieren)
```

### Status-Check vorm Release
```powershell
python -m pytest tests\ -q                   # Tests grün?
git status                                    # alles committed?
git log --oneline -5                          # letzte commits
git tag -l                                    # vorhandene Tags
```

---

## 11. Betriebs-Handbuch: Alles was ich wissen muss

Dieser Abschnitt ist die Kurzfassung für den Alltag. Wenn ich später nicht
mehr weiß, was zu tun ist, hier anfangen.

### 11.1 Die wichtigsten Entscheidungen

| Thema | Entscheidung / Empfehlung |
|---|---|
| Code-Repo | **Privat machen**, weil Code + Lizenz-Secret nicht öffentlich sein sollen |
| Update-Repo | Separates öffentliches Release-Repo nur für Installer verwenden |
| Lizenzsystem | Offline-Lizenz mit HMAC-Signatur, keine Serverpflicht |
| Trial | 30 Tage ab erstem Start |
| Kundenkontakt | `djiojoel2@gmail.com` |
| Installer-Name | `RZ-GCS-Setup-X.Y.Z.exe` |
| App-Name | `RZ GCS` |
| Backend-Name | `droneresearch` bleibt intern so |

### 11.2 Was der Kunde bekommt

Der Kunde bekommt **nur diese Datei**:

```text
RZ-GCS-Setup-X.Y.Z.exe
```

Der Kunde bekommt nicht:
- den Quellcode
- das GitHub-Repo
- das Lizenz-Generator-Script
- `LICENSE_SECRET`
- Build-Dateien

Nach Installation läuft die App 30 Tage als Trial. Danach muss der Kunde einen
Lizenz-Key eingeben.

### 11.3 Was ich niemals öffentlich machen darf

Nicht öffentlich teilen:
- `LICENSE_SECRET`
- privates Code-Repo
- Lizenz-Generator-Tool zusammen mit echtem Secret
- GitHub Token
- private Release-Links, wenn sie nur für bestimmte Kunden gedacht sind

Wichtig: Der aktuelle `LICENSE_SECRET` ist noch ein Dev-Secret:

```text
rz-solutions-dev-secret-CHANGE-ME-before-shipping
```

Vor echter Auslieferung muss er geändert werden.

### 11.4 Wann muss ich Versionen ändern?

Bei jedem Release muss die Version an mindestens diesen Stellen gleich sein:

```text
tools/ui/_version.py
tools/installer/inno/rz_gcs.iss
Git tag, z. B. v0.3.0
Installer-Datei, z. B. RZ-GCS-Setup-0.3.0.exe
GitHub Release, z. B. RZ GCS 0.3.0
```

Wenn diese Versionen nicht zusammenpassen, kann der Updater falsche Ergebnisse
anzeigen oder den Installer nicht finden.

### 11.5 Was muss der Updater finden?

Der Updater sucht im öffentlichen Release-Repo:

```python
GITHUB_REPO = "joeldjio/rz-gcs-releases"
```

nach dem neuesten GitHub Release und darin nach einem Asset:

```text
RZ-GCS-Setup-*.exe
```

Beispiel:

```text
RZ-GCS-Setup-0.3.0.exe
```

Wenn der Asset-Name anders ist, findet die App kein Update.

### 11.6 Beste Update-Strategie

Für echten Verkauf ist diese Strategie jetzt aktiv:

1. Code-Repo `joeldjio/uavresearchproject` privat lassen.
2. Öffentliches Release-Repo `joeldjio/rz-gcs-releases` verwenden.
3. In `tools/ui/_version.py` ist gesetzt:

```python
GITHUB_REPO = "joeldjio/rz-gcs-releases"
```

4. Installer nur als Release-Asset dort hochladen.
5. Code bleibt privat.
6. Updater funktioniert weiter ohne GitHub Token.

### 11.7 Lizenz-Key: Was passiert technisch?

Es gibt keine Online-Aktivierung und keine Key-Datenbank.

Der Key ist mathematisch signiert:

```text
SECRET + Ablaufdatum -> HMAC-SHA256 -> 12 Zeichen Signatur -> Key
```

Die App macht dieselbe Rechnung. Wenn die Signatur passt und das Datum nicht
abgelaufen ist, akzeptiert sie den Key.

Darum ist `LICENSE_SECRET` so wichtig. Wer den Secret kennt, kann gültige Keys
erzeugen.

### 11.8 Beispiel-Key-Lebenslauf

1. Kunde testet App.
2. Trial läuft 30 Tage.
3. Kunde will kaufen.
4. Kunde schreibt an `djiojoel2@gmail.com`.
5. Ich generiere Key:

```powershell
python tools\installer\gen_license.py --days 365 --customer "Kunde GmbH"
```

6. Ich schicke Key per Mail.
7. Kunde öffnet App.
8. Kunde gibt Key im Lizenzfenster/Help-Tab ein.
9. App speichert Key in:

```text
%LOCALAPPDATA%\RZ Solutions\RZ GCS\license.json
```

10. App läuft bis Ablaufdatum.

### 11.9 Was passiert bei Update und Lizenz?

Die Lizenzdatei liegt im Benutzerprofil, nicht im Installationsordner.

Darum bleibt die Lizenz normalerweise erhalten, wenn der Kunde ein Update
installiert.

Aber:
- Wenn `LICENSE_SECRET` gleich bleibt, bleiben alte Keys gültig.
- Wenn `LICENSE_SECRET` geändert wird, brauchen Kunden neue Keys.
- Wenn die Lizenzdatei gelöscht wird, startet die App wieder ohne gespeicherten Key.

### 11.10 Was passiert bei `python -m tools.ui`?

Auch beim lokalen Python-Start wird die Lizenzlogik geladen.

```powershell
python -m tools.ui
```

verwendet:
- denselben `LicenseManager`
- dieselbe Trial-Datei
- denselben Key-Check
- dasselbe Overlay

Das ist gut, weil ich die Lizenzlogik ohne Instalvemkler testen kann.

### 11.11 Was muss ich vor einem Kunden-Test prüfen?

Checkliste:

- [ ] App startet auf meinem PC
- [ ] Installer lässt sich bauen
- [ ] Frischer Install-Test funktioniert
- [ ] Trial wird angezeigt
- [ ] Lizenz-Key kann aktiviert werden
- [ ] Help-Tab zeigt richtige Kontakt-Mail
- [ ] Update-Check funktioniert oder ist bewusst noch nicht aktiv
- [ ] Repo/Release-Sichtbarkeit ist richtig eingestellt
- [ ] Kein Kunde hat Zugriff auf den Quellcode
- [ ] Flight Controller Verbindung mit SITL getestet
- [ ] Wenn Hardware-Test: COM-Port erscheint im Header

### 11.12 Was muss ich vor einem bezahlten Kunden prüfen?

Strengere Checkliste:

- [ ] Code-Repo privat
- [ ] Echter neuer `LICENSE_SECRET`
- [ ] Test-Key mit neuem Secret generiert
- [ ] Alter Dev-Key wird nicht mehr akzeptiert
- [ ] Separates Release-Repo oder eigener Update-Server eingerichtet
- [ ] `GITHUB_REPO` zeigt auf Release-Repo
- [ ] Installer-Dateiname passt zum Updater
- [ ] Release Notes geschrieben
- [ ] Windows Defender / SmartScreen getestet
- [ ] Optional: Code-Signing-Zertifikat
- [ ] Hardware-Verbindung mit echtem Flight Controller getestet
- [ ] PreArm-Fehler erscheinen im Log
- [ ] Autopilot und Vehicle-Type erscheinen in SYSTEM INFO

### 11.13 Typische Fehler und Ursache

| Problem | Wahrscheinliche Ursache | Lösung |
|---|---|---|
| Update wird nicht gefunden | Asset heißt nicht `RZ-GCS-Setup-*.exe` | Release Asset richtig benennen |
| Update geht bei privatem Repo nicht | GitHub API braucht Auth | Public Release-Repo verwenden |
| Key wird abgelehnt | Falscher Secret, Tippfehler oder abgelaufen | Mit aktuellem Secret neuen Key generieren |
| Kunde sieht Trial abgelaufen | Kein gültiger Key gespeichert | Key eingeben oder neuen Key schicken |
| COM-Port fehlt | Windows erkennt Gerät nicht | Treiber/Geräte-Manager prüfen |
| Autopilot unknown | Kein/komischer HEARTBEAT | Verbindung/FC-Firmware prüfen |
| Firmware leer | FC antwortet nicht auf `AUTOPILOT_VERSION` | Mit echter Hardware testen, ggf. später erneut anfragen |

### 11.14 Meine empfohlene Reihenfolge ab jetzt

1. Code-Repo privat machen.
2. Neues öffentliches Release-Repo erstellen.
3. `GITHUB_REPO` auf Release-Repo ändern.
4. `LICENSE_SECRET` ersetzen.
5. Version auf `0.3.0` erhöhen.
6. Tests laufen lassen.
7. Installer bauen.
8. Release mit Installer hochladen.
9. Auf sauberem Windows-PC installieren.
10. Trial + Lizenz + Update testen.
11. Erst danach an Tester/Kunden schicken.

### 11.14A Release-Repo `joeldjio/rz-gcs-releases`

Das öffentliche Release-Repo ist:

```text
https://github.com/joeldjio/rz-gcs-releases
```

Zweck:
- öffentliche Downloads für Kunden/Tester
- Update-Quelle für die App
- Release Notes
- keine Quellcode-Veröffentlichung

Dieses Repo ersetzt **nicht** das private Code-Repo. Es ist nur der öffentliche
Kanal für fertige Installer.

#### Was darf in das Release-Repo?

Erlaubt:
- GitHub Releases
- Installer-Dateien wie `RZ-GCS-Setup-0.3.0.exe`
- Release Notes
- README mit Download-/Lizenzhinweisen

Nicht erlaubt:
- Source-Code
- `.py` Dateien
- `tools/installer/gen_license.py`
- `LICENSE_SECRET`
- GitHub Tokens
- private Build-Scripte
- interne Notizen mit Secrets

#### Wie benutzt die App dieses Repo?

In `tools/ui/_version.py` steht:

```python
GITHUB_REPO = "joeldjio/rz-gcs-releases"
```

Der Updater ruft dadurch diese URL auf:

```text
https://api.github.com/repos/joeldjio/rz-gcs-releases/releases/latest
```

Dann sucht er im neuesten Release ein Asset:

```text
RZ-GCS-Setup-*.exe
```

Wenn kein Asset mit diesem Namen vorhanden ist, findet die App kein Update.

#### Wie erstelle ich dort einen Release?

1. Im privaten Code-Repo Version ändern.
2. Installer lokal bauen:

```powershell
.\tools\installer\build.ps1
```

3. Im Release-Repo auf GitHub öffnen:

```text
https://github.com/joeldjio/rz-gcs-releases
```

4. **Releases → Draft a new release**.
5. Tag setzen, z. B.:

```text
v0.3.0
```

6. Titel setzen:

```text
RZ GCS 0.3.0
```

7. Installer hochladen:

```text
tools\installer\out\RZ-GCS-Setup-0.3.0.exe
```

8. Release Notes schreiben.
9. Release veröffentlichen.

#### Wichtig zu Tags im Release-Repo

Der Tag im Release-Repo ist nur für Veröffentlichungen/Updates. Der private
Code bleibt im privaten Code-Repo.

Wenn du im Release-Repo einen Tag `v0.3.0` erstellst, sieht die Öffentlichkeit
nur:
- Release Name
- Release Notes
- Installer Asset

Sie sieht **nicht** automatisch den privaten Code.

#### README für das Release-Repo

Eine fertige Vorlage liegt im privaten Code-Repo unter:

```text
tools\installer\RELEASE_REPO_README.md
```

Den Inhalt kannst du in die `README.md` vom öffentlichen Release-Repo kopieren.

### 11.15 Muss ich vor dem Build committen und pushen?

Das hängt davon ab, **wo** der Build laufen soll.

| Build-Art | Commit nötig? | Push nötig? | Warum? |
|---|---:|---:|---|
| Windows lokal auf meinem PC | Nein | Nein | Der lokale Builder nimmt direkt meine aktuellen Dateien |
| Windows über GitHub Actions | Ja | Ja | GitHub kann nur Code bauen, der im Repo angekommen ist |
| macOS über GitHub Actions | Ja | Ja | Der Mac-Runner läuft bei GitHub, nicht auf meinem PC |
| Linux über GitHub Actions | Ja | Ja | Der Linux-Runner läuft bei GitHub, nicht auf meinem PC |
| Offizieller Release | Ja | Ja | Tag, Release und Build sollen reproduzierbar sein |

#### Windows lokal bauen

Für schnellen lokalen Test auf Windows brauche ich keinen Commit:

```powershell
.\tools\installer\build.ps1
```

Ergebnis:

```text
tools\installer\out\RZ-GCS-Setup-X.Y.Z.exe
```

Das ist gut für:
- schnellen Test
- Installer lokal prüfen
- Trial/Lizenz testen
- UI testen

#### GitHub Actions Build starten

Für Mac, Linux oder Windows in der Cloud muss ich erst pushen:

```powershell
git add -A
git commit -m "build: prepare release"
git push origin ui-dashboard
```

Danach startet der Workflow automatisch:

```text
.github/workflows/build-rz-gcs.yml
```

Alternativ kann ich ihn auf GitHub manuell starten:

```text
GitHub → Actions → Build RZ GCS → Run workflow
```

#### Mac-Build

Mac-Build geht praktisch nur über:
- GitHub Actions `macos-latest`
- echten Mac
- anderen macOS-CI-Dienst

Von Windows aus kann ich keinen sauberen macOS-Build erzeugen.

GitHub Actions erzeugt für macOS aktuell:

```text
RZ-GCS-macOS.tar.gz
```

Das ist noch kein schöner `.dmg` Installer. Für echte Mac-Kunden braucht es
später zusätzlich:
- `.app` sauber prüfen
- `.dmg` bauen
- Apple Developer Signing
- Apple Notarization

#### Windows-Build

Für Windows habe ich zwei Wege:

**Lokal:**

```powershell
.\tools\installer\build.ps1
```

Erzeugt den echten Inno Setup Installer:

```text
RZ-GCS-Setup-X.Y.Z.exe
```

**GitHub Actions:**

GitHub baut ein Windows-Artefakt:

```text
RZ-GCS-windows.zip
```

Wichtig: Für den offiziellen Kunden-Installer ist aktuell der lokale
Inno-Setup-Build der wichtigste Weg, weil er die fertige `.exe` erstellt.

#### Offizieller Release-Ablauf

Für einen echten Release immer committen, taggen und pushen:

```powershell
git add -A
git commit -m "release: v0.3.0"
git tag -a v0.3.0 -m "RZ GCS 0.3.0"
git push origin ui-dashboard --tags
```

Dann bauen:

```powershell
.\tools\installer\build.ps1
```

Dann die Datei hochladen:

```text
tools\installer\out\RZ-GCS-Setup-0.3.0.exe
```

als GitHub Release Asset zum Tag `v0.3.0`.

# Translation Guide

## Style Guidelines

### General Principles

1. **Clarity over Brevity**: Prefer clear, understandable translations over short ones
2. **Consistency**: Use the same translation for the same term throughout
3. **Context Awareness**: Consider where the text appears (button, label, error message)
4. **Technical Accuracy**: Maintain technical precision, especially for aviation/drone terms

### Tone

- **Professional**: Use formal, technical language
- **Direct**: Be clear and concise
- **Instructive**: Guide the user clearly

### Formatting

- **Capitalization**: 
  - German: Capitalize nouns (standard German rules)
  - English: Title case for buttons, sentence case for descriptions
- **Punctuation**: Follow target language conventions
- **Numbers**: Use locale-appropriate formatting (e.g., 1.234,56 vs 1,234.56)

## Terminology Glossary

### Core Terms (Deutsch ↔ English)

| Deutsch | English | Notes |
|---------|---------|-------|
| Drohne | Drone | Never "UAV" in UI |
| Schwarm | Swarm | Collective of drones |
| Verbinden | Connect | Network/communication connection |
| Trennen | Disconnect | |
| Starten | Takeoff | Aircraft taking off |
| Landen | Land | Aircraft landing |
| Bewaffnen | Arm | Enable motors |
| Entwaffnen | Disarm | Disable motors |
| Mission | Mission | Autonomous flight plan |
| Wegpunkt | Waypoint | GPS coordinate in mission |
| Sicherheit | Safety | Safety systems |
| Telemetrie | Telemetry | Sensor data stream |
| Höhe | Altitude | Height above ground/sea level |
| Geschwindigkeit | Speed | Velocity |
| Kurs | Heading | Direction (0-360°) |
| Batterie | Battery | Power source |
| GPS | GPS | Do not translate |
| Satellit | Satellite | GPS satellite |

### Flight States (FSM)

| Deutsch | English | Context |
|---------|---------|---------|
| IDLE (Verbunden, bereit) | IDLE (Connected, ready) | Drone connected, ready to arm |
| ARMING (Wird bewaffnet…) | ARMING (Arming…) | Motors being enabled |
| ARMED (Bereit zum Start) | ARMED (Ready for takeoff) | Motors enabled, ready to fly |
| TAKEOFF (Startet…) | TAKEOFF (Taking off…) | Ascending to target altitude |
| FLYING (In der Luft) | FLYING (In the air) | Airborne, manual control |
| MISSION (Autopilot aktiv) | MISSION (Autopilot active) | Following autonomous mission |
| RTL (Kehrt zurück) | RTL (Returning) | Return to launch |
| LANDING (Landet…) | LANDING (Landing…) | Descending to ground |
| EMERGENCY (Notfall!) | EMERGENCY (Emergency!) | Emergency state |
| ERROR (Fehler) | ERROR (Error) | Error state |
| DISCONNECTED (Keine Verbindung) | DISCONNECTED (No connection) | Not connected |

### UI Elements

| Deutsch | English | Context |
|---------|---------|---------|
| Öffnen | Open | Open file/dialog |
| Laden | Load | Load data |
| Speichern | Save | Save data |
| Ausführen | Execute | Run script/command |
| Stoppen | Stop | Stop operation |
| Beispiel | Example | Example/template |
| Verlauf | History | Historical data |
| Steuerung | Control | Control panel/system |
| Ablauf | Sequence | Step-by-step process |
| Hinweis | Note/Hint | Informational message |

### Technical Terms (Do Not Translate)

- **SITL** - Software In The Loop
- **MAVLink** - Micro Air Vehicle Link protocol
- **ROS2** - Robot Operating System 2
- **APF** - Artificial Potential Field
- **FSM** - Finite State Machine
- **GPS** - Global Positioning System
- **RTL** - Return To Launch
- **E-STOP** - Emergency Stop
- **CSV** - Comma-Separated Values
- **JSON** - JavaScript Object Notation
- **TCP/UDP** - Network protocols

### Drone Types

| Deutsch | English |
|---------|---------|
| Generic UAV (Standard) | Generic UAV (Standard) |
| Observation UAV (Gimbal/Kamera) | Observation UAV (Gimbal/Camera) |

### Swarm Roles

| Deutsch | English |
|---------|---------|
| Leader | Leader |
| Follower | Follower |
| Coordinator | Coordinator |

## Context-Specific Translations

### Buttons

Keep button text short and action-oriented:

| Context | Deutsch | English |
|---------|---------|---------|
| Add drone | ＋ ADD | ＋ ADD |
| Connect | VERBINDEN | CONNECT |
| Disconnect | TRENNEN | DISCONNECT |
| Arm | ARM | ARM |
| Disarm | DISARM | DISARM |
| Takeoff | TAKEOFF | TAKEOFF |
| Land | LAND | LAND |
| Emergency | E-STOP | E-STOP |

### Status Messages

| Deutsch | English |
|---------|---------|
| Verbunden | Connected |
| Getrennt | Disconnected |
| Bereit | Ready |
| Beschäftigt | Busy |
| Fehler | Error |
| Warnung | Warning |

### Error Messages

Be clear and actionable:

| Deutsch | English |
|---------|---------|
| Datei konnte nicht gelesen werden | File could not be read |
| Keine Verbindung | No connection |
| Bereits verbunden! | Already connected! |
| Ungültige Eingabe | Invalid input |

### Instructions

Use imperative mood:

| Deutsch | English |
|---------|---------|
| Drücke ARM um zu starten | Press ARM to start |
| Warten… | Wait… |
| Nicht eingreifen | Do not interfere |
| Sofort landen | Land immediately |

## Common Phrases

### Dashboard

| Deutsch | English |
|---------|---------|
| Drone ist verbunden | Drone is connected |
| Wird bewaffnet | Arming |
| Bereit zum Start | Ready for takeoff |
| In der Luft | In the air |
| Kehrt zurück | Returning |
| Landet | Landing |

### Experiment Panel

| Deutsch | English |
|---------|---------|
| Python-Script öffnen | Open Python Script |
| Script bereit | Script ready |
| Klicke auf 'Beispiel' für ein fertiges Experiment | Click 'Example' for a ready-made experiment |

### Flight Log Panel

| Deutsch | English |
|---------|---------|
| Kein Log geladen | No log loaded |
| Log öffnen | Open log |
| Dauer | Duration |
| Maximale Höhe | Maximum altitude |
| Maximale Geschwindigkeit | Maximum speed |

## Special Cases

### Abbreviations

- Keep technical abbreviations in English (GPS, RTL, FSM)
- Expand if needed for clarity in German

### Units

Always include units with numbers:
- Altitude: `10m` (meters)
- Speed: `5m/s` (meters per second)
- Heading: `180°` (degrees)
- Battery: `85%` (percent)
- Time: `30s` (seconds)

### Placeholders

Preserve placeholders in translations:
```
German:  "Drone %1 verbunden"
English: "Drone %1 connected"
```

## Quality Checklist

Before submitting translations:

- [ ] All strings translated
- [ ] Terminology consistent with glossary
- [ ] No UI text overflow
- [ ] Technical terms correct
- [ ] Grammar and spelling checked
- [ ] Context appropriate
- [ ] Placeholders preserved
- [ ] Units included where needed

## Examples

### Good Translations

✅ **German**: "Drücke ARM (InstrBar oben) → Status: ARMED"  
✅ **English**: "Press ARM (InstrBar above) → Status: ARMED"

✅ **German**: "Drone ist verbunden. Drücke ARM um zu starten."  
✅ **English**: "Drone is connected. Press ARM to start."

### Poor Translations

❌ **German**: "Klick ARM für Start" (too informal)  
✅ **Better**: "Drücke ARM um zu starten"

❌ **English**: "Drone connects" (wrong tense)  
✅ **Better**: "Drone is connected"

❌ **German**: "UAV fliegt" (use "Drohne" not "UAV")  
✅ **Better**: "Drohne fliegt"

## Resources

- [Duden](https://www.duden.de/) - German dictionary
- [LEO](https://dict.leo.org/) - German-English dictionary
- [Aviation terminology](https://en.wikipedia.org/wiki/Glossary_of_aviation_terms)
- [MAVLink documentation](https://mavlink.io/)

## Questions?

If you're unsure about a translation:
1. Check this glossary
2. Look at similar strings in the codebase
3. Ask in the project's discussion forum
4. When in doubt, prefer clarity over brevity
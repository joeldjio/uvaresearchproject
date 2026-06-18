# PySide6 Migration Guide

**Date:** 2026-06-17  
**Branch:** `license-compliance-pyside6-migration`  
**Status:** ✅ Complete

---

## Overview

This document describes the migration from PyQt6 (GPL v3) to PySide6 (LGPL v3) to enable commercial use of the UAVResearch project without GPL restrictions.

## Why Migrate?

### License Compatibility Issue

- **PyQt6:** GPL v3 (viral license)
  - Forces entire application to be GPL v3
  - Prohibits closed-source commercial distribution
  - Requires source code disclosure

- **PySide6:** LGPL v3 (permissive for dynamic linking)
  - Allows commercial closed-source applications
  - Only requires dynamic linking (standard in Python)
  - No source code disclosure required for application code

### Business Impact

| Aspect | PyQt6 (GPL v3) | PySide6 (LGPL v3) |
|--------|----------------|-------------------|
| Commercial Use | ❌ Restricted | ✅ Allowed |
| Closed Source | ❌ Not Allowed | ✅ Allowed |
| License Cost | €500-5000/dev/year | ✅ Free |
| Source Disclosure | ❌ Required | ✅ Not Required |

---

## Migration Summary

### Automated Changes (539 total)

The migration script [`tools/migrate_to_pyside6.py`](../../tools/migrate_to_pyside6.py) automatically converted:

1. **Import statements:** `PyQt6` → `PySide6`
2. **Signal declarations:** `pyqtSignal` → `Signal`
3. **Slot decorators:** `pyqtSlot` → `Slot`
4. **Property decorators:** `pyqtProperty` → `Property`

### Files Modified

- **36 Python files** across:
  - `tools/ui/` - Main UI code
  - `tools/ui/context/` - Context managers
  - `tests/` - Test files
  - Root level utilities

### API Compatibility

PySide6 API is **95% compatible** with PyQt6:

| Feature | PyQt6 | PySide6 | Compatible? |
|---------|-------|---------|-------------|
| Widgets | `QtWidgets` | `QtWidgets` | ✅ Yes |
| Core | `QtCore` | `QtCore` | ✅ Yes |
| GUI | `QtGui` | `QtGui` | ✅ Yes |
| QML | `QtQml` | `QtQml` | ✅ Yes |
| WebEngine | `QtWebEngineWidgets` | `QtWebEngineWidgets` | ✅ Yes |
| Signals | `pyqtSignal` | `Signal` | ⚠️ Rename |
| Slots | `pyqtSlot` | `Slot` | ⚠️ Rename |
| Properties | `pyqtProperty` | `Property` | ⚠️ Rename |

---

## Installation

### Uninstall PyQt6

```bash
pip uninstall PyQt6 PyQt6-WebEngine
```

### Install PySide6

```bash
pip install PySide6 PySide6-WebEngine
```

Or use the updated requirements:

```bash
pip install -r requirements.txt
```

---

## Testing

### Run Test Suite

```bash
# Full test suite
pytest tests/

# UI-specific tests
pytest tests/test_ui_*.py -v
pytest tests/e2e/ -v

# Skip slow tests
pytest tests/ -m "not slow"
```

### Manual UI Testing

```bash
# Launch UI
python -m tools.ui

# Test key features:
# 1. Dashboard displays telemetry
# 2. Map shows drone positions
# 3. Swarm panel controls multiple drones
# 4. Mission upload works
# 5. Safety filters activate
# 6. Experiment logging functions
```

---

## Known Differences

### Signal/Slot Syntax

**PyQt6:**
```python
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

class MyClass(QObject):
    mySignal = pyqtSignal(str)
    
    @pyqtSlot()
    def mySlot(self):
        pass
```

**PySide6:**
```python
from PySide6.QtCore import QObject, Signal, Slot

class MyClass(QObject):
    mySignal = Signal(str)
    
    @Slot()
    def mySlot(self):
        pass
```

### Property Syntax

**PyQt6:**
```python
from PyQt6.QtCore import pyqtProperty

@pyqtProperty(str)
def name(self):
    return self._name
```

**PySide6:**
```python
from PySide6.QtCore import Property

@Property(str)
def name(self):
    return self._name
```

### WebEngine Initialization

Both require initialization before QApplication:

```python
# Same for both PyQt6 and PySide6
from PySide6.QtWebEngineQuick import QtWebEngineQuick
QtWebEngineQuick.initialize()
```

---

## LGPL v3 Compliance

### Requirements

To comply with LGPL v3 when distributing PySide6-based applications:

1. **Dynamic Linking** ✅
   - Python naturally uses dynamic linking
   - Users can replace PySide6 via `pip install`

2. **License Notices** ✅
   - Include [`THIRD_PARTY_LICENSES.txt`](../../THIRD_PARTY_LICENSES.txt)
   - Include [`NOTICE.txt`](../../NOTICE.txt)

3. **Source Availability** ✅
   - PySide6 source: https://code.qt.io/cgit/pyside/pyside-setup.git/
   - No modifications made to PySide6

4. **User Rights** ✅
   - Users can replace PySide6 independently
   - No static linking or obfuscation

### Distribution Checklist

- [x] Include `THIRD_PARTY_LICENSES.txt` in distribution
- [x] Include `NOTICE.txt` in distribution
- [x] Document that PySide6 is dynamically linked
- [x] Provide instructions for replacing PySide6
- [x] No modifications to PySide6 source code

---

## Rollback Plan

If issues arise, rollback is straightforward:

```bash
# 1. Checkout previous commit
git checkout HEAD~1

# 2. Reinstall PyQt6
pip uninstall PySide6 PySide6-WebEngine
pip install PyQt6 PyQt6-WebEngine

# 3. Run tests
pytest tests/
```

---

## Migration Script

The migration was performed using [`tools/migrate_to_pyside6.py`](../../tools/migrate_to_pyside6.py):

```bash
python tools/migrate_to_pyside6.py
```

**Output:**
- Files modified: 36
- Total changes: 539
- Time: ~2 seconds

---

## Commercial Use

### Before Migration (PyQt6)

❌ **Cannot sell closed-source software**
- GPL v3 requires source code disclosure
- Commercial PyQt6 license: €500-5000/dev/year

### After Migration (PySide6)

✅ **Can sell closed-source software**
- LGPL v3 allows commercial use with dynamic linking
- No license fees
- No source code disclosure required

---

## References

### Documentation

- [PySide6 Documentation](https://doc.qt.io/qtforpython/)
- [LGPL v3 License](https://www.gnu.org/licenses/lgpl-3.0.html)
- [Qt Licensing](https://www.qt.io/licensing/)

### Related Documents

- [`LICENSE_AUDIT_2026-06.md`](LICENSE_AUDIT_2026-06.md) - Full license audit
- [`THIRD_PARTY_LICENSES.txt`](../../THIRD_PARTY_LICENSES.txt) - Third-party licenses
- [`NOTICE.txt`](../../NOTICE.txt) - Copyright notices

---

## Support

For questions about the migration:

1. Check this guide
2. Review the license audit: [`LICENSE_AUDIT_2026-06.md`](LICENSE_AUDIT_2026-06.md)
3. Consult PySide6 documentation
4. Open an issue on GitHub

---

**Migration Status:** ✅ Complete  
**Commercial Use:** ✅ Enabled  
**License Compliance:** ✅ Verified
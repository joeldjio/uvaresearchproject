# Translation Files

This directory contains compiled translation files (.qm) for the UAV Research Platform.

## Generating Translation Files

Translation files must be generated using Qt's `lupdate` and `lrelease` tools.

### Prerequisites

Install Qt Linguist tools:
```bash
# On Ubuntu/Debian
sudo apt-get install qttools5-dev-tools

# On macOS with Homebrew
brew install qt

# On Windows
# Install Qt from https://www.qt.io/download
```

### Step 1: Extract Strings

Extract translatable strings from QML and Python files:

```bash
# Extract from QML files
lupdate tools/ui/qml -ts droneresearch/i18n/translations/de_DE.ts
lupdate tools/ui/qml -ts droneresearch/i18n/translations/en_US.ts

# Extract from Python files (if using pylupdate6)
pylupdate6 tools/ui/*.py -ts droneresearch/i18n/translations/ui_de_DE.ts
pylupdate6 tools/ui/*.py -ts droneresearch/i18n/translations/ui_en_US.ts
```

### Step 2: Translate

Open the `.ts` files in Qt Linguist and translate:

```bash
linguist droneresearch/i18n/translations/de_DE.ts
linguist droneresearch/i18n/translations/en_US.ts
```

### Step 3: Compile

Compile `.ts` files to `.qm` (binary) files:

```bash
lrelease droneresearch/i18n/translations/*.ts
```

This will create:
- `de_DE.qm` - German translations
- `en_US.qm` - English translations

## File Types

- **`.ts` files**: XML source files (human-readable, version controlled)
- **`.qm` files**: Compiled binary files (used at runtime, not version controlled)

## Notes

- `.qm` files are in `.gitignore` and must be generated locally
- Source language is English (strings in code)
- Default UI language is German
- See `docs/i18n/README.md` for full documentation
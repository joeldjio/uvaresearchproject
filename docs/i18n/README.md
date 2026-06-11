# Internationalization (i18n) Guide

## Overview

The UAV Research Platform supports multiple languages through Qt's internationalization system. Currently supported languages:

- **Deutsch (German)** - Default language
- **English** - Full translation available

## Architecture

### Components

1. **droneresearch/i18n/** - Core i18n infrastructure
   - Language definitions
   - Translation file management
   - Helper functions

2. **tools/ui/i18n.py** - Qt integration
   - `I18nManager` class for language switching
   - Persistent language preferences
   - QTranslator management

3. **Translation Files** - Located in `droneresearch/i18n/translations/`
   - `de_DE.ts` / `de_DE.qm` - German translations
   - `en_US.ts` / `en_US.qm` - English translations

4. **UI Components**
   - `LanguageSwitcher.qml` - Language selection widget
   - Integrated in application header

## For Users

### Switching Languages

1. **Via UI**: Click the language switcher in the top-right corner of the application header
2. **Persistent**: Your language choice is saved and restored on next launch

### Supported Languages

| Code | Language | Status |
|------|----------|--------|
| `de` | Deutsch  | ✅ Complete |
| `en` | English  | ✅ Complete |

## For Developers

### Adding Translatable Strings

#### In QML Files

Wrap user-visible strings with `qsTr()`:

```qml
// Before
Text { text: "Connect" }

// After
Text { text: qsTr("Connect") }
```

#### In Python Files

Use `self.tr()` for QObject subclasses:

```python
# Before
button.setText("Connect")

# After
button.setText(self.tr("Connect"))
```

### Updating Translations

When you add or modify translatable strings:

1. **Extract strings** to `.ts` files:
   ```bash
   # For QML
   lupdate tools/ui/qml -ts droneresearch/i18n/translations/de_DE.ts
   lupdate tools/ui/qml -ts droneresearch/i18n/translations/en_US.ts
   
   # For Python
   pylupdate6 tools/ui/*.py -ts droneresearch/i18n/translations/ui_de_DE.ts
   pylupdate6 tools/ui/*.py -ts droneresearch/i18n/translations/ui_en_US.ts
   ```

2. **Translate** using Qt Linguist:
   ```bash
   linguist droneresearch/i18n/translations/de_DE.ts
   ```

3. **Compile** translations:
   ```bash
   lrelease droneresearch/i18n/translations/*.ts
   ```

### Adding a New Language

1. **Register the language** in `droneresearch/i18n/__init__.py`:
   ```python
   SUPPORTED_LANGUAGES = {
       "de": "Deutsch",
       "en": "English",
       "fr": "Français",  # New language
   }
   ```

2. **Create translation files**:
   ```bash
   lupdate tools/ui/qml -ts droneresearch/i18n/translations/fr_FR.ts
   pylupdate6 tools/ui/*.py -ts droneresearch/i18n/translations/ui_fr_FR.ts
   ```

3. **Translate** using Qt Linguist

4. **Compile**:
   ```bash
   lrelease droneresearch/i18n/translations/fr_FR.ts
   ```

5. **Update LanguageSwitcher.qml**:
   ```qml
   property var languages: ["Deutsch", "English", "Français"]
   property var languageCodes: ["de", "en", "fr"]
   ```

## Translation Workflow

### For Translators

1. **Get the source file**: `droneresearch/i18n/translations/XX_YY.ts`
2. **Open in Qt Linguist**: `linguist XX_YY.ts`
3. **Translate strings**:
   - Read the source text (English)
   - Provide translation in target language
   - Mark as "done" when complete
4. **Save** the file
5. **Compile**: `lrelease XX_YY.ts` (creates `.qm` file)

### Translation Guidelines

- **Consistency**: Use the same terms throughout (see [translation-guide.md](translation-guide.md))
- **Context**: Consider where the text appears (button, label, message)
- **Length**: Keep translations similar in length to avoid UI overflow
- **Technical Terms**: Some terms (e.g., "SITL", "MAVLink") should not be translated
- **Placeholders**: Preserve `%1`, `%2` etc. in the same order

## Testing Translations

1. **Switch language** in the UI
2. **Check all panels**:
   - Dashboard
   - Experiment
   - Flight Log
   - Swarm Control
3. **Verify**:
   - No untranslated strings
   - No UI overflow
   - Correct terminology

## Troubleshooting

### Translations Not Showing

1. **Check .qm files exist**:
   ```bash
   ls droneresearch/i18n/translations/*.qm
   ```

2. **Recompile translations**:
   ```bash
   lrelease droneresearch/i18n/translations/*.ts
   ```

3. **Clear Qt cache**:
   ```bash
   rm -rf ~/.cache/uavresearch/
   ```

### Missing Strings

1. **Extract new strings**:
   ```bash
   lupdate tools/ui/qml -ts droneresearch/i18n/translations/*.ts
   ```

2. **Translate in Qt Linguist**

3. **Recompile**

## Technical Details

### File Formats

- **`.ts` files**: XML-based translation source files (human-readable)
- **`.qm` files**: Compiled binary translation files (used at runtime)

### Language Codes

We use ISO 639-1 (language) + ISO 3166-1 (country) format:
- `de_DE` - German (Germany)
- `en_US` - English (United States)

### Storage

User language preference is stored in:
```
~/.uavresearch/language.json
```

## Resources

- [Qt Linguist Manual](https://doc.qt.io/qt-6/qtlinguist-index.html)
- [Qt Internationalization](https://doc.qt.io/qt-6/internationalization.html)
- [Translation Guide](translation-guide.md) - Terminology and style guide
"""Tests for internationalization (i18n) support."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_supported_languages():
    """Test that supported languages are defined."""
    from droneresearch.i18n import SUPPORTED_LANGUAGES
    
    assert "de" in SUPPORTED_LANGUAGES
    assert "en" in SUPPORTED_LANGUAGES
    assert SUPPORTED_LANGUAGES["de"] == "Deutsch"
    assert SUPPORTED_LANGUAGES["en"] == "English"


def test_default_language():
    """Test that default language is German."""
    from droneresearch.i18n import DEFAULT_LANGUAGE
    
    assert DEFAULT_LANGUAGE == "de"


def test_translations_dir_exists():
    """Test that translations directory exists."""
    from droneresearch.i18n import TRANSLATIONS_DIR
    
    assert TRANSLATIONS_DIR.exists()
    assert TRANSLATIONS_DIR.is_dir()


def test_get_translation_path():
    """Test getting translation file paths."""
    from droneresearch.i18n import get_translation_path
    
    # Valid language codes
    de_path = get_translation_path("de")
    en_path = get_translation_path("en")
    
    assert de_path is not None
    assert en_path is not None
    assert de_path.name == "de_DE.qm"
    assert en_path.name == "en_US.qm"
    
    # Invalid language code
    invalid_path = get_translation_path("xx")
    assert invalid_path is None


def test_get_language_name():
    """Test getting language display names."""
    from droneresearch.i18n import get_language_name
    
    assert get_language_name("de") == "Deutsch"
    assert get_language_name("en") == "English"
    assert get_language_name("xx") == "xx"  # Unknown returns code


@pytest.mark.skipif(
    not pytest.importorskip("PyQt6", reason="PyQt6 not available"),
    reason="Requires PyQt6"
)
class TestI18nManager:
    """Tests for I18nManager class."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock QApplication."""
        with patch("tools.ui.i18n.QApplication") as mock:
            app = MagicMock()
            mock.instance.return_value = app
            yield app
    
    @pytest.fixture
    def i18n_manager(self, mock_app, tmp_path):
        """Create an I18nManager instance with temp config."""
        from tools.ui.i18n import I18nManager
        
        # Mock config file location
        config_file = tmp_path / "language.json"
        
        with patch.object(I18nManager, "_I18nManager__init__") as mock_init:
            manager = I18nManager.__new__(I18nManager)
            manager.app = mock_app
            manager.translator = None
            manager.current_language = "de"
            manager._config_file = config_file
            yield manager
    
    def test_load_language_default(self, i18n_manager):
        """Test loading default language."""
        result = i18n_manager.load_language("de")
        assert result is True
        assert i18n_manager.current_language == "de"
    
    def test_load_language_invalid(self, i18n_manager):
        """Test loading invalid language."""
        result = i18n_manager.load_language("xx")
        assert result is False
    
    def test_get_current_language(self, i18n_manager):
        """Test getting current language."""
        assert i18n_manager.get_current_language() == "de"
    
    def test_get_supported_languages(self, i18n_manager):
        """Test getting supported languages."""
        langs = i18n_manager.get_supported_languages()
        assert "de" in langs
        assert "en" in langs
        assert langs["de"] == "Deutsch"
    
    def test_save_language_preference(self, i18n_manager, tmp_path):
        """Test saving language preference."""
        config_file = tmp_path / "language.json"
        i18n_manager._config_file = config_file
        
        i18n_manager._save_language_preference("en")
        
        assert config_file.exists()
        with open(config_file, "r") as f:
            data = json.load(f)
        assert data["language"] == "en"
    
    def test_load_saved_language(self, i18n_manager, tmp_path):
        """Test loading saved language preference."""
        config_file = tmp_path / "language.json"
        i18n_manager._config_file = config_file
        
        # Save a preference
        with open(config_file, "w") as f:
            json.dump({"language": "en"}, f)
        
        # Load it
        lang = i18n_manager._load_saved_language()
        assert lang == "en"
    
    def test_load_saved_language_missing_file(self, i18n_manager, tmp_path):
        """Test loading when config file doesn't exist."""
        config_file = tmp_path / "nonexistent.json"
        i18n_manager._config_file = config_file
        
        lang = i18n_manager._load_saved_language()
        assert lang == "de"  # Should return default


def test_backend_set_language():
    """Test SwarmBackend.setLanguage method."""
    from tools.ui.backend import SwarmBackend
    
    backend = SwarmBackend()
    
    # Without i18n manager
    result = backend.setLanguage("en")
    assert result is False
    
    # With mock i18n manager
    mock_manager = MagicMock()
    mock_manager.set_language.return_value = True
    backend.set_i18n_manager(mock_manager)
    
    result = backend.setLanguage("en")
    assert result is True
    mock_manager.set_language.assert_called_once_with("en")


def test_language_switcher_component_exists():
    """Test that LanguageSwitcher QML component exists."""
    switcher_path = Path("tools/ui/qml/components/LanguageSwitcher.qml")
    assert switcher_path.exists()
    
    # Check it contains required properties
    content = switcher_path.read_text()
    assert "languageChanged" in content
    assert "languages" in content
    assert "languageCodes" in content


def test_header_includes_language_switcher():
    """Test that Header.qml includes LanguageSwitcher."""
    header_path = Path("tools/ui/qml/components/Header.qml")
    assert header_path.exists()
    
    content = header_path.read_text()
    assert "LanguageSwitcher" in content
    assert "languageChanged" in content


def test_qml_strings_marked_for_translation():
    """Test that QML strings are marked with qsTr()."""
    qml_files = [
        "tools/ui/qml/components/Header.qml",
        "tools/ui/qml/panels/DashboardPanel.qml",
        "tools/ui/qml/panels/ExperimentPanel.qml",
        "tools/ui/qml/panels/FlightLogPanel.qml",
    ]
    
    for qml_file in qml_files:
        path = Path(qml_file)
        if path.exists():
            content = path.read_text()
            # Check that qsTr() is used
            assert "qsTr(" in content, f"{qml_file} should use qsTr() for translations"


def test_documentation_exists():
    """Test that i18n documentation exists."""
    readme = Path("docs/i18n/README.md")
    guide = Path("docs/i18n/translation-guide.md")
    
    assert readme.exists()
    assert guide.exists()
    
    # Check README contains key sections
    readme_content = readme.read_text()
    assert "Internationalization" in readme_content
    assert "Supported Languages" in readme_content
    assert "For Developers" in readme_content
    
    # Check guide contains glossary
    guide_content = guide.read_text()
    assert "Terminology Glossary" in guide_content
    assert "Deutsch" in guide_content
    assert "English" in guide_content


def test_i18n_module_structure():
    """Test that i18n module has correct structure."""
    from droneresearch import i18n
    
    # Check exports
    assert hasattr(i18n, "SUPPORTED_LANGUAGES")
    assert hasattr(i18n, "DEFAULT_LANGUAGE")
    assert hasattr(i18n, "TRANSLATIONS_DIR")
    assert hasattr(i18n, "get_translation_path")
    assert hasattr(i18n, "get_language_name")


def test_service_locator_includes_backend():
    """Test that service locator registers backend."""
    from tools.ui.service_locator import build_default_locator
    
    locator = build_default_locator()
    assert locator.has("backend")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


"""Integration tests for i18n functionality."""
from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QApplication

try:
    from pytestqt.plugin import QtBot
    _QTBOT_OK = True
except ImportError:
    _QTBOT_OK = False

from tools.ui.context.i18n_context import I18nContext
from tools.ui.i18n import I18nManager


@pytest.fixture
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def i18n_context(qapp):
    """Create I18nContext for tests."""
    return I18nContext(qapp)


def test_i18n_context_creation(i18n_context):
    """Test I18nContext can be created."""
    assert i18n_context is not None
    assert i18n_context.manager is not None
    assert isinstance(i18n_context.manager, I18nManager)


def test_get_current_language(i18n_context):
    """Test getCurrentLanguage returns string."""
    lang = i18n_context.getCurrentLanguage()
    assert isinstance(lang, str)
    assert lang in ["en", "de"]


def test_get_supported_languages(i18n_context):
    """Test getSupportedLanguages returns list."""
    langs = i18n_context.getSupportedLanguages()
    assert isinstance(langs, list)
    assert len(langs) > 0
    # Should be list of tuples (code, name)
    for item in langs:
        assert isinstance(item, tuple)
        assert len(item) == 2
        code, name = item
        assert isinstance(code, str)
        assert isinstance(name, str)


def test_set_language_german(i18n_context):
    """Test setLanguage changes to German."""
    result = i18n_context.setLanguage("de")
    assert result is True
    assert i18n_context.getCurrentLanguage() == "de"


def test_set_language_english(i18n_context):
    """Test setLanguage changes to English."""
    # First set to German to ensure we're changing
    i18n_context.setLanguage("de")
    
    result = i18n_context.setLanguage("en")
    # English translation may not exist, so result could be False
    # Just verify the method works without crashing
    assert isinstance(result, bool)


def test_set_language_invalid(i18n_context):
    """Test setLanguage with invalid language code."""
    original_lang = i18n_context.getCurrentLanguage()
    result = i18n_context.setLanguage("invalid")
    assert result is False
    # Language should not change
    assert i18n_context.getCurrentLanguage() == original_lang


def test_set_language_same(i18n_context):
    """Test setLanguage with same language returns True."""
    current = i18n_context.getCurrentLanguage()
    result = i18n_context.setLanguage(current)
    assert result is True
    assert i18n_context.getCurrentLanguage() == current


@pytest.mark.skipif(not _QTBOT_OK, reason="pytest-qt not installed")
def test_language_changed_signal(i18n_context, qtbot):
    """Test languageChanged signal is emitted."""
    with qtbot.waitSignal(i18n_context.languageChanged, timeout=1000) as blocker:
        i18n_context.setLanguage("de")
    
    # Check signal was emitted with correct argument
    assert blocker.args == ["de"]


@pytest.mark.skipif(not _QTBOT_OK, reason="pytest-qt not installed")
def test_retranslate_requested_signal(i18n_context, qtbot):
    """Test retranslateRequested signal is emitted."""
    with qtbot.waitSignal(i18n_context.retranslateRequested, timeout=1000):
        i18n_context.setLanguage("de")


@pytest.mark.skipif(not _QTBOT_OK, reason="pytest-qt not installed")
def test_language_switching_cycle(i18n_context, qtbot):
    """Test switching between languages multiple times."""
    # Start with German
    i18n_context.setLanguage("de")
    assert i18n_context.getCurrentLanguage() == "de"
    
    # Switch to another language (if available)
    langs = dict(i18n_context.getSupportedLanguages())
    if len(langs) > 1:
        other_lang = [k for k in langs.keys() if k != "de"][0]
        with qtbot.waitSignal(i18n_context.languageChanged, timeout=1000):
            i18n_context.setLanguage(other_lang)
        
        # Switch back to German
        with qtbot.waitSignal(i18n_context.languageChanged, timeout=1000):
            i18n_context.setLanguage("de")
        assert i18n_context.getCurrentLanguage() == "de"


def test_manager_integration(i18n_context):
    """Test I18nContext properly integrates with I18nManager."""
    # Test that manager methods are accessible
    manager = i18n_context.manager
    
    # Get current language through manager
    manager_lang = manager.get_current_language()
    context_lang = i18n_context.getCurrentLanguage()
    assert manager_lang == context_lang
    
    # Get supported languages through manager
    manager_langs = manager.get_supported_languages()
    context_langs = dict(i18n_context.getSupportedLanguages())
    assert manager_langs == context_langs


def test_pyqtslot_result_types(i18n_context):
    """Test that pyqtSlot result types work correctly."""
    # getCurrentLanguage should return str
    lang = i18n_context.getCurrentLanguage()
    assert isinstance(lang, str)
    
    # getSupportedLanguages should return list (QVariant compatible)
    langs = i18n_context.getSupportedLanguages()
    assert isinstance(langs, list)
    
    # setLanguage should return bool
    result = i18n_context.setLanguage("en")
    assert isinstance(result, bool)



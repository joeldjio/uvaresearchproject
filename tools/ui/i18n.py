"""Internationalization utilities for UAV Research Platform UI.

This module provides Qt-based i18n support for the UI, including:
- QTranslator management
- Language switching
- Persistent language preferences

Usage:
    from tools.ui.i18n import I18nManager
    
    # Initialize i18n
    manager = I18nManager(app)
    
    # Load saved language or default
    manager.load_language()
    
    # Switch language
    manager.set_language("en")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QCoreApplication, QLocale, QTranslator
from PyQt6.QtWidgets import QApplication

from droneresearch.i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    get_translation_path,
)

__all__ = ["I18nManager"]


class I18nManager:
    """Manages internationalization for the Qt application.
    
    Handles loading, switching, and persisting language preferences.
    
    Attributes:
        app: Qt application instance
        translator: Current QTranslator instance
        current_language: Currently active language code
    """
    
    def __init__(self, app: QApplication):
        """Initialize the i18n manager.
        
        Args:
            app: Qt application instance
        """
        self.app = app
        self.translator: Optional[QTranslator] = None
        self.current_language: str = DEFAULT_LANGUAGE
        self._config_file = Path.home() / ".uavresearch" / "language.json"
        
        # Ensure config directory exists
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
    
    def load_language(self, language_code: Optional[str] = None) -> bool:
        """Load a language translation.
        
        If no language code is provided, loads the saved preference or default.
        
        Args:
            language_code: Language code to load (e.g., "de", "en")
            
        Returns:
            True if translation loaded successfully, False otherwise
        """
        if language_code is None:
            language_code = self._load_saved_language()
        
        if language_code not in SUPPORTED_LANGUAGES:
            language_code = DEFAULT_LANGUAGE
        
        # Get translation file path
        qm_file = get_translation_path(language_code)
        if qm_file is None or not qm_file.exists():
            # No translation file, use source language (German)
            if language_code == "de":
                self.current_language = language_code
                return True
            return False
        
        # Remove old translator if exists
        if self.translator is not None:
            self.app.removeTranslator(self.translator)
        
        # Load new translator
        self.translator = QTranslator()
        if self.translator.load(str(qm_file)):
            self.app.installTranslator(self.translator)
            self.current_language = language_code
            
            # Set Qt locale
            locale_map = {
                "de": QLocale.Language.German,
                "en": QLocale.Language.English,
            }
            if language_code in locale_map:
                QLocale.setDefault(QLocale(locale_map[language_code]))
            
            return True
        
        return False
    
    def set_language(self, language_code: str) -> bool:
        """Switch to a different language.
        
        Args:
            language_code: Language code to switch to (e.g., "de", "en")
            
        Returns:
            True if language switched successfully, False otherwise
        """
        if language_code == self.current_language:
            return True
        
        if self.load_language(language_code):
            self._save_language_preference(language_code)
            
            # Emit language changed event
            # Note: QML engine will need to be reloaded for changes to take effect
            return True
        
        return False
    
    def get_current_language(self) -> str:
        """Get the currently active language code.
        
        Returns:
            Current language code (e.g., "de", "en")
        """
        return self.current_language
    
    def get_supported_languages(self) -> dict[str, str]:
        """Get all supported languages.
        
        Returns:
            Dictionary mapping language codes to display names
        """
        return SUPPORTED_LANGUAGES.copy()
    
    def _load_saved_language(self) -> str:
        """Load saved language preference from config file.
        
        Returns:
            Saved language code, or default if not found
        """
        if not self._config_file.exists():
            return DEFAULT_LANGUAGE
        
        try:
            with open(self._config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("language", DEFAULT_LANGUAGE)
        except (json.JSONDecodeError, OSError):
            return DEFAULT_LANGUAGE
    
    def _save_language_preference(self, language_code: str) -> None:
        """Save language preference to config file.
        
        Args:
            language_code: Language code to save
        """
        try:
            config = {"language": language_code}
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except OSError:
            # Silently fail if we can't save preferences
            pass
    
    def retranslate_ui(self) -> None:
        """Trigger UI retranslation.
        
        This should be called after switching languages to update all UI strings.
        Note: For QML, the engine typically needs to be reloaded.
        """
        # For Qt Widgets
        QCoreApplication.processEvents()
        
        # For QML, emit a signal that the QML engine can listen to
        # The actual retranslation happens when QML components call qsTr() again


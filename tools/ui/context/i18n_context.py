"""
I18n Context for Qt/QML language switching.

Provides a QML-accessible interface for changing the application language
and triggering UI retranslation.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QApplication

from tools.ui.i18n import I18nManager


class I18nContext(QObject):
    """QML-accessible i18n manager.
    
    Signals:
        languageChanged: Emitted when language is changed (language_code: str)
        retranslateRequested: Emitted to trigger QML retranslation
    """
    
    languageChanged = pyqtSignal(str)  # language_code
    retranslateRequested = pyqtSignal()
    
    def __init__(self, app: QApplication, parent=None):
        super().__init__(parent)
        self.manager = I18nManager(app)
        
        # Load saved language preference
        self.manager.load_language()
    
    @pyqtSlot(str, result="bool")
    def setLanguage(self, language_code: str) -> bool:
        """Switch to a different language.
        
        Args:
            language_code: Language code (e.g., "de", "en")
            
        Returns:
            True if language switched successfully
        """
        if self.manager.set_language(language_code):
            self.languageChanged.emit(language_code)
            self.retranslateRequested.emit()
            return True
        return False
    
    @pyqtSlot(result=str)
    def getCurrentLanguage(self) -> str:
        """Get currently active language code.
        
        Returns:
            Current language code (e.g., "de", "en")
        """
        return self.manager.get_current_language()
    
    @pyqtSlot(result="QVariant")
    def getSupportedLanguages(self) -> list:
        """Get all supported languages.
        
        Returns:
            List of tuples (language_code, display_name)
        """
        return list(self.manager.get_supported_languages().items())


"""Internationalization support for UAV Research Platform.

This module provides i18n infrastructure for the UAV Research Platform,
supporting multiple languages with Qt Linguist integration.

Supported Languages:
    - German (de_DE)
    - English (en_US)

Usage:
    from droneresearch.i18n import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
    
    # Get available languages
    languages = SUPPORTED_LANGUAGES
    
    # Get translation file path
    from droneresearch.i18n import get_translation_path
    qm_file = get_translation_path("de_DE")
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

__all__ = [
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
    "TRANSLATIONS_DIR",
    "get_translation_path",
    "get_language_name",
]

# Supported languages with their display names
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "de": "Deutsch",
    "en": "English",
}

# Default language (English)
DEFAULT_LANGUAGE: str = "en"

# Translation files directory
TRANSLATIONS_DIR: Path = Path(__file__).parent / "translations"


def get_translation_path(language_code: str) -> Path | None:
    """Get the path to a compiled translation file (.qm).
    
    Args:
        language_code: Language code (e.g., "de", "en")
        
    Returns:
        Path to .qm file if it exists, None otherwise
        
    Example:
        >>> path = get_translation_path("de")
        >>> if path and path.exists():
        ...     print(f"Translation file: {path}")
    """
    if language_code not in SUPPORTED_LANGUAGES:
        return None
    
    # Map short codes to full locale codes
    locale_map = {
        "de": "de_DE",
        "en": "en_US",
    }
    
    locale = locale_map.get(language_code, language_code)
    qm_file = TRANSLATIONS_DIR / f"{locale}.qm"
    
    return qm_file if qm_file.exists() else None


def get_language_name(language_code: str) -> str:
    """Get the display name for a language code.
    
    Args:
        language_code: Language code (e.g., "de", "en")
        
    Returns:
        Display name of the language, or the code itself if not found
        
    Example:
        >>> get_language_name("de")
        'Deutsch'
        >>> get_language_name("en")
        'English'
    """
    return SUPPORTED_LANGUAGES.get(language_code, language_code)


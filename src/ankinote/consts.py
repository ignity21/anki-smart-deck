from enum import StrEnum


class Language(StrEnum):
    """Supported languages for translations and definitions."""

    ENGLISH = "English"
    CHINESE_S = "Chinese(Simplified)"
    CHINESE_T = "Chinese(Traditional)"
    JAPANESE = "Japanese"
    FRENCH = "French"
    SPANISH = "Spanish"
    GERMAN = "German"
    KOREAN = "Korean"
    OTHER = "other"

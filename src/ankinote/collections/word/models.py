"""
Vocabulary card data models for Anki.

Two-stage architecture:
1. WordModel: Structured data returned by AI (with validation)
2. WordNoteType: Anki note fields (all strings, ready for HTML rendering)
"""

from dataclasses import dataclass
from enum import StrEnum
from pydantic import BaseModel


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


# ============================================================================
# AI Generation Models (structured data with validation)
# ============================================================================


class Definition(BaseModel):
    """A single definition in a specific language"""

    target_lang: str
    native_lang: str
    is_visualizable: bool  # whether the definition is easily visualizable


class Example(BaseModel):
    """Example sentence with translation"""

    sentence: str
    translation: str
    highlights: list[
        str
    ]  # words/phrases to highlight: collocations, idioms, phrasal verbs, inflections


class WordModel(BaseModel):
    """
    Structured vocabulary data model for AI generation.
    Includes validation and type checking via Pydantic.
    """

    word: str
    part_of_speech: str  # e.g., "n.", "vt.", "adj."
    pronunciation: (
        str | None
    )  # IPA notation, e.g., "/wɜːrd/" (US pronunciation by default)
    syllables: list[str]  # syllable breakdown, e.g., ["ex", "am", "ple"]
    difficulty: str  # e.g., "beginner", "intermediate", or CEFR levels
    definitions: list[Definition]
    synonyms: list[str]  # word or phrase synonyms
    examples: list[Example]
    etymology: str | None = None  # word origin to enhance learning interest
    collocations: list[str]  # common collocations, phrasal verbs, idioms
    notes: list[
        str
    ]  # irregular inflections, UK pronunciation/spelling differences, related terms, etc.


# ============================================================================
# Anki Note Type (all fields are strings for Anki compatibility)
# ============================================================================


@dataclass
class WordNoteType:
    """
    Anki note type with all fields as strings.
    Complex data (lists, dicts) should be converted to HTML before storing.
    """

    word: str
    part_of_speech: str
    pronunciation: str
    pron_audio: str
    syllables: str
    difficulty: str
    definitions: str
    synonyms: str
    examples: str
    etymology: str
    collocations: str
    notes: str
    user_notes: str

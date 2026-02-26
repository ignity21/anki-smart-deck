"""
Vocabulary card data models for Anki.

Two-stage architecture:
1. WordModel: Structured data returned by AI (with validation)
2. WordNoteType: Anki note fields (all strings, ready for HTML rendering)
"""

from dataclasses import dataclass
from enum import StrEnum
from pydantic import BaseModel


class Lang(StrEnum):
    """ISO 639 language codes"""

    ENGLISH = "en"
    S_CHINESE = "zh-CN"
    T_CHINESE = "zh-TW"
    JAPANESE = "ja"
    FRENCH = "fr"
    SPANISH = "es"
    GERMAN = "de"
    KOREAN = "ko"
    OTHER = "other"


# ============================================================================
# AI Generation Models (structured data with validation)
# ============================================================================


class Definition(BaseModel):
    """A single definition in a specific language"""

    target_lang: str
    native_lang: str
    is_visualizable: (
        bool  # whether the definition can be easily visualized with an image
    )


class Example(BaseModel):
    """Example sentence with translation"""

    highlights: list[str] | None = (
        None  # words/phrases to highlight: collocations, idioms, phrasal verbs, inflections
    )
    sentence: str
    translation: str


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
    notes: str
    images: str
    user_notes: str

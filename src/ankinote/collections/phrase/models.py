"""Phrase / idiom / sentence card data models for Anki."""

from dataclasses import dataclass
from pydantic import BaseModel

from ankinote.collections.word.models import Language


class Definition(BaseModel):
    """A single definition in a specific language."""

    target_lang: str
    native_lang: str


class Example(BaseModel):
    """Example sentence with translation.

    For phrases, we highlight only the phrase itself.
    """

    sentence: str
    translation: str
    highlight: str  # must equal the phrase as it appears in the sentence


class PhraseModel(BaseModel):
    """Structured phrase/idiom/sentence model for AI generation."""

    phrase: str
    difficulty: str  # e.g., "A2", "B1", "N3"
    definitions: list[Definition]
    examples: list[Example]
    notes: list[str]


@dataclass
class PhraseNoteType:
    """Anki note type for phrases (all string fields)."""

    phrase: str
    pron_audio: str
    difficulty: str
    definitions: str
    examples: str
    notes: str
    user_notes: str

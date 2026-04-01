"""Sentence card data models for Anki."""

from dataclasses import dataclass

from pydantic import BaseModel


class SentenceModel(BaseModel):
    """Structured sentence model for AI generation.

    The sentence collection is for translation-style cards:
    front shows the native language sentence, back shows the target language.
    """

    target_sentence: str
    native_sentence: str
    notes: list[str] = []
    phrases: dict[str, str] = {}


@dataclass
class SentenceNoteType:
    """Anki note type for sentence cards (all string fields)."""

    target_sentence: str
    native_sentence: str
    pron_audio: str
    notes: str
    phrases: str
    user_notes: str

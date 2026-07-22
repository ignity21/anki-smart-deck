"""Sentence card data models for Anki."""

from dataclasses import dataclass

from pydantic import BaseModel


class PhraseModel(BaseModel):
    """Structured phrase model for AI generation.

    The phrase collection is for translation-style cards:
    front shows the native language phrase, back shows the target language.
    """

    phrase: str
    translation: str
    example: str


class SentenceModel(BaseModel):
    """Structured sentence model for AI generation.

    The sentence collection is for translation-style cards:
    front shows the native language sentence, back shows the target language.
    """

    target_sentence: str
    native_sentence: str
    notes: list[str] = []
    phrases: list[PhraseModel] = []


@dataclass
class SentenceNoteType:
    """Anki note type for sentence cards (all string fields)."""

    target_sentence: str
    native_sentence: str
    pron_audio: str
    notes: str
    phrases: str
    user_notes: str

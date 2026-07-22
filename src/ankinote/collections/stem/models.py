"""STEM card data models for Anki."""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel


class CardType(StrEnum):
    CONCEPT = "concept"
    FORMULA = "formula"
    PROCEDURE = "procedure"


class StemModel(BaseModel):
    """Structured STEM model for AI generation.

    The STEM collection covers concept definitions, formulas/theorems,
    and step-by-step procedures across Math, Physics, CS, and Engineering.
    card_type controls which Anki template is rendered.
    back_brief is a concise answer (≤2 sentences, no derivation).
    back_detail is the full explanation, derivation, or worked steps.
    Supports LaTeX in all text fields via MathJax.
    """

    card_type: CardType
    front: str
    back_brief: str
    back_detail: str


@dataclass
class StemNoteType:
    """Anki note type for STEM cards (all string fields)."""

    card_type: str  # "concept" | "formula" | "procedure"
    front: str
    back_brief: str
    back_detail: str

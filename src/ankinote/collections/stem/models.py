"""STEM card data models for Anki."""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel


class CardType(StrEnum):
    CONCEPT = "concept"
    FORMULA = "formula"
    PROCEDURE = "procedure"


class Variable(BaseModel):
    """A single symbol definition for formula cards."""

    symbol: str
    description: str


class StemModel(BaseModel):
    """Structured STEM card model for AI generation.

    The STEM collection covers concept definitions, formulas/theorems,
    and step-by-step procedures across Math, Physics, CS, and Engineering.
    card_type controls which Anki template is rendered.
    back_brief is a concise answer (<=2 sentences, no derivation).
    back_detail is the full explanation, derivation, or worked steps.
    Supports LaTeX in all text fields via MathJax.

    Structured fields are optional and rendered into the stored back_detail
    HTML by the collection:
    - latex: the core formula expression, shown as a centered block
      (formula cards).
    - variables: symbol definitions, shown as a table (formula cards).
    - steps: ordered procedure steps, shown as a numbered list (procedure
      cards).

    If the AI determines that a diagram would aid understanding (e.g. graphs,
    geometry, flowcharts), it should set image_description. The system will
    generate an image from that description and embed it in back_detail.
    """

    card_type: CardType
    front: str
    back_brief: str
    back_detail: str
    tags: list[str]
    image_description: str | None = None
    latex: str | None = None
    variables: list[Variable] | None = None
    steps: list[str] | None = None


@dataclass
class StemNoteType:
    """Anki note type for STEM cards (all string fields)."""

    card_type: str  # "concept" | "formula" | "procedure"
    front: str
    back_brief: str
    back_detail: str
    tags: str

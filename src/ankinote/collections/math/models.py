"""
Math/Science knowledge card data models for Anki.

Two-stage architecture:
1. MathModel: Structured data returned by AI (with validation)
2. MathNoteType: Anki note fields (all strings, ready for HTML rendering)
"""

from dataclasses import dataclass

from pydantic import BaseModel

# ============================================================================
# AI Generation Models (structured data with validation)
# ============================================================================


class Example(BaseModel):
    """Example problem or application with solution"""

    problem: str  # The example problem or question
    solution: str  # Step-by-step solution or explanation
    is_visualizable: bool  # whether the example needs a diagram


class MathModel(BaseModel):
    """
    Structured math/science knowledge data model for AI generation.
    Includes validation and type checking via Pydantic.
    """

    front: str  # The original question/concept from user
    explanation: str  # Main explanation with LaTeX formulas
    key_points: list[str]  # Important points to remember
    examples: list[Example]  # Worked examples
    related_concepts: list[str]  # Related topics for further study
    difficulty: str  # e.g., "elementary", "intermediate", "advanced"
    tags: list[str]  # Auto-generated tags for organization


# ============================================================================
# Anki Note Type (all fields are strings for Anki compatibility)
# ============================================================================


@dataclass
class MathNoteType:
    """
    Anki note type with all fields as strings.
    Complex data (lists, dicts) should be converted to HTML before storing.
    """

    front: str
    back: str
    examples: str
    related_concepts: str
    difficulty: str
    tags: str

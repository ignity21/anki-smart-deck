"""Tests for the STEM collection: structured schema and note building."""

import json
from typing import cast

import pytest

from ankinote.collections.stem.collection import StemCollection
from ankinote.collections.stem.generator import StemGenerator
from ankinote.collections.stem.models import StemModel, Variable
from ankinote.services.ai import TextGenerationService
from ankinote.services.anki import AnkiCollectionClient


def _make_collection() -> StemCollection:
    """Build a StemCollection backed by a minimal fake Anki client."""

    class FakeAnkiClient:
        pass

    return StemCollection(
        cast(AnkiCollectionClient, FakeAnkiClient()),
        text_model_id="stem-model",
        text_service=cast(TextGenerationService, object()),
    )


def test_stem_model_validates_without_structured_fields():
    """Old-style payloads without latex/variables/steps still validate."""
    model = StemModel.model_validate(
        {
            "card_type": "concept",
            "front": "What is entropy?",
            "back_brief": "A measure of disorder.",
            "back_detail": "Entropy quantifies uncertainty.",
            "tags": ["Physics"],
        }
    )
    assert model.latex is None
    assert model.variables is None
    assert model.steps is None


def test_stem_model_validates_with_structured_fields():
    model = StemModel.model_validate(
        {
            "card_type": "formula",
            "front": "Newton's second law",
            "back_brief": "$F = ma$: acceleration follows force.",
            "back_detail": "Valid in inertial frames.",
            "tags": ["Physics"],
            "latex": "F = m \\cdot a",
            "variables": [
                {"symbol": "F", "description": "Net force (N)"},
                {"symbol": "m", "description": "Mass (kg)"},
            ],
            "steps": ["Step one.", "Step two."],
        }
    )
    assert model.latex == "F = m \\cdot a"
    assert model.variables is not None
    assert model.variables[0] == Variable(symbol="F", description="Net force (N)")
    assert model.steps == ["Step one.", "Step two."]


def test_build_note_data_renders_formula_block_and_symbol_table():
    collection = _make_collection()
    model = StemModel.model_validate(
        {
            "card_type": "formula",
            "front": "Newton's second law",
            "back_brief": "$F = ma$.",
            "back_detail": "Valid in inertial frames.",
            "tags": ["Physics"],
            "latex": "F = m \\cdot a",
            "variables": [
                {"symbol": "F", "description": "Net force (N)"},
                {"symbol": "m", "description": "Mass (kg)"},
            ],
        }
    )

    fields = collection._build_note_data(model, image_filename=None)

    assert (
        "<div class='formula-block'>\\[F = m \\cdot a\\]</div>" in fields["back_detail"]
    )
    assert "<table class='symbol-table'>" in fields["back_detail"]
    assert "\\(F\\)</td><td>Net force (N)" in fields["back_detail"]
    assert fields["back_detail"].endswith("<p>Valid in inertial frames.</p>") or (
        "Valid in inertial frames." in fields["back_detail"]
    )


def test_build_note_data_renders_step_list():
    collection = _make_collection()
    model = StemModel.model_validate(
        {
            "card_type": "procedure",
            "front": "How to invert a matrix?",
            "back_brief": "1. Check square. 2. Determinant. 3. Row-reduce.",
            "back_detail": "Row-reduction costs O(n^3).",
            "tags": ["Math"],
            "steps": ["Check square.", "Determinant nonzero.", "Row-reduce."],
        }
    )

    fields = collection._build_note_data(model, image_filename=None)

    assert "<ol class='step-list'>" in fields["back_detail"]
    assert "<li>Check square.</li>" in fields["back_detail"]
    assert fields["back_detail"].index("step-list") < fields["back_detail"].index(
        "Row-reduction costs"
    )


def test_build_note_data_concept_card_unchanged():
    """Concept cards without structured fields keep plain back_detail."""
    collection = _make_collection()
    model = StemModel.model_validate(
        {
            "card_type": "concept",
            "front": "What is entropy?",
            "back_brief": "A measure of disorder.",
            "back_detail": "Entropy quantifies uncertainty.",
            "tags": ["Physics"],
        }
    )

    fields = collection._build_note_data(model, image_filename=None)

    assert fields["back_detail"] == "Entropy quantifies uncertainty."
    assert fields["card_type"] == "concept"


@pytest.mark.asyncio
async def test_generator_parses_structured_fields_from_ai_response():
    """End-to-end mocked generation with the new structured keys."""
    payload = json.dumps(
        {
            "card_type": "formula",
            "front": "Quadratic formula",
            "back_brief": "$x = \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}$ solves $ax^2+bx+c=0$.",
            "back_detail": "Derived by completing the square.",
            "latex": "x = \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}",
            "variables": [{"symbol": "a", "description": "Leading coefficient"}],
            "tags": ["Math", "Algebra"],
            "image_description": None,
        }
    )

    class FakeTextService:
        calls: list[dict[str, object]] = []

        async def generate_text(self, **kwargs):
            type(self).calls.append(kwargs)
            return payload

    generator = StemGenerator(
        text_service=cast(TextGenerationService, FakeTextService()),
        text_model_id="stem-model",
    )
    model = await generator.generate("quadratic formula")

    assert model.card_type.value == "formula"
    assert model.latex is not None and "frac" in model.latex
    assert model.variables is not None and len(model.variables) == 1

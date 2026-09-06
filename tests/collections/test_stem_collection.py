"""Tests for the STEM collection: structured schema and note building."""

import json
from types import SimpleNamespace
from typing import ClassVar, cast

import pytest

from ankinote.collections.stem.collection import StemCollection
from ankinote.collections.stem.generator import StemGenerator
from ankinote.collections.stem.models import StemModel, Variable
from ankinote.services.ai import (
    ImageGenerationService,
    TextGenerationService,
)
from ankinote.services.anki import AnkiCollectionClient


def _make_collection() -> StemCollection:
    """Build a StemCollection backed by a minimal fake Anki client."""

    class FakeAnkiClient:
        pass

    return StemCollection(
        cast(AnkiCollectionClient, FakeAnkiClient()),
        text_model="stem-model",
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


def test_stem_model_validates_example_card_type():
    """The example card type reuses the steps field for the solution."""
    model = StemModel.model_validate(
        {
            "card_type": "example",
            "front": "Solve for x: 2x + 3 = 11",
            "back_brief": "x = 4",
            "back_detail": "Isolate x by undoing addition then multiplication.",
            "tags": ["Math", "Algebra"],
            "steps": ["Subtract 3 from both sides: 2x = 8.", "Divide by 2: x = 4."],
        }
    )
    assert model.card_type.value == "example"
    assert model.steps is not None and len(model.steps) == 2


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


def test_build_note_data_renders_example_card_with_steps():
    collection = _make_collection()
    model = StemModel.model_validate(
        {
            "card_type": "example",
            "front": "Solve for x: 2x + 3 = 11",
            "back_brief": "x = 4",
            "back_detail": "Standard linear equation.",
            "tags": ["Math", "Algebra"],
            "steps": ["Subtract 3 from both sides: 2x = 8.", "Divide by 2: x = 4."],
        }
    )

    fields = collection._build_note_data(model, image_filename=None)

    assert fields["card_type"] == "example"
    assert "<ol class='step-list'>" in fields["back_detail"]
    assert "<li>Divide by 2: x = 4.</li>" in fields["back_detail"]


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
        calls: ClassVar[list[dict[str, object]]] = []

        async def generate_text(self, **kwargs):
            type(self).calls.append(kwargs)
            return payload

    generator = StemGenerator(
        text_service=cast(TextGenerationService, FakeTextService()),
        text_model="stem-model",
    )
    model = await generator.generate("quadratic formula")

    assert model.card_type.value == "formula"
    assert model.latex is not None and "frac" in model.latex
    assert model.variables is not None and len(model.variables) == 1


@pytest.mark.asyncio
async def test_generator_attaches_reference_image_to_user_message():
    """A reference image is sent as a vision content part, not lost as text."""
    payload = _CONCEPT_PAYLOAD

    class FakeTextService:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        async def generate_text(self, **kwargs):
            self.calls.append(kwargs)
            return payload

    text_service = FakeTextService()
    generator = StemGenerator(
        text_service=cast(TextGenerationService, text_service),
        text_model="stem-model",
    )

    await generator.generate(
        "solve the problem in the photo",
        reference_image=b"fake-png-bytes",
        reference_image_mime="image/png",
    )

    user_message = text_service.calls[0]["messages"][1]
    assert user_message["role"] == "user"
    content = user_message["content"]
    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


@pytest.mark.asyncio
async def test_generator_without_reference_image_sends_plain_text():
    class FakeTextService:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        async def generate_text(self, **kwargs):
            self.calls.append(kwargs)
            return _CONCEPT_PAYLOAD

    text_service = FakeTextService()
    generator = StemGenerator(
        text_service=cast(TextGenerationService, text_service),
        text_model="stem-model",
    )

    await generator.generate("what is entropy")

    user_message = text_service.calls[0]["messages"][1]
    assert isinstance(user_message["content"], str)


# -- generate_model / add_note split ---------------------------------------------


class _RecordingTextService:
    def __init__(self, payload: str) -> None:
        self._payload = payload
        self.calls: list[dict[str, object]] = []

    async def generate_text(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        return self._payload


class _RecordingImageService:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def generate_image(self, *, prompt: str) -> bytes:
        self.prompts.append(prompt)
        return b"generated-bytes"


def _recording_anki_client() -> SimpleNamespace:
    stored: list[tuple[str, bytes]] = []
    added: list[dict[str, object]] = []

    async def store_file(filename: str, data: bytes) -> str:
        stored.append((filename, data))
        return filename

    async def find(*, deck_name: str, unique_fields: dict[str, str]) -> int | None:
        return None

    async def add(**kwargs: object) -> int:
        added.append(kwargs)
        return 42

    return SimpleNamespace(
        media=SimpleNamespace(store_file=store_file),
        notes=SimpleNamespace(find=find, add=add),
        _stored=stored,
        _added=added,
    )


_CONCEPT_PAYLOAD = json.dumps(
    {
        "card_type": "concept",
        "front": "What is entropy?",
        "back_brief": "A measure of disorder.",
        "back_detail": "Entropy quantifies uncertainty.",
        "tags": ["Physics"],
    }
)


@pytest.mark.asyncio
async def test_generate_model_threads_reasoning_effort():
    text_service = _RecordingTextService(_CONCEPT_PAYLOAD)
    collection = StemCollection(
        cast(AnkiCollectionClient, object()),
        text_model="stem-model",
        text_service=cast(TextGenerationService, text_service),
        reasoning_effort="high",
    )

    model = await collection.generate_model("entropy")

    assert model.card_type.value == "concept"
    assert text_service.calls[0]["reasoning_effort"] == "high"


@pytest.mark.asyncio
async def test_generate_model_threads_reference_image():
    text_service = _RecordingTextService(_CONCEPT_PAYLOAD)
    collection = StemCollection(
        cast(AnkiCollectionClient, object()),
        text_model="stem-model",
        text_service=cast(TextGenerationService, text_service),
    )

    await collection.generate_model(
        "solve this", reference_image=b"bytes", reference_image_mime="image/jpeg"
    )

    user_message = text_service.calls[0]["messages"][1]
    content = user_message["content"]
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


@pytest.mark.asyncio
async def test_add_note_stores_supplied_image_without_calling_service():
    anki = _recording_anki_client()
    image_service = _RecordingImageService()
    collection = StemCollection(
        cast(AnkiCollectionClient, anki),
        text_model="stem-model",
        text_service=cast(TextGenerationService, object()),
        image_service=cast(ImageGenerationService, image_service),
    )
    model = StemModel.model_validate(json.loads(_CONCEPT_PAYLOAD))

    note_id = await collection.add_note(model, topic="entropy", image_bytes=b"png")

    assert note_id == 42
    assert len(anki._stored) == 1
    name, data = anki._stored[0]
    assert name.startswith("stem_") and name.endswith(".png") and data == b"png"
    assert image_service.prompts == []
    fields = anki._added[0]["fields"]
    assert "<img src='" in fields["back_detail"]


@pytest.mark.asyncio
async def test_add_note_generates_image_from_description():
    anki = _recording_anki_client()
    image_service = _RecordingImageService()
    collection = StemCollection(
        cast(AnkiCollectionClient, anki),
        text_model="stem-model",
        text_service=cast(TextGenerationService, object()),
        image_service=cast(ImageGenerationService, image_service),
    )
    model = StemModel.model_validate(
        {**json.loads(_CONCEPT_PAYLOAD), "image_description": "a diagram"}
    )

    await collection.add_note(model, topic="entropy")

    assert image_service.prompts and "a diagram" in image_service.prompts[0]
    assert anki._stored and anki._stored[0][1] == b"generated-bytes"


@pytest.mark.asyncio
async def test_generate_and_add_note_composes_generate_and_add():
    anki = _recording_anki_client()
    text_service = _RecordingTextService(_CONCEPT_PAYLOAD)
    collection = StemCollection(
        cast(AnkiCollectionClient, anki),
        text_model="stem-model",
        text_service=cast(TextGenerationService, text_service),
    )

    note_id = await collection.generate_and_add_note("entropy", tags=["Extra"])

    assert note_id == 42
    assert "Extra" in anki._added[0]["tags"]
    assert "AI-generated" in anki._added[0]["tags"]

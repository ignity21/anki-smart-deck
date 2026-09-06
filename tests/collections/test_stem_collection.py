"""STEM type isolation, rendering, generation, and media contracts."""

import json
import re
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from ankinote.collections.stem.collection import StemCollection
from ankinote.collections.stem.generator import StemGenerator
from ankinote.collections.stem.models import (
    CARD_ADAPTER,
    NOTE_FIELDS,
    CardType,
    ConceptModel,
    ExampleModel,
    FormulaModel,
    ProcedureModel,
)
from ankinote.collections.stem.templates import load_template
from ankinote.services.ai import (
    GenerationTimeoutError,
    ImageGenerationService,
    TextGenerationService,
)
from ankinote.services.anki import AnkiCollectionClient

CARDS = [
    ConceptModel(
        front="Entropy?",
        back_brief="Uncertainty.",
        back_detail="An explanation.",
        tags=["Physics"],
    ),
    FormulaModel(
        front="Newton's law?",
        latex="F=ma",
        meaning="Force.",
        variables=[{"symbol": "F", "description": "Force"}],
        conditions="Inertial frame.",
        derivation="",
        tags=["Physics"],
    ),
    ProcedureModel(
        front="Solve a linear equation?",
        summary="Isolate x.",
        steps=["Subtract constant.", "Divide coefficient."],
        conditions="Nonzero coefficient.",
        tags=["Math"],
    ),
    ExampleModel(
        front="Solve 2x+3=11.",
        answer="x=4",
        steps=["Subtract 3.", "Divide by 2."],
        explanation="Inverse operations.",
        tags=["Math"],
    ),
]


def _make_collection(**kwargs) -> StemCollection:
    return StemCollection(
        cast(AnkiCollectionClient, object()),
        text_model="test",
        text_service=cast(TextGenerationService, object()),
        **kwargs,
    )


@pytest.mark.parametrize("model", CARDS)
def test_storage_fields_and_templates_are_type_specific(model):
    fields = _make_collection()._build_note_data(model, "diagram.png")
    assert list(fields) == list(NOTE_FIELDS[model.card_type])
    assert next(iter(fields)) == "front"
    assert "card_type" not in fields
    assert "tags" not in fields
    assert all(isinstance(value, str) for value in fields.values())
    assert "diagram.png" in fields["image"]
    for side in ("front", "back"):
        template = load_template(f"{model.card_type}/{side}.html")
        refs = set(re.findall(r"{{[#/^]?([^}]+)}}", template))
        assert refs <= set(fields) | {"FrontSide", "Tags"}
    assert "{{card_type}}" not in load_template(f"{model.card_type}/front.html")


def test_structured_content_stays_in_separate_fields():
    formula = _make_collection()._build_note_data(CARDS[1], None)
    assert formula["latex"] == "F=ma"
    assert "symbol-table" in formula["variables"]
    assert formula["conditions"] == "Inertial frame."
    assert "back_detail" not in formula
    example = _make_collection()._build_note_data(CARDS[3], None)
    assert "step-list" in example["steps"]
    assert example["answer"] == "x=4"
    assert "Subtract" not in example["explanation"]


def test_incompatible_fields_and_incomplete_solutions_are_rejected():
    with pytest.raises(ValidationError):
        ConceptModel.model_validate({**CARDS[0].model_dump(), "steps": ["irrelevant"]})
    with pytest.raises(ValidationError):
        ExampleModel.model_validate({**CARDS[3].model_dump(), "steps": []})
    with pytest.raises(ValidationError):
        FormulaModel.model_validate({**CARDS[1].model_dump(), "latex": ""})


@pytest.mark.parametrize("model", CARDS)
async def test_explicit_type_uses_one_call_and_its_own_schema(model):
    service = SimpleNamespace(
        generate_text=AsyncMock(return_value=model.model_dump_json())
    )
    generator = StemGenerator(cast(TextGenerationService, service), "test")
    result = await generator.generate(model.front, card_type=model.card_type)
    assert type(result) is type(model)
    service.generate_text.assert_awaited_once()
    system = service.generate_text.await_args.kwargs["messages"][0]["content"]
    assert type(model).__name__ in system
    assert (
        f"Generate a {model.card_type}" in system or model.card_type == CardType.EXAMPLE
    )


async def test_auto_classifies_then_generates_with_reference_in_both_calls():
    service = SimpleNamespace(
        generate_text=AsyncMock(
            side_effect=[
                '{"card_type":"example"}',
                CARDS[3].model_dump_json(),
            ]
        )
    )
    generator = StemGenerator(cast(TextGenerationService, service), "test")
    result = await generator.generate("Solve this", reference_image=b"photo")
    assert isinstance(result, ExampleModel)
    assert service.generate_text.await_count == 2
    for call in service.generate_text.await_args_list:
        parts = call.kwargs["messages"][1]["content"]
        assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert (
        "ExampleModel"
        in service.generate_text.await_args_list[1].kwargs["messages"][0]["content"]
    )


async def test_explicit_type_rejects_wrong_type_response():
    service = SimpleNamespace(
        generate_text=AsyncMock(return_value=CARDS[0].model_dump_json())
    )
    generator = StemGenerator(cast(TextGenerationService, service), "test")
    with pytest.raises(ValidationError):
        await generator.generate("topic", card_type=CardType.EXAMPLE)


async def test_same_front_is_scoped_to_note_type_for_insert_and_update():
    notes = SimpleNamespace(
        find=AsyncMock(side_effect=[None, 17]),
        add=AsyncMock(return_value=42),
        update_fields=AsyncMock(),
        update_tags=AsyncMock(),
    )
    collection = StemCollection(
        cast(AnkiCollectionClient, SimpleNamespace(notes=notes)),
        text_model="test",
        text_service=cast(TextGenerationService, object()),
    )
    concept = CARDS[0]
    example = CARDS[3].model_copy(update={"front": concept.front})
    await collection.add_note(concept)
    await collection.add_note(example)
    assert notes.find.await_args_list[0].kwargs["model_name"] == "AINote STEM Concept"
    assert notes.find.await_args_list[1].kwargs["model_name"] == "AINote STEM Example"
    assert notes.add.await_args.kwargs["model_name"] == "AINote STEM Concept"
    assert notes.update_fields.await_args.args[0] == 17
    assert "answer" in notes.update_fields.await_args.args[1]


async def test_selected_collection_rejects_other_type_before_writing():
    with pytest.raises(ValueError, match="does not match"):
        await _make_collection(card_type=CardType.CONCEPT).add_note(CARDS[3])


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

    async def find(
        *, deck_name: str, unique_fields: dict[str, str], model_name: str
    ) -> int | None:
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
    model = CARD_ADAPTER.validate_python(json.loads(_CONCEPT_PAYLOAD))

    note_id = await collection.add_note(model, topic="entropy", image_bytes=b"png")

    assert note_id == 42
    assert len(anki._stored) == 1
    name, data = anki._stored[0]
    assert name.startswith("stem_") and name.endswith(".png") and data == b"png"
    assert image_service.prompts == []
    fields = anki._added[0]["fields"]
    assert "<img src='" in fields["image"]


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
    model = CARD_ADAPTER.validate_python(
        {**json.loads(_CONCEPT_PAYLOAD), "image_description": "a diagram"}
    )

    await collection.add_note(model, topic="entropy")

    assert image_service.prompts and "a diagram" in image_service.prompts[0]
    assert anki._stored and anki._stored[0][1] == b"generated-bytes"


@pytest.mark.asyncio
async def test_add_note_reports_non_fatal_diagram_failure() -> None:
    class TimeoutImageService:
        async def generate_image(self, *, prompt: str) -> bytes:
            raise GenerationTimeoutError("Image generation", 180)

    anki = _recording_anki_client()
    collection = StemCollection(
        cast(AnkiCollectionClient, anki),
        text_model="stem-model",
        text_service=cast(TextGenerationService, object()),
        image_service=cast(ImageGenerationService, TimeoutImageService()),
    )
    errors: list[Exception] = []
    model = CARD_ADAPTER.validate_python(
        {**json.loads(_CONCEPT_PAYLOAD), "image_description": "a diagram"}
    )

    note_id = await collection.add_note(
        model, topic="entropy", on_image_error=errors.append
    )

    assert note_id == 42
    assert len(errors) == 1
    assert str(errors[0]) == "Image generation timed out after 180 seconds"
    assert anki._stored == []


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

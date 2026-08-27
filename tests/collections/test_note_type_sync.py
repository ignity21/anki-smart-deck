"""Tests for updating existing STEM and Math note types."""

from types import SimpleNamespace
from typing import cast

import pytest

from ankinote.collections.math import MathCollection
from ankinote.collections.math.models import MathNoteType
from ankinote.collections.stem import StemCollection
from ankinote.collections.stem.models import StemNoteType
from ankinote.services.ai import ImageGenerationService, TextGenerationService
from ankinote.services.anki import (
    AnkiCollectionClient,
    AnkiDeckService,
    AnkiModelService,
    TemplateUpsert,
)


class RecordingModelService:
    """Record updates made to an existing note type."""

    def __init__(self) -> None:
        self.ensured_fields: list[str] | None = None
        self.updated_templates: list[TemplateUpsert] | None = None
        self.updated_css: str | None = None

    async def exists(self, model_name: str) -> bool:
        return True

    async def ensure_fields(self, model_name: str, field_names: list[str]) -> None:
        self.ensured_fields = field_names

    async def update_templates(
        self, model_name: str, templates: list[TemplateUpsert]
    ) -> None:
        self.updated_templates = templates

    async def update_styling(self, model_name: str, css: str) -> None:
        self.updated_css = css


class FakeDeckService:
    """Record-free deck service for protocol completeness."""

    async def create(self, deck_name: str) -> int:
        return 1


def _build_client(models: RecordingModelService) -> AnkiCollectionClient:
    return cast(
        AnkiCollectionClient,
        SimpleNamespace(
            models=cast(AnkiModelService, models),
            decks=cast(AnkiDeckService, FakeDeckService()),
        ),
    )


@pytest.mark.asyncio
async def test_stem_sync_updates_an_existing_note_type() -> None:
    models = RecordingModelService()
    collection = StemCollection(
        _build_client(models),
        text_model_id="test-model",
        text_service=cast(TextGenerationService, object()),
    )

    await collection.ensure_in_anki()

    assert models.ensured_fields == [
        field.name for field in StemNoteType.__dataclass_fields__.values()
    ]
    assert models.updated_templates is not None
    assert models.updated_templates[0].name == "Card 1"
    assert models.updated_css is not None


@pytest.mark.asyncio
async def test_math_sync_updates_an_existing_note_type() -> None:
    models = RecordingModelService()
    collection = MathCollection(
        _build_client(models),
        text_model_id="test-model",
        text_service=cast(TextGenerationService, object()),
        image_service=cast(ImageGenerationService, object()),
    )

    await collection.ensure_in_anki()

    assert models.ensured_fields == [
        field.name for field in MathNoteType.__dataclass_fields__.values()
    ]
    assert models.updated_templates is not None
    assert models.updated_templates[0].name == "Card 1"
    assert models.updated_css is not None

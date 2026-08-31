"""STEM collection management for Anki."""

import dataclasses
import hashlib
from typing import Self

from loguru import logger

from ankinote.services.ai import ImageGenerationService, TextGenerationService
from ankinote.services.anki import AnkiCollectionClient, TemplateUpsert

from .generator import StemGenerator
from .models import StemModel, StemNoteType
from .templates import load_card_style, load_template


class StemCollection:
    """Manages STEM knowledge notes in Anki.

    Covers concept definitions, formulas/theorems, and step-by-step
    procedures across Math, Statistics, Finance, Computer Science,
    Programming, and Machine Learning.
    """

    def __init__(
        self,
        anki_client: AnkiCollectionClient,
        *,
        notetype_name: str = "AINote STEM",
        deck_name: str = "AINote::STEM",
        text_model_id: str,
        text_service: TextGenerationService,
        image_service: ImageGenerationService | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        """Initialize StemCollection.

        Args:
            anki_client: AnkiConnect client instance
            notetype_name: Name of the Anki note type to use
            deck_name: Name of the Anki deck to add notes to
            text_model_id: Model ID for the LLM used to generate content
            text_service: Shared text generation service
            image_service: Optional image generation service for diagrams
            reasoning_effort: Extended-thinking level forwarded to the provider;
                ``None`` keeps the provider default (thinking on)
        """
        self.notetype_name = notetype_name
        self.deck_name = deck_name
        self._anki_client = anki_client
        self._reasoning_effort = reasoning_effort
        self._generator = StemGenerator(
            text_service=text_service,
            text_model_id=text_model_id,
            image_service=image_service,
        )

    async def __aenter__(self) -> Self:
        """Async context manager entry: ensure note type and deck exist."""
        await self._ensure_note_type_exists()
        await self._ensure_deck_exists()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""

    async def ensure_in_anki(self) -> None:
        """Create or update this note type and its deck in Anki.

        Idempotent equivalent of the CLI ``init`` command: creates the note
        type with the current fields, templates and styling when missing, or
        refreshes templates, styling and missing fields when it already exists,
        then ensures the deck is present. Does not start TTS or LLM services,
        so it is safe to call from the GUI setup flow.
        """
        await self._ensure_note_type_exists()
        await self._ensure_deck_exists()

    async def _ensure_note_type_exists(self) -> None:
        """Ensure the note type exists in Anki, creating or updating it."""
        fields = [field.name for field in dataclasses.fields(StemNoteType)]
        front_template = load_template("front.html")
        back_template = load_template("back.html")
        style = load_card_style()
        exists = await self._anki_client.models.exists(self.notetype_name)
        if not exists:
            await self._anki_client.models.create(
                model_name=self.notetype_name,
                fields=fields,
                templates=[
                    {
                        "Name": "Card 1",
                        "Front": front_template,
                        "Back": back_template,
                    },
                ],
                css=style,
                is_cloze=False,
            )
            logger.success(f"Created note type: {self.notetype_name}")
            return

        await self._anki_client.models.ensure_fields(self.notetype_name, fields)
        await self._anki_client.models.update_templates(
            self.notetype_name,
            [
                TemplateUpsert(
                    name="Card 1",
                    question_format=front_template,
                    answer_format=back_template,
                )
            ],
        )
        await self._anki_client.models.update_styling(self.notetype_name, style)
        logger.success(f"Updated note type: {self.notetype_name}")

    async def _ensure_deck_exists(self) -> int:
        """Ensure the deck exists in Anki, create it if it doesn't."""
        deck_id = await self._anki_client.decks.create(self.deck_name)
        logger.success(f"Ensured deck exists: {self.deck_name}")
        return deck_id

    async def generate_and_add_note(
        self,
        topic: str,
        tags: list[str] | None = None,
    ) -> int:
        """Generate a STEM card and add/update note in Anki.

        This method:
        1. Uses LLM to generate structured card data (auto-detects card type)
        2. Generates a diagram if the AI determines one is needed
        3. Creates or updates the note in Anki

        Args:
            topic: The user's question or concept (e.g. "What is a derivative?")
            tags: Optional additional tags to apply

        Returns:
            Note ID
        """
        logger.info(f"Starting generation for STEM card: {topic[:50]}...")

        # Step 1: Generate text data using LLM
        stem_model = await self._generator.generate(
            topic, reasoning_effort=self._reasoning_effort
        )

        # Step 2: Optionally generate an image
        image_filename: str | None = None
        if stem_model.image_description and self._generator._image_service:
            try:
                image_bytes = await self._generator.generate_image(
                    stem_model.image_description
                )
                card_hash = hashlib.md5(topic.encode()).hexdigest()[:12]
                image_filename = f"stem_{card_hash}.png"
                await self._anki_client.media.store_file(image_filename, image_bytes)
                logger.info(f"Stored diagram: {image_filename}")
            except Exception as e:
                logger.warning(f"Image generation failed: {e}")

        # Step 3: Build note data
        note_data = self._build_note_data(stem_model, image_filename)

        # Step 4: Combine tags
        all_tags = list(tags or [])
        all_tags.extend(stem_model.tags)
        all_tags.append("AI-generated")

        # Step 5: Add or update note
        note_id = await self._anki_client.notes.find(
            deck_name=self.deck_name,
            unique_fields={"front": stem_model.front},
        )

        if note_id is not None:
            await self._anki_client.notes.update_fields(note_id, note_data)
            await self._anki_client.notes.update_tags(note_id, all_tags)
            logger.info(f"Updated note {note_id}")
        else:
            note_id = await self._anki_client.notes.add(
                deck_name=self.deck_name,
                model_name=self.notetype_name,
                fields=note_data,
                tags=all_tags,
                allow_duplicate=True,
            )
            logger.info(f"Created note {note_id}")

        return note_id

    def _build_note_data(
        self,
        stem_model: StemModel,
        image_filename: str | None,
    ) -> dict[str, str]:
        """Convert StemModel and optional image to Anki note fields.

        Structured fields (latex, variables, steps) are rendered into the
        stored back_detail HTML so the note type stays all-string and old
        notes remain valid. If an image was generated, it is appended to
        back_detail as an <img> tag.
        """
        parts: list[str] = []

        if stem_model.latex:
            parts.append(f"<div class='formula-block'>\\[{stem_model.latex}\\]</div>")

        if stem_model.variables:
            rows = "".join(
                "<tr>"
                f"<td class='symbol-cell'>\\({v.symbol}\\)</td>"
                f"<td>{v.description}</td>"
                "</tr>"
                for v in stem_model.variables
            )
            parts.append(f"<table class='symbol-table'>{rows}</table>")

        if stem_model.steps:
            items = "".join(f"<li>{step}</li>" for step in stem_model.steps)
            parts.append(f"<ol class='step-list'>{items}</ol>")

        parts.append(stem_model.back_detail)
        back_detail = "\n".join(parts)

        if image_filename:
            back_detail += f"\n<div class='diagram-container'><img src='{image_filename}' class='diagram'></div>"

        return {
            "card_type": stem_model.card_type.value,
            "front": stem_model.front,
            "back_brief": stem_model.back_brief,
            "back_detail": back_detail,
            "tags": ", ".join(stem_model.tags),
        }

"""Math/Science collection management for Anki."""

import dataclasses
import hashlib
from dataclasses import dataclass
from typing import Self

from loguru import logger

from ankinote.services.anki import AnkiConnectClient

from .generator import MathGenerator, MathMediaFiles
from .models import MathModel, MathNoteType
from .templates import load_card_style, load_template


# ============================================================================
# Data Structures
# ============================================================================
@dataclass
class MathCardData:
    """Complete card data including model and media files."""

    model: MathModel
    media: MathMediaFiles


@dataclass
class MediaReferences:
    """References to media files stored in Anki."""

    explanation_images: list[str]  # Filenames for explanation diagrams
    example_images: dict[int, str]  # {example_idx: filename}


# ============================================================================
# MathCollection Class
# ============================================================================


class MathCollection:
    """Manages math/science knowledge notes in Anki."""

    def __init__(
        self,
        anki_client: AnkiConnectClient,
        *,
        notetype_name: str = "AINote Math",
        deck_name: str = "AINote::Math",
        llm_model_id: str = "gemini/gemini-3.1-flash-lite-preview",
        image_model_id: str = "gemini/gemini-2.5-flash-image",
        image_size: int = 512,
    ) -> None:
        """Initialize MathCollection.

        Args:
            anki_client: AnkiConnect client instance
            notetype_name: Name of the Anki note type to use
            deck_name: Name of the Anki deck to add notes to
            llm_model_id: Model ID for the LLM used to generate content
            image_model_id: Model ID for the image generator
            image_size: Target size (pixels) for generated images (square)
        """
        self.notetype_name = notetype_name
        self.deck_name = deck_name
        self._anki_client = anki_client
        self._generator = MathGenerator(
            llm_model_id=llm_model_id,
            image_model_id=image_model_id,
            image_size=image_size,
        )

    async def __aenter__(self) -> Self:
        """Async context manager entry: ensure note type and deck exist."""
        await self._ensure_note_type_exists()
        await self._ensure_deck_exists()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        pass

    async def _ensure_note_type_exists(self) -> None:
        """Ensure the note type exists in Anki, create it if it doesn't.

        Raises:
            RuntimeError: If there's an error communicating with AnkiConnect
        """
        exists = await self._anki_client.models.exists(self.notetype_name)
        if not exists:
            fields = [f.name for f in dataclasses.fields(MathNoteType)]
            front_template = load_template("front.html")
            back_template = load_template("back.html")
            style = load_card_style()

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

    async def _ensure_deck_exists(self) -> int:
        """Ensure the deck exists in Anki, create it if it doesn't.

        Returns:
            The ID of the deck (existing or newly created)

        Raises:
            RuntimeError: If there's an error communicating with AnkiConnect
        """
        deck_id = await self._anki_client.decks.create(self.deck_name)
        logger.success(f"Ensured deck exists: {self.deck_name}")
        return deck_id

    async def generate_and_add_note(
        self,
        front: str,
        tags: list[str] | None = None,
    ) -> int:
        """Generate complete math card data and add/update note in Anki.

        This method:
        1. Uses LLM to generate structured explanation and examples
        2. Generates diagrams/charts if needed
        3. Stores media files in Anki
        4. Creates or updates the note

        Args:
            front: The question or concept from the user
            tags: Optional list of tags to apply to the note

        Returns:
            Note ID

        Raises:
            ValueError: If LLM generation fails
            RuntimeError: If there's an error communicating with AnkiConnect
        """
        logger.info(f"Starting generation for math card: {front[:50]}...")

        # Step 1: Generate text data using LLM
        math_model = await self._generator.generate_math_data(front)

        # Step 2: Generate media files (diagrams)
        media = await self._generator.generate_media(math_model)

        # Step 3: Create card data
        card_data = MathCardData(model=math_model, media=media)

        # Step 4: Add or update note in Anki
        # Combine user-provided tags with auto-generated tags
        all_tags = list(tags or [])
        all_tags.extend(math_model.tags)
        all_tags.append("AI-generated")
        all_tags.append("Math")

        note_id = await self._add_or_update_note(
            card_data=card_data,
            tags=all_tags,
        )

        logger.success(f"Completed generation for math card: note {note_id}")
        return note_id

    async def _add_or_update_note(
        self,
        card_data: MathCardData,
        tags: list[str],
    ) -> int:
        """Add or update a note in Anki.

        Args:
            card_data: Complete card data including model and media
            tags: Tags to apply to the note

        Returns:
            The ID of the created or updated note
        """
        math_model = card_data.model

        logger.info(f"Adding/updating note to {self.deck_name}")

        # Step 1: Store media files in Anki
        media_refs = await self._store_media_files(card_data)

        # Step 2: Convert to Anki note format
        note_data = self._convert_to_note_type(math_model, media_refs)

        # Step 3: Check if note exists (by front field)
        note_id = await self._anki_client.notes.find(
            deck_name=self.deck_name,
            unique_fields={"front": math_model.front},
        )

        # Step 4: Add or update
        if note_id is not None:
            await self._anki_client.notes.update_fields(note_id, note_data)
            await self._anki_client.notes.update_tags(note_id, tags)
            logger.info(f"Updated note {note_id}")
        else:
            note_id = await self._anki_client.notes.add(
                deck_name=self.deck_name,
                model_name=self.notetype_name,
                fields=note_data,
                tags=tags,
                allow_duplicate=True,
            )
            logger.info(f"Created note {note_id}")

        return note_id

    async def _store_media_files(self, card_data: MathCardData) -> MediaReferences:
        """Store media files in Anki and return their references.

        Args:
            card_data: Card data containing media files

        Returns:
            MediaReferences with filenames for stored media
        """
        math_model = card_data.model
        media = card_data.media

        # Generate unique hash for this card
        card_hash = hashlib.md5(math_model.front.encode()).hexdigest()[:12]

        # Store explanation images
        explanation_image_names = []
        for i, img in enumerate(media.explanation_images):
            name = f"math_{card_hash}_exp{i}.png"
            await self._anki_client.media.store_file(name, img)
            explanation_image_names.append(name)
        logger.debug(f"Stored {len(explanation_image_names)} explanation image(s)")

        # Store example images
        example_image_names = {}
        for ex_idx, img in media.example_images.items():
            name = f"math_{card_hash}_ex{ex_idx}.png"
            await self._anki_client.media.store_file(name, img)
            example_image_names[ex_idx] = name
        logger.debug(f"Stored {len(example_image_names)} example image(s)")

        return MediaReferences(
            explanation_images=explanation_image_names,
            example_images=example_image_names,
        )

    def _convert_to_note_type(
        self,
        math_model: MathModel,
        media_refs: MediaReferences,
    ) -> dict[str, str]:
        """Convert MathModel and media references to Anki note fields.

        Args:
            math_model: The math model data
            media_refs: References to stored media files

        Returns:
            Dictionary mapping field names to HTML string values
        """
        # Build the back content
        back_html = self._format_back_html(math_model, media_refs)

        return {
            "front": math_model.front,
            "back": back_html,
            "examples": self._format_examples_html(
                math_model.examples, media_refs.example_images
            ),
            "related_concepts": self._format_related_concepts_html(
                math_model.related_concepts
            ),
            "difficulty": math_model.difficulty,
            "tags": ", ".join(math_model.tags),
        }

    def _format_back_html(
        self, math_model: MathModel, media_refs: MediaReferences
    ) -> str:
        """Format the back side content including explanation and diagrams."""
        parts = []

        # Main explanation
        parts.append(
            f"<div class='explanation'>{self._process_latex(math_model.explanation)}</div>"
        )

        # Explanation diagrams
        if media_refs.explanation_images:
            parts.append("<div class='explanation-images'>")
            for img_name in media_refs.explanation_images:
                parts.append(f"<img src='{img_name}' class='diagram'>")
            parts.append("</div>")

        # Key points
        if math_model.key_points:
            parts.append("<div class='key-points'>")
            parts.append("<div class='section-title'>Key Points</div>")
            parts.append("<ul>")
            for point in math_model.key_points:
                parts.append(f"<li>{self._process_latex(point)}</li>")
            parts.append("</ul>")
            parts.append("</div>")

        return "\n".join(parts)

    def _format_examples_html(
        self, examples: list, example_images: dict[int, str]
    ) -> str:
        """Format examples with solutions and diagrams."""
        if not examples:
            return ""

        parts = []
        for idx, example in enumerate(examples):
            parts.append("<div class='example'>")
            parts.append(
                f"<div class='example-problem'><strong>Problem:</strong> {self._process_latex(example.problem)}</div>"
            )
            parts.append(
                f"<div class='example-solution'><strong>Solution:</strong> {self._process_latex(example.solution)}</div>"
            )

            # Add diagram if available
            if idx in example_images:
                parts.append(
                    f"<div class='example-image'><img src='{example_images[idx]}' class='diagram'></div>"
                )

            parts.append("</div>")

        return "\n".join(parts)

    def _format_related_concepts_html(self, concepts: list[str]) -> str:
        """Format related concepts as a list."""
        if not concepts:
            return ""

        items = [f"<li>{concept}</li>" for concept in concepts]
        return "<ul>" + "".join(items) + "</ul>"

    def _process_latex(self, text: str) -> str:
        """Process text to ensure LaTeX formulas are properly formatted for Anki.

        Anki uses MathJax, which recognizes:
        - Inline math: \\( ... \\) or $ ... $
        - Display math: \\[ ... \\] or $$ ... $$

        We'll ensure proper escaping and formatting.
        """
        # Replace newlines with <br> for better HTML rendering
        text = text.replace("\n", "<br>")
        return text

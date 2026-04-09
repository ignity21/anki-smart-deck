"""Word collection management for Anki."""

import dataclasses
import hashlib
from dataclasses import dataclass
from typing import Self

from loguru import logger

from ankinote.collections.common import convert_to_ruby_annotation
from ankinote.collections.word.models import Definition, Example, WordModel
from ankinote.consts import RUBY_ANNOTATION_LANGUAGES, Language
from ankinote.services.anki import AnkiConnectClient
from ankinote.services.tts import TTS_LANG_CODES, GoogleTTSService

from .generator import WordGenerator, WordMediaFiles
from .models import WordNoteType
from .templates import load_card_style, load_template


# ============================================================================
# Data Structures
# ============================================================================
@dataclass
class WordCardData:
    """Complete card data including model and media files."""

    model: WordModel
    media: WordMediaFiles


@dataclass
class MediaReferences:
    """References to media files stored in Anki."""

    word_audio: str  # Filename: "word_uuid.mp3"
    example_audios: list[str]  # Filenames: ["word_ex0_uuid.mp3", ...]
    images: dict[int, str]  # {0, "word_img0_uuid.png", ...}


# ============================================================================
# WordCollection Class
# ============================================================================


class WordCollection:
    """Manages vocabulary word notes in Anki."""

    def __init__(
        self,
        anki_client: AnkiConnectClient,
        *,
        native_language: Language,
        target_language: Language,
        notetype_name: str = "AINote Word",
        deck_name: str = "AINote::Words",
        llm_model_id: str = "gemini/gemini-3.1-flash-lite-preview",
        image_model_id: str = "gemini/gemini-2.5-flash-image",
        image_size: int = 256,
    ) -> None:
        """Initialize WordCollection.

        Args:
            anki_client: AnkiConnect client instance
            native_language: User's native language for translations
            target_language: Language being learned
            notetype_name: Name of the Anki note type to use
            deck_name: Name of the Anki deck to add notes to
            llm_model_id: Model ID for the LLM used to generate word data
            image_model_id: Model ID for the image generator
            image_size: Target size (pixels) for generated images (square)
        """
        self.notetype_name = notetype_name
        self.deck_name = deck_name
        self._native_language = native_language
        self._target_language = target_language
        self._anki_client = anki_client
        self._tts_service = GoogleTTSService(TTS_LANG_CODES[target_language])
        self._generator = WordGenerator(
            tts_service=self._tts_service,
            llm_model_id=llm_model_id,
            image_model_id=image_model_id,
            image_size=image_size,
        )
        if target_language in RUBY_ANNOTATION_LANGUAGES:
            self._convert_target_lang_text = convert_to_ruby_annotation
        else:
            self._convert_target_lang_text = lambda x: x  # No conversion needed

    async def __aenter__(self) -> Self:
        """Async context manager entry: ensure note type and deck exist."""
        await self._tts_service.__aenter__()
        await self._ensure_note_type_exists()
        await self._ensure_deck_exists()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit: clean up TTS service."""
        await self._tts_service.__aexit__(exc_type, exc_val, exc_tb)

    async def _ensure_note_type_exists(self) -> None:
        """Ensure the note type exists in Anki, create it if it doesn't.

        Raises:
            RuntimeError: If there's an error communicating with AnkiConnect
        """
        exists = await self._anki_client.models.exists(self.notetype_name)
        if not exists:
            fields = [f.name for f in dataclasses.fields(WordNoteType)]
            front_template = load_template("front.html")
            back_template = load_template("back.html")
            rfront_template = load_template("reverse_front.html")
            rback_template = load_template("reverse_back.html")
            spelling_front = load_template("spelling_front.html")
            spelling_back = load_template("spelling_back.html")
            style = load_card_style()

            await self._anki_client.models.create(
                model_name=self.notetype_name,
                fields=fields,
                templates=[
                    {
                        "Name": "Recognition",
                        "Front": front_template,
                        "Back": back_template,
                    },
                    {
                        "Name": "Recall",
                        "Front": rfront_template,
                        "Back": rback_template,
                    },
                    {
                        "Name": "Spelling",
                        "Front": spelling_front,
                        "Back": spelling_back,
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
        word: str,
        tags: list[str] | None = None,
    ) -> list[int]:
        """Generate complete word data and add/update notes in Anki.

        This method:
        1. Uses LLM to generate structured word data (may return multiple entries for different parts of speech)
        2. Generates audio files (word pronunciation + example sentences)
        3. Generates images for visualizable definitions
        4. Stores media files in Anki
        5. Creates or updates notes

        Args:
            word: The word to analyze and add
            tags: Optional list of tags to apply to the notes

        Returns:
            List of note IDs (one per part of speech)

        Raises:
            ValueError: If LLM generation fails
            RuntimeError: If there's an error communicating with AnkiConnect
        """
        logger.info(f"Starting generation for word: {word}")

        # Step 1: Generate text data using LLM
        word_models = await self._generate_word_models(word)

        # Step 2: For each WordModel (one per part of speech)
        note_ids = []
        for word_model in word_models:
            # Step 2a: Generate media files
            media = await self._generator.generate_media(word_model=word_model)

            # Step 2b: Create card data
            card_data = WordCardData(model=word_model, media=media)

            # Step 2c: Add or update note in Anki
            note_id = await self._add_or_update_note(
                card_data=card_data,
                tags=tags or [self._target_language.value, "AI-generated", "Word"],
            )
            note_ids.append(note_id)

        logger.success(
            f"Completed generation for '{word}': {len(note_ids)} note(s) created/updated"
        )
        return note_ids

    async def _generate_word_models(self, word: str) -> list[WordModel]:
        """Generate WordModel list using LLM and normalize the data.

        Args:
            word: The word to analyze

        Returns:
            List of WordModel objects (one per part of speech)
        """
        logger.info(f"Generating word data for: {word}")

        word_models = await self._generator.generate_word_data(
            word=word,
            target_lang=self._target_language,
            native_lang=self._native_language,
        )

        return word_models

    async def _add_or_update_note(
        self,
        card_data: WordCardData,
        tags: list[str],
    ) -> int:
        """Add or update a note in Anki.

        Args:
            card_data: Complete card data including model and media
            tags: Tags to apply to the note

        Returns:
            The ID of the created or updated note
        """
        word_model = card_data.model

        logger.info(
            f"Adding/updating note {word_model.word} ({word_model.part_of_speech}) to {self.deck_name}"
        )

        # Step 1: Store media files in Anki
        media_refs = await self._store_media_files(card_data)

        # Step 2: Convert to Anki note format
        note_data = self._convert_to_note_type(word_model, media_refs)

        # Step 3: Check if note exists
        note_id = await self._anki_client.notes.find(
            deck_name=self.deck_name,
            unique_fields={
                "word": word_model.word,
                "part_of_speech": word_model.part_of_speech,
            },
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

    async def _store_media_files(self, card_data: WordCardData) -> MediaReferences:
        """Store media files in Anki and return their references.

        Args:
            card_data: Card data containing media files

        Returns:
            MediaReferences with filenames for stored media
        """
        word_model = card_data.model
        media = card_data.media

        # Generate unique filenames
        word_base = f"{word_model.word}_{word_model.part_of_speech}"
        word_hash = hashlib.md5(word_base.encode()).hexdigest()[:12]

        # Store word audio
        word_audio_name = f"{word_hash}.mp3"
        await self._anki_client.media.store_file(word_audio_name, media.pronunciation)
        logger.debug(f"Stored word audio: {word_audio_name}")

        # Store example audios
        example_audio_names = []
        for i, audio in enumerate(media.examples):
            name = f"{word_hash}_ex{i}.mp3"
            await self._anki_client.media.store_file(name, audio)
            example_audio_names.append(name)
        logger.debug(f"Stored {len(example_audio_names)} example audio(s)")

        # Store images
        image_names = {}
        for def_idx, img in media.images.items():
            name = f"{word_hash}_img{def_idx}.png"
            await self._anki_client.media.store_file(name, img)
            image_names[def_idx] = name
        logger.debug(f"Stored {len(image_names)} image(s)")

        return MediaReferences(
            word_audio=word_audio_name,
            example_audios=example_audio_names,
            images=image_names,
        )

    def _convert_to_note_type(
        self,
        word_model: WordModel,
        media_refs: MediaReferences,
    ) -> dict[str, str]:
        """Convert WordModel and media references to Anki note fields.

        Args:
            word_model: The word model data
            media_refs: References to stored media files

        Returns:
            Dictionary mapping field names to HTML string values
        """
        return {
            "word": word_model.word,
            "part_of_speech": word_model.part_of_speech,
            "pronunciation": word_model.pronunciation or "",
            "pron_audio": f"[sound:{media_refs.word_audio}]",
            "syllables": "-".join(word_model.syllables),
            "difficulty": word_model.difficulty,
            "definitions": self._format_definitions_html(
                word_model.definitions, media_refs.images
            ),
            "synonyms": self._format_synonyms_html(word_model.synonyms),
            "examples": self._format_examples_html(
                word_model.examples, media_refs.example_audios
            ),
            "etymology": self._convert_target_lang_text(word_model.etymology or ""),
            "collocations": self._format_collocations_html(word_model.collocations),
            "notes": self._format_notes_html(word_model.notes),
            "user_notes": "",  # Empty by default, user can fill in
        }

    def _format_definitions_html(
        self, definitions: list[Definition], image_refs: dict[int, str]
    ) -> str:
        """Format definitions as HTML, attaching images under corresponding items.

        Args:
            definitions: List of definition objects.
            image_refs: Mapping from definition index (0-based) to image filename.
        """
        html_parts = []
        for idx, definition in enumerate(definitions):
            img_html = ""
            img_name = image_refs.get(idx)
            if img_name:
                img_html = f"<div class='definition-image'><img src='{img_name}'></div>"

            target_lang = self._convert_target_lang_text(definition.target_lang)

            html_parts.append(
                f"<div class='definition'>"
                f"<strong>{idx + 1}.</strong> "
                f"{target_lang} "
                f"<span class='translation'>({definition.native_lang})</span>"
                f"{img_html}"
                f"</div>"
            )
        return "\n".join(html_parts)

    def _format_synonyms_html(self, synonyms: list[str]) -> str:
        """Format synonyms as HTML."""
        if not synonyms:
            return ""
        formatted = [
            f"<span class='synonym'>{self._convert_target_lang_text(s)}</span>"
            for s in synonyms
        ]
        return ", ".join(formatted)

    def _format_examples_html(
        self, examples: list[Example], audio_refs: list[str]
    ) -> str:
        """Format examples with audio as HTML."""
        html_parts = []
        for example, audio_ref in zip(examples, audio_refs):
            sentence = example.sentence
            # Highlight important phrases if specified
            if example.highlights:
                for phrase in example.highlights:
                    # Convert the phrase to ruby format for matching

                    sentence = sentence.replace(phrase, f"<strong>{phrase}</strong>")
            sentence = self._convert_target_lang_text(sentence)

            html_parts.append(
                f"<div class='example'>"
                f"<div class='example-sentence'>"
                f"{sentence} [sound:{audio_ref}]"
                f"</div>"
                f"<div class='example-translation'>{example.translation}</div>"
                f"</div>"
            )
        return "\n".join(html_parts)

    def _format_collocations_html(self, collocations: list[str]) -> str:
        """Format collocations as HTML."""
        if not collocations:
            return ""
        formatted = [
            f"<span class='collocation'>{self._convert_target_lang_text(c)}</span>"
            for c in collocations
        ]
        return ", ".join(formatted)

    def _format_notes_html(self, notes: list[str]) -> str:
        """Format notes as HTML."""
        if not notes:
            return ""
        formatted = [f"• {self._convert_target_lang_text(note)}" for note in notes]
        return "<br>".join(formatted)

    def _format_images_html(self, image_refs: list[str]) -> str:
        """Format image references as HTML."""
        if not image_refs:
            return ""
        return " ".join(f"<img src='{ref}'>" for ref in image_refs)

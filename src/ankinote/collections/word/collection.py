"""Word collection management for Anki."""

import dataclasses
from dataclasses import dataclass

import shortuuid
from loguru import logger

from ankinote.collections.word.models import Definition, Example, WordModel, Language
from ankinote.services.anki import AnkiConnectClient

# from .generator import TTS_LANG_CODES, WordGenerator
from .models import WordNoteType
from .templates import load_card_style, load_template

# ============================================================================
# Constants
# ============================================================================

MAX_EXAMPLES = 3  # Maximum number of example sentences to generate audio for
MAX_IMAGES = 3  # Maximum number of images to generate per word


# ============================================================================
# Data Structures
# ============================================================================


@dataclass
class WordMediaFiles:
    """Media files generated for a single WordModel."""

    word_audio: bytes
    example_audios: list[bytes]  # Corresponds 1-1 with WordModel.examples
    images: list[bytes]  # Images for visualizable definitions


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
    images: list[str]  # Filenames: ["word_img0_uuid.png", ...]


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
    ) -> None:
        """Initialize WordCollection.

        Args:
            anki_client: AnkiConnect client instance
            native_language: User's native language for translations
            target_language: Language being learned
            notetype_name: Name of the Anki note type to use
            deck_name: Name of the Anki deck to add notes to
        """
        self.notetype_name = notetype_name
        self.deck_name = deck_name
        self._native_language = native_language
        self._target_language = target_language
        self._anki_client = anki_client
        self._generator = WordGenerator()

    async def ensure_note_type_exists(self) -> None:
        """Ensure the note type exists in Anki, create it if it doesn't.

        Raises:
            RuntimeError: If there's an error communicating with AnkiConnect
        """
        exists = await self._anki_client.models.exists(self.notetype_name)
        if not exists:
            fields = [f.name for f in dataclasses.fields(WordNoteType)]
            front_template = load_template("front.html")
            back_template = load_template("back.html")
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
                ],
                css=style,
                is_cloze=False,
            )
            logger.success(f"Created note type: {self.notetype_name}")

    async def ensure_deck_exists(self) -> int:
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
            media = await self._generate_media_files(word_model)

            # Step 2b: Create card data
            card_data = WordCardData(model=word_model, media=media)

            # Step 2c: Add or update note in Anki
            note_id = await self._add_or_update_note(
                card_data=card_data,
                tags=tags or [self._target_language.value, "ai-generated"],
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

        # Normalize: limit examples to MAX_EXAMPLES
        for model in word_models:
            if len(model.examples) > MAX_EXAMPLES:
                logger.debug(
                    f"Truncating examples for {model.word} ({model.part_of_speech}): "
                    f"{len(model.examples)} -> {MAX_EXAMPLES}"
                )
                model.examples = model.examples[:MAX_EXAMPLES]

        return word_models

    async def _generate_media_files(self, word_model: WordModel) -> WordMediaFiles:
        """Generate all media files for a WordModel.

        Args:
            word_model: The word model to generate media for

        Returns:
            WordMediaFiles containing audio and images
        """
        logger.info(
            f"Generating media for: {word_model.word} ({word_model.part_of_speech})"
        )

        tts_lang_code = TTS_LANG_CODES[self._target_language]

        # Generate word pronunciation audio
        logger.debug(f"Generating pronunciation audio for: {word_model.word}")
        word_audio = await self._generator.generate_audio(
            word_model.word, tts_lang_code
        )

        # Generate example sentence audios
        logger.debug(f"Generating audio for {len(word_model.examples)} example(s)")
        example_audios = []
        for i, example in enumerate(word_model.examples):
            audio = await self._generator.generate_audio(
                example.sentence, tts_lang_code
            )
            example_audios.append(audio)

        # Generate images for visualizable definitions
        images = await self._generate_images(word_model)

        logger.success(
            f"Generated media: 1 word audio, {len(example_audios)} example audios, {len(images)} images"
        )

        return WordMediaFiles(
            word_audio=word_audio,
            example_audios=example_audios,
            images=images,
        )

    async def _generate_images(self, word_model: WordModel) -> list[bytes]:
        """Generate images for visualizable definitions.

        Args:
            word_model: The word model containing definitions

        Returns:
            List of image bytes (max MAX_IMAGES)
        """
        # Filter visualizable definitions
        visualizable_defs = [d for d in word_model.definitions if d.is_visualizable][
            :MAX_IMAGES
        ]

        if not visualizable_defs:
            logger.debug(
                f"No visualizable definitions for {word_model.word}, skipping image generation"
            )
            return []

        logger.debug(
            f"Generating {len(visualizable_defs)} image(s) for: "
            f"{word_model.word} ({word_model.part_of_speech})"
        )

        images = []
        for definition in visualizable_defs:
            try:
                image = await self._generator.generate_image(
                    word=word_model.word,
                    definition=definition.target_lang,
                )
                images.append(image)
            except Exception as e:
                logger.warning(
                    f"Failed to generate image for '{word_model.word}' "
                    f"(def: {definition.target_lang[:30]}...): {e}"
                )
                # Continue with other images

        return images

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
            f"Adding/updating note for: {word_model.word} ({word_model.part_of_speech})"
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
        if note_id:
            await self._anki_client.notes.update_fields(note_id, note_data)
            await self._anki_client.notes.update_tags(note_id, tags)
            logger.info(f"Updated note {note_id}")
        else:
            note_id = await self._anki_client.notes.add(
                deck_name=self.deck_name,
                model_name=self.notetype_name,
                fields=note_data,
                tags=tags,
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

        # Store word audio
        word_audio_name = f"{word_base}_{shortuuid.uuid()}.mp3"
        await self._anki_client.media.store_file(word_audio_name, media.word_audio)
        logger.debug(f"Stored word audio: {word_audio_name}")

        # Store example audios
        example_audio_names = []
        for i, audio in enumerate(media.example_audios):
            name = f"{word_base}_ex{i}_{shortuuid.uuid()}.mp3"
            await self._anki_client.media.store_file(name, audio)
            example_audio_names.append(name)
        logger.debug(f"Stored {len(example_audio_names)} example audio(s)")

        # Store images
        image_names = []
        for i, img in enumerate(media.images):
            name = f"{word_base}_img{i}_{shortuuid.uuid()}.png"
            await self._anki_client.media.store_file(name, img)
            image_names.append(name)
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
            "definitions": self._format_definitions_html(word_model.definitions),
            "synonyms": self._format_synonyms_html(word_model.synonyms),
            "examples": self._format_examples_html(
                word_model.examples, media_refs.example_audios
            ),
            "etymology": word_model.etymology or "",
            "notes": self._format_notes_html(word_model.notes),
            "images": self._format_images_html(media_refs.images),
            "user_notes": "",  # Empty by default, user can fill in
        }

    def _format_definitions_html(self, definitions: list[Definition]) -> str:
        """Format definitions as HTML."""
        html_parts = []
        for i, definition in enumerate(definitions, 1):
            html_parts.append(
                f"<div class='definition'>"
                f"<strong>{i}.</strong> "
                f"{definition.target_lang} "
                f"<span class='translation'>({definition.native_lang})</span>"
                f"</div>"
            )
        return "\n".join(html_parts)

    def _format_synonyms_html(self, synonyms: list[str]) -> str:
        """Format synonyms as HTML."""
        if not synonyms:
            return ""
        return ", ".join(f"<span class='synonym'>{s}</span>" for s in synonyms)

    def _format_examples_html(
        self, examples: list[Example], audio_refs: list[str]
    ) -> str:
        """Format examples with audio as HTML."""
        html_parts = []
        for i, (example, audio_ref) in enumerate(zip(examples, audio_refs), 1):
            # Highlight important phrases if specified
            sentence = example.sentence
            if example.highlights:
                for phrase in example.highlights:
                    sentence = sentence.replace(phrase, f"<mark>{phrase}</mark>")

            html_parts.append(
                f"<div class='example'>"
                f"<div class='example-sentence'>"
                f"{sentence} [sound:{audio_ref}]"
                f"</div>"
                f"<div class='example-translation'>{example.translation}</div>"
                f"</div>"
            )
        return "\n".join(html_parts)

    def _format_notes_html(self, notes: list[str]) -> str:
        """Format notes as HTML."""
        if not notes:
            return ""
        return "<br>".join(f"• {note}" for note in notes)

    def _format_images_html(self, image_refs: list[str]) -> str:
        """Format image references as HTML."""
        if not image_refs:
            return ""
        return " ".join(f"<img src='{ref}'>" for ref in image_refs)

"""Phrase collection management for Anki."""

import dataclasses
from dataclasses import dataclass

import shortuuid
from loguru import logger

from ankinote.collections.word.models import Language
from ankinote.services.anki import AnkiConnectClient

from .generator import PhraseGenerator, PhraseMediaFiles
from .models import Definition, Example, PhraseModel, PhraseNoteType
from .templates import load_card_style, load_template


@dataclass
class PhraseCardData:
    """Complete card data including model and media files."""

    model: PhraseModel
    media: PhraseMediaFiles


@dataclass
class MediaReferences:
    """References to media files stored in Anki."""

    phrase_audio: str  # Filename: "phrase_uuid.mp3"
    example_audios: list[str]  # Filenames: ["phrase_ex0_uuid.mp3", ...]


class PhraseCollection:
    """Manages phrase / idiom / sentence notes in Anki."""

    def __init__(
        self,
        anki_client: AnkiConnectClient,
        *,
        native_language: Language,
        target_language: Language,
        notetype_name: str = "AINote Phrase",
        deck_name: str = "AINote::Phrases",
        llm_model_id: str = "gemini/gemini-3.1-flash-lite-preview",
    ) -> None:
        """Initialize PhraseCollection."""
        self.notetype_name = notetype_name
        self.deck_name = deck_name
        self._native_language = native_language
        self._target_language = target_language
        self._anki_client = anki_client
        self._generator = PhraseGenerator(llm_model_id=llm_model_id)

    async def ensure_note_type_exists(self) -> None:
        """Ensure the note type exists in Anki, create it if it doesn't."""
        exists = await self._anki_client.models.exists(self.notetype_name)
        if exists:
            return

        fields = [f.name for f in dataclasses.fields(PhraseNoteType)]
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
                }
            ],
            css=style,
            is_cloze=False,
        )
        logger.success(f"Created phrase note type: {self.notetype_name}")

    async def ensure_deck_exists(self) -> int:
        """Ensure the deck exists in Anki, create it if it doesn't."""
        deck_id = await self._anki_client.decks.create(self.deck_name)
        logger.success(f"Ensured deck exists: {self.deck_name}")
        return deck_id

    async def generate_and_add_note(
        self,
        phrase: str,
        tags: list[str] | None = None,
    ) -> int:
        """Generate complete phrase data and add/update note in Anki."""
        logger.info(f"Starting generation for phrase: {phrase}")

        phrase_model = await self._generator.generate_phrase_data(
            phrase=phrase,
            target_lang=self._target_language,
            native_lang=self._native_language,
        )

        media = await self._generator.generate_media(
            phrase_model=phrase_model,
            target_lang=self._target_language,
        )

        card_data = PhraseCardData(model=phrase_model, media=media)

        note_id = await self._add_or_update_note(
            card_data=card_data,
            tags=tags or [self._target_language.value, "ai-generated", "phrase"],
        )

        logger.success(f"Completed generation for phrase '{phrase}', note {note_id}")
        return note_id

    async def _add_or_update_note(
        self,
        card_data: PhraseCardData,
        tags: list[str],
    ) -> int:
        """Add or update a phrase note in Anki."""
        phrase_model = card_data.model
        logger.info(
            f"Adding/updating phrase note '{phrase_model.phrase}' to {self.deck_name}"
        )

        media_refs = await self._store_media_files(card_data)
        note_data = self._convert_to_note_type(phrase_model, media_refs)

        note_id = await self._anki_client.notes.find(
            deck_name=self.deck_name,
            unique_fields={"phrase": phrase_model.phrase},
        )

        if note_id is not None:
            await self._anki_client.notes.update_fields(note_id, note_data)
            await self._anki_client.notes.update_tags(note_id, tags)
            logger.info(f"Updated phrase note {note_id}")
        else:
            note_id = await self._anki_client.notes.add(
                deck_name=self.deck_name,
                model_name=self.notetype_name,
                fields=note_data,
                tags=tags,
                allow_duplicate=True,
            )
            logger.info(f"Created phrase note {note_id}")

        return note_id

    async def _store_media_files(self, card_data: PhraseCardData) -> MediaReferences:
        """Store media files in Anki and return their references."""
        phrase_model = card_data.model
        media = card_data.media

        base = phrase_model.phrase.replace(" ", "_")

        phrase_audio_name = f"{base}_{shortuuid.uuid()}.mp3"
        await self._anki_client.media.store_file(phrase_audio_name, media.phrase_audio)
        logger.debug(f"Stored phrase audio: {phrase_audio_name}")

        example_audio_names: list[str] = []
        for i, audio in enumerate(media.example_audios):
            name = f"{base}_ex{i}_{shortuuid.uuid()}.mp3"
            await self._anki_client.media.store_file(name, audio)
            example_audio_names.append(name)
        logger.debug(f"Stored {len(example_audio_names)} example audio(s)")

        return MediaReferences(
            phrase_audio=phrase_audio_name,
            example_audios=example_audio_names,
        )

    def _convert_to_note_type(
        self,
        phrase_model: PhraseModel,
        media_refs: MediaReferences,
    ) -> dict[str, str]:
        """Convert PhraseModel and media references to Anki note fields."""
        return {
            "phrase": phrase_model.phrase,
            "pron_audio": f"[sound:{media_refs.phrase_audio}]",
            "difficulty": phrase_model.difficulty,
            "definitions": self._format_definitions_html(phrase_model.definitions),
            "examples": self._format_examples_html(
                phrase_model.examples,
                media_refs.example_audios,
            ),
            "notes": self._format_notes_html(phrase_model.notes),
            "user_notes": "",
        }

    def _format_definitions_html(self, definitions: list[Definition]) -> str:
        """Format definitions as HTML."""
        html_parts: list[str] = []
        for idx, definition in enumerate(definitions):
            html_parts.append(
                f"<div class='definition'>"
                f"<strong>{idx + 1}.</strong> "
                f"{definition.target_lang} "
                f"<span class='translation'>({definition.native_lang})</span>"
                f"</div>"
            )
        return "\n".join(html_parts)

    def _format_examples_html(
        self,
        examples: list[Example],
        audio_refs: list[str],
    ) -> str:
        """Format examples with audio as HTML."""
        html_parts: list[str] = []
        for example, audio_ref in zip(examples, audio_refs):
            sentence = example.sentence
            if example.highlight:
                sentence = sentence.replace(
                    example.highlight,
                    f"<strong>{example.highlight}</strong>",
                )

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

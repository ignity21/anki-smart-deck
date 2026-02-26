"""Word collection management for Anki."""

import dataclasses

from loguru import logger

from ankinote.collections.word.models import Lang
from ankinote.services.anki import AnkiConnectClient

from .models import WordNoteType
from .templates import load_card_style, load_template


class WordCollection:
    """Manages vocabulary word notes in Anki."""

    def __init__(
        self,
        anki_client: AnkiConnectClient,
        *,
        native_language: Lang,
        target_language: Lang,
        notetype_name: str = "AINote Word",
        deck_name: str = "AINote::Words",
    ) -> None:
        """Initialize WordCollection.

        Args:
            notetype_name: Name of the Anki note type to use
            deck_name: Name of the Anki deck to add notes to
            native_language: User's native language for translations
            target_language: Language being learned
            anki_client: AnkiConnect client instance
        """
        self.notetype_name = notetype_name
        self.deck_name = deck_name
        self._native_language = native_language
        self._target_language = target_language
        self._anki_client = anki_client
        self._logger = logger.bind(
            collection="WordCollection",
            native_language=native_language.value,
            target_language=target_language.value,
        )

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
            self._logger.success(f"Created note type: {self.notetype_name}")

    async def ensure_deck_exists(self) -> int:
        """Ensure the deck exists in Anki, create it if it doesn't.

        Returns:
            The ID of the deck (existing or newly created)

        Raises:
            RuntimeError: If there's an error communicating with AnkiConnect
        """
        deck_id = await self._anki_client.decks.create(self.deck_name)
        self._logger.success(f"Ensured deck exists: {self.deck_name}")
        return deck_id

    async def add_or_update_note(
        self,
        deck_name: str,
        note_data: dict[str, str],
        tags: list[str] | None = None,
    ) -> int:
        """Add a new note or update an existing one.

        Args:
            deck_name: Name of the deck to add the note to
            note_data: The note data
            tags: Optional list of tags to apply to the note

        Returns:
            The ID of the note (existing or newly created)

        Raises:
            RuntimeError: If there's an error communicating with AnkiConnect
            ModelNotFound: If the required note type doesn't exist
        """
        pass

"""Protocol for collection management in Anki."""

from typing import Protocol


class CollectionProtocol(Protocol):
    """Protocol for managing Anki note collections.

    This protocol defines the interface for classes that manage specific
    collections of Anki notes (e.g., vocabulary words, phrases, math problems).
    Each implementation handles the creation of note types, decks, and
    individual notes with their associated data.
    """

    notetype_name: str
    deck_name: str

    async def ensure_note_type_exists(self) -> None:
        """Ensure the note type exists in Anki, create it if it doesn't.

        This method checks if the required note type (model) exists in Anki.
        If it doesn't exist, it creates the note type with appropriate fields,
        templates, and styling.

        Raises:
            RuntimeError: If there's an error communicating with AnkiConnect
        """
        ...

    async def ensure_deck_exists(self) -> int:
        """Ensure the deck exists in Anki, create it if it doesn't.

        Returns:
            The ID of the deck (existing or newly created)

        Raises:
            RuntimeError: If there's an error communicating with AnkiConnect
        """
        ...

    async def add_or_update_note(
        self,
        deck_name: str,
        note_data: dict[str, str],
        tags: list[str] | None = None,
    ) -> int:
        """Add a new note or update an existing one.

        This method checks if a note with the same unique field values already
        exists in the specified deck. If it exists, the note is updated with
        new data. If it doesn't exist, a new note is created.

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
        ...

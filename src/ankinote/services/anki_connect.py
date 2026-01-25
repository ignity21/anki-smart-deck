import base64
from typing import Any

from ankinote.utils import get_session


class AnkiConnectClient:
    """Client for interacting with AnkiConnect API."""

    def __init__(self, url: str = "http://localhost:8765") -> None:
        """Initialize AnkiConnect client.

        Args:
            url: AnkiConnect server URL
        """
        self._url = url

    async def _invoke(self, action: str, params: dict[str, Any] | None = None) -> Any:
        """Invoke an AnkiConnect action.

        Args:
            action: The action to perform
            params: Parameters for the action

        Returns:
            The result from AnkiConnect

        Raises:
            RuntimeError: If AnkiConnect returns an error
        """
        payload = {"action": action, "version": 6, "params": params or {}}
        session = await get_session()

        async with session.post(self._url, json=payload) as response:
            response.raise_for_status()
            result = await response.json()

        if result.get("error"):
            raise RuntimeError(f"AnkiConnect error: {result['error']}")

        return result.get("result")

    # Deck operations
    async def get_deck_names(self) -> list[str]:
        """Get all deck names.

        Returns:
            List of deck names
        """
        return await self._invoke("deckNames")

    # Note operations
    async def add_note(
        self,
        deck_name: str,
        model_name: str,
        fields: dict[str, str],
        tags: list[str] | None = None,
    ) -> int:
        """Add a note to Anki.

        Args:
            deck_name: Name of the deck
            model_name: Name of the note type
            fields: Field name to value mapping
            tags: Optional list of tags

        Returns:
            The note ID
        """
        params = {
            "note": {
                "deckName": deck_name,
                "modelName": model_name,
                "fields": fields,
                "tags": tags or [],
                "options": {"allowDuplicate": False},
            }
        }
        return await self._invoke("addNote", params)

    async def update_note_fields(self, note_id: int, fields: dict[str, str]) -> None:
        """Update fields of an existing note.

        Args:
            note_id: The note ID to update
            fields: Field name to value mapping
        """
        params = {"note": {"id": note_id, "fields": fields}}
        await self._invoke("updateNoteFields", params)

    async def find_notes(self, query: str) -> list[int]:
        """Find notes matching a query.

        Args:
            query: Anki search query (e.g., 'deck:English Word:hello')

        Returns:
            List of note IDs matching the query
        """
        return await self._invoke("findNotes", {"query": query})

    async def notes_info(self, notes: list[int]) -> list[dict[str, Any]]:
        """Get detailed information about notes.

        Args:
            notes: List of note IDs

        Returns:
            List of note info dicts with fields, tags, etc.
        """
        return await self._invoke("notesInfo", {"notes": notes})

    # Media operations
    async def store_media_file(self, filename: str, data: bytes) -> str:
        """Store a media file in Anki's collection.media folder.

        Args:
            filename: The filename to use
            data: The file data as bytes

        Returns:
            The stored filename
        """
        params = {
            "filename": filename,
            "data": base64.b64encode(data).decode("utf-8"),
        }
        return await self._invoke("storeMediaFile", params)

    # NoteType operations
    async def get_note_type_names(self) -> list[str]:
        """Get all note type names.

        Returns:
            List of note type names
        """
        return await self._invoke("modelNames")

    def note_type(self, name: str) -> "NoteType":
        """Get a NoteType instance for managing a specific note type.

        Args:
            name: The note type name

        Returns:
            NoteType instance
        """
        return NoteType(self, name)


class NoteType:
    """Represents an Anki note type (model)."""

    def __init__(self, client: AnkiConnectClient, name: str) -> None:
        """Initialize NoteType.

        Args:
            client: The AnkiConnect client
            name: The note type name
        """
        self._client = client
        self.name = name

    async def create(
        self,
        fields: list[str],
        card_templates: list[dict[str, str]],
        css: str = "",
    ) -> None:
        """Create a new note type.

        Args:
            fields: List of field names
            card_templates: List of card templates, each with 'Name', 'Front', 'Back'
            css: CSS styling for all cards
        """
        params = {
            "modelName": self.name,
            "inOrderFields": fields,
            "cardTemplates": card_templates,
            "css": css,
        }
        await self._client._invoke("createModel", params)

    async def get_fields(self) -> list[str]:
        """Get field names for this note type.

        Returns:
            List of field names
        """
        return await self._client._invoke("modelFieldNames", {"modelName": self.name})

    async def add_field(self, field_name: str, index: int | None = None) -> None:
        """Add a field to this note type.

        Args:
            field_name: Name of the field to add
            index: Optional position to insert the field (default: append)
        """
        params = {"modelName": self.name, "fieldName": field_name}
        if index is not None:
            params["index"] = index
        await self._client._invoke("addFieldToModel", params)

    async def reorder_fields(self, field_names: list[str]) -> None:
        """Reorder fields in this note type.

        Args:
            field_names: List of field names in desired order
        """
        params = {"modelName": self.name, "fieldNames": field_names}
        await self._client._invoke("reorderModelFields", params)

    def card(self, card_name: str) -> "Card":
        """Get a Card instance for managing a specific card template.

        Args:
            card_name: The card template name

        Returns:
            Card instance
        """
        return Card(self._client, self.name, card_name)


class Card:
    """Represents a card template within a note type."""

    def __init__(
        self, client: AnkiConnectClient, note_type_name: str, card_name: str
    ) -> None:
        """Initialize Card.

        Args:
            client: The AnkiConnect client
            note_type_name: The note type this card belongs to
            card_name: The card template name
        """
        self._client = client
        self.note_type_name = note_type_name
        self.card_name = card_name

    async def update_template(self, front: str, back: str) -> None:
        """Update the front and back templates for this card.

        Args:
            front: Front template HTML
            back: Back template HTML
        """
        params = {
            "model": {
                "name": self.note_type_name,
                "templates": {
                    self.card_name: {
                        "Front": front,
                        "Back": back,
                    }
                },
            }
        }
        await self._client._invoke("updateModelTemplates", params)

    async def update_styling(self, css: str) -> None:
        """Update the CSS styling for this card's note type.

        Args:
            css: CSS styling
        """
        params = {
            "model": {
                "name": self.note_type_name,
                "css": css,
            }
        }
        await self._client._invoke("updateModelStyling", params)

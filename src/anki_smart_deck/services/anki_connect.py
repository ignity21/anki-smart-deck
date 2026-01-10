import base64
from typing import Any

import aiohttp


class AnkiConnectClient:
    """Client for interacting with AnkiConnect API."""

    def __init__(self, url: str = "http://localhost:8765"):
        """Initialize AnkiConnect client.

        Args:
            url: AnkiConnect server URL
        """
        self._url = url
        self._session: aiohttp.ClientSession | None = None
        self._timeout = aiohttp.ClientTimeout(total=30.0)

    async def __aenter__(self):
        # Create session on enter
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # Close session on exit
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure session is available and not closed.

        Returns:
            Active aiohttp session
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

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

        # Ensure we have a valid session
        session = await self._ensure_session()

        try:
            async with session.post(self._url, json=payload) as response:
                response.raise_for_status()
                result = await response.json()
        except (aiohttp.ClientError, aiohttp.ServerDisconnectedError):
            # Session might be stale, recreate and retry once
            if self._session:
                await self._session.close()
            self._session = aiohttp.ClientSession(timeout=self._timeout)

            async with self._session.post(self._url, json=payload) as response:
                response.raise_for_status()
                result = await response.json()

        if result.get("error"):
            raise RuntimeError(f"AnkiConnect error: {result['error']}")

        return result.get("result")

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

        note_id = await self._invoke("addNote", params)
        return note_id

    async def get_deck_names(self) -> list[str]:
        """Get all deck names.

        Returns:
            List of deck names
        """
        return await self._invoke("deckNames")

    async def get_model_names(self) -> list[str]:
        """Get all model (note type) names.

        Returns:
            List of model names
        """
        return await self._invoke("modelNames")

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

    async def update_note_fields(self, note_id: int, fields: dict[str, str]) -> None:
        """Update fields of an existing note.

        Args:
            note_id: The note ID to update
            fields: Field name to value mapping
        """
        params = {
            "note": {
                "id": note_id,
                "fields": fields,
            }
        }

        await self._invoke("updateNoteFields", params)

    async def find_notes(self, query: str) -> list[int]:
        """Find notes matching a query.

        Args:
            query: Anki search query (e.g., 'deck:English Word:hello')

        Returns:
            List of note IDs matching the query
        """
        params = {"query": query}
        return await self._invoke("findNotes", params)

    async def notes_info(self, notes: list[int]) -> list[dict[str, Any]]:
        """Get detailed information about notes.

        Args:
            notes: List of note IDs

        Returns:
            List of note info dicts with fields, tags, etc.
        """
        params = {"notes": notes}
        return await self._invoke("notesInfo", params)

"""
AnkiConnect API Client - Simplified version for card management
Official API docs: https://foosoft.net/projects/anki-connect/
"""

import base64
import requests
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class MediaFile:
    """Media file representation for Anki (audio/image)"""

    data: bytes
    filename: str
    fields: list[str]  # Fields to attach the media to


class AnkiConnect:
    """Simplified AnkiConnect client for adding, updating, and deleting cards"""

    def __init__(self, url: str = "http://localhost:8765"):
        """Initialize AnkiConnect client

        Args:
            url: AnkiConnect server URL (default: http://localhost:8765)
        """
        self.url = url
        self.version = 6

    def invoke(self, action: str, **params) -> Any:
        """Invoke AnkiConnect API

        Args:
            action: API action name
            **params: Action parameters

        Returns:
            API result

        Raises:
            Exception: If API returns an error
        """
        response = requests.post(
            self.url, json={"action": action, "version": self.version, "params": params}
        )
        result = response.json()

        if len(result) != 2:
            raise Exception("Response has unexpected number of fields")
        if "error" in result and result["error"] is not None:
            raise Exception(result["error"])

        return result["result"]

    def store_media_file(self, filename: str, data: bytes) -> str:
        """Store media file (audio/image) in Anki's media collection

        Args:
            filename: File name (e.g., "hello_us.mp3", "word_image.jpg")
            data: Binary file data

        Returns:
            Stored filename
        """
        data_base64 = base64.b64encode(data).decode("utf-8")
        return self.invoke("storeMediaFile", filename=filename, data=data_base64)

    def add_note(
        self,
        deck_name: str,
        model_name: str,
        fields: dict[str, str],
        tags: list[str] | None = None,
        audio_files: list[MediaFile] | None = None,
        picture_files: list[MediaFile] | None = None,
        allow_duplicate: bool = False,
    ) -> int:
        """Add a new note (card) to Anki

        Args:
            deck_name: Target deck name
            model_name: Note type/model name
            fields: Field values, e.g., {'Word': 'hello', 'Definition': 'greeting'}
            tags: List of tags to add
            audio_files: List of audio dicts, e.g., [
                {
                    'data': b'<audio_bytes>',
                    'filename': 'hello_us.mp3',
                    'fields': ['US Audio']
                }
            ]
            picture_files: List of picture dicts, e.g., [
                {
                    'data': b'<image_bytes>',
                    'filename': 'hello.jpg',
                    'fields': ['Image']
                }
            ]
            allow_duplicate: Whether to allow duplicate notes

        Returns:
            Note ID of the created note

        Example:
            note_id = anki.add_note(
                deck_name="English",
                model_name="Vocabulary",
                fields={
                    'Word': 'hello',
                    'Definition': 'a greeting'
                },
                audio_files=[{
                    'data': audio_bytes,
                    'filename': 'hello_us.mp3',
                    'fields': ['US Audio']
                }],
                tags=['basic', 'greetings']
            )
        """
        note = {
            "deckName": deck_name,
            "modelName": model_name,
            "fields": fields,
            "tags": tags or [],
            "options": {"allowDuplicate": allow_duplicate, "duplicateScope": "deck"},
        }

        # Process audio files
        if audio_files:
            audio_list = []
            for audio in audio_files:
                # Store audio file first
                self.store_media_file(audio.filename, audio.data)
                audio_list.append({"filename": audio.filename, "fields": audio.fields})
            note["audio"] = audio_list

        # Process picture files
        if picture_files:
            picture_list = []
            for picture in picture_files:
                # Store picture file first
                self.store_media_file(picture.filename, picture.data)
                picture_list.append(
                    {"filename": picture.filename, "fields": picture.fields}
                )
            note["picture"] = picture_list

        return self.invoke("addNote", note=note)

    def update_note_fields(
        self,
        note_id: int,
        fields: dict[str, str],
        audio_files: Optional[list[dict]] = None,
        picture_files: Optional[list[dict]] = None,
    ) -> None:
        """Update fields of an existing note

        Args:
            note_id: ID of the note to update
            fields: Fields to update, e.g., {'Definition': 'new definition'}
            audio_files: Audio files to add (same format as add_note)
            picture_files: Picture files to add (same format as add_note)

        Example:
            anki.update_note_fields(
                note_id=1234567890,
                fields={'Definition': 'updated definition'},
                audio_files=[{
                    'data': new_audio_bytes,
                    'filename': 'hello_uk.mp3',
                    'fields': ['UK Audio']
                }]
            )
        """
        # Store media files first if provided
        if audio_files:
            for audio in audio_files:
                self.store_media_file(audio["filename"], audio["data"])
                # Add sound tag to field if not already present
                for field_name in audio["fields"]:
                    if field_name not in fields:
                        fields[field_name] = f"[sound:{audio['filename']}]"

        if picture_files:
            for picture in picture_files:
                self.store_media_file(picture["filename"], picture["data"])
                # Add img tag to field if not already present
                for field_name in picture["fields"]:
                    if field_name not in fields:
                        fields[field_name] = f'<img src="{picture["filename"]}">'

        note = {"id": note_id, "fields": fields}
        return self.invoke("updateNoteFields", note=note)

    def delete_notes(self, note_ids: list[int]) -> None:
        """Delete notes by their IDs

        Args:
            note_ids: List of note IDs to delete

        Example:
            anki.delete_notes([1234567890, 1234567891])
        """
        return self.invoke("deleteNotes", notes=note_ids)

    def find_notes(self, query: str) -> list[int]:
        """Search for notes using Anki's search syntax

        Args:
            query: Search query string
                Examples:
                - 'deck:English'
                - 'tag:vocabulary'
                - 'Word:hello'
                - 'deck:English tag:vocabulary'

        Returns:
            List of note IDs matching the query

        Example:
            note_ids = anki.find_notes('deck:English tag:vocabulary')
        """
        return self.invoke("findNotes", query=query)

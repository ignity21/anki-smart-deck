#!/usr/bin/env python
import asyncio

from rich import print as rprint

from ankinote.services.anki import AnkiConnectClient
from ankinote.utils import http


async def main():
    async with http:
        client = AnkiConnectClient()

        # ========== Notes API Examples ==========
        deck_name = "My Test Deck"
        model_name = "My Test Model"

        # ========== Media API Examples ==========

        # image file
        image_filename = "example.jpeg"
        with open(image_filename, "rb") as f:
            image_data = f.read()

        await client.media.store_file(image_filename, image_data)
        rprint(f"Image filename in Anki: {image_filename}")

        # audio file
        audio_filename = "example.mp3"
        with open(audio_filename, "rb") as f:
            audio_data = f.read()
        await client.media.store_file(audio_filename, audio_data)
        rprint(f"Audio filename in Anki: {audio_filename}")

        # Create a deck if it doesn't exist
        deck_id = await client.notes.create_deck(deck_name)
        print(f"Deck ID: {deck_id}")

        # Check if the model exists
        note_id = await client.notes.find(
            deck_name=deck_name, unique_fields={"Front": "media test"}
        )
        if not note_id:
            # Create a new note
            note_id = await client.notes.add(
                deck_name=deck_name,
                model_name=model_name,
                fields={
                    "Front": "media test",
                    "Back": f"<img src='{image_filename}'> [sound:{audio_filename}]",
                },
                allow_duplicate=False,
            )
            rprint(f"Created note with ID: {note_id}")
        else:
            await client.notes.update_fields(
                note_id=note_id,
                fields={
                    "Front": "media test",
                    "Back": f"<img src='{image_filename}'> [sound:{audio_filename}]",
                },
            )
            rprint(f"Updated note {note_id} with media content")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python
import asyncio

from rich import print as rprint

from ankinote.app import Application
from ankinote.services.anki import AnkiConnectClient


async def main():
    async with Application():
        client = AnkiConnectClient()

        # ========== Notes API Examples ==========
        deck_name = "My Test Deck"
        model_name = "My Test Model"

        # Create a deck if it doesn't exist
        deck_id = await client.decks.create(deck_name)
        print(f"Deck ID: {deck_id}")

        # Check if the model exists
        note_id = await client.notes.find(
            deck_name=deck_name, unique_fields={"Front": "hello"}
        )
        if note_id:
            print(f"Found note ID: {note_id}")

        if not note_id:
            # Create a new note
            note_id = await client.notes.add(
                deck_name=deck_name,
                model_name=model_name,
                fields={"Front": "hello", "Back": "你好"},
                tags=["chinese", "vocabulary"],
                allow_duplicate=False,
            )
            rprint(f"Created note with ID: {note_id}")

        await client.notes.update_fields(
            note_id=note_id, fields={"Front": "hello (updated)", "Back": "你好 (更新)"}
        )
        rprint(f"Updated note {note_id} fields")

        # tag apis
        await client.notes.clear_all_unused_tags()
        await client.notes.update_tags(
            note_id=note_id, tags=["chinese", "vocabulary", "updated"]
        )
        rprint(f"Updated note {note_id} tags")


if __name__ == "__main__":
    asyncio.run(main())

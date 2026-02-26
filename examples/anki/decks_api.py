#!/usr/bin/env python
import asyncio

from rich import print as rprint

from ankinote.app import Application
from ankinote.services.anki import AnkiConnectClient


async def main():
    async with Application():
        anki_cli = AnkiConnectClient()
        deck_name = "My Test Deck"

        exists = await anki_cli.decks.exists(deck_name)

        if not exists:
            deck_id = await anki_cli.decks.create(deck_name)
            rprint(f"Created deck '{deck_name}' with ID: {deck_id}")


if __name__ == "__main__":
    asyncio.run(main())

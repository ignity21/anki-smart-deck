#!/usr/bin/env python
import asyncio

from ankinote.services.anki import AnkiConnectClient
from ankinote.app import Application
from ankinote.collections.word import WordCollection, Language


async def main():
    async with Application():
        client = AnkiConnectClient()
        collection = WordCollection(
            client, native_language=Language.CHINESE_S, target_language=Language.ENGLISH
        )
        await collection.ensure_note_type_exists()
        await collection.ensure_deck_exists()


if __name__ == "__main__":
    asyncio.run(main())

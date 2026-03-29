#!/usr/bin/env python
import asyncio

from ankinote.services.anki import AnkiConnectClient
from ankinote.app import Application
from ankinote.collections.sentence import SentenceCollection, Language


async def main():
    async with Application():
        client = AnkiConnectClient()
        collection = SentenceCollection(
            client,
            native_language=Language.CHINESE_S,
            target_language=Language.ENGLISH,
            llm_model_id="openai/gpt-5-nano",
        )
        await collection.ensure_note_type_exists()
        await collection.ensure_deck_exists()
        await collection.generate_and_add_note(
            "There is no doubt that my bed is the best place on Earth on Monday morning."
        )


if __name__ == "__main__":
    asyncio.run(main())

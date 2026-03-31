#!/usr/bin/env python
import asyncio

from ankinote.services.anki import AnkiConnectClient
from ankinote.app import Application
from ankinote.collections.phrase import PhraseCollection, Language


async def main():
    async with Application():
        client = AnkiConnectClient()
        async with PhraseCollection(
            client,
            native_language=Language.CHINESE_S,
            target_language=Language.ENGLISH,
            llm_model_id="openai/gpt-5-mini",
        ) as collection:
            await collection.generate_and_add_note("focus on")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python
import asyncio

from ankinote.app import Application
from ankinote.collections.phrase import PhraseCollection
from ankinote.consts import Language
from ankinote.services.anki import AnkiConnectClient


async def main():
    async with Application():
        client = AnkiConnectClient()
        async with PhraseCollection(
            client,
            native_language=Language.CHINESE_S,
            target_language=Language.JAPANESE,
            llm_model_id="gemini/gemini-3.1-flash-lite-preview",
        ) as collection:
            await collection.generate_and_add_note("役に立つ")


if __name__ == "__main__":
    asyncio.run(main())

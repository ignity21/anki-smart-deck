#!/usr/bin/env python
import asyncio

from ankinote.app import Application
from ankinote.collections.word import WordCollection
from ankinote.consts import Language
from ankinote.services.anki import AnkiConnectClient


async def main():
    async with Application():
        client = AnkiConnectClient()
        async with WordCollection(
            client,
            native_language=Language.CHINESE_S,
            target_language=Language.JAPANESE,
            llm_model_id="gemini/gemini-3.1-flash-lite-preview",
            image_model_id="gemini/gemini-2.5-flash-image",
            image_size=128,
        ) as collection:
            await collection.generate_and_add_note("時間")


if __name__ == "__main__":
    asyncio.run(main())

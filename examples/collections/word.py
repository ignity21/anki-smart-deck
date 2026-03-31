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
            target_language=Language.ENGLISH,
            llm_model_id="openai/gpt-5-nano",
            image_model_id="openai/gpt-image-1-mini",
            image_size=128,
        ) as collection:
            await collection.generate_and_add_note("basketball")


if __name__ == "__main__":
    asyncio.run(main())

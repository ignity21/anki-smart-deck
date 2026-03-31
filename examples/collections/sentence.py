#!/usr/bin/env python
import asyncio

from ankinote.app import Application
from ankinote.collections.sentence import Language, SentenceCollection
from ankinote.services.anki import AnkiConnectClient


async def main():
    async with Application():
        client = AnkiConnectClient()
        async with SentenceCollection(
            client,
            native_language=Language.CHINESE_S,
            target_language=Language.ENGLISH,
            llm_model_id="openai/gpt-5-nano",
        ) as collection:
            await collection.generate_and_add_note(
                "There is no doubt that my bed is the best place on Earth on Monday morning."
            )


if __name__ == "__main__":
    asyncio.run(main())

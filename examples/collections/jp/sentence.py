#!/usr/bin/env python
import asyncio

from ankinote.app import Application
from ankinote.collections import SentenceCollection
from ankinote.consts import Language
from ankinote.services.anki import AnkiConnectClient


async def main():
    async with Application():
        client = AnkiConnectClient()
        async with SentenceCollection(
            client,
            native_language=Language.CHINESE_S,
            target_language=Language.JAPANESE,
            llm_model_id="gemini/gemini-3.1-flash-lite-preview",
        ) as collection:
            await collection.generate_and_add_note(
                "日本へ行くために、一生懸命日本語を勉強しています。"
            )


if __name__ == "__main__":
    asyncio.run(main())

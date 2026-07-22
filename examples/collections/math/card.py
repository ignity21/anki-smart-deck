#!/usr/bin/env python
"""Example: generate and add a math card to Anki."""

import asyncio

from ankinote.app import Application
from ankinote.collections.math import MathCollection
from ankinote.services.anki import AnkiConnectClient


async def main():
    async with Application():
        client = AnkiConnectClient()
        async with MathCollection(
            client,
            llm_model_id="gemini/gemini-3.1-flash-lite-preview",
            image_model_id="gemini/gemini-2.5-flash-image",
            image_size=512,
        ) as collection:
            # Example 1: English question
            # await collection.generate_and_add_note(
            #     "Explain the Pythagorean theorem and provide a geometric proof."
            # )

            # Example 2: Chinese question
            await collection.generate_and_add_note(
                "什么是泰勒级数？请给出e^x的泰勒展开式。",
                tags=["calculus", "series"],
            )


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python
import asyncio
import pickle

from rich import print as rprint

from anki_smart_deck.services.ai import GoogleAIService


async def main():
    ai_srv = GoogleAIService()
    async with ai_srv:
        return await ai_srv.analyze_word("word")


if __name__ == "__main__":
    cards = asyncio.run(main())
    rprint(cards)
    pickle.dump(cards, open("word.pkl", "wb"))

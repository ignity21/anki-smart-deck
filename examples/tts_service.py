#!/usr/bin/env python
import asyncio
import pickle

from rich import print as rprint


async def main():
    word_dict = pickle.loads(open("word.pkl", "rb").read())
    rprint(word_dict)


if __name__ == "__main__":
    asyncio.run(main())

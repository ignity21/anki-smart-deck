#!/usr/bin/env python
import asyncio

from rich import print as rprint

from ankinote.services.anki import AnkiConnectClient
from ankinote.app import Application


async def main():
    async with Application():
        client = AnkiConnectClient()

        # ========== Notes API Examples ==========
        deck_name = "My Test Deck"
        model_name = "My Test Model"

        # Create a deck if it doesn't exist
        deck_id = await client.notes.create_deck(deck_name)
        print(f"Deck ID: {deck_id}")

        # Check if the model exists
        note_id = await client.notes.find(
            deck_name=deck_name, unique_fields={"Front": "hello"}
        )
        if note_id:
            print(f"Found note ID: {note_id}")

        if not note_id:
            # Create a new note
            note_id = await client.notes.add(
                deck_name=deck_name,
                model_name=model_name,
                fields={"Front": "hello", "Back": "你好"},
                tags=["chinese", "vocabulary"],
                allow_duplicate=False,
            )
            rprint(f"Created note with ID: {note_id}")

        await client.notes.update_fields(
            note_id=note_id, fields={"Front": "hello (updated)", "Back": "你好 (更新)"}
        )
        rprint(f"Updated note {note_id} fields")

        # tag apis
        await client.notes.clear_all_unused_tags()
        await client.notes.update_tags(
            note_id=note_id, tags=["chinese", "vocabulary", "updated"]
        )
        rprint(f"Updated note {note_id} tags")

        # # ========== Media API Examples ==========

        # # 存储文本文件
        # text_data = b"Hello, this is a test file!"
        # filename1 = await client.media.store_file("_test_file.txt", text_data)
        # rprint(f"Stored text file: {filename1}")

        # 存储图片文件（假设你有一个图片）
        # with open("example.png", "rb") as f:
        #     image_data = f.read()
        # filename2 = await client.media.store_file("example_image.png", image_data)
        # rprint(f"Stored image file: {filename2}")

        # 存储音频文件并在笔记中使用
        # with open("pronunciation.mp3", "rb") as f:
        #     audio_data = f.read()
        # audio_filename = await client.media.store_file("hello_pronunciation.mp3", audio_data)
        #
        # # 在笔记中引用音频
        # note_id_with_audio = await client.notes.add(
        #     deck_name=deck_name,
        #     model_name="Basic",
        #     fields={
        #         "Front": f"hello [sound:{audio_filename}]",
        #         "Back": "你好"
        #     },
        #     tags=["audio"]
        # )
        # rprint(f"Created note with audio: {note_id_with_audio}")


if __name__ == "__main__":
    asyncio.run(main())

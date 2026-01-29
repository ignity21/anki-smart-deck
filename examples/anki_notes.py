#!/usr/bin/env python
import asyncio
from rich import print as rprint
from ankinote.services import AnkiConnectClient
from ankinote.utils import close_session


async def main():
    client = AnkiConnectClient()

    # ========== Notes API 示例 ==========

    # 添加新笔记
    note_id = await client.notes.add(
        deck_name="Default",
        model_name="Basic",
        fields={
            "Front": "hello",
            "Back": "你好"
        },
        tags=["chinese", "vocabulary"]
    )
    rprint(f"Created note with ID: {note_id}")

    # 更新笔记的字段
    await client.notes.update(
        note_id=note_id,
        fields={
            "Front": "hello (updated)",
            "Back": "你好 (更新)"
        }
    )
    rprint(f"Updated note {note_id} fields")

    # 更新笔记的标签
    await client.notes.update(
        note_id=note_id,
        tags=["chinese", "vocabulary", "updated"]
    )
    rprint(f"Updated note {note_id} tags")

    # 同时更新字段和标签
    await client.notes.update(
        note_id=note_id,
        fields={"Front": "hello (final)"},
        tags=["chinese", "greetings"]
    )
    rprint(f"Updated note {note_id} fields and tags")

    # ========== Media API 示例 ==========

    # 存储文本文件
    text_data = b"Hello, this is a test file!"
    filename1 = await client.media.store_file("_test_file.txt", text_data)
    rprint(f"Stored text file: {filename1}")

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
    #     deck_name="Default",
    #     model_name="Basic",
    #     fields={
    #         "Front": f"hello [sound:{audio_filename}]",
    #         "Back": "你好"
    #     },
    #     tags=["audio"]
    # )
    # rprint(f"Created note with audio: {note_id_with_audio}")

    await close_session()


if __name__ == "__main__":
    asyncio.run(main())

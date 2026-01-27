#!/usr/bin/env python
import asyncio

from rich import print as rprint

from ankinote.services import AnkiConnectClient
from ankinote.utils import close_session


async def main():
    client = AnkiConnectClient()

    # 获取所有 Note Type 名称
    # rprint(await client.list_models())
    rprint(await client.find_model("AI Word (R)"))

    # # 创建 note type
    # note_type = client.note_type("MyVocab1111111111")
    # await note_type.create(
    #     fields=["Word", "Definition"],
    #     card_templates=[
    #         {"Name": "Card 1", "Front": "{{Word}}", "Back": "{{Definition}}"}
    #     ],
    #     css=".card { font-size: 20px; }",
    # )

    # # 更新卡片模板
    # card = note_type.card("Card 1")
    # await card.update_template(front="<h1>{{Word}}</h1>", back="{{Definition}}")

    await close_session()



if __name__ == "__main__":
    asyncio.run(main())

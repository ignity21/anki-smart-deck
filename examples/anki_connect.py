#!/usr/bin/env python
import asyncio
from rich import print as rprint
from ankinote.services import AnkiConnectClient
from ankinote.utils import close_session


async def main():
    client = AnkiConnectClient()

    # 获取所有 Note Type 名称
    # rprint(await client.list_models())

    # 查找现有模型
    # rprint(await client.find_model("AI Word (R)"))

    # 创建新的 Note Model
    templates = [
        {
            "Name": "Word F->B",
            "Front": "{{Word}}",
            "Back": "{{FrontSide}}<hr id=answer><div>{{Definition}}</div>",
        },
        {
            "Name": "Word B->F",
            "Front": "{{Definition}}",
            "Back": "{{FrontSide}}<hr id=answer><div>{{Word}}</div>",
        },
    ]

    css = """
.card {
    font-family: Arial, sans-serif;
    font-size: 20px;
    text-align: center;
    color: #333;
    background-color: #fff;
}
    """

    result = await client.create_model(
        model_name="MyVocab Test",
        fields=["Word", "Definition", "Example", "Notes"],
        templates=templates,
        css=css,
        is_cloze=False,
    )
    rprint("Created model:", result)

    # 验证模型已创建
    created_model = await client.find_model("MyVocab Test")
    rprint("Found created model:", created_model)

    await close_session()


if __name__ == "__main__":
    asyncio.run(main())

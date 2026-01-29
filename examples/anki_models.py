#!/usr/bin/env python
import asyncio
from rich import print as rprint
from ankinote.services import AnkiConnectClient
from ankinote.utils import close_session


async def main():
    client = AnkiConnectClient()

    # 使用新的 API 结构

    # 获取所有 Note Type 名称
    # models = await client.models.list()
    # rprint("All models:", models)

    # 查找现有模型
    model = await client.models.find("AI Word (R)")
    rprint("Found model:", model)

#     # 创建新的 Note Model
#     templates = [
#         {
#             "Name": "Word F->B",
#             "Front": "{{Word}}",
#             "Back": "{{FrontSide}}<hr id=answer><div>{{Definition}}</div>"
#         },
#         {
#             "Name": "Word B->F",
#             "Front": "{{Definition}}",
#             "Back": "{{FrontSide}}<hr id=answer><div>{{Word}}</div>"
#         }
#     ]

#     css = """
# .card {
#     font-family: Arial, sans-serif;
#     font-size: 20px;
#     text-align: center;
#     color: #333;
#     background-color: #fff;
# }
#     """

#     result = await client.models.create(
#         model_name="MyVocab Test",
#         fields=["Word", "Definition", "Example", "Notes"],
#         templates=templates,
#         css=css,
#         is_cloze=False
#     )
#     rprint("Created model:", result)

#     # 更新模板
#     model.templates[0].question_format = "<h1>{{Word}}</h1>"
#     await client.models.update_templates(model)
#     rprint("Updated templates")

#     # 更新样式
#     new_css = ".card { font-size: 24px; }"
#     await client.models.update_styling("MyVocab Test", new_css)
#     rprint("Updated styling")

    await close_session()


if __name__ == "__main__":
    asyncio.run(main())

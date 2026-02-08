#!/usr/bin/env python
import asyncio

from rich import print as rprint

from ankinote.services.anki import AnkiConnectClient, ModelTemplate
from ankinote.utils import http


async def main():
    async with http:
        anki_cli = AnkiConnectClient()

        model_name = "My Test Model"

        # list all models
        models = await anki_cli.models.list()
        rprint("All models:", models)

        # check if model exists
        exists = await anki_cli.models.exists(model_name)
        if exists:
            rprint("Found model:", model_name)
            rprint("Model details:", await anki_cli.models.info(model_name))
        else:
            rprint("Model not found:", model_name)

        # create model if it doesn't exist
        if not exists:
            result = await anki_cli.models.create(
                model_name=model_name,
                fields=["Front", "Back"],
                templates=[
                    {
                        "Name": "Card 1",
                        "Front": "{{Front}}",
                        "Back": "{{FrontSide}}<hr id=answer><div>{{Back}}</div>",
                    }
                ],
                css=".card { font-size: 20px; }",
                is_cloze=False,
            )
            rprint("Created model:", result)

        if exists:
            # update model templates
            new_templates = [
                ModelTemplate(
                    name="Test F->B",
                    question_format="{{Front}}",
                    answer_format="{{FrontSide}}<hr id=answer><div>{{Back}}</div>",
                ),
                ModelTemplate(
                    name="Test B->F",
                    question_format="{{Back}}",
                    answer_format="{{FrontSide}}<hr id=answer><div>{{Front}}</div>",
                ),
            ]
            await anki_cli.models.update_templates(model_name, new_templates)

            # update model styling
            new_css = """
            .card {
                font-size: 24px;
                color: blue;
            }
            """
            await anki_cli.models.update_styling(model_name, new_css)


if __name__ == "__main__":
    asyncio.run(main())

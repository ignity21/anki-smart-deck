#!/usr/bin/env python
from rich import print as rprint

from anki_smart_deck._card_gen import CardGenerator
from anki_smart_deck.services import (
    AIWordDictService,
    AnkiConnectClient,
    GoogleTTSService,
)

if __name__ == "__main__":
    import asyncio

    async def main():
        """Example usage of CardGenerator."""
        # Initialize services
        ai_service = AIWordDictService()
        anki_client = AnkiConnectClient()
        tts_service = GoogleTTSService()

        async with ai_service, anki_client:
            # Create card generator
            generator = CardGenerator(
                word_service=ai_service,
                anki_client=anki_client,
                tts_service=tts_service,
                deck_name="English::AI Words",
                model_name="AI Word (R)",
            )

            # Generate a single card (will update if exists)
            word = "basketball"
            note_id, is_updated = await generator.generate_card(
                word,
                tags=["example", "sports"],
                include_images=True,
                include_example_audio=False,
            )

            if is_updated:
                rprint(
                    f"\n[bold yellow]Card updated successfully![/bold yellow] Note ID: {note_id}"
                )
            else:
                rprint(
                    f"\n[bold green]Card created successfully![/bold green] Note ID: {note_id}"
                )

            # Or generate multiple cards
            # words = ["serendipity", "ephemeral", "eloquent"]
            # results = await generator.analyze_word_batch(words)

    asyncio.run(main())

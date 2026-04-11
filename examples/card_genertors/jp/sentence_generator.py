#!/usr/bin/env python
"""Example: generate vocabulary card data for a phrase."""

import asyncio
from pathlib import Path

from rich import print as rprint
from rich.console import Console
from rich.panel import Panel

from ankinote.app import Application
from ankinote.collections.sentence import SentenceGenerator
from ankinote.consts import Language
from ankinote.services.tts import TTS_LANG_CODES, GoogleTTSService

console = Console()
OUTPUT_DIR = Path("output")


# ============================================================================
# Main
# ============================================================================


async def main() -> None:
    sentence = "前向きに検討させていただきます。"
    native_lang = Language.CHINESE_S
    target_lang = Language.JAPANESE

    console.print(
        Panel.fit(
            f"[bold black]Sentence Generation Example[/bold black]\n"
            f"Sentence: '{sentence}' | Target: {target_lang.value} | Native: {native_lang.value}",
            border_style="cyan",
        )
    )

    async with Application():
        async with GoogleTTSService(
            language_code=TTS_LANG_CODES[target_lang]
        ) as tts_service:
            gen = SentenceGenerator(
                tts_service=tts_service,
                llm_model_id="gemini/gemini-3.1-flash-lite-preview",
            )
            # Step 1: generate text data
            console.print("\n[bold]Step 1:[/bold] Generating word data via LLM…")
            sentence_model = await gen.generate_sentence_data(
                target_sentence=sentence,
                target_lang=target_lang,
                native_lang=native_lang,
            )
            rprint("\n[bold]Generated Sentence Model:[/bold]", sentence_model)

    console.print(
        Panel.fit(
            "[bold green]Done![/bold green]",
            border_style="green",
        )
    )


if __name__ == "__main__":
    asyncio.run(main())

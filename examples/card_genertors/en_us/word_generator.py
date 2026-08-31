#!/usr/bin/env python
"""Example: generate vocabulary card data (text + media) for a word.

Output layout
-------------
output/
  <word>/
    pronunciation.mp3
    example_0.mp3
    example_1.mp3
    ...
    image_def<N>.png      # N = index in WordModel.definitions
"""

import asyncio
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from ankinote.app import Application
from ankinote.collections.word.generator import (
    WordGenerator,
    WordMediaFiles,
)
from ankinote.collections.word.models import WordModel
from ankinote.consts import Language
from ankinote.services.tts import TTS_LANG_CODES, GoogleTTSService

console = Console()
OUTPUT_DIR = Path("output")


# ============================================================================
# Display helpers
# ============================================================================


def display_word_model(word_model: WordModel) -> None:
    header = f"[bold cyan]{word_model.word}[/bold cyan] ({word_model.part_of_speech})"
    if word_model.pronunciation:
        header += f"  {word_model.pronunciation}"

    console.print(f"\n{'=' * 60}")
    console.print(header)
    console.print(f"Syllables: {' · '.join(word_model.syllables)}")
    console.print(f"Difficulty: [yellow]{word_model.difficulty}[/yellow]")

    console.print("\n[bold green]Definitions:[/bold green]")
    for i, defn in enumerate(word_model.definitions):
        tag = "👁️ " if defn.is_visualizable else ""
        console.print(f"  {i}. {tag}{defn.target_lang}")
        console.print(f"     → {defn.native_lang}")

    if word_model.synonyms:
        console.print(
            f"\n[bold blue]Synonyms:[/bold blue] {', '.join(word_model.synonyms)}"
        )

    console.print("\n[bold magenta]Examples:[/bold magenta]")
    for i, ex in enumerate(word_model.examples):
        console.print(f"  {i}. {ex.sentence}")
        console.print(f"     → {ex.translation}")

    if word_model.etymology:
        console.print(
            f"\n[bold yellow]Etymology:[/bold yellow]\n  {word_model.etymology}"
        )

    if word_model.notes:
        console.print("\n[bold red]Notes:[/bold red]")
        for note in word_model.notes:
            console.print(f"  • {note}")


def save_media(word: str, pos: str, media: WordMediaFiles) -> None:
    """Save all media files under output/<word>/."""
    # Use word + part-of-speech to avoid collisions when a word has
    # multiple entries (e.g. "book" as noun and verb).
    safe_pos = pos.rstrip(".").replace(".", "")
    folder = OUTPUT_DIR / f"{word}_{safe_pos}"
    folder.mkdir(parents=True, exist_ok=True)

    # Pronunciation
    pron_path = folder / "pronunciation.mp3"
    pron_path.write_bytes(media.pronunciation)
    console.print(f"  [green]✓[/green] {pron_path}")

    # Example audios
    for i, audio in enumerate(media.examples):
        path = folder / f"example_{i}.mp3"
        path.write_bytes(audio)
        console.print(f"  [green]✓[/green] {path}")

    # Images (keyed by definition index)
    for def_idx, img_bytes in media.images.items():
        path = folder / f"image_def{def_idx}.png"
        path.write_bytes(img_bytes)
        console.print(f"  [green]✓[/green] {path}")


# ============================================================================
# Main
# ============================================================================


async def main() -> None:
    word = "book"
    native_lang = Language.CHINESE_S
    target_lang = Language.ENGLISH

    console.print(
        Panel.fit(
            f"[bold black]Word Generation Example[/bold black]\n"
            f"Word: '{word}' | Target: {target_lang.value} | Native: {native_lang.value}",
            border_style="cyan",
        )
    )

    async with Application(), GoogleTTSService(
        language_code=TTS_LANG_CODES[target_lang]
    ) as tts_service:
        gen = WordGenerator(
            tts_service=tts_service,
            llm_model_id="gemini/gemini-3.1-flash-lite-preview",
            image_model_id="gemini/gemini-2.5-flash-image",
            image_size=256,
        )
        # Step 1: generate text data
        console.print("\n[bold]Step 1:[/bold] Generating word data via LLM…")
        word_models = await gen.generate_word_data(
            word=word,
            target_lang=target_lang,
            native_lang=native_lang,
        )

        for word_model in word_models:
            display_word_model(word_model)

            # Step 2: generate media
            console.print(
                f"\n[bold]Step 2:[/bold] Generating media for "
                f"'{word_model.word}' ({word_model.part_of_speech})…"
            )
            media = await gen.generate_media(
                word_model=word_model,
                target_lang=target_lang,
            )

            # Step 3: save to disk
            console.print("\n[bold]Step 3:[/bold] Saving media files…")
            save_media(word_model.word, word_model.part_of_speech, media)

    console.print(
        Panel.fit(
            f"[bold green]Done![/bold green] Files saved under [cyan]{OUTPUT_DIR}/[/cyan]",
            border_style="green",
        )
    )


if __name__ == "__main__":
    asyncio.run(main())

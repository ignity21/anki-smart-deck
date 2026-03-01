#!/usr/bin/env python
"""Example of using the word generator to create vocabulary cards."""

import asyncio

from rich.console import Console
from rich.panel import Panel

from ankinote.app import Application
from ankinote.collections.word.generator import generate_word_data
from ankinote.collections.word.models import Language

console = Console()


def display_word_model(word_model):
    """Display a WordModel in a formatted way."""

    # Create header
    header = f"[bold cyan]{word_model.word}[/bold cyan] ({word_model.part_of_speech})"
    if word_model.pronunciation:
        header += f" {word_model.pronunciation}"

    console.print(f"\n{'=' * 60}")
    console.print(header)
    console.print(f"Syllables: {' · '.join(word_model.syllables)}")
    console.print(f"Difficulty: [yellow]{word_model.difficulty}[/yellow]")

    # Definitions
    console.print("\n[bold green]Definitions:[/bold green]")
    for i, defn in enumerate(word_model.definitions, 1):
        visualizable = "👁️ " if defn.is_visualizable else ""
        console.print(f"  {i}. {visualizable}{defn.target_lang}")
        console.print(f"     → {defn.native_lang}")

    # Synonyms
    if word_model.synonyms:
        console.print(
            f"\n[bold blue]Synonyms:[/bold blue] {', '.join(word_model.synonyms)}"
        )

    # Examples
    console.print("\n[bold magenta]Examples:[/bold magenta]")
    for i, example in enumerate(word_model.examples, 1):
        console.print(f"  {i}. {example.sentence}")
        console.print(f"     → {example.translation}")
        if example.highlights:
            console.print(f"     💡 Highlights: {', '.join(example.highlights)}")

    # Etymology
    if word_model.etymology:
        console.print("\n[bold yellow]Etymology:[/bold yellow]")
        console.print(f"  {word_model.etymology}")

    # Notes
    if word_model.notes:
        console.print("\n[bold red]Notes:[/bold red]")
        for note in word_model.notes:
            console.print(f"  • {note}")


async def main():
    """Main example function."""
    async with Application():
        # English word with Chinese translations
        word = "book"
        native_lang = Language.CHINESE_S
        target_lang = Language.ENGLISH

        # Japanese word with English translations
        # word = "食べる"
        # native_lang = Language.ENGLISH
        # target_lang = Language.JAPANESE

        console.print(
            Panel.fit(
                f"[bold white]Example: Word Generation[/bold white]\n"
                f"Word: '{word}' | Target: {target_lang.value} | Native: {native_lang.value}",
                border_style="cyan",
            )
        )

        try:
            word_models = await generate_word_data(
                word=word,
                target_language=target_lang,
                native_language=native_lang,
            )
            for model in word_models:
                display_word_model(model)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")


if __name__ == "__main__":
    asyncio.run(main())

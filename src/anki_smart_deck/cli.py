"""Command-line interface for Anki Smart Deck card generation."""

import asyncio
import sys
from pathlib import Path

import click
from rich import print as rprint
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from anki_smart_deck._card_gen import CardGenerator
from anki_smart_deck.services.ai import GoogleAIService
from anki_smart_deck.services.anki_connect import AnkiConnectClient
from anki_smart_deck.services.image_search import GoogleImageSearchService
from anki_smart_deck.services.tts import GoogleTTSService

console = Console()


def print_banner():
    """Print welcome banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║           🎴  Anki Smart Deck Generator  🎴           ║
    ║                                                       ║
    ║         AI-Powered Vocabulary Card Creator            ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def print_summary(results: dict[str, tuple[int | None, bool]]) -> None:
    """Print generation summary table.

    Args:
        results: Dictionary mapping words to (note_id, is_updated) tuples
    """
    table = Table(
        title="Generation Summary", show_header=True, header_style="bold cyan"
    )
    table.add_column("Word", style="yellow", width=20)
    table.add_column("Status", style="green", width=15)
    table.add_column("Note ID", style="dim", width=15)

    for word, (note_id, is_updated) in results.items():
        if note_id is None:
            status = "❌ Failed"
            note_id_str = "N/A"
        elif is_updated:
            status = "↻ Updated"
            note_id_str = str(note_id)
        else:
            status = "✓ Created"
            note_id_str = str(note_id)

        table.add_row(word, status, note_id_str)

    console.print(table)


async def initialize_services(deck_name: str, model_name: str) -> CardGenerator:
    """Initialize all services and create card generator.

    Args:
        deck_name: Target Anki deck name
        model_name: Anki note type name

    Returns:
        Initialized CardGenerator instance
    """
    rprint("\n[cyan]Initializing services...[/cyan]")

    ai_service = GoogleAIService()
    anki_client = AnkiConnectClient()
    tts_service = GoogleTTSService()
    image_service = GoogleImageSearchService()

    # Enter async contexts
    await ai_service.__aenter__()
    await anki_client.__aenter__()

    generator = CardGenerator(
        ai_service=ai_service,
        anki_client=anki_client,
        tts_service=tts_service,
        image_service=image_service,
        deck_name=deck_name,
        model_name=model_name,
    )

    rprint("[green]✓[/green] Services initialized successfully\n")
    return generator


async def cleanup_services(generator: CardGenerator) -> None:
    """Cleanup services and close connections.

    Args:
        generator: CardGenerator instance to cleanup
    """
    rprint("\n[cyan]Cleaning up...[/cyan]")
    await generator._ai_service.__aexit__(None, None, None)
    await generator._anki_client.__aexit__(None, None, None)
    rprint("[green]✓[/green] Cleanup complete")


@click.group()
def main():
    """Anki Smart Deck - AI-powered vocabulary card generator.

    Create professional Anki flashcards with AI-generated definitions,
    example sentences, pronunciations, audio, and images.
    """
    pass


@main.command()
@click.argument("word")
@click.option(
    "--deck",
    "-d",
    default="English::AI Words",
    help="Target Anki deck name",
    show_default=True,
)
@click.option(
    "--model",
    "-m",
    default="AI Word (R)",
    help="Anki note type/model name",
    show_default=True,
)
@click.option(
    "--no-images",
    is_flag=True,
    help="Skip image search and generation",
)
@click.option(
    "--tags",
    "-t",
    multiple=True,
    help="Add custom tags to the card (can be used multiple times)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force create new card even if one exists",
)
def generate(
    word: str,
    deck: str,
    model: str,
    no_images: bool,
    tags: tuple[str, ...],
    force: bool,
):
    """Generate a single Anki card for the specified WORD.

    Examples:

        $ anki-deck generate serendipity

        $ anki-deck generate "hungry artist" --no-images

        $ anki-deck generate ephemeral -t poetry -t beautiful-word
    """
    print_banner()

    async def run():
        generator = await initialize_services(deck, model)

        try:
            include_images = not no_images
            tags_list = list(tags) if tags else None

            note_id, is_updated = await generator.generate_card(
                word=word,
                tags=tags_list,
                force_new=force,
                include_images=include_images,
            )

            # Print result
            if is_updated:
                rprint(
                    f"\n[bold yellow]✓ Card updated successfully![/bold yellow] "
                    f"Note ID: [cyan]{note_id}[/cyan]"
                )
            else:
                rprint(
                    f"\n[bold green]✓ Card created successfully![/bold green] "
                    f"Note ID: [cyan]{note_id}[/cyan]"
                )

        except Exception as e:
            rprint(f"\n[bold red]Error:[/bold red] {str(e)}")
            sys.exit(1)
        finally:
            await cleanup_services(generator)

    asyncio.run(run())


@main.command()
@click.option(
    "--deck",
    "-d",
    default="English::AI Words",
    help="Target Anki deck name",
    show_default=True,
)
@click.option(
    "--model",
    "-m",
    default="AI Word (R)",
    help="Anki note type/model name",
    show_default=True,
)
@click.option(
    "--no-images",
    is_flag=True,
    help="Skip image search for all cards",
)
@click.option(
    "--tags",
    "-t",
    multiple=True,
    help="Add custom tags to all cards",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force create new cards even if they exist",
)
def interactive(
    deck: str, model: str, no_images: bool, tags: tuple[str, ...], force: bool
):
    """Interactive mode - add multiple words with prompts.

    Keep adding words one by one with options to:
    - Enable/disable images per word
    - Continue adding more words
    - Review generation summary

    Examples:

        $ anki-deck interactive

        $ anki-deck interactive --no-images -t vocabulary
    """
    print_banner()

    async def run():
        generator = await initialize_services(deck, model)
        results = {}

        try:
            rprint(
                "\n[bold cyan]Interactive Mode[/bold cyan]\n"
                "Add words one by one. Press Ctrl+C to finish.\n"
            )

            tags_list = list(tags) if tags else None
            default_include_images = not no_images

            while True:
                try:
                    # Prompt for word
                    word = Prompt.ask("\n[cyan]Enter a word[/cyan]").strip()

                    if not word:
                        rprint("[yellow]Please enter a valid word[/yellow]")
                        continue

                    # Ask about images for this word
                    include_images = default_include_images
                    if default_include_images:
                        include_images = Confirm.ask(
                            "Include images for this word?",
                            default=True,
                        )

                    # Generate card
                    try:
                        note_id, is_updated = await generator.generate_card(
                            word=word,
                            tags=tags_list,
                            force_new=force,
                            include_images=include_images,
                        )
                        results[word] = (note_id, is_updated)

                        if is_updated:
                            rprint(
                                f"[bold yellow]✓ Updated![/bold yellow] "
                                f"Note ID: [cyan]{note_id}[/cyan]"
                            )
                        else:
                            rprint(
                                f"[bold green]✓ Created![/bold green] "
                                f"Note ID: [cyan]{note_id}[/cyan]"
                            )

                    except Exception as e:
                        rprint(
                            f"[red]Failed to generate card for '{word}':[/red] {str(e)}"
                        )
                        results[word] = (None, False)

                    # Ask to continue
                    if not Confirm.ask("\nAdd another word?", default=True):
                        break

                except KeyboardInterrupt:
                    rprint("\n\n[yellow]Interrupted by user[/yellow]")
                    break

            # Print summary
            if results:
                rprint("\n")
                print_summary(results)

        finally:
            await cleanup_services(generator)

    asyncio.run(run())


@main.command()
@click.argument("words", nargs=-1, required=True)
@click.option(
    "--deck",
    "-d",
    default="English::AI Words",
    help="Target Anki deck name",
    show_default=True,
)
@click.option(
    "--model",
    "-m",
    default="AI Word (R)",
    help="Anki note type/model name",
    show_default=True,
)
@click.option(
    "--no-images",
    is_flag=True,
    help="Skip image search for all cards",
)
@click.option(
    "--tags",
    "-t",
    multiple=True,
    help="Add custom tags to all cards",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force create new cards even if they exist",
)
def batch(
    words: tuple[str, ...],
    deck: str,
    model: str,
    no_images: bool,
    tags: tuple[str, ...],
    force: bool,
):
    """Generate multiple cards in batch mode.

    Provide multiple words as arguments to generate cards for all of them.

    Examples:

        $ anki-deck batch serendipity ephemeral eloquent

        $ anki-deck batch word1 word2 word3 --no-images -t batch-2024
    """
    print_banner()

    async def run():
        generator = await initialize_services(deck, model)

        try:
            words_list = list(words)
            tags_list = list(tags) if tags else None
            include_images = not no_images

            rprint(f"\n[cyan]Generating {len(words_list)} cards...[/cyan]\n")

            results = await generator.generate_cards_batch(
                words=words_list,
                tags=tags_list,
                force_new=force,
                include_images=include_images,
            )

            # Print summary
            rprint("\n")
            print_summary(results)

        except Exception as e:
            rprint(f"\n[bold red]Error:[/bold red] {str(e)}")
            sys.exit(1)
        finally:
            await cleanup_services(generator)

    asyncio.run(run())


@main.command()
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--deck",
    "-d",
    default="English::AI Words",
    help="Target Anki deck name",
    show_default=True,
)
@click.option(
    "--model",
    "-m",
    default="AI Word (R)",
    help="Anki note type/model name",
    show_default=True,
)
@click.option(
    "--no-images",
    is_flag=True,
    help="Skip image search for all cards",
)
@click.option(
    "--tags",
    "-t",
    multiple=True,
    help="Add custom tags to all cards",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force create new cards even if they exist",
)
def from_file(
    file: str,
    deck: str,
    model: str,
    no_images: bool,
    tags: tuple[str, ...],
    force: bool,
):
    """Generate cards from a word list file.

    The file should contain one word per line. Empty lines and lines
    starting with # will be ignored.

    Examples:

        $ anki-deck from-file words.txt

        $ anki-deck from-file vocabulary.txt --no-images -t chapter-5
    """
    print_banner()

    # Read words from file
    try:
        file_path = Path(file)
        words_list = []

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    words_list.append(line)

        if not words_list:
            rprint("[red]Error: No valid words found in file[/red]")
            sys.exit(1)

        rprint(
            f"[green]✓[/green] Loaded {len(words_list)} words from {file_path.name}\n"
        )

    except Exception as e:
        rprint(f"[red]Error reading file:[/red] {str(e)}")
        sys.exit(1)

    async def run():
        generator = await initialize_services(deck, model)

        try:
            tags_list = list(tags) if tags else None
            include_images = not no_images

            results = await generator.generate_cards_batch(
                words=words_list,
                tags=tags_list,
                force_new=force,
                include_images=include_images,
            )

            # Print summary
            rprint("\n")
            print_summary(results)

        except Exception as e:
            rprint(f"\n[bold red]Error:[/bold red] {str(e)}")
            sys.exit(1)
        finally:
            await cleanup_services(generator)

    asyncio.run(run())


if __name__ == "__main__":
    main()

"""CLI commands for math/science card generation."""

import asyncio
from pathlib import Path

import click
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ankinote.cli.factory import (
    MathCollectionOptions,
    build_math_collection,
    collection_context,
)
from ankinote.services.ai import DEFAULT_AI_SERVICE_CONFIG

console = Console()


def collection_options(f):
    """Decorator for common collection options."""
    f = click.option(
        "--llm",
        default=None,
        show_default=DEFAULT_AI_SERVICE_CONFIG.text_model_id,
        help="LLM model ID for content generation",
    )(f)
    f = click.option(
        "--image-model",
        default=None,
        show_default=DEFAULT_AI_SERVICE_CONFIG.image_model_id,
        help="Image model ID for diagram generation",
    )(f)
    f = click.option(
        "--image-size",
        default=None,
        show_default=DEFAULT_AI_SERVICE_CONFIG.image_size,
        type=int,
        help="Image size in pixels (square)",
    )(f)
    return f


def build_options(
    llm: str | None,
    image_model: str | None,
    image_size: int | None,
) -> MathCollectionOptions:
    """Convert CLI parameters to typed collection options."""
    return MathCollectionOptions(
        llm_model_id=llm,
        image_model_id=image_model,
        image_size=image_size,
    )


@click.group("math")
def math():
    """Manage math/science knowledge cards."""
    pass


@math.command("init")
@collection_options
def init(llm, image_model, image_size):
    """Create note type and deck in Anki."""

    async def _run():
        options = build_options(llm, image_model, image_size)
        async with collection_context(build_math_collection, options) as collection:
            console.print(
                f"[green]✓[/green] Initialized math collection: {collection.deck_name}"
            )

    asyncio.run(_run())


@math.command("add")
@click.argument("front")
@collection_options
def add(front, llm, image_model, image_size):
    """Generate and push a single math card.

    FRONT should be your question or concept in any language.
    """

    async def _run():
        options = build_options(llm, image_model, image_size)
        async with collection_context(build_math_collection, options) as collection:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"Generating card for: {front[:50]}...", total=None
                )
                note_id = await collection.generate_and_add_note(front)
                progress.update(task, completed=True)

            console.print(f"[green]✓[/green] Created/updated note {note_id}")

    asyncio.run(_run())


@math.command("batch")
@click.argument("questions", nargs=-1)
@click.option(
    "--file",
    type=click.Path(exists=True, path_type=Path),
    help="File containing questions (one per line)",
)
@collection_options
@click.option(
    "--rpm",
    default=10,
    type=int,
    help="Requests per minute limit",
)
def batch(questions, file, llm, image_model, image_size, rpm):
    """Generate and push multiple math cards.

    \b
    Questions can be passed as arguments, read from a file (one per line),
    or both at the same time.

    \b
    Examples:
      anki math batch "What is a derivative?" "Explain integration"
      anki math batch --file questions.txt
      anki math batch "What is entropy?" --file more_questions.txt
    """
    # Collect all questions
    all_questions = list(questions)
    if file:
        all_questions.extend(
            line.strip()
            for line in file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )

    if not all_questions:
        console.print("[red]Error:[/red] No questions provided")
        return

    console.print(f"[cyan]Processing {len(all_questions)} question(s)...[/cyan]")

    success = 0

    async def _run():
        nonlocal success
        options = build_options(llm, image_model, image_size)

        async with collection_context(build_math_collection, options) as collection:
            # Calculate delay between requests
            delay = 60.0 / rpm if rpm > 0 else 0

            async def _process(q: str):
                nonlocal success
                try:
                    with console.status(f"[bold cyan]Generating: {q[:50]}..."):
                        note_id = await collection.generate_and_add_note(q)
                    console.print(f"[green]✓[/green] Note {note_id}: {q[:60]}...")
                    success += 1
                except Exception as e:
                    logger.error(f"Failed to process '{q}': {e}")
                    console.print(f"[red]✗[/red] Failed: {q[:60]}...")

            for i, question in enumerate(all_questions):
                await _process(question)
                # Rate limiting
                if delay > 0 and i < len(all_questions) - 1:
                    await asyncio.sleep(delay)

    asyncio.run(_run())

    console.print(
        f"\n[bold]Summary:[/bold] {success}/{len(all_questions)} cards successfully created"
    )

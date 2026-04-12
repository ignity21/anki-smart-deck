import asyncio
from pathlib import Path

import click
from asynciolimiter import StrictLimiter

from ankinote.app import Application
from ankinote.cli.phrase import MAX_CONCURRENCY
from ankinote.collections import WordCollection
from ankinote.consts import Language
from ankinote.services.anki import AnkiConnectClient

# -- Shared options -----------------------------------------------------------

COLLECTION_OPTIONS = [
    click.option(
        "--native",
        default="Chinese(Simplified)",
        show_default=True,
        type=click.Choice([lang.value for lang in Language]),
    ),
    click.option(
        "--target",
        default="English",
        show_default=True,
        type=click.Choice([lang.value for lang in Language]),
    ),
    click.option(
        "--llm", default="gemini/gemini-3.1-flash-lite-preview", show_default=True
    ),
    click.option(
        "--image-model", default="gemini/gemini-2.5-flash-image", show_default=True
    ),
    click.option("--image-size", default=128, show_default=True, type=int),
]


def collection_options(cmd):
    for option in reversed(COLLECTION_OPTIONS):
        cmd = option(cmd)
    return cmd


def make_collection(
    client, native, target, llm, image_model, image_size
) -> WordCollection:
    return WordCollection(
        client,
        native_language=Language(native),
        target_language=Language(target),
        llm_model_id=llm,
        image_model_id=image_model,
        image_size=image_size,
    )


# -- word group ---------------------------------------------------------------


@click.group("word")
def word():
    """Word card commands"""
    pass


# -- init: create note type and deck ------------------------------------------


@word.command("init")
@collection_options
def init(native, target, llm, image_model, image_size):
    """Create note type and deck in Anki."""

    async def _run():
        async with Application():
            client = AnkiConnectClient()
            collection = make_collection(
                client, native, target, llm, image_model, image_size
            )
            await collection._ensure_note_type_exists()
            await collection._ensure_deck_exists()

    asyncio.run(_run())
    click.echo("✓ Ready (word collection)")


# -- add: single word ---------------------------------------------------------


@word.command("add")
@click.argument("word")
@collection_options
def add(word, native, target, llm, image_model, image_size):
    """Generate and push a single word card."""

    async def _run():
        async with Application():
            client = AnkiConnectClient()
            collection = make_collection(
                client, native, target, llm, image_model, image_size
            )
            await collection.generate_and_add_note(word)

    asyncio.run(_run())
    click.echo(f"✓ Added: {word}")


# -- batch: multiple words, optionally from file ------------------------------


@word.command("batch")
@click.argument("words", nargs=-1, metavar="[WORD ...]")
@click.option(
    "--file", "-f", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--rpm",
    default=60,
    show_default=True,
    help="Max requests per minute (match your AI provider's limit).",
)
@collection_options
def batch(words, file, native, target, llm, image_model, image_size, rpm):
    """Generate and push multiple word cards.

    \\b
    Words can be passed as arguments, read from a file (whitespace-separated),
    or both at the same time.

    \\b
    Examples:
      anki word batch apple banana cat
      anki word batch --file words.txt
      anki word batch --rpm 30 apple --file more.txt
    """
    all_words = list(words)
    if file:
        all_words += file.read_text(encoding="utf-8").split()

    if not all_words:
        raise click.UsageError("Provide at least one word via argument or --file.")

    success, failed = [], []

    async def _run():
        nonlocal success

        sem = asyncio.Semaphore(MAX_CONCURRENCY)
        limiter = StrictLimiter(rpm / 60)

        async def _process(w: str):
            nonlocal success
            async with sem:
                await limiter.wait()
                try:
                    await collection.generate_and_add_note(w)
                    success.append(w)
                except Exception as e:
                    failed.append((w, str(e)))

        async with Application():
            client = AnkiConnectClient()
            collection = make_collection(
                client, native, target, llm, image_model, image_size
            )
            await asyncio.gather(*[_process(w) for w in all_words])

    total = len(all_words)
    click.echo(
        f"Processing {total} words (concurrency={MAX_CONCURRENCY}, rpm={rpm}) ..."
    )
    asyncio.run(_run())
    if len(success) == total:
        click.echo("✅ All words processed successfully!")
    else:
        click.echo(f"\n✅ {len(success)}/{total} succeeded")
        for s in success:
            click.echo(f"   • {s}")
    if failed:
        click.echo(f"\n❌ {len(failed)} failed")
    for s, reason in failed:
        click.echo(f"   • {s}: {reason}")

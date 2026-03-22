import asyncio
from pathlib import Path
from time import perf_counter

import click

from ankinote.app import Application
from ankinote.collections.word import Language, WordCollection
from ankinote.services.anki import AnkiConnectClient

MAX_CONCURRENCY = 10

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
    click.option("--llm", default="openai/gpt-5-nano", show_default=True),
    click.option("--image-model", default="openai/gpt-image-1-mini", show_default=True),
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
            await collection.ensure_note_type_exists()
            await collection.ensure_deck_exists()

    asyncio.run(_run())
    click.echo("✓ Ready")


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
@collection_options
def batch(words, file, native, target, llm, image_model, image_size):
    """Generate and push multiple word cards.

    \b
    Words can be passed as arguments, read from a file (whitespace-separated),
    or both at the same time.

    \b
    Examples:
      anki word batch apple banana cat
      anki word batch --file words.txt
      anki word batch apple --file more.txt
    """
    all_words = list(words)
    if file:
        all_words += file.read_text(encoding="utf-8").split()

    if not all_words:
        raise click.UsageError("Provide at least one word via argument or --file.")

    success, failed = 0, []

    async def _run():
        nonlocal success

        async def _process(w: str):
            nonlocal success
            try:
                await collection.generate_and_add_note(w)
                success += 1
                click.echo(f"  ✓ {w}")
            except Exception as e:
                failed.append((w, str(e)))
                click.echo(f"  ✗ {w}  ({e})", err=True)

        async with Application():
            client = AnkiConnectClient()
            collection = make_collection(
                client, native, target, llm, image_model, image_size
            )

            WINDOW = 60.0
            batches = [
                all_words[i : i + MAX_CONCURRENCY]
                for i in range(0, len(all_words), MAX_CONCURRENCY)
            ]

            for batch_idx, batch_words in enumerate(batches):
                batch_start = perf_counter()

                await asyncio.gather(*[_process(w) for w in batch_words])

                if batch_idx < len(batches) - 1:
                    elapsed = perf_counter() - batch_start
                    remaining = WINDOW - elapsed
                    if remaining > 0:
                        click.echo(
                            f"  ⏳ Batch done in {elapsed:.1f}s, waiting {remaining:.1f}s ..."
                        )
                        await asyncio.sleep(remaining)
                    else:
                        click.echo(
                            f"  ⚡ Batch took {elapsed:.1f}s, starting next immediately."
                        )

    total = len(all_words)
    click.echo(f"Processing {total} words (concurrency={MAX_CONCURRENCY}) ...")
    asyncio.run(_run())
    click.echo(
        f"\n✅ {success}/{total} succeeded"
        + (f", ❌ {len(failed)} failed" if failed else "")
    )
    for w, reason in failed:
        click.echo(f"   • {w}: {reason}")

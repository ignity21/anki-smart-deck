import asyncio
from pathlib import Path

import click
from asynciolimiter import StrictLimiter

from ankinote.app import Application
from ankinote.collections.sentence import Language, SentenceCollection
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
    click.option(
        "--llm", default="gemini/gemini-3.1-flash-lite-preview", show_default=True
    ),
]


def collection_options(cmd):
    for option in reversed(COLLECTION_OPTIONS):
        cmd = option(cmd)
    return cmd


def make_collection(client, native, target, llm) -> SentenceCollection:
    return SentenceCollection(
        client,
        native_language=Language(native),
        target_language=Language(target),
        llm_model_id=llm,
    )


# -- sentence group -----------------------------------------------------------


@click.group("sentence")
def sentence():
    """Sentence card commands."""
    pass


# -- init: create note type and deck ------------------------------------------


@sentence.command("init")
@collection_options
def init(native, target, llm):
    """Create sentence note type and deck in Anki."""

    async def _run():
        async with Application():
            client = AnkiConnectClient()
            collection = make_collection(client, native, target, llm)
            await collection.ensure_note_type_exists()
            await collection.ensure_deck_exists()

    asyncio.run(_run())
    click.echo("✓ Ready (sentence collection)")


# -- add: single sentence -----------------------------------------------------


@sentence.command("add")
@click.argument("sentence")
@collection_options
def add(sentence, native, target, llm):
    """Generate and push a single sentence card.

    The *sentence* argument should be in the target language.
    """

    async def _run():
        async with Application():
            client = AnkiConnectClient()
            collection = make_collection(client, native, target, llm)
            await collection.generate_and_add_note(sentence)

    asyncio.run(_run())
    click.echo(f"✓ Added sentence: {sentence}")


# -- batch: multiple sentences, optionally from file --------------------------


@sentence.command("batch")
@click.argument("sentences", nargs=-1, metavar="[SENTENCE ...]")
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
def batch(sentences, file, native, target, llm, rpm):
    """Generate and push multiple sentence cards.

    \b
    Sentences should be provided in the target language. They can be passed as
    arguments, read from a file (one per line), or both at the same time.

    \b
    Examples:
      anki sentence batch "I overslept again."
      anki sentence batch --file sentences.txt
      anki sentence batch "I overslept again." --file more.txt
    """
    all_sentences = list(sentences)
    if file:
        # One sentence per line; strip empty lines
        file_sentences = [
            line.strip()
            for line in file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        all_sentences += file_sentences

    if not all_sentences:
        raise click.UsageError("Provide at least one sentence via argument or --file.")

    success, failed = 0, []

    async def _run():
        nonlocal success

        sem = asyncio.Semaphore(MAX_CONCURRENCY)
        limiter = StrictLimiter(rpm / 60)

        async def _process(s: str):
            nonlocal success
            async with sem:
                await limiter.wait()
                try:
                    await collection.generate_and_add_note(s)
                    success += 1
                    click.echo(f"  ✓ {s}")
                except Exception as e:
                    failed.append((s, str(e)))
                    click.echo(f"  ✗ {s}  ({e})", err=True)

        async with Application():
            client = AnkiConnectClient()
            collection = make_collection(client, native, target, llm)
            await asyncio.gather(*[_process(s) for s in all_sentences])

    total = len(all_sentences)
    click.echo(
        f"Processing {total} sentences (concurrency={MAX_CONCURRENCY}, rpm={rpm}) ..."
    )
    asyncio.run(_run())
    click.echo(
        f"\n✅ {success}/{total} succeeded"
        + (f", ❌ {len(failed)} failed" if failed else "")
    )
    for s, reason in failed:
        click.echo(f"   • {s}: {reason}")

import asyncio
from pathlib import Path

import click
from asynciolimiter import StrictLimiter

from ankinote.app import Application
from ankinote.collections.phrase import Language, PhraseCollection
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


def make_collection(client, native, target, llm) -> PhraseCollection:
    return PhraseCollection(
        client,
        native_language=Language(native),
        target_language=Language(target),
        llm_model_id=llm,
    )


# -- phrase group -------------------------------------------------------------


@click.group("phrase")
def phrase():
    """Phrase / sentence card commands."""
    pass


# -- init: create note type and deck ------------------------------------------


@phrase.command("init")
@collection_options
def init(native, target, llm):
    """Create phrase note type and deck in Anki."""

    async def _run():
        async with Application():
            client = AnkiConnectClient()
            collection = make_collection(client, native, target, llm)
            await collection.ensure_note_type_exists()
            await collection.ensure_deck_exists()

    asyncio.run(_run())
    click.echo("✓ Ready (phrase collection)")


# -- add: single phrase -------------------------------------------------------


@phrase.command("add")
@click.argument("phrase")
@collection_options
def add(phrase, native, target, llm):
    """Generate and push a single phrase card."""

    async def _run():
        async with Application():
            client = AnkiConnectClient()
            collection = make_collection(client, native, target, llm)
            await collection.generate_and_add_note(phrase)

    asyncio.run(_run())
    click.echo(f"✓ Added phrase: {phrase}")


# -- batch: multiple phrases, optionally from file ----------------------------


@phrase.command("batch")
@click.argument("phrases", nargs=-1, metavar="[PHRASE ...]")
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
def batch(phrases, file, native, target, llm, rpm):
    """Generate and push multiple phrase cards.

    \b
    Phrases can be passed as arguments, read from a file (one per line),
    or both at the same time.

    \b
    Examples:
      anki phrase batch "focus on" "look after"
      anki phrase batch --file phrases.txt
      anki phrase batch "call off" --file more.txt
    """
    all_phrases = list(phrases)
    if file:
        # One phrase per line; strip empty lines
        file_phrases = [
            line.strip()
            for line in file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        all_phrases += file_phrases

    if not all_phrases:
        raise click.UsageError("Provide at least one phrase via argument or --file.")

    success, failed = 0, []

    async def _run():
        nonlocal success

        sem = asyncio.Semaphore(MAX_CONCURRENCY)
        limiter = StrictLimiter(rpm / 60)

        async def _process(p: str):
            nonlocal success
            async with sem:
                await limiter.wait()
                try:
                    await collection.generate_and_add_note(p)
                    success += 1
                    click.echo(f"  ✓ {p}")
                except Exception as e:
                    failed.append((p, str(e)))
                    click.echo(f"  ✗ {p}  ({e})", err=True)

        async with Application():
            client = AnkiConnectClient()
            collection = make_collection(client, native, target, llm)
            await asyncio.gather(*[_process(p) for p in all_phrases])

    total = len(all_phrases)
    click.echo(f"Processing {total} phrases (concurrency={MAX_CONCURRENCY}) ...")
    asyncio.run(_run())
    click.echo(
        f"\n✅ {success}/{total} succeeded"
        + (f", ❌ {len(failed)} failed" if failed else "")
    )
    for p, reason in failed:
        click.echo(f"   • {p}: {reason}")

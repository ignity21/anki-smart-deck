#!/usr/bin/env python
"""Example: generate STEM card data for a topic."""

import asyncio

from rich import print as rprint
from rich.console import Console
from rich.panel import Panel

from ankinote.app import Application
from ankinote.collections.stem import StemGenerator
from ankinote.collections.stem.models import CardType

console = Console()


# ============================================================================
# Main
# ============================================================================


async def main() -> None:
    topic = "Eigenvalues and eigenvectors"
    card_type = CardType.CONCEPT

    console.print(
        Panel.fit(
            f"[bold black]STEM Card Generation Example[/bold black]\n"
            f"Topic: '{topic}' | Type: {card_type.value}",
            border_style="cyan",
        )
    )

    async with Application():
        gen = StemGenerator(llm_model_id="gemini/gemini-3.1-flash-lite-preview")

        console.print("\n[bold]Step 1:[/bold] Generating card data via LLM…")
        stem_model = await gen.generate(
            topic=topic,
            card_type=card_type,
        )
        rprint("\n[bold]Generated STEM Model:[/bold]", stem_model)

    console.print(
        Panel.fit(
            "[bold green]Done![/bold green]",
            border_style="green",
        )
    )


if __name__ == "__main__":
    asyncio.run(main())

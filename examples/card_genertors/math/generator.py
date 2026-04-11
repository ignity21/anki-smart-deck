#!/usr/bin/env python
"""Example: generate math/science card data (text + diagrams) for a concept.

Output layout
-------------
output/
  <hash>/
    explanation_0.png
    example_0.png
    example_1.png
    ...
"""

import asyncio
import hashlib
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from ankinote.app import Application
from ankinote.collections.math.generator import (
    MathGenerator,
    MathMediaFiles,
)
from ankinote.collections.math.models import MathModel

console = Console()
OUTPUT_DIR = Path("output")


# ============================================================================
# Display helpers
# ============================================================================


def display_math_model(math_model: MathModel) -> None:
    console.print(f"\n{'=' * 60}")
    console.print(f"[bold cyan]Front:[/bold cyan] {math_model.front}")
    console.print(f"[bold yellow]Difficulty:[/bold yellow] {math_model.difficulty}")
    console.print(f"[bold magenta]Tags:[/bold magenta] {', '.join(math_model.tags)}")

    console.print("\n[bold green]Explanation:[/bold green]")
    console.print(f"  {math_model.explanation[:200]}...")

    console.print("\n[bold blue]Key Points:[/bold blue]")
    for i, point in enumerate(math_model.key_points):
        console.print(f"  {i + 1}. {point}")

    console.print("\n[bold magenta]Examples:[/bold magenta]")
    for i, ex in enumerate(math_model.examples):
        vis_tag = "🖼️ " if ex.is_visualizable else ""
        console.print(f"  {i}. {vis_tag}{ex.problem[:60]}...")
        console.print(f"     Solution: {ex.solution[:80]}...")

    if math_model.related_concepts:
        console.print(
            f"\n[bold cyan]Related Concepts:[/bold cyan] {', '.join(math_model.related_concepts)}"
        )


def save_media(front: str, media: MathMediaFiles) -> None:
    """Save all media files under output/<hash>/."""
    # Use hash of front to create folder
    folder_hash = hashlib.md5(front.encode()).hexdigest()[:12]
    folder = OUTPUT_DIR / folder_hash
    folder.mkdir(parents=True, exist_ok=True)

    # Explanation images
    for i, img in enumerate(media.explanation_images):
        path = folder / f"explanation_{i}.png"
        path.write_bytes(img)
        console.print(f"  [green]✓[/green] {path}")

    # Example images
    for ex_idx, img in media.example_images.items():
        path = folder / f"example_{ex_idx}.png"
        path.write_bytes(img)
        console.print(f"  [green]✓[/green] {path}")


# ============================================================================
# Main
# ============================================================================


async def main() -> None:
    # Example 1: English math question
    front_en = "What is the derivative of x^2 and why?"

    # Example 2: Chinese math question
    front_zh = "什么是导数？请解释导数的几何意义。"

    # Use the Chinese example
    front = front_zh

    console.print(
        Panel.fit(
            f"[bold black]Math Card Generation Example[/bold black]\n"
            f"Question: '{front[:50]}...'",
            border_style="cyan",
        )
    )

    async with Application():
        gen = MathGenerator(
            llm_model_id="gemini/gemini-3.1-flash-lite-preview",
            image_model_id="gemini/gemini-2.5-flash-image",
            image_size=512,
        )

        # Step 1: generate text data
        console.print("\n[bold]Step 1:[/bold] Generating math card data via LLM…")
        math_model = await gen.generate_math_data(front=front)

        display_math_model(math_model)

        # Step 2: generate media (diagrams)
        console.print("\n[bold]Step 2:[/bold] Generating diagrams…")
        media = await gen.generate_media(math_model=math_model)

        # Step 3: save to disk
        console.print("\n[bold]Step 3:[/bold] Saving media files…")
        save_media(math_model.front, media)

    console.print(
        Panel.fit(
            f"[bold green]Done![/bold green] Files saved under [cyan]{OUTPUT_DIR}/[/cyan]",
            border_style="green",
        )
    )


if __name__ == "__main__":
    asyncio.run(main())

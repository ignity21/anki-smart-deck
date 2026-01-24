#!/usr/bin/env python
from rich import print as rprint

from ankinote.services.image_search import (
    WordImageSearchService,
    GoogleImageSearchService,
)


def main():
    google_service = GoogleImageSearchService()
    word_service = WordImageSearchService(google_service)

    # rprint("\n[bold cyan]═══ Image Search Demo ═══[/bold cyan]\n")

    # Demo 1: Simple search with keywords
    rprint("[bold magenta]Demo 1: Search 'apple' with keywords[/bold magenta]")
    images = word_service.search(
        word="apple",
        definition="a round fruit",
        img_size="MEDIUM",
        num_results=3,
        keywords=["red apple fruit", "apple illustration"],
        exclude_terms=["logo", "brand"],
    )
    rprint(f"Found {len(images)} images\n")

    # Demo 2: Search without keywords
    # rprint("[bold magenta]Demo 2: Search 'umbrella' without keywords[/bold magenta]")
    # images = word_service.search(
    #     word="umbrella",
    #     num_results=3,
    #     exclude_terms=["shop", "buy"],
    # )
    # rprint(f"Found {len(images)} images\n")

    # Demo 3: Filter results
    # rprint("[bold magenta]Demo 3: Search and filter 'cat'[/bold magenta]")
    # images = word_service.search(word="cat", num_results=3)
    # filtered = word_service.filter_results(
    #     images, blacklist_keywords=["meme", "funny", "video"]
    # )
    # rprint(f"Found {len(images)} images, {len(filtered)} after filtering\n")

    # Demo 4: Download image
    for idx, image in enumerate(images):
        image_data = google_service.download_image(image["thumbnail"])
        if image_data:
            rprint(
                f"[green]Image {idx + 1}: Downloaded {len(image_data)} bytes[/green]"
            )
            with open(f"image_{idx + 1}.jpg", "wb") as f:
                f.write(image_data)

    rprint("\n[bold green]✅ Demo completed![/bold green]")


if __name__ == "__main__":
    main()

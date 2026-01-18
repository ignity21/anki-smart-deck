from typing import Literal

from anki_smart_deck.config import get_config
from googleapiclient.discovery import build
from rich import print as rprint


class GoogleImageSearchService:
    """Generic Google Custom Search API wrapper for image search."""

    def __init__(self):
        app_config = get_config()
        self._api_key = app_config.google_search_key
        self._cse_id = app_config.google_cse_id
        self._service = build("customsearch", "v1", developerKey=self._api_key)

    def search(
        self,
        query: str,
        num_results: int = 5,
        img_size: Literal[
            "ICON", "SMALL", "MEDIUM", "LARGE", "XLARGE", "XXLARGE", "HUGE"
        ] = "SMALL",
        img_type: Literal["clipart", "face", "lineart", "stock", "photo", "animated"]
        | None = None,
        safe: Literal["active", "off"] = "active",
    ) -> list[dict]:
        """
        Search for images using Google Custom Search API.

        Args:
            query: Search query string
            num_results: Number of results to return (1-10)
            img_size: Image size constraint
            img_type: Image type filter
            safe: Safe search level

        Returns:
            List of image info dictionaries with keys: url, title, thumbnail, width, height, context_link, mime_type
        """
        rprint(f"🔍 [cyan]Searching:[/cyan] [yellow]{query}[/yellow]")

        try:
            search_params = {
                "q": query,
                "cx": self._cse_id,
                "searchType": "image",
                "num": min(num_results, 10),
                "imgSize": img_size,
                "safe": safe,
            }

            if img_type:
                search_params["imgType"] = img_type

            result = self._service.cse().list(**search_params).execute()

            images = []
            if "items" in result:
                for item in result["items"]:
                    image_info = {
                        "url": item["link"],
                        "title": item.get("title", ""),
                        "thumbnail": item.get("image", {}).get("thumbnailLink", ""),
                        "width": item.get("image", {}).get("width", 0),
                        "height": item.get("image", {}).get("height", 0),
                        "context_link": item.get("image", {}).get("contextLink", ""),
                        "mime_type": item.get("mime", ""),
                    }
                    images.append(image_info)

                rprint(f"✅ [green]Found {len(images)} images[/green]")
            else:
                rprint("[yellow]⚠️  No images found[/yellow]")

            return images

        except Exception as e:
            rprint(f"[red]❌ Search failed: {str(e)}[/red]")
            return []

    def download_image(self, image_url: str, timeout: int = 10) -> bytes | None:
        """
        Download image from URL.

        Args:
            image_url: Image URL
            timeout: Request timeout in seconds

        Returns:
            Image binary data, or None if failed
        """
        import urllib.request

        try:
            rprint(f"⬇️  [cyan]Downloading:[/cyan] [dim]{image_url[:60]}...[/dim]")

            req = urllib.request.Request(
                image_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                image_data = response.read()

            image_size_kb = len(image_data) / 1024
            rprint(f"✅ [green]Downloaded[/green] [dim]({image_size_kb:.1f} KB)[/dim]")

            return image_data

        except Exception as e:
            rprint(f"[red]❌ Download failed: {str(e)}[/red]")
            return None


class WordImageSearchService:
    """Service for searching images suitable for vocabulary learning (Anki cards)."""

    def __init__(self, image_service: GoogleImageSearchService | None = None):
        if image_service is None:
            image_service = GoogleImageSearchService()
        self._image_service = image_service

    def search(
        self,
        word: str,
        definition: str | None = None,
        num_results: int = 3,
        img_size: Literal[
            "ICON", "SMALL", "MEDIUM", "LARGE", "XLARGE", "XXLARGE", "HUGE"
        ] = "SMALL",
        img_type: Literal["clipart", "face", "lineart", "stock", "photo", "animated"]
        | None = "clipart",
        keywords: list[str] | None = None,
        exclude_terms: list[str] | None = None,
    ) -> list[dict]:
        """
        Search for word-related images.

        Args:
            word: The word to search for
            definition: Optional definition for context
            num_results: Number of results desired
            img_size: Image size preference
            img_type: Image type preference (clipart recommended for vocabulary)
            keywords: Optional AI-provided keywords for better targeting
            exclude_terms: Optional terms to exclude from search

        Returns:
            List of image info dictionaries
        """
        # Build search query
        if keywords and len(keywords) > 0:
            # Use AI-provided keywords
            context = f" ({definition[:40]}...)" if definition else ""
            rprint(
                f"🎯 [bold cyan]Searching '{word}'{context}:[/bold cyan] [yellow]{', '.join(keywords)}[/yellow]"
            )

            all_images = []
            for keyword in keywords:
                query = self._build_query(keyword, exclude_terms)
                images = self._image_service.search(
                    query=query,
                    num_results=num_results * 2,  # Get more to filter
                    img_size=img_size,
                    img_type=img_type,
                )
                all_images.extend(images)

                if len(all_images) >= num_results:
                    break

            return all_images[:num_results]

        else:
            # Fallback: use word directly
            query = self._build_query(word, exclude_terms)
            images = self._image_service.search(
                query=query,
                num_results=num_results,
                img_size=img_size,
                img_type=img_type,
            )
            return images

    def _build_query(self, base_term: str, exclude_terms: list[str] | None) -> str:
        """
        Build search query with exclusions.

        Args:
            base_term: Main search term
            exclude_terms: Terms to exclude (will be prefixed with -)

        Returns:
            Formatted query string
        """
        query = base_term

        if exclude_terms:
            exclusions = " ".join(f"-{term}" for term in exclude_terms)
            query = f"{query} {exclusions}"

        return query

    def filter_results(
        self,
        images: list[dict],
        blacklist_keywords: list[str] | None = None,
    ) -> list[dict]:
        """
        Filter image results based on title and context.

        Args:
            images: List of image info dictionaries
            blacklist_keywords: Keywords to filter out

        Returns:
            Filtered list of images
        """
        if not blacklist_keywords:
            return images

        filtered = []
        for img in images:
            title = img.get("title", "").lower()
            context = img.get("context_link", "").lower()

            # Check if any blacklist keyword appears
            is_blacklisted = any(
                keyword.lower() in title or keyword.lower() in context
                for keyword in blacklist_keywords
            )

            if not is_blacklisted:
                filtered.append(img)

        return filtered

#!/usr/bin/env python
import asyncio

from rich import print as rprint

from ankinote.services import AIWordDictService


# Example usage and testing
async def main():
    """Test the updated service."""

    service = AIWordDictService()

    async with service:
        # Test Case 1: Concrete object
        rprint("\n[bold cyan]Test 1: Concrete object (bicycle)[/bold cyan]")
        result = await service.analyze_word("bicycle")
        rprint(result[0])

        # Verify pronunciation format
        assert result[0]["us_pron"].startswith("/") and result[0]["us_pron"].endswith(
            "/"
        )
        assert result[0]["uk_pron"].startswith("/") and result[0]["uk_pron"].endswith(
            "/"
        )
        rprint("[green]✓ Pronunciations have slashes[/green]")

        # Verify definition format
        for i, defn in enumerate(result[0]["definitions"]):
            assert len(defn) == 3, f"Definition {i} should have 3 elements"
            assert isinstance(defn[0], bool), (
                f"Definition {i} image_friendly should be boolean"
            )
        rprint("[green]✓ Definitions have correct format[/green]")

        # Verify no word-level image_friendly
        assert "image_friendly" not in result[0], (
            "Should not have word-level image_friendly"
        )
        rprint("[green]✓ No word-level image_friendly[/green]")

        # Test Case 2: Abstract concept
        rprint("\n[bold cyan]Test 2: Abstract concept (justice)[/bold cyan]")
        result = await service.analyze_word("justice")
        rprint(result[0])

        # Check that abstract definitions have image_friendly=false
        for defn in result[0]["definitions"]:
            rprint(f"  Definition: {defn[1][:50]}... -> image_friendly={defn[0]}")

        # Test Case 3: Mixed definitions
        rprint("\n[bold cyan]Test 3: Mixed definitions (bank)[/bold cyan]")
        result = await service.analyze_word("bank")
        rprint(result[0])

        for defn in result[0]["definitions"]:
            rprint(f"  Definition: {defn[1][:50]}... -> image_friendly={defn[0]}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

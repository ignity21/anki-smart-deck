"""Card Generator for Anki Smart Deck.

This module generates Anki cards using AI services and AnkiConnect.
"""

import re
from typing import Any

from rich import print as rprint

from anki_smart_deck.services.ai import GoogleAIService
from anki_smart_deck.services.anki_connect import AnkiConnectClient


class CardGenerator:
    """Generator for creating Anki cards from words."""

    def __init__(
        self,
        ai_service: GoogleAIService,
        anki_client: AnkiConnectClient,
        deck_name: str,
        model_name: str = "AI Word (R)",
    ):
        """Initialize card generator.

        Args:
            ai_service: Google AI service for generating card content
            anki_client: AnkiConnect client for adding cards
            deck_name: Target Anki deck name
            model_name: Anki note type name
        """
        self._ai_service = ai_service
        self._anki_client = anki_client
        self._deck_name = deck_name
        self._model_name = model_name

    def _format_definitions(self, definitions: list[list[str]]) -> tuple[str, str]:
        """Format definition pairs into EN and CN strings.

        Args:
            definitions: List of [en, cn] definition pairs

        Returns:
            Tuple of (english_definitions, chinese_definitions)
        """
        if not definitions:
            return "", ""

        en_defs = []
        cn_defs = []

        for i, (en, cn) in enumerate(definitions, 1):
            en_defs.append(f"{i}. {en}")
            cn_defs.append(f"{i}. {cn}")

        # Join with <br> for proper HTML line breaks in Anki
        return "<br>".join(en_defs), "<br>".join(cn_defs)

    def _format_examples(self, examples: dict[str, list[list[str]]]) -> str:
        """Format examples into a single string with HTML formatting.

        Args:
            examples: Dict mapping phrase to [en, cn] example pairs

        Returns:
            Formatted examples string with HTML tags
        """
        if not examples:
            return ""

        formatted = []
        for phrase, example_pairs in examples.items():
            for en, cn in example_pairs:
                # Add bullet point with line breaks
                # AI already returns <b>word</b> format, no conversion needed
                formatted.append(f"• {en}")
                formatted.append(
                    f"&nbsp;&nbsp;{cn}"
                )  # Use non-breaking space for indentation

        # Join with <br> for proper line breaks in Anki
        return "<br>".join(formatted)

    def _format_synonyms(self, synonyms: list[str]) -> str:
        """Format synonyms list into a string.

        Args:
            synonyms: List of synonym words

        Returns:
            Comma-separated synonyms
        """
        return ", ".join(synonyms) if synonyms else ""

    def _format_notes(self, notes: list[str]) -> str:
        """Format notes list into a string with HTML formatting.

        Args:
            notes: List of notes (e.g., BrE variants)

        Returns:
            Formatted notes string with HTML tags
        """
        if not notes:
            return ""

        # Join with <br> for proper line breaks in Anki
        return "<br>".join(f"• {note}" for note in notes)

    async def _find_existing_note(self, word: str, word_form: str) -> int | None:
        """Find existing note with matching word and word form.

        Args:
            word: The word to search for
            word_form: The word form (part of speech) to match

        Returns:
            Note ID if found, None otherwise
        """
        # Step 1: Search for notes with this word in the deck
        # Escape quotes in word for Anki query
        escaped_word = word.replace('"', '\\"')
        query = f'deck:"{self._deck_name}" "Word:{escaped_word}"'

        try:
            note_ids = await self._anki_client.find_notes(query)

            if not note_ids:
                return None

            # Step 2: Get detailed info and find matching word form
            notes_info = await self._anki_client.notes_info(note_ids)

            for note in notes_info:
                # Check if this note has the same word form
                note_word_form = note["fields"].get("Word Form", {}).get("value", "")
                if note_word_form == word_form:
                    rprint(
                        f"[yellow]⚠️  Found existing note:[/yellow] ID={note['noteId']} "
                        f"[dim](Word: {word}, Form: {word_form})[/dim]"
                    )
                    return note["noteId"]

            return None

        except Exception as e:
            rprint(f"[yellow]⚠️  Error searching for existing note:[/yellow] {str(e)}")
            return None

    async def _get_user_notes(self, note_id: int) -> str:
        """Get the User Notes field from an existing note.

        Args:
            note_id: The note ID

        Returns:
            The User Notes field value, empty string if not found
        """
        try:
            notes_info = await self._anki_client.notes_info([note_id])
            if notes_info:
                return notes_info[0]["fields"].get("User Notes", {}).get("value", "")
        except Exception as e:
            rprint(f"[yellow]⚠️  Error getting user notes:[/yellow] {str(e)}")

        return ""

    async def generate_card(
        self, word: str, tags: list[str] | None = None, force_new: bool = False
    ) -> tuple[int, bool]:
        """Generate and add a card for the given word.

        Args:
            word: The word to create a card for
            tags: Optional tags to add to the card
            force_new: If True, always create new card even if one exists

        Returns:
            Tuple of (note_id, is_updated) where is_updated is True if an existing note was updated

        Raises:
            ValueError: If AI response is invalid
            RuntimeError: If card creation fails
        """
        rprint(
            f"\n[bold cyan]═══ Generating card for:[/bold cyan] [yellow]{word}[/yellow] [bold cyan]═══[/bold cyan]"
        )

        # Step 1: Generate card data using AI
        rprint("\n[cyan]Step 1:[/cyan] Generating card content with AI...")
        ai_response = await self._ai_service.generate_cards(word)

        if not ai_response or not isinstance(ai_response, list) or not ai_response:
            raise ValueError(f"Invalid AI response for word: {word}")

        # Take the first word form (could be multiple if word has multiple parts of speech)
        card_data = ai_response[0]

        rprint(
            f"[green]✓[/green] AI generated data for: [yellow]{card_data.get('word', word)}[/yellow]"
        )
        rprint(f"  Word form: [dim]{card_data.get('word_form', 'N/A')}[/dim]")
        rprint(f"  Frequency: [dim]{card_data.get('frequency', 'N/A')}[/dim]")

        # Step 2: Check for existing note
        existing_note_id = None
        if not force_new:
            rprint("\n[cyan]Step 2:[/cyan] Checking for existing card...")
            existing_note_id = await self._find_existing_note(
                word=card_data.get("word", word),
                word_form=card_data.get("word_form", ""),
            )

            if existing_note_id:
                rprint(
                    f"[yellow]  → Will update existing card (ID: {existing_note_id})[/yellow]"
                )
            else:
                rprint("[green]  → No existing card found, will create new[/green]")
        else:
            rprint("\n[cyan]Step 2:[/cyan] Skipped (force_new=True)")

        # Step 3: Format fields according to note type
        step_num = 3 if not force_new else 2
        rprint(f"\n[cyan]Step {step_num}:[/cyan] Formatting card fields...")

        def_en, def_cn = self._format_definitions(card_data.get("definitions", []))

        fields = {
            "Word": card_data.get("word", word),
            "US Pronunciation": card_data.get("us_pron", ""),
            "UK Pronunciation": card_data.get("uk_pron", ""),
            "US Audio": "",  # Will be added later with TTS
            "UK Audio": "",  # Will be added later with TTS
            "Word Form": card_data.get("word_form", ""),
            "Definition EN": def_en,
            "Definition CN": def_cn,
            "Synonyms": self._format_synonyms(card_data.get("synonyms", [])),
            "Examples": self._format_examples(card_data.get("examples", {})),
            "Images": "",  # Will be added later with image search
            "Notes": self._format_notes(card_data.get("notes", [])),
            "User Notes": "",  # Will be preserved if updating
        }

        rprint(f"[green]✓[/green] Formatted {len(fields)} fields")

        # Step 4: Add or update in Anki
        step_num += 1
        is_updated = False

        if existing_note_id:
            # UPDATE existing note
            rprint(f"\n[cyan]Step {step_num}:[/cyan] Updating existing card in Anki...")

            # Preserve User Notes field
            user_notes = await self._get_user_notes(existing_note_id)
            if user_notes:
                fields["User Notes"] = user_notes
                rprint(f"[dim]  → Preserved User Notes ({len(user_notes)} chars)[/dim]")
            else:
                # Remove User Notes from update to avoid clearing it
                fields.pop("User Notes", None)

            try:
                await self._anki_client.update_note_fields(existing_note_id, fields)

                rprint(
                    f"[bold green]✓ Updated![/bold green] Card ID: [yellow]{existing_note_id}[/yellow]"
                )
                return existing_note_id, True

            except Exception as e:
                rprint(f"[red]✗ Failed to update card:[/red] {str(e)}")
                raise RuntimeError(f"Failed to update card in Anki: {str(e)}") from e

        else:
            # CREATE new note
            rprint(f"\n[cyan]Step {step_num}:[/cyan] Adding new card to Anki...")

            try:
                note_id = await self._anki_client.add_note(
                    deck_name=self._deck_name,
                    model_name=self._model_name,
                    fields=fields,
                    tags=tags or ["ai-generated"],
                )

                rprint(
                    f"[bold green]✓ Created![/bold green] Card ID: [yellow]{note_id}[/yellow]"
                )
                return note_id, False

            except Exception as e:
                rprint(f"[red]✗ Failed to add card:[/red] {str(e)}")
                raise RuntimeError(f"Failed to add card to Anki: {str(e)}") from e

    async def generate_cards_batch(
        self, words: list[str], tags: list[str] | None = None, force_new: bool = False
    ) -> dict[str, tuple[int | None, bool]]:
        """Generate cards for multiple words.

        Args:
            words: List of words to create cards for
            tags: Optional tags to add to all cards
            force_new: If True, always create new cards even if they exist

        Returns:
            Dict mapping word to (note_id, is_updated) tuple (None if failed)
        """
        rprint(f"\n[bold cyan]═══ Batch generating {len(words)} cards ═══[/bold cyan]")

        results: dict[str, tuple[int | None, bool]] = {}

        for i, word in enumerate(words, 1):
            rprint(f"\n[dim]───── [{i}/{len(words)}] ─────[/dim]")

            try:
                note_id, is_updated = await self.generate_card(
                    word, tags, force_new=force_new
                )
                results[word] = (note_id, is_updated)
            except Exception as e:
                rprint(f"[red]✗ Error generating card for '{word}':[/red] {str(e)}")
                results[word] = (None, False)

        # Summary
        created = sum(1 for nid, upd in results.values() if nid and not upd)
        updated = sum(1 for nid, upd in results.values() if nid and upd)
        failed = sum(1 for nid, _ in results.values() if not nid)

        rprint(f"\n[bold cyan]═══ Batch Summary ═══[/bold cyan]")
        rprint(f"[green]✓ Created:[/green] {created}")
        rprint(f"[yellow]↻ Updated:[/yellow] {updated}")
        rprint(f"[red]✗ Failed:[/red] {failed}")

        return results


if __name__ == "__main__":
    import asyncio

    async def main():
        """Example usage of CardGenerator."""
        # Initialize services
        ai_service = GoogleAIService()
        anki_client = AnkiConnectClient()

        async with ai_service, anki_client:
            # Create card generator
            generator = CardGenerator(
                ai_service=ai_service,
                anki_client=anki_client,
                deck_name="English::AI Words",
                model_name="AI Word (R)",
            )

            # Generate a single card (will update if exists)
            word = "serendipity"
            note_id, is_updated = await generator.generate_card(
                word, tags=["example", "beautiful-word"]
            )

            if is_updated:
                rprint(
                    f"\n[bold yellow]Card updated successfully![/bold yellow] Note ID: {note_id}"
                )
            else:
                rprint(
                    f"\n[bold green]Card created successfully![/bold green] Note ID: {note_id}"
                )

            # Or generate multiple cards
            # words = ["serendipity", "ephemeral", "eloquent"]
            # results = await generator.generate_cards_batch(words)

    asyncio.run(main())

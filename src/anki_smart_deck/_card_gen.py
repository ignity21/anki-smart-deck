"""Card Generator for Anki Smart Deck.

This module generates Anki cards using AI services and AnkiConnect.
"""

import shortuuid
from rich import print as rprint

from anki_smart_deck.services.ai import GoogleAIService
from anki_smart_deck.services.anki_connect import AnkiConnectClient
from anki_smart_deck.services.image_search import GoogleImageSearchService
from anki_smart_deck.services.tts import GoogleTTSService


class CardGenerator:
    """Generator for creating Anki cards from words."""

    def __init__(
        self,
        ai_service: GoogleAIService,
        anki_client: AnkiConnectClient,
        tts_service: GoogleTTSService,
        image_service: GoogleImageSearchService,
        deck_name: str,
        model_name: str = "AI Word (R)",
    ):
        """Initialize card generator.

        Args:
            ai_service: Google AI service for generating card content
            anki_client: AnkiConnect client for adding cards
            tts_service: Google TTS service for generating audio
            image_service: Google Image Search service for finding images
            deck_name: Target Anki deck name
            model_name: Anki note type name
        """
        self._ai_service = ai_service
        self._anki_client = anki_client
        self._tts_service = tts_service
        self._image_service = image_service
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

    async def _format_examples(
        self, examples: dict[str, list[list[str]]], word: str
    ) -> str:
        """Format examples into a single string with HTML formatting and TTS audio.

        Args:
            examples: Dict mapping phrase to [en, cn] example pairs
            word: The word being defined (for TTS generation)

        Returns:
            Formatted examples string with HTML tags and audio
        """
        if not examples:
            return ""

        formatted = []
        example_count = sum(len(pairs) for pairs in examples.values())
        current_example = 0

        for phrase, example_pairs in examples.items():
            for en, cn in example_pairs:
                current_example += 1

                # Generate TTS audio for the example sentence (without HTML)
                audio_tag = ""
                try:
                    audio_result = await self._generate_audio(
                        text=en, language_code="en-US", audio_type="sentence"
                    )
                    if audio_result:
                        audio_tag = f" {audio_result[1]}"
                except Exception as e:
                    rprint(
                        f"[yellow]⚠️  Failed to generate audio for example:[/yellow] {str(e)}"
                    )

                # Add bold formatting to the phrase in the English sentence
                en_formatted = en.replace(phrase, f"<b>{phrase}</b>")

                # Add bullet point with English sentence and audio
                formatted.append(f"• {en_formatted}{audio_tag}")
                # Add Chinese translation with indentation
                formatted.append(f"&nbsp;&nbsp;{cn}")

                # Add separator after each example group (except the last one)
                if current_example < example_count:
                    formatted.append("<hr>")

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

    async def _search_and_store_images(self, word: str, num_images: int = 2) -> str:
        """Search for images and store them in Anki.

        Args:
            word: The word to search images for
            num_images: Number of images to search and store

        Returns:
            HTML string with image tags for Anki
        """
        try:
            # Search for images
            images = self._image_service.search_word_image(
                word=word, num_results=num_images, img_size="SMALL", prefer_simple=True
            )

            if not images:
                rprint("[yellow]  ⚠️  No images found[/yellow]")
                return ""

            image_tags = []
            for i, img_info in enumerate(images[:num_images], 1):
                try:
                    # Use thumbnail URL instead of original URL to avoid 403 errors
                    thumbnail_url = img_info.get("thumbnail", "")
                    if not thumbnail_url:
                        rprint(f"[yellow]  ⚠️  No thumbnail for image {i}[/yellow]")
                        continue

                    # Download thumbnail image
                    image_data = self._image_service.download_image(thumbnail_url)

                    if image_data:
                        # Generate filename
                        file_id = shortuuid.uuid()
                        # Thumbnails are usually JPEG
                        filename = f"img_{word}_{file_id}.jpg"

                        # Store in Anki media folder
                        stored_filename = await self._anki_client.store_media_file(
                            filename=filename, data=image_data
                        )

                        # Add image tag
                        image_tags.append(f'<img src="{stored_filename}">')
                        rprint(
                            f"  [green]✓[/green] Stored image {i}: [dim]{stored_filename}[/dim]"
                        )

                except Exception as e:
                    rprint(f"[yellow]  ⚠️  Failed to process image {i}:[/yellow] {str(e)}")
                    continue

            # Join images with space
            return " ".join(image_tags) if image_tags else ""

        except Exception as e:
            rprint(f"[yellow]⚠️  Image search failed:[/yellow] {str(e)}")
            return ""

    def _generate_syllabication(self, word: str, us_pron: str) -> str:
        """Generate syllabication from word and pronunciation.

        Args:
            word: The word to syllabicate
            us_pron: US pronunciation (IPA) for reference

        Returns:
            Syllabicated word (e.g., "ser-en-dip-i-ty")
        """
        # This is a simple heuristic approach
        # For production, you might want to use a proper syllabication library
        # or add syllabication to the AI prompt

        # For now, we'll use a basic pattern based on common syllable breaks
        # This could be improved with AI generation or a syllabication library

        # Simple heuristic: split on vowel-consonant boundaries
        # But this is very basic - ideally syllabication should come from AI
        syllabified = word.lower()

        # Add hyphens before consonants that follow vowels
        # This is a placeholder - real syllabication is complex
        vowels = "aeiouAEIOU"
        result = []
        prev_vowel = False

        for i, char in enumerate(syllabified):
            is_vowel = char in vowels
            if i > 0 and not is_vowel and prev_vowel and i < len(syllabified) - 1:
                # Check if next char is also consonant
                if i + 1 < len(syllabified) and syllabified[i + 1] not in vowels:
                    result.append("-")
            result.append(char)
            prev_vowel = is_vowel

        return "".join(result)

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

    async def _generate_audio(
        self, text: str, language_code: str, audio_type: str = "word"
    ) -> tuple[str, str] | None:
        """Generate audio file for word pronunciation.

        Args:
            text: The text to synthesize
            language_code: Language code ("en-US" or "en-GB")
            audio_type: Type of audio ("word" or "sentence")

        Returns:
            Tuple of (filename, anki_sound_tag) or None if failed
        """
        try:
            # Generate unique filename with prefix
            file_id = shortuuid.uuid()
            filename = f"tts_{audio_type}_{file_id}.mp3"

            # Synthesize speech with random WaveNet voice
            (
                audio_data,
                voice_name,
            ) = await self._tts_service.synthesize_with_random_voice(
                text=text,
                language_code=language_code,
            )

            # Store in Anki media folder
            stored_filename = await self._anki_client.store_media_file(
                filename=filename, data=audio_data
            )

            # Return Anki sound tag format
            anki_sound_tag = f"[sound:{stored_filename}]"
            rprint(f"  [green]✓[/green] Generated audio: [dim]{stored_filename}[/dim]")

            return stored_filename, anki_sound_tag

        except Exception as e:
            rprint(
                f"[yellow]⚠️  Failed to generate {language_code} audio:[/yellow] {str(e)}"
            )
            return None

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
        self, word: str, tags: list[str] | None = None, force_new: bool = False, include_images: bool = True
    ) -> tuple[int, bool]:
        """Generate and add a card for the given word.

        Args:
            word: The word to create a card for
            tags: Optional tags to add to the card
            force_new: If True, always create new card even if one exists
            include_images: If True, search and add images to the card (default: True)

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

        # Step 3: Generate TTS audio
        step_num = 3 if not force_new else 2
        rprint(f"\n[cyan]Step {step_num}:[/cyan] Generating TTS audio...")

        # Generate US audio
        us_audio_result = await self._generate_audio(
            text=card_data.get("word", word), language_code="en-US", audio_type="word"
        )
        us_audio = us_audio_result[1] if us_audio_result else ""

        # Generate UK audio
        uk_audio_result = await self._generate_audio(
            text=card_data.get("word", word), language_code="en-GB", audio_type="word"
        )
        uk_audio = uk_audio_result[1] if uk_audio_result else ""

        # Step 4: Format fields according to note type
        step_num += 1
        rprint(f"\n[cyan]Step {step_num}:[/cyan] Formatting card fields...")

        def_en, def_cn = self._format_definitions(card_data.get("definitions", []))
        frequency = card_data.get("frequency", "")

        # Generate examples with TTS audio (async)
        examples_formatted = await self._format_examples(
            card_data.get("examples", {}), card_data.get("word", word)
        )

        # Get syllabication from AI or generate as fallback
        syllabication = card_data.get("syllabication", "")
        if not syllabication:
            syllabication = self._generate_syllabication(
                card_data.get("word", word), card_data.get("us_pron", "")
            )

        # Step 5: Search and download images (optional)
        images_html = ""
        if include_images:
            step_num += 1
            rprint(f"\n[cyan]Step {step_num}:[/cyan] Searching for images...")
            images_html = await self._search_and_store_images(
                card_data.get("word", word), num_images=2
            )
        else:
            rprint("\n[dim]ℹ️  Skipping image search (include_images=False)[/dim]")

        fields = {
            "Word": card_data.get("word", word),
            "US Pronunciation": card_data.get("us_pron", ""),
            "UK Pronunciation": card_data.get("uk_pron", ""),
            "US Audio": us_audio,
            "UK Audio": uk_audio,
            "Word Form": card_data.get("word_form", ""),
            "Definition EN": def_en,
            "Definition CN": def_cn,
            "Synonyms": self._format_synonyms(card_data.get("synonyms", [])),
            "Examples": examples_formatted,
            "Images": images_html,
            "Notes": self._format_notes(card_data.get("notes", [])),
            "User Notes": "",  # Will be preserved if updating
            "Frequency": frequency,
            "Syllabication": syllabication,
        }

        rprint(f"[green]✓[/green] Formatted {len(fields)} fields")

        # Step N: Prepare tags (include frequency tag)
        step_num += 1
        rprint(f"\n[cyan]Step {step_num}:[/cyan] Preparing tags...")

        all_tags = tags.copy() if tags else []
        all_tags.append("ai-generated")

        # Add frequency tag if available
        if frequency:
            all_tags.append(frequency)
            rprint(f"[dim]  → Added frequency tag: {frequency}[/dim]")

        rprint(f"[green]✓[/green] Tags: [dim]{', '.join(all_tags)}[/dim]")

        # Step 6: Add or update in Anki
        step_num += 1

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
                    tags=all_tags,
                )

                rprint(
                    f"[bold green]✓ Created![/bold green] Card ID: [yellow]{note_id}[/yellow]"
                )
                return note_id, False

            except Exception as e:
                rprint(f"[red]✗ Failed to add card:[/red] {str(e)}")
                raise RuntimeError(f"Failed to add card to Anki: {str(e)}") from e

    async def generate_cards_batch(
        self, words: list[str], tags: list[str] | None = None, force_new: bool = False, include_images: bool = True
    ) -> dict[str, tuple[int | None, bool]]:
        """Generate cards for multiple words.

        Args:
            words: List of words to create cards for
            tags: Optional tags to add to all cards
            force_new: If True, always create new cards even if they exist
            include_images: If True, search and add images to cards (default: True)

        Returns:
            Dict mapping word to (note_id, is_updated) tuple (None if failed)
        """
        rprint(f"\n[bold cyan]═══ Batch generating {len(words)} cards ═══[/bold cyan]")

        results: dict[str, tuple[int | None, bool]] = {}

        for i, word in enumerate(words, 1):
            rprint(f"\n[dim]───── [{i}/{len(words)}] ─────[/dim]")

            try:
                note_id, is_updated = await self.generate_card(
                    word, tags, force_new=force_new, include_images=include_images
                )
                results[word] = (note_id, is_updated)
            except Exception as e:
                rprint(f"[red]✗ Error generating card for '{word}':[/red] {str(e)}")
                results[word] = (None, False)

        # Summary
        created = sum(1 for nid, upd in results.values() if nid and not upd)
        updated = sum(1 for nid, upd in results.values() if nid and upd)
        failed = sum(1 for nid, _ in results.values() if not nid)

        rprint("[bold cyan]═══ Batch Summary ═══[/bold cyan]")
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
        tts_service = GoogleTTSService()
        image_service = GoogleImageSearchService()

        async with ai_service, anki_client:
            # Create card generator
            generator = CardGenerator(
                ai_service=ai_service,
                anki_client=anki_client,
                tts_service=tts_service,
                image_service=image_service,
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

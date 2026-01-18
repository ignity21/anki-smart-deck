"""Card Generator for Anki Smart Deck.

This module generates Anki cards using AI services and AnkiConnect.
"""

import shortuuid
from rich import print as rprint

from anki_smart_deck.services.ai import AIWordDictService
from anki_smart_deck.services.anki_connect import AnkiConnectClient
from anki_smart_deck.services.tts import GoogleTTSService


class CardGenerator:
    """Generator for creating Anki cards from words."""

    def __init__(
        self,
        word_service: AIWordDictService,
        anki_client: AnkiConnectClient,
        tts_service: GoogleTTSService,
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
        self._word_service = word_service
        self._anki_client = anki_client
        self._tts_service = tts_service
        self._deck_name = deck_name
        self._model_name = model_name

    def _format_definitions(self, definitions: list[list]) -> str:
        """Format definition tuples into a single string with Chinese following English.

        Args:
            definitions: List of [image_friendly, en, cn] definition tuples

        Returns:
            Formatted definitions string with EN and CN combined
        """
        if not definitions:
            return ""

        formatted_defs = []

        for i, definition in enumerate(definitions, 1):
            # New format: [image_friendly, en, cn]
            if len(definition) >= 3:
                image_friendly, en, cn = definition[0], definition[1], definition[2]
            # Fallback for old format: [en, cn]
            elif len(definition) >= 2:
                en, cn = definition[0], definition[1]
            else:
                continue

            # Format: 1. English definition<br>   中文释义
            formatted_defs.append(f"{i}. {en}")
            formatted_defs.append(f"&nbsp;&nbsp;&nbsp;{cn}")

        # Join with <br> for proper line breaks in Anki
        return "<br>".join(formatted_defs)

    async def _format_examples(
        self,
        examples: dict[str, list[list[str]]],
        word: str,
        include_audio: bool = True,
    ) -> str:
        """Format examples into a single string with HTML formatting and optional TTS audio.

        Args:
            examples: Dict mapping phrase to [en, cn] example pairs
            word: The word being defined (for TTS generation)
            include_audio: If True, generate TTS audio for example sentences

        Returns:
            Formatted examples string with HTML tags and optional audio
        """
        if not examples:
            return ""

        formatted = []
        example_count = sum(len(pairs) for pairs in examples.values())
        current_example = 0

        for phrase, example_pairs in examples.items():
            for en, cn in example_pairs:
                current_example += 1

                # Generate TTS audio for the example sentence (if enabled)
                audio_tag = ""
                if include_audio:
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

    async def _search_and_store_images(self, word: str, definitions: list[list]) -> str:
        """Generate and store images for image-friendly definitions.

        Args:
            word: The word to generate images for
            definitions: List of [image_friendly, en, cn] definition tuples

        Returns:
            HTML string with image tags for Anki
        """
        if not definitions:
            return ""

        image_tags = []

        for i, definition in enumerate(definitions, 1):
            # Check if this definition is image-friendly
            # New format: [image_friendly, en, cn]
            if len(definition) < 3:
                rprint(
                    f"  [dim]→ Skipping image for definition {i} (invalid format)[/dim]"
                )
                continue

            image_friendly, en_definition, cn_definition = (
                definition[0],
                definition[1],
                definition[2],
            )

            if not image_friendly:
                rprint(
                    f"  [dim]→ Skipping image for definition {i} (not image-friendly)[/dim]"
                )
                continue

            try:
                rprint(f"  [cyan]→ Generating image for definition {i}...[/cyan]")

                # Generate image using AI service
                image_data: bytes = await self._word_service.generate_word_image(
                    word=word,
                    definition=en_definition,
                )

                # Generate filename
                file_id = shortuuid.uuid()
                filename = f"img_{word}_{i}_{file_id}.png"

                # Store in Anki media folder
                stored_filename = await self._anki_client.store_media_file(
                    filename=filename, data=image_data
                )

                image_tags.append(f'<img src="{stored_filename}">')
                rprint(
                    f"  [green]✓[/green] Stored image {i}: [dim]{stored_filename}[/dim]"
                )

            except Exception as e:
                rprint(
                    f"[yellow]  ⚠️  Failed to generate/process image for definition {i}:[/yellow] {str(e)}"
                )
                continue

        # Join images with space
        return " ".join(image_tags) if image_tags else ""

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
        self,
        word: str,
        tags: list[str] | None = None,
        force_new: bool = False,
        include_images: bool = True,
        include_example_audio: bool = True,
    ) -> tuple[int, bool]:
        """Generate and add a card for the given word.

        Args:
            word: The word to create a card for
            tags: Optional tags to add to the card
            force_new: If True, always create new card even if one exists
            include_images: If True, search and add images to the card (default: True)
            include_example_audio: If True, generate TTS audio for example sentences (default: True)

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
        ai_response = await self._word_service.analyze_word(word)

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

        definitions = self._format_definitions(card_data.get("definitions", []))
        frequency = card_data.get("frequency", "")

        # Generate examples with optional TTS audio (async)
        if include_example_audio:
            rprint("[dim]  → Including example sentence audio[/dim]")
        else:
            rprint("[dim]  → Skipping example sentence audio[/dim]")

        examples_formatted = await self._format_examples(
            card_data.get("examples", {}),
            card_data.get("word", word),
            include_audio=include_example_audio,
        )

        # Get syllabication from AI (required field now)
        syllabication = card_data.get("syllabication", "")

        # AI already returns pronunciations with slashes
        us_pron = card_data.get("us_pron", "")
        uk_pron = card_data.get("uk_pron", "")

        # Step 5: Search and download images (optional)
        images_html = ""
        if include_images:
            step_num += 1
            rprint(
                f"\n[cyan]Step {step_num}:[/cyan] Generating images for image-friendly definitions..."
            )
            images_html = await self._search_and_store_images(
                word=card_data.get("word", word),
                definitions=card_data.get("definitions", []),
            )
        else:
            rprint("\n[dim]ℹ️  Skipping image generation (include_images=False)[/dim]")

        fields = {
            "Word": card_data.get("word", word),
            "US Pronunciation": us_pron,
            "UK Pronunciation": uk_pron,
            "US Audio": us_audio,
            "UK Audio": uk_audio,
            "Word Form": card_data.get("word_form", ""),
            "Definitions": definitions,
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

    async def analyze_word_batch(
        self,
        words: list[str],
        tags: list[str] | None = None,
        force_new: bool = False,
        include_images: bool = True,
        include_example_audio: bool = True,
    ) -> dict[str, tuple[int | None, bool]]:
        """Generate cards for multiple words.

        Args:
            words: List of words to create cards for
            tags: Optional tags to add to all cards
            force_new: If True, always create new cards even if they exist
            include_images: If True, search and add images to cards (default: True)
            include_example_audio: If True, generate TTS audio for example sentences (default: True)

        Returns:
            Dict mapping word to (note_id, is_updated) tuple (None if failed)
        """
        rprint(f"\n[bold cyan]═══ Batch generating {len(words)} cards ═══[/bold cyan]")

        results: dict[str, tuple[int | None, bool]] = {}

        for i, word in enumerate(words, 1):
            rprint(f"\n[dim]───── [{i}/{len(words)}] ─────[/dim]")

            try:
                note_id, is_updated = await self.generate_card(
                    word,
                    tags,
                    force_new=force_new,
                    include_images=include_images,
                    include_example_audio=include_example_audio,
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

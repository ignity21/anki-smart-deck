import json

from google import genai
from rich import print as rprint

from anki_smart_deck.config import get_config


class AIWordDictService:
    """Service for analyzing words and generating vocabulary card data using Google AI."""

    PROMPT = (
        "Analyze the word '%s' with a focus on American English (AmE) and return a JSON array of objects.\n"
        "Each object MUST strictly follow the structure below and use double quotes for all JSON keys and values:\n\n"
        "{\n"
        '  "word": "string",\n'
        '  "us_pron": "/IPA string/",\n'
        '  "uk_pron": "/IPA string/",\n'
        '  "word_form": "abbreviated string (e.g., n., vt., vi., adj., adv., prep., conj.)",\n'
        '  "frequency": "CEFR level (A1, A2, B1, B2, C1, or C2)",\n'
        '  "syllabication": "syllable breakdown with hyphens (e.g., ser-en-dip-i-ty)",\n'
        '  "definitions": [\n'
        '    [image_friendly, "English definition", "Chinese definition"]\n'
        "  ],\n"
        '  "synonyms": ["string"],\n'
        '  "notes": ["string (including British English variations if applicable)"],\n'
        '  "examples": {\n'
        '    "word or phrase": [\n'
        '      ["English example sentence", "Chinese translation"]\n'
        "    ]\n"
        "  }\n"
        "}\n\n"
        "Strict Rules:\n"
        "1. AMERICAN ENGLISH: All definitions, examples, and spelling must prioritize AmE usage.\n"
        '2. BRITISH ENGLISH: If a British variant exists, add it to "notes" in the format: "BrE: <word>".\n'
        "3. FREQUENCY: Assign exactly ONE CEFR level (A1–C2) for each word form.\n"
        "4. WORD FORM: Use ONLY the following abbreviations: n., vt., vi., adj., adv., prep., conj.\n"
        "5. SYLLABICATION: Provide the correct syllable breakdown with hyphens (e.g., 'formal' → 'for-mal').\n"
        "6. DEFINITIONS MAPPING: Each English definition must align one-to-one with its Chinese translation by array index.\n"
        "7. CHINESE DEFINITIONS: Keep Chinese definitions CONCISE - use 2-4 characters when possible (e.g., '巧合' instead of '偶然发现有价值事物的能力'). Only use longer definitions when absolutely necessary for clarity.\n"
        "8. IMAGE FRIENDLY:\n"
        '   - Set "image_friendly" to true if the word represents a concrete, visible concept (e.g., apple, car, mountain, smile).\n'
        '   - Set "image_friendly" to false for abstract concepts (e.g., justice, concept, ability, although).\n'
        "   - Every definition must have its own image_friendly boolean in the definitions array.\n"
        "   - Guideline: Concrete nouns, most verbs with visible actions, and adjectives describing visual properties are typically image-friendly.\n"
        "9. EXAMPLES:\n"
        "   - Provide natural example sentences without any HTML formatting.\n"
        "   - Each key may contain a maximum of 2 example sentence pairs.\n"
        "10. OUTPUT FORMAT: Respond ONLY with valid raw JSON. Do NOT include explanations, comments, or markdown."
    )

    def __init__(self, model_id: str = "gemini-3-flash-preview"):
        """
        Initialize the word analysis service.

        Args:
            model_id: Google AI model identifier
        """
        self._ai_model_id = model_id
        app_config = get_config()
        self._aclient = genai.Client(api_key=app_config.google_ai_key).aio

    async def __aenter__(self):
        await self._aclient.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._aclient.__aexit__(exc_type, exc, tb)

    async def analyze_word(self, word: str) -> list[dict]:
        """
        Analyze a word and generate structured data for vocabulary cards.

        Args:
            word: The word to analyze

        Returns:
            A list of card dictionaries containing:
                - word: The word itself
                - us_pron: US pronunciation in IPA
                - uk_pron: UK pronunciation in IPA
                - word_form: Part of speech abbreviation
                - frequency: CEFR level
                - syllabication: Syllable breakdown
                - image_friendly: Whether the word is easily visualizable
                - image_keywords: Keywords for image search (or null)
                - definitions: List of [English, Chinese] definition pairs
                - synonyms: List of synonyms
                - notes: Additional notes
                - examples: Dictionary of example sentences

        Raises:
            ValueError: If no response from AI model
        """
        rprint(f"🤖 [cyan]Analyzing word:[/cyan] [yellow]{word}[/yellow]")

        resp = await self._aclient.models.generate_content(
            model=self._ai_model_id, contents=self.PROMPT % word
        )
        resp_txt = resp.text
        if resp_txt is None:
            raise ValueError(f"No response from AI model for word: {word}")

        try:
            cards = json.loads(resp_txt)
            rprint(f"✅ [green]Generated {len(cards)} card(s)[/green]")
            return cards
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from AI model: {e}") from e

    async def generate_word_image(
        self, word: str, definition: str, image_size: int = 150
    ) -> bytes:
        """
        Generate an AI image to help memorize a word using Gemini 2.5 Flash Image.
        """
        rprint(
            f"🎨 [cyan]Generating image for:[/cyan] [yellow]{word}[/yellow] [dim]({definition}...)[/dim]"
        )

        # 针对原生图像模型优化 Prompt
        prompt = (
            f"A bold and clear illustration of '{word}' ({definition}). "
            f"Composition: The main subject should be large and FILL 80-90% OF THE FRAME. "
            f"Minimal margins and very little empty space around the edges. "
            f"Style: Clean, vibrant, high-quality minimalist flashcard icon. "
            f"Details: Flat design, solid colors, white background, no text, no labels. "
            f"The image should be a close-up, making the concept instantly recognizable."
        )

        try:
            # 1. 使用 generate_content 而非 generate_images
            # 2. 修正安全设置的 Category 名称，必须带 HARM_CATEGORY_ 前缀
            response = await self._aclient.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=prompt,
                config={  # pyright: ignore[reportArgumentType]
                    "safety_settings": [
                        {
                            "category": "HARM_CATEGORY_HATE_SPEECH",
                            "threshold": "BLOCK_ONLY_HIGH",
                        },
                        {
                            "category": "HARM_CATEGORY_HARASSMENT",
                            "threshold": "BLOCK_ONLY_HIGH",
                        },
                        {
                            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            "threshold": "BLOCK_ONLY_HIGH",
                        },
                        {
                            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                            "threshold": "BLOCK_ONLY_HIGH",
                        },
                    ],
                },
            )

            # 从响应的 Parts 中提取图像数据
            image_data = None
            if response.candidates and response.candidates[0].content.parts:  # pyright: ignore[reportOptionalMemberAccess]
                for part in response.candidates[0].content.parts:  # pyright: ignore[reportOptionalMemberAccess]
                    if part.inline_data:
                        # 在 google-genai SDK 中，inline_data.data 会自动处理为 bytes
                        image_data = part.inline_data.data
                        break

            if not image_data:
                reason = (
                    response.candidates[0].finish_reason
                    if response.candidates
                    else "Unknown"
                )
                raise ValueError(f"No image data returned. Finish reason: {reason}")

            # 保持原有的 PIL 缩放逻辑
            try:
                import io

                from PIL import Image

                img = Image.open(io.BytesIO(image_data))
                if img.size != (image_size, image_size):
                    img = img.resize((image_size, image_size), Image.Resampling.LANCZOS)
                    output = io.BytesIO()
                    img.save(output, format="PNG")
                    image_data = output.getvalue()
            except ImportError:
                rprint(
                    "[yellow]⚠️  PIL not available, using original image size[/yellow]"
                )

            rprint(
                f"✅ [green]Generated image[/green] [dim]({len(image_data)} bytes)[/dim]"
            )
            return image_data

        except Exception as e:
            raise ValueError(f"Failed to generate image for word '{word}': {e}") from e

import json

from google import genai

from anki_smart_deck.config import get_config


class GoogleAIService:
    PROMPT = (
        "Analyze the word '%s' with a focus on American English (AmE) and return a JSON array of objects.\n"
        "Each object MUST strictly follow the structure below and use double quotes for all JSON keys and values:\n\n"
        "{\n"
        '  "word": "string",\n'
        '  "us_pron": "IPA string",\n'
        '  "uk_pron": "IPA string",\n'
        '  "word_form": "abbreviated string (e.g., n., vt., vi., adj., adv., prep., conj.)",\n'
        '  "frequency": "CEFR level (A1, A2, B1, B2, C1, or C2)",\n'
        '  "definitions": [\n'
        '    ["English definition", "Chinese definition"]\n'
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
        "5. DEFINITIONS MAPPING: Each English definition must align one-to-one with its Chinese translation by array index.\n"
        "6. EXAMPLES:\n"
        "   - Highlight the target word or phrase using <b>...</b> in English sentences.\n"
        "   - Each key may contain a maximum of 2 example sentence pairs.\n"
        "7. OUTPUT FORMAT: Respond ONLY with valid raw JSON. Do NOT include explanations, comments, or markdown."
    )

    def __init__(self, model_id: str = "gemini-3-flash-preview"):
        self._ai_model_id = model_id
        app_config = get_config()
        self._aclient = genai.Client(api_key=app_config.google_ai_key).aio

    async def __aenter__(self):
        await self._aclient.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._aclient.__aexit__(exc_type, exc, tb)

    async def generate_cards(self, word: str) -> list[dict]:
        resp = await self._aclient.models.generate_content(
            model=self._ai_model_id, contents=self.PROMPT % word
        )
        resp_txt = resp.text
        if resp_txt is None:
            raise ValueError("No response from AI model.")
        return json.loads(resp_txt)


if __name__ == "__main__":
    import asyncio

    from rich import print as rprint

    async def main():
        ai_srv = GoogleAIService()
        async with ai_srv:
            return await ai_srv.generate_cards("formal")

    cards = asyncio.run(main())
    rprint(cards)

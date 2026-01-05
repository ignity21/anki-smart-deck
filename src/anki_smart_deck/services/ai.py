import json

from google import genai

from anki_smart_deck.config import get_config


class GoogleAIService:
    PROMPT = (
        "Analyze the word '%s' with a focus on American English (AmE) and return a JSON array of objects. "
        "Each object must follow this structure exactly:\n"
        "{\n"
        "  'word': 'string',\n"
        "  'us_pron': 'IPA string',\n"
        "  'uk_pron': 'IPA string',\n"
        "  'word_form': 'abbreviated string (e.g., n., vt., vi., adj.)',\n"
        "  'frequency': 'string (CEFR level: A1, A2, B1, B2, C1, or C2)',\n"
        "  'definitions': ['array of definition pair ['en def', 'cn def']'],\n"
        "  'synonyms': ['array of strings'],\n"
        "  'notes': ['array of strings including British English variations'],\n"
        "  'examples': {\n"
        "    'word or phrase': ['array of pair ['english', 'chinese_translation'] max 2 example sentences']\n"
        "  }\n"
        "}\n"
        "Strict Rules:\n"
        "1. AMERICAN ENGLISH: All definitions and examples must prioritize AmE usage and spelling.\n"
        "2. BRITISH ENGLISH: If there is a British variant (spelling or different word), add it to 'notes' as 'BrE: [word]'.\n"
        "3. FREQUENCY: Assign a CEFR level (A1-C2) to each word form to indicate its commonality.\n"
        "4. WORD FORM: Use ONLY concise abbreviations (n., vt., vi., adj., adv., prep., conj.).\n"
        "5. ONE-TO-ONE MAPPING: 'def_en' and 'def_cn' must match exactly by index.\n"
        "6. EXAMPLES: Use '**phrase**' formatting in sentences and limit to 2 per key.\n"
        "7. NO MARKDOWN: Respond ONLY with raw JSON."
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

    async def generate_cards(self, word: str) -> str:
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

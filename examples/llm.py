#!/usr/bin/env python
import asyncio
import base64

from litellm import acompletion, aimage_generation
from rich import print as rprint

from ankinote.app import Application
from ankinote.utils import img


async def main():
    # model_id = "gemini/gemini-3.1-flash-lite-preview"
    # image_model_id = "gemini/gemini-2.5-flash-image"
    model_id = "openai/gpt-5-nano"
    image_model_id = "openai/gpt-image-1-mini"
    image_quality = "low"
    image_size = "1024x1024"

    async with Application():
        prompt = "What is the capital of France?"
        response = await acompletion(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )
        resp = response.choices[0].message  # pyright: ignore[reportAttributeAccessIssue]
        rprint(f"Answer: {resp.content}")
        rprint(f"Usage: {response.usage}")  # pyright: ignore[reportAttributeAccessIssue]

        image_prompt = "Create a picture of a nano banana dish in a fancy restaurant with a Gemini theme"
        image_response = await aimage_generation(
            model=image_model_id,
            prompt=image_prompt,
            quality=image_quality,
            n=1,
            size=image_size,
        )
        rprint(f"Usage: {image_response.usage}")

        img_b64: str = image_response.data[0].b64_json  # pyright: ignore[reportAssignmentType, reportOptionalSubscript]
        img_bytes = base64.b64decode(img_b64)

        img_scaled = img.scale(img_bytes, target_size=128)
        with open("generated_image.png", "wb") as f:
            f.write(img_scaled)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python
import asyncio
import base64

from litellm import acompletion, aimage_generation
from rich import print as rprint

from ankinote.app import Application
from ankinote.utils import img


async def main():
    model_id = "gemini-3-flash-preview"
    image_model_id = "gemini-2.5-flash-image"
    async with Application():
        prompt = "What is the capital of France?"
        response = await acompletion(
            model=f"gemini/{model_id}",
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )
        resp = response.choices[0].message  # pyright: ignore[reportAttributeAccessIssue]
        rprint(f"Answer: {resp.content}")
        rprint(f"Usage: {response.usage}")  # pyright: ignore[reportAttributeAccessIssue]

        image_prompt = "Create a picture of a nano banana dish in a fancy restaurant with a Gemini theme"
        image_response = await aimage_generation(
            model=f"gemini/{image_model_id}",
            prompt=image_prompt,
            n=1,
            size="512x512",  # or 1024x1024
        )
        rprint(f"Usage: {image_response.usage}")

        img_b64: str = image_response.data[0].b64_json  # pyright: ignore[reportAssignmentType, reportOptionalSubscript]
        img_bytes = base64.b64decode(img_b64)

        img_scaled = img.scale(img_bytes, target_size=128)
        with open("generated_image.png", "wb") as f:
            f.write(img_scaled)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python
import asyncio

from rich import print as rprint

from ankinote.app import Application
from ankinote.services.tts import GoogleTTSService


async def main():
    language_code = "en-US"
    model = "Wavenet"
    async with Application():
        # 2. Random voice synthesis (English)
        async with GoogleTTSService(
            language_code=language_code,
            model=model,
        ) as us_tts:
            rprint("[bold blue]📋 Available Voices[/bold blue]")
            voices = await us_tts._get_all_voices()
            rprint(voices)

            rprint("\n[bold blue]🎵 Generate English Audio[/bold blue]")
            text_en = "Hello! This is a test of Google text to speech."
            audio_content = await us_tts.synthesize_with_random_voice(text=text_en)
            output_file = "en-US_test.mp3"
            with open(output_file, "wb") as f:
                f.write(audio_content)
            rprint(f"💾 [green]Saved:[/green] [cyan]{output_file}[/cyan]")

        # 3. Random voice synthesis (Japanese)
        async with GoogleTTSService(
            language_code="ja-JP",
            model="Neural2",
        ) as jp_tts:
            rprint("[bold blue]📋 Available Voices[/bold blue]")
            voices = await jp_tts._get_all_voices()
            rprint(voices)

            rprint("\n[bold blue]🎵 Generate Japanese Audio[/bold blue]")
            text_ja = "こんにちは！これはGoogleテキスト読み上げのテストです。"
            audio_content_ja = await jp_tts.synthesize_with_random_voice(
                text=text_ja, speaking_rate=0.9
            )
            output_file_ja = "ja-JP_test.mp3"
            with open(output_file_ja, "wb") as f:
                f.write(audio_content_ja)
            rprint(f"💾 [green]Saved:[/green] [cyan]{output_file_ja}[/cyan]")


if __name__ == "__main__":
    asyncio.run(main())

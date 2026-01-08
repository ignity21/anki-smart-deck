#!/usr/bin/env python
from anki_smart_deck.services.tts import GoogleTTSService
from rich import print as rprint


def main():
    rprint("\n[bold magenta]═══════════════════════════════════════[/bold magenta]")
    rprint("[bold magenta]  Google Cloud TTS - WaveNet 服务[/bold magenta]")
    rprint("[bold magenta]═══════════════════════════════════════[/bold magenta]\n")

    tts_service = GoogleTTSService()

    # 1. 查看可用语音
    rprint("[bold blue]📋 查看可用语音[/bold blue]")
    voices = tts_service.list_all_voices("en-US")
    rprint(voices)

    # 2. 随机语音合成（英语）
    rprint("\n[bold blue]🎵 生成英语音频[/bold blue]")
    text_en = "Hello! This is a test of Google WaveNet text to speech."
    audio_content, voice_name = tts_service.synthesize_with_random_voice(text=text_en)

    output_file = f"output_{voice_name}.mp3"
    with open(output_file, "wb") as out:
        out.write(audio_content)
    rprint(f"💾 [green]已保存:[/green] [cyan]{output_file}[/cyan]")

    # 3. 随机语音合成（中文）
    rprint("\n[bold blue]🎵 生成中文音频[/bold blue]")
    text_cn = "你好，这是 Google WaveNet 语音合成测试。"
    audio_content_cn, voice_name_cn = tts_service.synthesize_with_random_voice(
        text=text_cn, language_code="zh-CN", speaking_rate=0.9
    )

    output_file_cn = f"output_{voice_name_cn}.mp3"
    with open(output_file_cn, "wb") as out:
        out.write(audio_content_cn)
    rprint(f"💾 [green]已保存:[/green] [cyan]{output_file_cn}[/cyan]")

    # 4. 使用指定语音
    rprint("\n[bold blue]🎯 使用指定语音[/bold blue]")
    audio_specific = tts_service.synthesize_with_specific_voice(
        text="This uses a specific voice.",
        voice_name="en-US-Wavenet-D",
        language_code="en-US",
    )

    with open("output_specific.mp3", "wb") as out:
        out.write(audio_specific)
    rprint("💾 [green]已保存:[/green] [cyan]output_specific.mp3[/cyan]")


if __name__ == "__main__":
    main()

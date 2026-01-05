"""
Google Cloud Text-to-Speech API Example
This script demonstrates how to use Google's TTS API to convert text to speech.
"""

from google.cloud import texttospeech


def synthesize_speech(text, output_filename="output.mp3"):
    """
    Convert text to speech using Google Cloud TTS API

    Args:
        text (str): The text to convert to speech
        output_filename (str): The output audio file name
    """
    # Initialize the TTS client
    client = texttospeech.TextToSpeechClient()

    # Set the text input to be synthesized
    synthesis_input = texttospeech.SynthesisInput(text=text)

    # Build the voice request
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",  # Language code
        name="en-US-Neural2-F",  # Specific voice (female neural voice)
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )

    # Select the audio format
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.0,  # Speed (0.25 to 4.0)
        pitch=0.0,  # Pitch (-20.0 to 20.0)
    )

    # Perform the text-to-speech request
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    # Save the audio to a file
    with open(output_filename, "wb") as out:
        out.write(response.audio_content)
        print(f'Audio content written to file "{output_filename}"')


def list_available_voices():
    """
    List all available voices from Google Cloud TTS
    """
    client = texttospeech.TextToSpeechClient()

    # Performs the list voices request
    voices = client.list_voices()

    print("Available voices:")
    for voice in voices.voices:
        # Display the voice's name
        print(f"Name: {voice.name}")

        # Display the supported language codes
        for language_code in voice.language_codes:
            print(f"  Language: {language_code}")

        # Display the SSML Voice Gender
        print(f"  Gender: {voice.ssml_gender.name}")

        # Display the natural sample rate
        print(f"  Sample Rate: {voice.natural_sample_rate_hertz} Hz")
        print()


def synthesize_ssml(ssml_text, output_filename="output_ssml.mp3"):
    """
    Convert SSML text to speech for more control over pronunciation

    Args:
        ssml_text (str): SSML formatted text
        output_filename (str): The output audio file name
    """
    client = texttospeech.TextToSpeechClient()

    # Set the SSML input
    synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)

    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US", name="en-US-Neural2-F"
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    with open(output_filename, "wb") as out:
        out.write(response.audio_content)
        print(f'SSML audio content written to file "{output_filename}"')


if __name__ == "__main__":
    # Example 1: Basic text-to-speech
    text = "Hello! This is a demonstration of Google Cloud Text-to-Speech API."
    synthesize_speech(text, "basic_example.mp3")

    # Example 2: Using SSML for more control
    ssml_text = """
    <speak>
        Hello! <break time="500ms"/>
        This is a demonstration of <emphasis level="strong">SSML</emphasis>.
        <prosody rate="slow" pitch="-2st">This part is slow and low.</prosody>
        <prosody rate="fast" pitch="+2st">This part is fast and high!</prosody>
    </speak>
    """
    synthesize_ssml(ssml_text, "ssml_example.mp3")

    # Example 3: List all available voices (commented out to avoid long output)
    # list_available_voices()

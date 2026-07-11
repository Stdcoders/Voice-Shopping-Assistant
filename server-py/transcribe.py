import os
import tempfile
import uuid

from groq_client import client


async def transcribe_audio(audio_bytes: bytes, original_name: str = "audio.webm") -> str:
    """
    Transcribes an audio buffer using Groq's hosted Whisper model.

    Args:
        audio_bytes: raw audio bytes (webm/wav/mp3/etc.)
        original_name: original filename, used to infer extension

    Returns:
        The transcribed text.
    """
    ext = os.path.splitext(original_name)[1] or ".webm"
    temp_path = os.path.join(tempfile.gettempdir(), f"voice-{uuid.uuid4()}{ext}")

    try:
        with open(temp_path, "wb") as f:
            f.write(audio_bytes)

        with open(temp_path, "rb") as f:
            transcription = await client.audio.transcriptions.create(
                file=(os.path.basename(temp_path), f.read()),
                model="whisper-large-v3-turbo",
                response_format="text",
            )

        # response_format "text" returns a plain string from the SDK;
        # fall back to .text in case a structured object comes back instead.
        text = transcription if isinstance(transcription, str) else getattr(transcription, "text", "")
        return (text or "").strip()
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass
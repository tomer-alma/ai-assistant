from __future__ import annotations

import asyncio
import os
import sys
import time
import wave
from pathlib import Path
from typing import Optional

import arabic_reshaper
from bidi.algorithm import get_display
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.settings import load_settings, AppSettings
from src.audio.capture import AudioCapture
from src.audio.vad import Endpointer


def _write_wav(path: Path, pcm16: bytes, sample_rate: int, channels: int) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # int16
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16)


async def _record_utterance(settings: AppSettings, max_seconds: float = 10.0) -> bytes:
    endpointer = Endpointer(
        frame_ms=settings.audio.vad_frame_ms,
        sample_rate=settings.audio.sample_rate,
        finalize_silence_ms=settings.timeouts.stt_finalize_ms,
        aggressiveness=settings.audio.vad_aggressiveness,
    )

    capture = AudioCapture(
        sample_rate=settings.audio.sample_rate,
        channels=settings.audio.channels,
        device=settings.audio.device_input,
        frame_ms=settings.audio.vad_frame_ms,
    )
    try:
        start_time = time.time()
        audio_buf = bytearray()
        async for frame in capture.frames():
            is_speech, is_final = endpointer.process(frame)
            if is_speech:
                audio_buf.extend(frame)
            if is_final:
                break
            if time.time() - start_time > max_seconds:
                break
        return bytes(audio_buf)
    finally:
        await capture.stop()


def _transcribe_file(filepath: Path, model: str, language: Optional[str]) -> str:
    # Use OpenAI Python SDK if available
    try:
        from openai import OpenAI
    except Exception as e:  # pragma: no cover
        return f"OpenAI SDK not available: {e}"

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return "Missing OPENAI_API_KEY in environment"

    client = OpenAI(api_key=api_key)

    try:
        with filepath.open("rb") as f:
            resp = client.audio.transcriptions.create(
                model=model,
                file=f,
                language=language if language else None,
            )
        # The SDK returns an object with .text in most audio APIs
        text = getattr(resp, "text", None)
        if isinstance(resp, dict):
            text = text or resp.get("text")
        return text or "(no text in response)"
    except Exception as e:  # pragma: no cover
        return f"Transcription error: {e}"


async def main() -> int:
    load_dotenv()
    settings = load_settings()

    print(
        "Audio config:",
        f"sr={settings.audio.sample_rate}",
        f"ch={settings.audio.channels}",
        f"input={settings.audio.device_input}",
        f"vad_ms={settings.audio.vad_frame_ms}",
        f"vad_aggr={settings.audio.vad_aggressiveness}",
    )
    print("Models:", f"stt={settings.models.stt}")

    print("Speak now… (Ctrl+C to abort)")
    try:
        audio = await _record_utterance(settings)
    except KeyboardInterrupt:
        print("Interrupted")
        return 130

    if not audio:
        print("No speech captured. Try increasing vad_aggressiveness or frame_ms.")
        return 2

    out_path = Path("/tmp/stt_check.wav")
    _write_wav(out_path, audio, settings.audio.sample_rate, settings.audio.channels)
    kb = len(audio) / 1024
    seconds = len(audio) / (settings.audio.sample_rate * settings.audio.channels * 2)
    print(f"Saved {kb:.1f} KB ({seconds:.2f}s) to {out_path}")

    transcript = _transcribe_file(
        out_path, model=settings.models.stt, language=settings.language.stt_lang
    )
    print("Transcript:")
    reshaped_text = arabic_reshaper.reshape(transcript)
    bidi_text = get_display(reshaped_text)
    print(bidi_text)
    return 0


if __name__ == "__main__":
    try:
        rc = asyncio.run(main())
    except KeyboardInterrupt:
        rc = 130
    sys.exit(rc)



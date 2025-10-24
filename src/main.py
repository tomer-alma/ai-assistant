from __future__ import annotations

import asyncio
import os
import signal
import sys
import time
from typing import Optional, AsyncIterator, List

import pyaudio
from dotenv import load_dotenv

from src.config.settings import load_settings, AppSettings
from src.utils.logging import configure_logging
from src.audio.capture import AudioCapture
from src.audio.vad import Endpointer
from src.audio.playback import AudioPlayback
from src.stt.openai_stt import OpenAIStreamingSTT
from src.llm.openai_llm import OpenAILLM
from src.tts.openai_tts import OpenAIStreamingTTS


class Conversation:
    def __init__(self, settings: AppSettings):
        self._settings = settings
        self._pa = pyaudio.PyAudio()
        self._capture = AudioCapture(
            self._pa,
            sample_rate=settings.audio.sample_rate,
            channels=settings.audio.channels,
            device=settings.audio.device_input,
            frame_ms=settings.audio.vad_frame_ms,
        )
        self._endpointer = Endpointer(
            frame_ms=settings.audio.vad_frame_ms,
            sample_rate=settings.audio.sample_rate,
            finalize_silence_ms=settings.timeouts.stt_finalize_ms,
            aggressiveness=settings.audio.vad_aggressiveness,
        )
        self._stt = OpenAIStreamingSTT(
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            model=settings.models.stt,
            language=settings.language.stt_lang,
            sample_rate=settings.audio.sample_rate,
            channels=settings.audio.channels,
        )
        self._llm = OpenAILLM(
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            model=settings.models.llm,
            system_prompt=settings.language.style_prompt,
        )
        self._tts = OpenAIStreamingTTS(
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            model=settings.models.tts,
            voice=settings.models.tts_voice,
            language=settings.language.tts_lang,
        )
        self._playback = AudioPlayback(
            self._pa,
            sample_rate=settings.audio.sample_rate,
            channels=settings.audio.channels,
            device=settings.audio.device_output,
        )
        # Flag to control when we're actually listening for user speech
        self._is_listening = False
        self._capture_frames_iterator = None

    async def stop(self) -> None:
        await self._capture.stop()
        await self._playback.stop()
        self._pa.terminate()

    def warm_up(self) -> None:
        print("AI Assistant starting…")
        print(
            "Language: STT="
            f"{self._settings.language.stt_lang}, TTS={self._settings.language.tts_lang}"
        )
        print(
            f"Models: STT={self._settings.models.stt}, LLM={self._settings.models.llm}, "
            f"TTS={self._settings.models.tts}"
        )
        print(
            "Audio: sample_rate="
            f"{self._settings.audio.sample_rate}, channels={self._settings.audio.channels}, "
            f"input={self._settings.audio.device_input}, output={self._settings.audio.device_output}, "
            f"vad_frame_ms={self._settings.audio.vad_frame_ms}, vad_aggr={self._settings.audio.vad_aggressiveness}"
        )
    
    def _should_exit(self, text: str) -> bool:
        """Check if the user's input contains an exit keyword."""
        text_lower = text.lower().strip()
        for keyword in self._settings.language.exit_keywords:
            if keyword.lower() in text_lower:
                return True
        return False
    
    async def _say_goodbye(self) -> None:
        """Speak the closing message and prepare for shutdown."""
        closing_text = self._settings.language.closing
        if closing_text:
            # Display with proper bidirectional text support
            if any("\u0590" <= c <= "\u05ea" for c in closing_text):
                from bidi.algorithm import get_display
                import arabic_reshaper
                printable_closing = get_display(arabic_reshaper.reshape(closing_text))
                print(f"\n💬 Assistant: {printable_closing}")
            else:
                print(f"\n💬 Assistant: {closing_text}")
            
            async def closing_stream():
                yield closing_text
            
            audio_stream = self._tts.synth_stream(closing_stream())
            await self._playback.play_stream(audio_stream)
            
            # Brief pause to let the closing message finish
            await asyncio.sleep(0.5)
        
        print("\n👋 Goodbye!")

    async def _gather_speech(self) -> bytes:
        """Gather one utterance worth of audio based on VAD endpointer.
        
        Resets the endpointer state and starts a fresh capture session.
        Includes minimum duration check to filter out spurious detections.
        """
        # Reset endpointer state to avoid contamination from previous turns
        self._endpointer.reset()
        
        # Signal that we're now actively listening
        self._is_listening = True
        
        utterance_frames: List[bytes] = []
        async for frame in self._capture_frames_iterator:
            if not self._is_listening:
                # Stop gathering if playback started
                break
                
            is_speech, is_final = self._endpointer.process(frame)
            if is_speech:
                # print("[VAD] speech frame")
                utterance_frames.append(frame)
            if is_final:
                # print("[VAD] end of speech")
                break

        if not utterance_frames:
            return b""

        # Safety check: Reject very short utterances to prevent echo/noise artifacts
        # Minimum 600ms of speech (30 frames at 20ms each) to filter out TTS echoes
        min_frames = 30
        if len(utterance_frames) < min_frames:
            print(f"[VAD] Rejected short utterance: {len(utterance_frames)} frames (min {min_frames})")
            return b""

        return bytes(b''.join(utterance_frames))

    async def _log_and_tee(self, aname: str, aiterator: AsyncIterator[str]) -> AsyncIterator[str]:
        full_response_parts: List[str] = []
        async for item in aiterator:
            full_response_parts.append(item)
            yield item

        full_response = "".join(full_response_parts)

        # Reverse Hebrew text for correct display in terminals
        if any("\u0590" <= c <= "\u05ea" for c in full_response):
            from bidi.algorithm import get_display
            import arabic_reshaper

            printable_response = get_display(arabic_reshaper.reshape(full_response))
            print(f"{aname}: {printable_response}")
        else:
            print(f"{aname}: {full_response}")

    async def start(self) -> None:
        # Start capture once and keep it running
        self._capture_frames_iterator = self._capture.frames()
        
        # Speak opening greeting
        greeting_text = self._settings.language.greeting
        if greeting_text:
            # Display with proper bidirectional text support
            if any("\u0590" <= c <= "\u05ea" for c in greeting_text):
                from bidi.algorithm import get_display
                import arabic_reshaper
                printable_greeting = get_display(arabic_reshaper.reshape(greeting_text))
                print(f"\n💬 Assistant: {printable_greeting}")
            else:
                print(f"\n💬 Assistant: {greeting_text}")
            
            async def greeting_stream():
                yield greeting_text
            
            audio_stream = self._tts.synth_stream(greeting_stream())
            await self._playback.play_stream(audio_stream)
            
            # CRITICAL: Extra long settling time after greeting to prevent first-utterance echo
            # Greeting is longer than typical responses, needs more time to clear
            settle_time = self._settings.timeouts.post_greeting_settle_ms / 1000.0
            await asyncio.sleep(settle_time)
            
            # Aggressive drain of audio queue to remove ALL greeting echoes
            for i in range(5):
                await self._capture.drain_queue()
                await asyncio.sleep(0.15)
            
            # Final reset of endpointer
            self._endpointer.reset()
            
            # Signal ready state clearly
            print("\n✅ Ready! You can speak now.")
            
            # Brief pause to let user see the ready message before listening starts
            await asyncio.sleep(0.3)
        
        while True:
            print("\n🎤 Listening...")
            audio_bytes = await self._gather_speech()
            if not audio_bytes:
                print("⚠️  No speech detected (or filtered as echo).")
                continue

            # Signal that we're no longer listening (prevents VAD from processing during playback)
            self._is_listening = False

            print("🤔 Thinking...")
            
            # Start timing for latency monitoring
            t_start = time.time()

            async def one_shot_frames() -> AsyncIterator[bytes]:
                yield audio_bytes

            t_stt_start = time.time()
            transcript = await self._stt.transcribe_stream(one_shot_frames())
            t_stt_end = time.time()

            # Reverse Hebrew text for correct display in terminals
            if any("\u0590" <= c <= "\u05ea" for c in transcript):
                from bidi.algorithm import get_display
                import arabic_reshaper
                printable_transcript = get_display(arabic_reshaper.reshape(transcript))
                print(f"STT: {printable_transcript}")
            else:
                print(f"STT: {transcript}")
            
            # Check if user wants to exit
            if self._should_exit(transcript):
                await self._say_goodbye()
                break

            t_llm_start = time.time()
            text_stream = self._llm.stream_reply(transcript)
            logged_text_stream = self._log_and_tee("LLM", text_stream)
            
            t_tts_start = time.time()
            audio_stream = self._tts.synth_stream(logged_text_stream)
            await self._playback.play_stream(audio_stream)
            t_end = time.time()
            
            # Log latency breakdown if enabled
            if self._settings.debugging.show_latency:
                stt_time = (t_stt_end - t_stt_start) * 1000
                total_time = (t_end - t_start) * 1000
                print(f"⏱️  Latency: STT={stt_time:.0f}ms | Total={total_time:.0f}ms")
            
            # Optimized settling time to prevent TTS echo pickup while reducing latency
            settle_time = self._settings.timeouts.post_response_settle_ms / 1000.0
            await asyncio.sleep(settle_time)
            
            # Drain audio queue to ensure TTS echoes are removed
            for i in range(2):
                await self._capture.drain_queue()
                await asyncio.sleep(0.1)
            
            # Final reset of endpointer to clear any lingering VAD state
            self._endpointer.reset()


async def _run() -> None:
    settings = load_settings()
    configure_logging(os.getenv("LOG_LEVEL", "INFO"))
    conversation = Conversation(settings)
    conversation.warm_up()
    try:
        await conversation.start()
    finally:
        await conversation.stop()


def main() -> None:
    load_dotenv()
    
    # Check for required API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable is not set!")
        print("Please create a .env file with your OpenAI API key:")
        print("  OPENAI_API_KEY=your_api_key_here")
        print("\nGet your API key from: https://platform.openai.com/api-keys")
        sys.exit(1)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    stop: Optional[asyncio.Future[None]] = loop.create_future()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: (not stop.done()) and stop.set_result(None))

    async def runner() -> None:
        task = asyncio.create_task(_run())
        await stop
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    try:
        loop.run_until_complete(runner())
    finally:
        loop.close()


if __name__ == "__main__":
    main()


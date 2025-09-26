from __future__ import annotations

from typing import Tuple

import webrtcvad


class VadWrapper:
    def __init__(self, aggressiveness: int = 2) -> None:
        self._vad = webrtcvad.Vad(aggressiveness)

    def is_speech(self, pcm16: bytes, sample_rate: int) -> bool:
        return self._vad.is_speech(pcm16, sample_rate)


class Endpointer:
    """Simple endpointer that finalizes after trailing silence threshold."""

    def __init__(
        self,
        frame_ms: int,
        sample_rate: int,
        finalize_silence_ms: int = 800,
        aggressiveness: int = 2,
    ) -> None:
        self._vad = webrtcvad.Vad(aggressiveness)
        self._sample_rate = sample_rate
        self._frame_ms = frame_ms
        self._finalize_silence_ms = finalize_silence_ms
        self._trailing_silence_ms = 0
        self._in_speech = False

    def process(self, frame: bytes) -> Tuple[bool, bool]:
        """Return (is_speech, is_final)."""
        speech = self._vad.is_speech(frame, self._sample_rate)
        if speech:
            self._trailing_silence_ms = 0
            self._in_speech = True
            return True, False
        if self._in_speech:
            self._trailing_silence_ms += self._frame_ms
            if self._trailing_silence_ms >= self._finalize_silence_ms:
                self._trailing_silence_ms = 0
                self._in_speech = False
                return False, True
        return False, False


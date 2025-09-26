from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional

import sounddevice as sd


class AudioCapture:
    """Asynchronous microphone capture yielding raw PCM16 frames.

    Produces frames of size frame_ms at sample_rate and channels.
    """

    def __init__(self, sample_rate: int, channels: int, device: Optional[str], frame_ms: int = 20) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device
        self.frame_ms = frame_ms

        self._queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=50)
        self._running: bool = False

    def _callback(self, in_data, frames, time, status) -> None:  # type: ignore[no-untyped-def]
        if status:
            # Drop status details for now; skeleton implementation
            pass
        try:
            # Copy bytes; in_data is a memoryview
            self._queue.put_nowait(bytes(in_data))
        except asyncio.QueueFull:
            # Backpressure: drop the oldest frame and insert the newest
            try:
                _ = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                self._queue.put_nowait(bytes(in_data))
            except Exception:
                pass

    async def frames(self) -> AsyncIterator[bytes]:
        """Yield PCM16 frames as bytes (little-endian)."""
        blocksize = int(self.sample_rate * self.frame_ms / 1000)
        dtype = "int16"
        self._running = True
        with sd.RawInputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=dtype,
            blocksize=blocksize,
            callback=self._callback,
            device=self.device if self.device and self.device != "default" else None,
        ):
            while self._running:
                chunk = await self._queue.get()
                yield chunk

    def stop(self) -> None:
        self._running = False


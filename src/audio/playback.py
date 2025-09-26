from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional

import numpy as np
import sounddevice as sd


class AudioPlayback:
    """Asynchronous PCM16 playback with small jitter buffer and optional fade-out."""

    def __init__(self, sample_rate: int, channels: int, device: Optional[str]) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device

        self._queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=100)
        self._running: bool = False

    def _callback(self, out_data, frames, time, status) -> None:  # type: ignore[no-untyped-def]
        if status:
            # Ignore for skeleton
            pass
        try:
            data = self._queue.get_nowait()
        except asyncio.QueueEmpty:
            out_data[:] = b"\x00" * (frames * self.channels * 2)
            return

        needed_bytes = frames * self.channels * 2
        if len(data) < needed_bytes:
            data = data + b"\x00" * (needed_bytes - len(data))
        elif len(data) > needed_bytes:
            data = data[:needed_bytes]
        out_data[:] = data

    async def play_stream(self, source: AsyncIterator[bytes]) -> None:
        """Consume an async stream of PCM16 frames and play them."""
        blocksize = int(self.sample_rate * 20 / 1000)
        self._running = True
        with sd.RawOutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=blocksize,
            callback=self._callback,
            device=self.device if self.device and self.device != "default" else None,
        ):
            async for chunk in source:
                if not self._running:
                    break
                await self._queue.put(chunk)

    async def fade_out_and_stop(self, duration_ms: int = 150) -> None:
        """Fade out queued audio and stop playback."""
        steps = max(1, duration_ms // 20)
        buffered: list[bytes] = []
        while not self._queue.empty():
            try:
                buffered.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        for i in range(steps, 0, -1):
            factor = i / steps
            for chunk in buffered:
                arr = np.frombuffer(chunk, dtype=np.int16)
                faded = (arr.astype(np.float32) * factor).astype(np.int16)
                await self._queue.put(faded.tobytes())
        self._running = False


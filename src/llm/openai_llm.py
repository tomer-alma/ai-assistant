from __future__ import annotations

from typing import AsyncIterator, Iterable, List

from openai import AsyncOpenAI


class OpenAILLM:
    def __init__(self, api_key: str, model: str, system_prompt: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._system = system_prompt

    async def stream_reply(self, user_text: str) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": self._system}, {"role": "user", "content": user_text}],
            temperature=0.5,
            max_tokens=180,
            stream=True,
        )
        async for event in stream:
            delta = event.choices[0].delta.content or ""
            if delta:
                yield delta


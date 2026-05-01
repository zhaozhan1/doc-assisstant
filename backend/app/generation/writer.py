from __future__ import annotations

from collections.abc import AsyncGenerator

from app.llm.base import BaseLLMProvider


class Writer:
    def __init__(self, llm: BaseLLMProvider) -> None:
        self._llm = llm

    async def generate(self, messages: list[dict]) -> str:
        return await self._llm.chat(messages)

    async def generate_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        async for token in self._llm.chat_stream(messages):
            yield token

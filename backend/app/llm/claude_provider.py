from __future__ import annotations

import anthropic

from app.llm.base import BaseLLMProvider


class ClaudeProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str, chat_model: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key, base_url=base_url)
        self._model = chat_model

    async def chat(self, messages: list[dict], **kwargs) -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=messages,
        )
        return response.content[0].text

    async def chat_stream(self, messages: list[dict], **kwargs):
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=4096,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("Claude 不支持 embedding，请配置 Ollama 作为 embed Provider")

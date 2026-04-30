from __future__ import annotations

import httpx

from app.llm.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: str, chat_model: str, embed_model: str) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=120.0)
        self._chat_model = chat_model
        self._embed_model = embed_model

    async def chat(self, messages: list[dict], **kwargs) -> str:
        resp = await self._client.post(
            "/api/chat",
            json={"model": self._chat_model, "messages": messages, "stream": False},
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.post(
            "/api/embed",
            json={"model": self._embed_model, "input": texts},
        )
        resp.raise_for_status()
        return [item["embedding"] for item in resp.json()["embeddings"]]

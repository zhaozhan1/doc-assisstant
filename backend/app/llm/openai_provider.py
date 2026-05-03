from __future__ import annotations

import json

import httpx

from app.llm.base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, base_url: str, api_key: str, chat_model: str, embed_model: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=120.0,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        self._chat_model = chat_model
        self._embed_model = embed_model

    async def chat(self, messages: list[dict], **kwargs) -> str:
        resp = await self._client.post(
            "/chat/completions",
            json={"model": self._chat_model, "messages": messages},
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    async def chat_stream(self, messages: list[dict], **kwargs):
        async with self._client.stream(
            "POST",
            "/chat/completions",
            json={"model": self._chat_model, "messages": messages, "stream": True},
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                payload = line[len("data: "):]
                if payload == "[DONE]":
                    break
                data = json.loads(payload)
                content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                if content:
                    yield content

    async def embed(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.post(
            "/embeddings",
            json={"model": self._embed_model, "input": texts},
        )
        resp.raise_for_status()
        return [item["embedding"] for item in resp.json()["data"]]

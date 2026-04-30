from __future__ import annotations

import httpx
import pytest
import respx

from app.llm.ollama_provider import OllamaProvider


@pytest.fixture
def provider() -> OllamaProvider:
    return OllamaProvider(
        base_url="http://localhost:11434",
        chat_model="qwen2.5:14b",
        embed_model="bge-large-zh-v1.5",
    )


class TestOllamaChat:
    @respx.mock
    @pytest.mark.asyncio
    async def test_chat_returns_content(self, provider: OllamaProvider) -> None:
        respx.post("http://localhost:11434/api/chat").mock(
            return_value=httpx.Response(
                200,
                json={
                    "message": {"role": "assistant", "content": "你好，有什么可以帮你？"},
                },
            )
        )
        result = await provider.chat([{"role": "user", "content": "你好"}])
        assert result == "你好，有什么可以帮你？"

    @respx.mock
    @pytest.mark.asyncio
    async def test_chat_raises_on_error(self, provider: OllamaProvider) -> None:
        respx.post("http://localhost:11434/api/chat").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        with pytest.raises(httpx.HTTPStatusError):
            await provider.chat([{"role": "user", "content": "test"}])


class TestOllamaEmbed:
    @respx.mock
    @pytest.mark.asyncio
    async def test_embed_returns_vectors(self, provider: OllamaProvider) -> None:
        fake_embedding = [0.1, 0.2, 0.3]
        respx.post("http://localhost:11434/api/embed").mock(
            return_value=httpx.Response(
                200,
                json={
                    "embeddings": [{"embedding": fake_embedding}, {"embedding": fake_embedding}],
                },
            )
        )
        result = await provider.embed(["文本1", "文本2"])
        assert len(result) == 2
        assert result[0] == fake_embedding

    @respx.mock
    @pytest.mark.asyncio
    async def test_embed_empty_list(self, provider: OllamaProvider) -> None:
        respx.post("http://localhost:11434/api/embed").mock(return_value=httpx.Response(200, json={"embeddings": []}))
        result = await provider.embed([])
        assert result == []

from __future__ import annotations

import pytest
import respx

from app.llm.openai_provider import OpenAIProvider


@pytest.fixture
def base_url() -> str:
    return "https://mock.test/v1"


@pytest.fixture
def provider(base_url: str) -> OpenAIProvider:
    return OpenAIProvider(
        base_url=base_url,
        api_key="test-key",
        chat_model="test-chat",
        embed_model="test-embed",
    )


class TestChat:
    @respx.mock
    async def test_chat_returns_content(self, provider: OpenAIProvider, base_url: str) -> None:
        respx.post(f"{base_url}/chat/completions").mock(
            return_value=respx.MockResponse(
                200,
                json={"choices": [{"message": {"content": "你好！"}}]},
            )
        )
        result = await provider.chat([{"role": "user", "content": "你好"}])
        assert result == "你好！"

    @respx.mock
    async def test_chat_sends_auth_header(self, provider: OpenAIProvider, base_url: str) -> None:
        route = respx.post(f"{base_url}/chat/completions").mock(
            return_value=respx.MockResponse(
                200,
                json={"choices": [{"message": {"content": "ok"}}]},
            )
        )
        await provider.chat([{"role": "user", "content": "hi"}])
        assert route.calls[0].request.headers["authorization"] == "Bearer test-key"

    @respx.mock
    async def test_chat_sends_model_and_messages(self, provider: OpenAIProvider, base_url: str) -> None:
        route = respx.post(f"{base_url}/chat/completions").mock(
            return_value=respx.MockResponse(
                200,
                json={"choices": [{"message": {"content": "ok"}}]},
            )
        )
        await provider.chat([{"role": "user", "content": "hi"}])
        body = route.calls[0].request.read()
        import json

        data = json.loads(body)
        assert data["model"] == "test-chat"
        assert data["messages"] == [{"role": "user", "content": "hi"}]


class TestChatStream:
    @respx.mock
    async def test_chat_stream_yields_chunks(self, provider: OpenAIProvider, base_url: str) -> None:
        import json

        chunks = [
            f"data: {json.dumps({'choices': [{'delta': {'content': '你'}}]})}\n\n",
            f"data: {json.dumps({'choices': [{'delta': {'content': '好'}}]})}\n\n",
            "data: [DONE]\n\n",
        ]
        respx.post(f"{base_url}/chat/completions").mock(
            return_value=respx.MockResponse(200, content="".join(chunks), content_type="text/event-stream")
        )
        collected = [chunk async for chunk in provider.chat_stream([{"role": "user", "content": "hi"}])]
        assert collected == ["你", "好"]


class TestEmbed:
    @respx.mock
    async def test_embed_returns_vectors(self, provider: OpenAIProvider, base_url: str) -> None:
        respx.post(f"{base_url}/embeddings").mock(
            return_value=respx.MockResponse(
                200,
                json={"data": [{"embedding": [0.1, 0.2, 0.3]}, {"embedding": [0.4, 0.5, 0.6]}]},
            )
        )
        result = await provider.embed(["hello", "world"])
        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

    @respx.mock
    async def test_embed_sends_model_and_input(self, provider: OpenAIProvider, base_url: str) -> None:
        route = respx.post(f"{base_url}/embeddings").mock(
            return_value=respx.MockResponse(
                200,
                json={"data": [{"embedding": [0.1]}]},
            )
        )
        await provider.embed(["test"])
        import json

        body = json.loads(route.calls[0].request.read())
        assert body["model"] == "test-embed"
        assert body["input"] == ["test"]

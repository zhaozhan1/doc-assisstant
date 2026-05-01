from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx

from app.llm.claude_provider import ClaudeProvider
from app.llm.ollama_provider import OllamaProvider

# ---------------------------------------------------------------------------
# OllamaProvider.chat_stream
# ---------------------------------------------------------------------------


class TestOllamaChatStream:
    @respx.mock
    @pytest.mark.asyncio
    async def test_yields_content_tokens(self) -> None:
        """chat_stream should yield individual content tokens from SSE lines."""
        provider = OllamaProvider(
            base_url="http://localhost:11434",
            chat_model="qwen2.5:14b",
            embed_model="bge-large-zh-v1.5",
        )

        # Build a streaming response body with SSE lines
        sse_lines = [
            'data: {"message":{"content":"你"},"done":false}',
            'data: {"message":{"content":"好"},"done":false}',
            'data: {"done":true}',
        ]
        body = "\n".join(sse_lines)

        route = respx.post("http://localhost:11434/api/chat")
        route.mock(
            return_value=httpx.Response(
                200,
                content=body.encode(),
                headers={"content-type": "application/x-ndjson"},
            )
        )

        tokens: list[str] = []
        async for token in provider.chat_stream([{"role": "user", "content": "你好"}]):
            tokens.append(token)

        assert tokens == ["你", "好"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_empty_stream_yields_nothing(self) -> None:
        """An immediate done message should yield no tokens."""
        provider = OllamaProvider(
            base_url="http://localhost:11434",
            chat_model="qwen2.5:14b",
            embed_model="bge-large-zh-v1.5",
        )

        route = respx.post("http://localhost:11434/api/chat")
        route.mock(
            return_value=httpx.Response(
                200,
                content=b'data: {"done":true}\n',
                headers={"content-type": "application/x-ndjson"},
            )
        )

        tokens: list[str] = []
        async for token in provider.chat_stream([{"role": "user", "content": "hi"}]):
            tokens.append(token)

        assert tokens == []


# ---------------------------------------------------------------------------
# ClaudeProvider.chat_stream
# ---------------------------------------------------------------------------


class TestClaudeChatStream:
    @pytest.mark.asyncio
    async def test_yields_content_tokens(self) -> None:
        """chat_stream should yield text chunks from Anthropic stream."""
        provider = ClaudeProvider(
            api_key="test-key",
            base_url="https://api.anthropic.com",
            chat_model="claude-sonnet-4-20250514",
        )

        # Create an async generator that simulates text_stream
        async def fake_text_stream():
            yield "你"
            yield "好"

        # Build a mock context manager for messages.stream()
        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_stream_cm)
        mock_stream_cm.__aexit__ = AsyncMock(return_value=False)
        mock_stream_cm.text_stream = fake_text_stream()

        provider._client.messages.stream = MagicMock(return_value=mock_stream_cm)

        tokens: list[str] = []
        async for token in provider.chat_stream([{"role": "user", "content": "你好"}]):
            tokens.append(token)

        assert tokens == ["你", "好"]

    @pytest.mark.asyncio
    async def test_empty_stream_yields_nothing(self) -> None:
        """An empty stream should yield no tokens."""
        provider = ClaudeProvider(
            api_key="test-key",
            base_url="https://api.anthropic.com",
            chat_model="claude-sonnet-4-20250514",
        )

        async def empty_text_stream():
            return
            yield

        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_stream_cm)
        mock_stream_cm.__aexit__ = AsyncMock(return_value=False)
        mock_stream_cm.text_stream = empty_text_stream()

        provider._client.messages.stream = MagicMock(return_value=mock_stream_cm)

        tokens: list[str] = []
        async for token in provider.chat_stream([{"role": "user", "content": "hi"}]):
            tokens.append(token)

        assert tokens == []

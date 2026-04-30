from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.llm.claude_provider import ClaudeProvider


@pytest.fixture
def provider() -> ClaudeProvider:
    return ClaudeProvider(
        api_key="test-key",
        base_url="https://api.anthropic.com",
        chat_model="claude-sonnet-4-20250514",
    )


class TestClaudeChat:
    @pytest.mark.asyncio
    async def test_chat_returns_content(self, provider: ClaudeProvider) -> None:
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="你好")]
        provider._client.messages.create = AsyncMock(return_value=mock_message)

        result = await provider.chat([{"role": "user", "content": "你好"}])
        assert result == "你好"
        provider._client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_raises_not_implemented(self, provider: ClaudeProvider) -> None:
        with pytest.raises(NotImplementedError, match="Claude 不支持 embedding"):
            await provider.embed(["文本"])

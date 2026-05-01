from __future__ import annotations

import pytest

from app.generation.writer import Writer
from app.llm.base import BaseLLMProvider


class MockStreamLLM(BaseLLMProvider):
    def __init__(self, response: str = "生成的公文内容"):
        self._response = response

    async def chat(self, messages: list[dict], **kwargs) -> str:
        return self._response

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return []

    async def chat_stream(self, messages: list[dict], **kwargs):
        for char in self._response:
            yield char


class TestWriter:
    @pytest.mark.asyncio
    async def test_generate_returns_content(self):
        writer = Writer(MockStreamLLM("测试公文"))
        result = await writer.generate([{"role": "user", "content": "写通知"}])
        assert result == "测试公文"

    @pytest.mark.asyncio
    async def test_generate_stream_yields_tokens(self):
        writer = Writer(MockStreamLLM("你好"))
        tokens = []
        async for token in writer.generate_stream([{"role": "user", "content": "写通知"}]):
            tokens.append(token)
        assert tokens == ["你", "好"]

    @pytest.mark.asyncio
    async def test_generate_empty_response(self):
        writer = Writer(MockStreamLLM(""))
        result = await writer.generate([{"role": "user", "content": "写通知"}])
        assert result == ""

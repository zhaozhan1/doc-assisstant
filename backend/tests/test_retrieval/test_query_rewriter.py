from __future__ import annotations

import pytest

from app.llm.base import BaseLLMProvider
from app.retrieval.query_rewriter import QueryRewriter


class FakeLLM(BaseLLMProvider):
    async def chat(self, messages, **kwargs):
        return "关于2026年工作总结的通知公告"

    async def chat_stream(self, messages, **kwargs):
        yield ""

    async def embed(self, texts):
        return []


class TestQueryRewriter:
    @pytest.mark.asyncio
    async def test_rewrite_returns_string(self):
        rewriter = QueryRewriter(FakeLLM())
        result = await rewriter.rewrite("2026工作总结")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_rewrite_sends_query_in_prompt(self):
        llm = FakeLLM()
        rewriter = QueryRewriter(llm)
        result = await rewriter.rewrite("安全生产通知")
        assert "2026" in result or "工作" in result

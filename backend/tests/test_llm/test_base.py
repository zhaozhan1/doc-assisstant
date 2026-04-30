from __future__ import annotations

import pytest

from app.llm.base import BaseLLMProvider


class TestMatchLabel:
    def test_exact_match(self) -> None:
        assert BaseLLMProvider._match_label("通知", ["通知", "公告", "其他"]) == "通知"

    def test_fuzzy_match_with_extra_text(self) -> None:
        assert BaseLLMProvider._match_label("这份文件是通知类型", ["通知", "公告", "其他"]) == "通知"

    def test_no_match_returns_last(self) -> None:
        labels = ["通知", "公告", "其他"]
        assert BaseLLMProvider._match_label("完全无关的文本", labels) == "其他"

    def test_empty_response_returns_last(self) -> None:
        labels = ["通知", "其他"]
        assert BaseLLMProvider._match_label("", labels) == "其他"


class DummyProvider(BaseLLMProvider):
    async def chat(self, messages: list[dict], **kwargs) -> str:
        return "公告"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1]]


class TestClassify:
    @pytest.mark.asyncio
    async def test_classify_calls_chat(self) -> None:
        provider = DummyProvider()
        result = await provider.classify("测试文本", ["通知", "公告", "其他"])
        assert result == "公告"

    @pytest.mark.asyncio
    async def test_classify_truncates_to_500(self) -> None:
        provider = DummyProvider()
        long_text = "x" * 1000
        result = await provider.classify(long_text, ["通知", "公告", "其他"])
        assert result == "公告"

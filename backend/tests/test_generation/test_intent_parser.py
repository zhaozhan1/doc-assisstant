from __future__ import annotations

import json

import pytest

from app.generation.intent_parser import IntentParser
from app.llm.base import BaseLLMProvider


class MockLLM(BaseLLMProvider):
    def __init__(self, response: str):
        self._response = response

    async def chat(self, messages: list[dict], **kwargs) -> str:
        return self._response

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return []

    async def chat_stream(self, messages: list[dict], **kwargs):
        return
        yield


@pytest.fixture
def mock_llm():
    return MockLLM(
        response=json.dumps({"doc_type": "notice", "topic": "节假日安排", "keywords": ["放假", "节假日", "安排"]})
    )


class TestIntentParser:
    @pytest.mark.asyncio
    async def test_parse_notice(self, mock_llm):
        parser = IntentParser(mock_llm)
        result = await parser.parse("请帮我写一份关于国庆节放假安排的通知")
        assert result.doc_type == "notice"
        assert "放假" in result.keywords or "节假日" in result.keywords
        assert result.raw_input == "请帮我写一份关于国庆节放假安排的通知"

    @pytest.mark.asyncio
    async def test_parse_defaults_on_invalid_json(self):
        bad_llm = MockLLM(response="这不是JSON")
        parser = IntentParser(bad_llm)
        result = await parser.parse("写个东西")
        assert result.doc_type == "report"
        assert result.topic != ""
        assert result.raw_input == "写个东西"

    @pytest.mark.asyncio
    async def test_parse_extracts_keywords(self, mock_llm):
        parser = IntentParser(mock_llm)
        result = await parser.parse("写一份通知")
        assert len(result.keywords) > 0

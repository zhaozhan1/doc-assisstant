from __future__ import annotations

from pathlib import Path

import pytest

from app.generation.docx_formatter import DocxFormatter
from app.generation.intent_parser import IntentParser
from app.generation.prompt_builder import PromptBuilder
from app.generation.template_manager import TemplateManager
from app.generation.writer import Writer
from app.generation.writer_service import WriterService
from app.llm.base import BaseLLMProvider
from app.models.generation import GenerationRequest
from app.models.search import SourceType, UnifiedSearchResult


class FakeStreamLLM(BaseLLMProvider):
    async def chat(self, messages: list[dict], **kwargs) -> str:
        if any("doc_type" in str(m.get("content", "")) for m in messages):
            return '{"doc_type": "notice", "topic": "测试", "keywords": ["测试"]}'
        return "# 关于测试的通知\n\n测试正文内容"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return []

    async def chat_stream(self, messages: list[dict], **kwargs):
        for char in "测试流式内容":
            yield char


class FakeRetriever:
    async def search(self, request) -> list[UnifiedSearchResult]:
        return [
            UnifiedSearchResult(
                source_type=SourceType.LOCAL,
                title="参考文档",
                content="参考内容",
                score=0.9,
                metadata={"doc_date": "2024-01-01"},
            )
        ]

    async def search_local(self, request) -> list[UnifiedSearchResult]:
        return await self.search(request)


@pytest.fixture
def builtin_dir() -> Path:
    return Path(__file__).parent.parent.parent / "app" / "generation" / "templates"


@pytest.fixture
def writer_service(tmp_path: Path, builtin_dir: Path) -> WriterService:
    llm = FakeStreamLLM()
    return WriterService(
        intent_parser=IntentParser(llm),
        prompt_builder=PromptBuilder(max_tokens=2000),
        template_mgr=TemplateManager(builtin_dir=builtin_dir, custom_dir=tmp_path / "custom"),
        writer=Writer(llm),
        docx_formatter=DocxFormatter(output_dir=tmp_path / "output"),
        retriever=FakeRetriever(),
    )


class TestWriterService:
    @pytest.mark.asyncio
    async def test_generate_from_description(self, writer_service: WriterService):
        req = GenerationRequest(description="写一份测试通知")
        result = await writer_service.generate_from_description(req)
        assert result.content != ""
        assert result.template_used == "notice"
        assert result.output_path is not None

    @pytest.mark.asyncio
    async def test_generate_stream(self, writer_service: WriterService):
        req = GenerationRequest(description="写一份测试通知")
        tokens = []
        async for token in writer_service.generate_stream(req):
            tokens.append(token)
        assert len(tokens) > 0
        assert "".join(tokens) == "测试流式内容"

    @pytest.mark.asyncio
    async def test_sources_extracted(self, writer_service: WriterService):
        req = GenerationRequest(description="写一份测试通知")
        result = await writer_service.generate_from_description(req)
        assert len(result.sources) > 0
        assert result.sources[0].title == "参考文档"

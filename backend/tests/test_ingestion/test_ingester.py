from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.config import OCRConfig
from app.db.vector_store import VectorStore
from app.ingestion.ingester import Ingester
from app.llm.base import BaseLLMProvider
from app.models.task import FileResult


class MockLLMProvider(BaseLLMProvider):
    async def chat(self, messages: list[dict], **kwargs) -> str:
        return "通知"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 8 for _ in texts]


class MockConfig:
    class KnowledgeBase:
        chunk_size = 100
        chunk_overlap = 20

    knowledge_base = KnowledgeBase()
    ocr = OCRConfig()


@pytest.fixture
def mock_llm() -> MockLLMProvider:
    return MockLLMProvider()


@pytest.fixture
def mock_vector_store(tmp_path: Path, mock_llm: MockLLMProvider) -> VectorStore:
    return VectorStore(db_path=str(tmp_path / "db"), llm=mock_llm)


@pytest.fixture
def ingester(mock_llm: MockLLMProvider, mock_vector_store: VectorStore) -> Ingester:
    return Ingester(config=MockConfig(), llm=mock_llm, vector_store=mock_vector_store)


class TestProcessFile:
    @pytest.mark.asyncio
    async def test_processes_txt_file(self, ingester: Ingester, tmp_path: Path) -> None:
        txt = tmp_path / "test.txt"
        txt.write_text("测试文档内容，用于验证文件处理流程。", encoding="utf-8")

        result = await ingester.process_file(txt)
        assert result.status == "success"
        assert result.chunks_count >= 1

    @pytest.mark.asyncio
    async def test_skips_unsupported_format(self, ingester: Ingester, tmp_path: Path) -> None:
        xyz = tmp_path / "test.xyz"
        xyz.write_text("unknown")

        result = await ingester.process_file(xyz)
        assert result.status == "skipped"

    @pytest.mark.asyncio
    async def test_failure_returns_failed_result(self, ingester: Ingester, tmp_path: Path) -> None:
        bad = tmp_path / "bad.docx"
        bad.write_bytes(b"\x00\x01\x02")

        result = await ingester.process_file(bad)
        assert result.status == "failed"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_skips_unchanged_file(self, ingester: Ingester, mock_vector_store: VectorStore, tmp_path: Path) -> None:
        txt = tmp_path / "cached.txt"
        txt.write_text("已存在的内容", encoding="utf-8")

        # First import
        await ingester.process_file(txt)

        # Second import should skip (MD5 unchanged)
        result = await ingester.process_file(txt)
        assert result.status == "success"
        assert result.chunks_count == 0

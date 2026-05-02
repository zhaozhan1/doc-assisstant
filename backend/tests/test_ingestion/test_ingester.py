from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.config import OCRConfig
from app.db.vector_store import VectorStore
from app.ingestion.ingester import Ingester
from app.llm.base import BaseLLMProvider
from app.models.chunk import Chunk
from app.models.document import DocumentMetadata, ExtractedDoc, FileInfo


class MockLLMProvider(BaseLLMProvider):
    async def chat(self, messages: list[dict], **kwargs) -> str:
        return "通知"

    async def chat_stream(self, messages: list[dict], **kwargs):
        yield "通"
        yield "知"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 8 for _ in texts]


class MockConfig:
    class KnowledgeBase:
        chunk_size = 100
        chunk_overlap = 20
        smart_chunking = False

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
    async def test_skips_unchanged_file(
        self, ingester: Ingester, mock_vector_store: VectorStore, tmp_path: Path
    ) -> None:
        txt = tmp_path / "cached.txt"
        txt.write_text("已存在的内容", encoding="utf-8")

        # First import
        await ingester.process_file(txt)

        # Second import should skip (MD5 unchanged)
        result = await ingester.process_file(txt)
        assert result.status == "success"
        assert result.chunks_count == 0


class TestMD5GlobalDedup:
    """Tests for MD5-based global dedup: same content moved to a new path."""

    @pytest.mark.asyncio
    async def test_process_file_md5_global_dedup_new_path(self, ingester: Ingester, tmp_path: Path) -> None:
        """When file content already exists at /old/path, delete old path and upsert new."""
        new_path = tmp_path / "new" / "a.txt"
        new_path.parent.mkdir(parents=True, exist_ok=True)
        new_path.write_text("测试内容", encoding="utf-8")

        old_path_str = str(tmp_path / "old" / "a.txt")

        # Mock internal components
        fixed_meta = DocumentMetadata(
            file_name="a.txt",
            source_path=str(new_path),
            import_time=datetime(2026, 1, 1, 12, 0, 0),
            doc_type="通知",
            file_md5="abc123",
        )

        ingester.decompressor.extract = lambda p: [FileInfo(path=new_path, format="txt")]
        ingester.extractor.extract = lambda fi: ExtractedDoc(text="测试内容", structure=[], source_path=new_path)
        ingester.metadata_extractor.extract = lambda doc: fixed_meta

        # find_by_md5 returns old path (different from current)
        ingester.vector_store.find_by_md5 = AsyncMock(return_value=old_path_str)
        # check_file_exists returns False so processing proceeds
        ingester.vector_store.check_file_exists = AsyncMock(return_value=False)
        ingester.vector_store.delete_by_file = AsyncMock()
        ingester.vector_store.upsert = AsyncMock()

        # Mock classifier
        ingester.classifier.classify = AsyncMock(return_value="通知")  # type: ignore[attr-defined]

        result = await ingester.process_file(new_path)

        assert result.status == "success"
        assert result.chunks_count >= 1
        # Old path chunks should be deleted
        ingester.vector_store.delete_by_file.assert_any_call(old_path_str)
        # Upsert should happen with new chunks
        ingester.vector_store.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_file_md5_dedup_same_path_no_delete(self, ingester: Ingester, tmp_path: Path) -> None:
        """When find_by_md5 returns the SAME path, no extra delete_by_file call."""
        new_path = tmp_path / "a.txt"
        new_path.write_text("测试内容", encoding="utf-8")

        fixed_meta = DocumentMetadata(
            file_name="a.txt",
            source_path=str(new_path),
            import_time=datetime(2026, 1, 1, 12, 0, 0),
            doc_type="通知",
            file_md5="abc123",
        )

        ingester.decompressor.extract = lambda p: [FileInfo(path=new_path, format="txt")]
        ingester.extractor.extract = lambda fi: ExtractedDoc(text="测试内容", structure=[], source_path=new_path)
        ingester.metadata_extractor.extract = lambda doc: fixed_meta

        # find_by_md5 returns same path as current
        ingester.vector_store.find_by_md5 = AsyncMock(return_value=str(new_path))
        ingester.vector_store.check_file_exists = AsyncMock(return_value=False)
        ingester.vector_store.delete_by_file = AsyncMock()
        ingester.vector_store.upsert = AsyncMock()
        ingester.classifier.classify = AsyncMock(return_value="通知")  # type: ignore[attr-defined]

        result = await ingester.process_file(new_path)

        assert result.status == "success"
        # delete_by_file should only be called for the current path (existing behavior),
        # NOT an extra call for dedup
        calls = [c.args[0] for c in ingester.vector_store.delete_by_file.call_args_list]
        assert calls.count(str(new_path)) == 1


class TestImportTimeInjection:
    """Tests for import_time being injected into chunk metadata."""

    @pytest.mark.asyncio
    async def test_process_file_injects_import_time(self, ingester: Ingester, tmp_path: Path) -> None:
        """After process_file, chunk metadata should contain import_time."""
        new_path = tmp_path / "b.txt"
        new_path.write_text("带时间的文档", encoding="utf-8")

        fixed_import_time = datetime(2026, 5, 1, 10, 30, 0)
        fixed_meta = DocumentMetadata(
            file_name="b.txt",
            source_path=str(new_path),
            import_time=fixed_import_time,
            doc_type="通知",
            file_md5="deadbeef",
        )

        ingester.decompressor.extract = lambda p: [FileInfo(path=new_path, format="txt")]
        ingester.extractor.extract = lambda fi: ExtractedDoc(text="带时间的文档", structure=[], source_path=new_path)
        ingester.metadata_extractor.extract = lambda doc: fixed_meta

        ingester.vector_store.find_by_md5 = AsyncMock(return_value=None)
        ingester.vector_store.check_file_exists = AsyncMock(return_value=False)
        ingester.vector_store.delete_by_file = AsyncMock()
        ingester.vector_store.upsert = AsyncMock()
        ingester.classifier.classify = AsyncMock(return_value="通知")  # type: ignore[attr-defined]

        result = await ingester.process_file(new_path)

        assert result.status == "success"
        assert result.chunks_count >= 1

        # Verify upsert was called and chunk metadata has import_time
        upsert_call = ingester.vector_store.upsert.call_args
        chunks: list[Chunk] = upsert_call.args[0]
        assert len(chunks) > 0
        for chunk in chunks:
            assert "import_time" in chunk.metadata
            assert chunk.metadata["import_time"] == fixed_import_time.isoformat()

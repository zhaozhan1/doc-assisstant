from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.db.vector_store import SearchResult, VectorStore
from app.models.chunk import Chunk


@pytest.fixture
def mock_llm() -> AsyncMock:
    llm = AsyncMock()
    llm.embed.side_effect = lambda texts: [[0.1] * 10 for _ in texts]
    return llm


@pytest.fixture
def vector_store(mock_llm: AsyncMock, tmp_path: Path) -> VectorStore:
    return VectorStore(db_path=str(tmp_path / "chroma_db"), llm=mock_llm)


def _make_chunks(n: int, source_file: str = "/tmp/test.txt") -> list[Chunk]:
    return [
        Chunk(
            text=f"文本块{i}",
            source_file=source_file,
            chunk_index=i,
            metadata={"doc_type": "通知", "file_name": "test.txt", "file_md5": "abc123"},
        )
        for i in range(n)
    ]


class TestUpsert:
    @pytest.mark.asyncio
    async def test_upsert_stores_chunks(self, vector_store: VectorStore, mock_llm: AsyncMock) -> None:
        chunks = _make_chunks(3)
        await vector_store.upsert(chunks)
        mock_llm.embed.assert_called_once()
        assert vector_store._collection.count() == 3

    @pytest.mark.asyncio
    async def test_upsert_empty_list_does_nothing(self, vector_store: VectorStore, mock_llm: AsyncMock) -> None:
        await vector_store.upsert([])
        mock_llm.embed.assert_not_called()


class TestDeleteByFile:
    @pytest.mark.asyncio
    async def test_delete_removes_chunks(self, vector_store: VectorStore) -> None:
        chunks = _make_chunks(2, "/tmp/a.txt")
        await vector_store.upsert(chunks)
        assert vector_store._collection.count() == 2

        await vector_store.delete_by_file("/tmp/a.txt")
        assert vector_store._collection.count() == 0


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_returns_results(self, vector_store: VectorStore, mock_llm: AsyncMock) -> None:
        chunks = _make_chunks(3)
        await vector_store.upsert(chunks)
        mock_llm.embed.return_value = [[0.1] * 10]

        results = await vector_store.search("查询", top_k=2)
        assert len(results) <= 2
        assert all(isinstance(r, SearchResult) for r in results)


class TestCheckFileExists:
    @pytest.mark.asyncio
    async def test_returns_false_when_not_exists(self, vector_store: VectorStore) -> None:
        result = await vector_store.check_file_exists("/tmp/nonexistent.txt", "abc123")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_when_md5_matches(self, vector_store: VectorStore) -> None:
        chunks = _make_chunks(1)
        await vector_store.upsert(chunks)
        result = await vector_store.check_file_exists("/tmp/test.txt", "abc123")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_md5_changed(self, vector_store: VectorStore) -> None:
        chunks = _make_chunks(1)
        await vector_store.upsert(chunks)
        result = await vector_store.check_file_exists("/tmp/test.txt", "new_md5")
        assert result is False

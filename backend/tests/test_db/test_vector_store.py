from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

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


@pytest.fixture
def mock_collection() -> MagicMock:
    return MagicMock()


@pytest.fixture
def vs_with_mock_collection(mock_llm: AsyncMock, mock_collection: MagicMock) -> VectorStore:
    vs = VectorStore.__new__(VectorStore)
    vs._collection = mock_collection
    vs._llm = mock_llm
    return vs


class TestListAllChunks:
    @pytest.mark.asyncio
    async def test_returns_all_chunks_as_search_results(
        self, vs_with_mock_collection: VectorStore, mock_collection: MagicMock
    ) -> None:
        mock_collection.get.return_value = {
            "ids": ["f.txt::0", "f.txt::1"],
            "documents": ["chunk0", "chunk1"],
            "metadatas": [{"source_file": "f.txt"}, {"source_file": "f.txt"}],
        }

        results = await vs_with_mock_collection.list_all_chunks()

        mock_collection.get.assert_called_once_with(include=["documents", "metadatas"])
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].text == "chunk0"
        assert results[0].metadata == {"source_file": "f.txt"}
        assert results[0].score == 0.0
        assert results[1].text == "chunk1"

    @pytest.mark.asyncio
    async def test_returns_empty_when_collection_empty(
        self, vs_with_mock_collection: VectorStore, mock_collection: MagicMock
    ) -> None:
        mock_collection.get.return_value = {
            "ids": [],
            "documents": [],
            "metadatas": [],
        }

        results = await vs_with_mock_collection.list_all_chunks()

        assert results == []


class TestUpdateFileMetadata:
    @pytest.mark.asyncio
    async def test_updates_metadata_for_all_chunks(
        self, vs_with_mock_collection: VectorStore, mock_collection: MagicMock
    ) -> None:
        mock_collection.get.return_value = {
            "ids": ["a.txt::0", "a.txt::1"],
        }
        updates = {"status": "processed"}

        await vs_with_mock_collection.update_file_metadata("a.txt", updates)

        mock_collection.get.assert_called_once_with(where={"source_file": "a.txt"})
        mock_collection.update.assert_called_once_with(
            ids=["a.txt::0", "a.txt::1"],
            metadatas=[{"status": "processed"}, {"status": "processed"}],
        )

    @pytest.mark.asyncio
    async def test_noop_when_no_chunks_found(
        self, vs_with_mock_collection: VectorStore, mock_collection: MagicMock
    ) -> None:
        mock_collection.get.return_value = {"ids": []}

        await vs_with_mock_collection.update_file_metadata("missing.txt", {"status": "x"})

        mock_collection.update.assert_not_called()


class TestFindByMd5:
    @pytest.mark.asyncio
    async def test_returns_source_file_when_found(
        self, vs_with_mock_collection: VectorStore, mock_collection: MagicMock
    ) -> None:
        mock_collection.get.return_value = {
            "ids": ["doc.pdf::0"],
            "metadatas": [{"source_file": "doc.pdf", "file_md5": "deadbeef"}],
        }

        result = await vs_with_mock_collection.find_by_md5("deadbeef")

        mock_collection.get.assert_called_once_with(where={"file_md5": "deadbeef"})
        assert result == "doc.pdf"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(
        self, vs_with_mock_collection: VectorStore, mock_collection: MagicMock
    ) -> None:
        mock_collection.get.return_value = {"ids": [], "metadatas": []}

        result = await vs_with_mock_collection.find_by_md5("nonexistent")

        assert result is None

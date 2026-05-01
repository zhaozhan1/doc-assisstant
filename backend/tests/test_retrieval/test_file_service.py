from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.db.vector_store import SearchResult
from app.models.search import FileListRequest
from app.models.task import FileResult
from app.retrieval.file_service import FileService


@pytest.fixture
def mock_vs() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_ingester() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def svc(mock_vs: AsyncMock, mock_ingester: AsyncMock) -> FileService:
    return FileService(vector_store=mock_vs, ingester=mock_ingester)


# --- helper to build SearchResult ---
def _chunk(source_file: str, file_name: str, doc_type: str, doc_date: str, file_md5: str) -> SearchResult:
    return SearchResult(
        text="some text",
        metadata={
            "source_file": source_file,
            "file_name": file_name,
            "doc_type": doc_type,
            "doc_date": doc_date,
            "file_md5": file_md5,
        },
        score=0.0,
    )


# ---------- Tests ----------


async def test_list_files_aggregates_by_source(svc: FileService, mock_vs: AsyncMock) -> None:
    """3 chunks from 2 files -> 2 IndexedFile with correct chunk_count."""
    mock_vs.list_all_chunks.return_value = [
        _chunk("/data/a.docx", "a.docx", "通知", "2025-01-01", "md5_a"),
        _chunk("/data/a.docx", "a.docx", "通知", "2025-01-01", "md5_a"),
        _chunk("/data/b.docx", "b.docx", "批复", "2025-02-01", "md5_b"),
    ]

    result = await svc.list_files(FileListRequest())

    assert len(result) == 2
    by_file = {f.source_file: f for f in result}
    assert by_file["/data/a.docx"].chunk_count == 2
    assert by_file["/data/b.docx"].chunk_count == 1


async def test_list_files_filters_by_type(svc: FileService, mock_vs: AsyncMock) -> None:
    """Filter doc_types=["通知"] returns only matching files."""
    mock_vs.list_all_chunks.return_value = [
        _chunk("/data/a.docx", "a.docx", "通知", "2025-01-01", "md5_a"),
        _chunk("/data/b.docx", "b.docx", "批复", "2025-02-01", "md5_b"),
    ]

    result = await svc.list_files(FileListRequest(doc_types=["通知"]))

    assert len(result) == 1
    assert result[0].doc_type == "通知"


async def test_delete_file(svc: FileService, mock_vs: AsyncMock) -> None:
    """delete_file delegates to vector_store.delete_by_file when file exists."""
    mock_vs.file_exists.return_value = True

    await svc.delete_file("/data/a.docx")

    mock_vs.file_exists.assert_awaited_once_with("/data/a.docx")
    mock_vs.delete_by_file.assert_awaited_once_with("/data/a.docx")


async def test_delete_file_rejects_unknown(svc: FileService, mock_vs: AsyncMock) -> None:
    """delete_file raises ValueError when file not in knowledge base."""
    mock_vs.file_exists.return_value = False

    with pytest.raises(ValueError, match="文件不在知识库中"):
        await svc.delete_file("/data/unknown.docx")

    mock_vs.delete_by_file.assert_not_awaited()


async def test_reindex_file(svc: FileService, mock_vs: AsyncMock, mock_ingester: AsyncMock) -> None:
    """reindex_file calls ingester.process_file and returns FileResult."""
    mock_vs.file_exists.return_value = True
    expected = FileResult(path="/data/a.docx", status="success", chunks_count=5)
    mock_ingester.process_file.return_value = expected

    result = await svc.reindex_file("/data/a.docx")

    mock_vs.file_exists.assert_awaited_once_with("/data/a.docx")
    mock_ingester.process_file.assert_awaited_once_with(Path("/data/a.docx"))
    assert result == expected


async def test_reindex_file_rejects_unknown(svc: FileService, mock_vs: AsyncMock, mock_ingester: AsyncMock) -> None:
    """reindex_file raises ValueError when file not in knowledge base."""
    mock_vs.file_exists.return_value = False

    with pytest.raises(ValueError, match="文件不在知识库中"):
        await svc.reindex_file("/data/unknown.docx")

    mock_ingester.process_file.assert_not_awaited()


async def test_update_classification(svc: FileService, mock_vs: AsyncMock) -> None:
    """update_classification calls vs.update_file_metadata with correct payload."""
    await svc.update_classification("/data/a.docx", "批复")

    mock_vs.update_file_metadata.assert_awaited_once_with("/data/a.docx", {"doc_type": "批复"})

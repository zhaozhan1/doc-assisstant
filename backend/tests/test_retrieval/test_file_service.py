from __future__ import annotations

from datetime import date
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


def _chunk(
    source_file: str,
    file_name: str,
    doc_type: str,
    file_md5: str,
    import_time: str = "2025-01-15T10:00:00",
    file_created_time: str = "2024-12-01T08:00:00",
) -> SearchResult:
    return SearchResult(
        text="some text",
        metadata={
            "source_file": source_file,
            "file_name": file_name,
            "doc_type": doc_type,
            "file_md5": file_md5,
            "import_time": import_time,
            "file_created_time": file_created_time,
        },
        score=0.0,
    )


# ---------- Tests ----------


async def test_list_files_aggregates_by_source(svc: FileService, mock_vs: AsyncMock) -> None:
    mock_vs.list_all_chunks.return_value = [
        _chunk("/data/a.docx", "a.docx", "通知", "md5_a"),
        _chunk("/data/a.docx", "a.docx", "通知", "md5_a"),
        _chunk("/data/b.docx", "b.docx", "批复", "md5_b"),
    ]

    result = await svc.list_files(FileListRequest())

    assert len(result) == 2
    by_file = {f.source_file: f for f in result}
    assert by_file["/data/a.docx"].chunk_count == 2
    assert by_file["/data/a.docx"].import_date == "2025-01-15T10:00:00"
    assert by_file["/data/a.docx"].created_date == "2024-12-01T08:00:00"
    assert by_file["/data/b.docx"].chunk_count == 1


async def test_list_files_filters_by_type(svc: FileService, mock_vs: AsyncMock) -> None:
    mock_vs.list_all_chunks.return_value = [
        _chunk("/data/a.docx", "a.docx", "通知", "md5_a"),
        _chunk("/data/b.docx", "b.docx", "批复", "md5_b"),
    ]

    result = await svc.list_files(FileListRequest(doc_types=["通知"]))

    assert len(result) == 1
    assert result[0].doc_type == "通知"


async def test_list_files_sorts_by_import_date_desc(svc: FileService, mock_vs: AsyncMock) -> None:
    mock_vs.list_all_chunks.return_value = [
        _chunk("/data/a.docx", "a.docx", "通知", "md5_a", import_time="2025-01-01T00:00:00"),
        _chunk("/data/b.docx", "b.docx", "批复", "md5_b", import_time="2025-06-01T00:00:00"),
    ]

    result = await svc.list_files(FileListRequest())

    assert result[0].source_file == "/data/b.docx"
    assert result[1].source_file == "/data/a.docx"


async def test_list_files_filters_by_import_date_range(svc: FileService, mock_vs: AsyncMock) -> None:
    mock_vs.list_all_chunks.return_value = [
        _chunk("/data/a.docx", "a.docx", "通知", "md5_a", import_time="2025-01-15T00:00:00"),
        _chunk("/data/b.docx", "b.docx", "批复", "md5_b", import_time="2025-06-15T00:00:00"),
    ]

    result = await svc.list_files(
        FileListRequest(date_from=date(2025, 6, 1), date_to=date(2025, 6, 30))
    )

    assert len(result) == 1
    assert result[0].source_file == "/data/b.docx"


async def test_list_files_old_data_created_date_none(svc: FileService, mock_vs: AsyncMock) -> None:
    mock_vs.list_all_chunks.return_value = [
        _chunk("/data/old.docx", "old.docx", "通知", "md5_old", file_created_time=""),
    ]

    result = await svc.list_files(FileListRequest())

    assert result[0].created_date is None
    assert result[0].import_date is not None


async def test_delete_file(svc: FileService, mock_vs: AsyncMock) -> None:
    mock_vs.file_exists.return_value = True

    await svc.delete_file("/data/a.docx")

    mock_vs.file_exists.assert_awaited_once_with("/data/a.docx")
    mock_vs.delete_by_file.assert_awaited_once_with("/data/a.docx")


async def test_delete_file_rejects_unknown(svc: FileService, mock_vs: AsyncMock) -> None:
    mock_vs.file_exists.return_value = False

    with pytest.raises(ValueError, match="文件不在知识库中"):
        await svc.delete_file("/data/unknown.docx")

    mock_vs.delete_by_file.assert_not_awaited()


async def test_reindex_file(svc: FileService, mock_vs: AsyncMock, mock_ingester: AsyncMock) -> None:
    mock_vs.file_exists.return_value = True
    expected = FileResult(path="/data/a.docx", status="success", chunks_count=5)
    mock_ingester.process_file.return_value = expected

    result = await svc.reindex_file("/data/a.docx")

    mock_vs.file_exists.assert_awaited_once_with("/data/a.docx")
    mock_ingester.process_file.assert_awaited_once_with(Path("/data/a.docx"))
    assert result == expected


async def test_reindex_file_rejects_unknown(svc: FileService, mock_vs: AsyncMock, mock_ingester: AsyncMock) -> None:
    mock_vs.file_exists.return_value = False

    with pytest.raises(ValueError, match="文件不在知识库中"):
        await svc.reindex_file("/data/unknown.docx")

    mock_ingester.process_file.assert_not_awaited()


async def test_update_classification(svc: FileService, mock_vs: AsyncMock) -> None:
    await svc.update_classification("/data/a.docx", "批复")

    mock_vs.update_file_metadata.assert_awaited_once_with("/data/a.docx", {"doc_type": "批复"})

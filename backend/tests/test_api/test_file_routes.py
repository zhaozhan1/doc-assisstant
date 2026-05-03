from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.models.search import IndexedFile
from app.models.task import FileResult


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("{}")

    from app.main import create_app

    app = create_app()

    # Override app.state services with mocks
    mock_file_service = AsyncMock()
    mock_file_service.list_files.return_value = [
        IndexedFile(
            source_file="/a.docx",
            file_name="a.docx",
            doc_type="通知",
            file_md5="abc",
            chunk_count=3,
            created_date="2024-12-01T08:00:00",
            import_date="2025-01-15T10:00:00",
        )
    ]
    mock_file_service.delete_file.return_value = None
    mock_file_service.reindex_file.return_value = FileResult(
        path="/a.docx",
        status="success",
        chunks_count=5,
    )
    mock_file_service.update_classification.return_value = None

    app.state.retriever = AsyncMock()
    app.state.file_service = mock_file_service
    app.state.settings_service = AsyncMock()

    return TestClient(app)


def test_list_files(client: TestClient) -> None:
    response = client.get("/api/files")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["file_name"] == "a.docx"
    assert data[0]["doc_type"] == "通知"
    assert data[0]["created_date"] == "2024-12-01T08:00:00"
    assert data[0]["import_date"] == "2025-01-15T10:00:00"


def test_delete_file(client: TestClient) -> None:
    response = client.delete("/api/files/a.docx")
    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}


def test_reindex_file(client: TestClient) -> None:
    response = client.post("/api/files/a.docx/reindex")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["chunks_count"] == 5


def test_update_classification(client: TestClient) -> None:
    response = client.put(
        "/api/files/a.docx/classification",
        json={"doc_type": "公告"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "updated"}

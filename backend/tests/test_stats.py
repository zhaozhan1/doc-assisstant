from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_file_service
from app.models.search import IndexedFile


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("{}")

    from app.main import create_app

    app = create_app()

    mock_file_service = AsyncMock()
    mock_file_service.list_files.return_value = [
        IndexedFile(
            source_file="/data/a.docx",
            file_name="a.docx",
            doc_type="通知",
            doc_date="2025-03-10",
            file_md5="aaa",
            chunk_count=3,
        ),
        IndexedFile(
            source_file="/data/b.docx",
            file_name="b.docx",
            doc_type="请示",
            doc_date="2025-04-20",
            file_md5="bbb",
            chunk_count=2,
        ),
        IndexedFile(
            source_file="/data/c.docx",
            file_name="c.docx",
            doc_type="通知",
            doc_date=None,
            file_md5="ccc",
            chunk_count=1,
        ),
    ]

    app.dependency_overrides[get_file_service] = lambda: mock_file_service

    with TestClient(app) as c:
        yield c


def test_stats_returns_expected_fields(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_files" in data
    assert "type_distribution" in data
    assert "last_updated" in data


def test_stats_counts_and_distribution(client):
    resp = client.get("/api/stats")
    data = resp.json()
    assert data["total_files"] == 3
    assert data["type_distribution"] == {"通知": 2, "请示": 1}


def test_stats_last_updated_picks_max_date(client):
    resp = client.get("/api/stats")
    data = resp.json()
    assert data["last_updated"] == "2025-04-20"


def test_stats_empty_knowledge_base(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("{}")

    from app.main import create_app

    app = create_app()

    mock_file_service = AsyncMock()
    mock_file_service.list_files.return_value = []
    app.dependency_overrides[get_file_service] = lambda: mock_file_service

    with TestClient(app) as c:
        resp = c.get("/api/stats")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_files"] == 0
    assert data["type_distribution"] == {}
    assert data["last_updated"] is None

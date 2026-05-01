from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.models.search import SourceType, UnifiedSearchResult


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("{}")

    from app.main import create_app

    app = create_app()

    # Override app.state services with mocks
    mock_retriever = AsyncMock()
    mock_retriever.search.return_value = [
        UnifiedSearchResult(
            source_type=SourceType.LOCAL,
            title="test.docx",
            content="内容",
            score=0.85,
            metadata={},
        )
    ]
    mock_retriever.search_local.return_value = [
        UnifiedSearchResult(
            source_type=SourceType.LOCAL,
            title="test.docx",
            content="内容",
            score=0.85,
            metadata={},
        )
    ]
    app.state.retriever = mock_retriever
    app.state.file_service = AsyncMock()
    app.state.settings_service = AsyncMock()

    return TestClient(app)


def test_search_endpoint(client: TestClient) -> None:
    response = client.post(
        "/api/search",
        json={"query": "测试查询", "top_k": 10},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "test.docx"
    assert data[0]["source_type"] == "local"


def test_search_local_endpoint(client: TestClient) -> None:
    response = client.post(
        "/api/search/local",
        json={"query": "本地查询", "top_k": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["source_type"] == "local"


def test_health_still_works(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

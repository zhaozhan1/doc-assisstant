from __future__ import annotations

import io
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


def test_upload_file_returns_task_id(client: TestClient):
    file_content = b"test document content"
    resp = client.post(
        "/api/files/upload",
        files=[("files", ("test.txt", io.BytesIO(file_content), "text/plain"))],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data


def test_upload_empty_files_rejected(client: TestClient):
    resp = client.post("/api/files/upload", files=[])
    assert resp.status_code == 422

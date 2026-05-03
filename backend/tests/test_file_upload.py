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


def test_upload_fake_pdf_rejected(client: TestClient):
    """Upload a .pdf whose content does NOT start with %PDF magic bytes."""
    fake_pdf = b"this is not a real pdf file content"
    resp = client.post(
        "/api/files/upload",
        files=[("files", ("fake.pdf", io.BytesIO(fake_pdf), "application/pdf"))],
    )
    assert resp.status_code == 422
    assert "格式不匹配" in resp.json()["detail"]


def test_upload_fake_png_rejected(client: TestClient):
    """Upload a .png whose content does NOT start with PNG magic bytes."""
    fake_png = b"this is not a real png file content"
    resp = client.post(
        "/api/files/upload",
        files=[("files", ("fake.png", io.BytesIO(fake_png), "image/png"))],
    )
    assert resp.status_code == 422
    assert "格式不匹配" in resp.json()["detail"]


def test_upload_valid_pdf_accepted(client: TestClient):
    """Upload a .pdf that starts with the correct %PDF magic bytes."""
    valid_pdf = b"%PDF-1.4 rest of pdf content here"
    resp = client.post(
        "/api/files/upload",
        files=[("files", ("real.pdf", io.BytesIO(valid_pdf), "application/pdf"))],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data


def test_upload_oversized_file_rejected(client: TestClient):
    """Upload a file larger than 50 MB and expect 413."""
    oversize_content = b"x" * (51 * 1024 * 1024)  # 51 MB
    resp = client.post(
        "/api/files/upload",
        files=[("files", ("huge.pdf", io.BytesIO(b"%PDF" + oversize_content), "application/pdf"))],
    )
    assert resp.status_code == 413
    assert "文件过大" in resp.json()["detail"]


def test_upload_multiple_files(client: TestClient):
    """Upload 2+ valid files and expect 200 with task_id."""
    file_a = b"%PDF-1.4 content a"
    file_b = b"%PDF-1.4 content b"
    resp = client.post(
        "/api/files/upload",
        files=[
            ("files", ("a.pdf", io.BytesIO(file_a), "application/pdf")),
            ("files", ("b.pdf", io.BytesIO(file_b), "application/pdf")),
        ],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data

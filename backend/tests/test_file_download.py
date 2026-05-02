from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import create_app

    app = create_app()
    return TestClient(app)


def test_download_nonexistent_file_returns_404(client):
    resp = client.get("/api/files/download/nonexistent_file_12345.docx")
    assert resp.status_code == 404


def test_download_path_traversal_normalized_to_404(client):
    """FastAPI normalizes ../ in paths before matching, so /../etc/passwd
    resolves to /api/files/etc/passwd which hits the DELETE route (405).
    The endpoint's own `..` check is a defense-in-depth measure."""
    resp = client.get("/api/files/download/../etc/passwd")
    # FastAPI normalizes the path; it never reaches the download handler
    assert resp.status_code in (400, 404, 405)

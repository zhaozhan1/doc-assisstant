from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("{}")

    from app.config import AppConfig
    from app.main import create_app

    app = create_app()
    config = AppConfig()
    app.state.config = config
    return TestClient(app)


def test_download_file_outside_save_path_returns_403(client):
    resp = client.get("/api/files/download/nonexistent_file_12345.docx")
    assert resp.status_code == 403


def test_download_nonexistent_file_in_save_path_returns_404(client, tmp_path: Path):
    save_dir = tmp_path / "output"
    save_dir.mkdir()
    resp = client.get(f"/api/files/download/{save_dir}/nonexistent_file_12345.docx")
    assert resp.status_code == 404


def test_download_path_traversal_normalized_to_404(client):
    """FastAPI normalizes ../ in paths before matching, so /../etc/passwd
    resolves to /api/files/etc/passwd which hits the DELETE route (405).
    The endpoint's own `..` check is a defense-in-depth measure."""
    resp = client.get("/api/files/download/../etc/passwd")
    # FastAPI normalizes the path; it never reaches the download handler
    assert resp.status_code in (400, 404, 405)

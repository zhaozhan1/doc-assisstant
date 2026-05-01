from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.generation.template_manager import TemplateManager


@pytest.fixture
def builtin_dir() -> Path:
    return Path(__file__).parent.parent.parent / "app" / "generation" / "templates"


@pytest.fixture
def client(builtin_dir: Path, tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("{}")

    from app.main import create_app

    app = create_app()
    app.state.template_mgr = TemplateManager(builtin_dir=builtin_dir, custom_dir=tmp_path / "custom")
    app.state.settings_service = __import__("unittest.mock", fromlist=["AsyncMock"]).AsyncMock()

    return TestClient(app)


class TestTemplateRoutes:
    def test_list_templates(self, client):
        resp = client.get("/api/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 12

    def test_get_template(self, client):
        resp = client.get("/api/templates/notice")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "notice"
        assert data["is_builtin"] is True

    def test_get_nonexistent_template(self, client):
        resp = client.get("/api/templates/nonexistent")
        assert resp.status_code == 404

    def test_create_custom_template(self, client):
        resp = client.post(
            "/api/templates",
            json={
                "id": "custom_test",
                "name": "自定义模板",
                "doc_type": "notice",
                "sections": [],
                "is_builtin": False,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["is_builtin"] is False

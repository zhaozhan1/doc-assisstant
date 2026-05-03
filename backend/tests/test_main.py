from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


def test_health_endpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("{}")

    from app.main import create_app

    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class TestStaticServing:
    def _make_app_with_frontend(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "config.yaml"
        config_file.write_text("{}")

        # Create fake frontend dist
        frontend_dir = tmp_path / "frontend_dist"
        frontend_dir.mkdir()
        (frontend_dir / "index.html").write_text("<html>SPA</html>")
        assets_dir = frontend_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "app.js").write_text("console.log('app')")

        with patch("app.main._find_frontend_dir", return_value=frontend_dir):
            from app.main import create_app

            app = create_app()
        return TestClient(app)

    def test_root_returns_index_html(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        client = self._make_app_with_frontend(tmp_path, monkeypatch)
        response = client.get("/")
        assert response.status_code == 200
        assert "SPA" in response.text

    def test_spa_route_returns_index_html(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        client = self._make_app_with_frontend(tmp_path, monkeypatch)
        response = client.get("/knowledge-base")
        assert response.status_code == 200
        assert "SPA" in response.text

    def test_static_assets_served(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        client = self._make_app_with_frontend(tmp_path, monkeypatch)
        response = client.get("/assets/app.js")
        assert response.status_code == 200
        assert "console.log" in response.text

    def test_api_routes_not_intercepted(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        client = self._make_app_with_frontend(tmp_path, monkeypatch)
        # /api/search is a valid POST route; SPA fallback returns 404 for api/ paths
        response = client.get("/api/search")
        assert response.status_code == 404

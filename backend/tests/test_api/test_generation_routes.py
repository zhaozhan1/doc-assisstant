from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.models.generation import GenerationResult, SourceAttribution
from app.models.search import SourceType


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("{}")

    from app.main import create_app

    app = create_app()

    mock_svc = AsyncMock()
    mock_svc.generate_from_description.return_value = GenerationResult(
        content="测试公文内容",
        sources=[SourceAttribution(title="参考1", source_type=SourceType.LOCAL)],
        output_path="/tmp/test.docx",
        template_used="notice",
    )
    app.state.writer_service = mock_svc
    app.state.settings_service = AsyncMock()

    return TestClient(app)


class TestGenerationRoutes:
    def test_generate_endpoint(self, client):
        resp = client.post(
            "/api/generation/generate",
            json={"description": "写一份测试通知"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["template_used"] == "notice"
        assert data["content"] == "测试公文内容"

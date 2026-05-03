from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.config import AppConfig
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

    def test_generate_stream_endpoint(self, client):
        """POST /api/generation/generate/stream returns SSE events with tokens and [DONE]."""
        tokens = ["你", "好", "世", "界"]

        async def _fake_stream(req):
            for t in tokens:
                yield t

        client.app.state.writer_service.generate_stream = _fake_stream
        client.app.state.writer_service.save_stream_result = AsyncMock(return_value="/tmp/stream_output.docx")

        resp = client.post(
            "/api/generation/generate/stream",
            json={"description": "写一份测试通知"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        text = resp.text
        # Parse SSE data lines and extract JSON payloads
        data_lines = [line.replace("data: ", "", 1) for line in text.strip().split("\n\n") if line.startswith("data: ")]
        token_events = [json.loads(d) for d in data_lines if d != "[DONE]"]
        received_tokens = [e["token"] for e in token_events if "token" in e]
        assert received_tokens == tokens

        # Verify output_path event
        output_events = [e for e in token_events if "output_path" in e]
        assert len(output_events) == 1
        assert output_events[0]["output_path"] == "/tmp/stream_output.docx"

        # Verify final [DONE] marker
        assert "data: [DONE]" in text

    def test_ppt_generate_endpoint(self, tmp_path, monkeypatch):
        """POST /api/generation/generate-pptx returns task_id for valid file_path."""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "config.yaml"
        config_file.write_text("{}")

        from app.main import create_app

        app = create_app()

        # Build a config whose save_path sits under tmp_path so _validate_path passes
        save_dir = tmp_path / "output"
        save_dir.mkdir()
        mock_generation = MagicMock()
        mock_generation.save_path = str(save_dir)
        mock_kb = MagicMock()
        mock_kb.source_folder = str(tmp_path / "kb")
        mock_config = MagicMock(spec=AppConfig)
        mock_config.generation = mock_generation
        mock_config.knowledge_base = mock_kb

        # Place a real file inside save_dir so _validate_path resolves it
        docx_file = save_dir / "source.docx"
        docx_file.write_bytes(b"PK fake docx")

        # Mock PptxTaskManager to return a deterministic task_id
        fake_task_id = "test-task-1234"
        mock_task_mgr = MagicMock()
        mock_task_mgr.can_start.return_value = True
        mock_task_mgr.create_task.return_value = fake_task_id

        app.state.pptx_generator = AsyncMock()
        app.state.pptx_task_manager = mock_task_mgr
        app.state.config = mock_config
        app.state.writer_service = AsyncMock()
        app.state.settings_service = AsyncMock()

        client = TestClient(app)
        resp = client.post(
            "/api/generation/generate-pptx",
            json={
                "source_type": "upload",
                "file_path": str(docx_file),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == fake_task_id
        mock_task_mgr.create_task.assert_called_once()

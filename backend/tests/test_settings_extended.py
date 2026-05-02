from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.config import AppConfig, ClaudeConfig
from app.settings_service import SettingsService


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("{}")

    from app.main import create_app

    app = create_app()

    config = AppConfig()
    # Ensure claude provider exists for masking test
    config.llm.providers["claude"] = ClaudeConfig(api_key="secret-key")
    settings_service = SettingsService(config, config_path=config_file)

    app.state.config = config
    app.state.retriever = AsyncMock()
    app.state.file_service = AsyncMock()
    app.state.settings_service = settings_service

    return TestClient(app)


def test_kb_config_get(client: TestClient) -> None:
    resp = client.get("/api/settings/knowledge-base")
    assert resp.status_code == 200
    data = resp.json()
    assert "db_path" in data
    assert "chunk_size" in data


def test_kb_config_update(client: TestClient) -> None:
    resp = client.put(
        "/api/settings/knowledge-base",
        json={"chunk_size": 800},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["chunk_size"] == 800


def test_llm_config_get_masks_api_key(client: TestClient) -> None:
    resp = client.get("/api/settings/llm")
    assert resp.status_code == 200
    data = resp.json()
    assert "default_provider" in data
    assert "providers" in data
    assert data["providers"]["claude"]["api_key"] == "********"


def test_llm_config_update(client: TestClient) -> None:
    resp = client.put(
        "/api/settings/llm",
        json={"ollama_chat_model": "qwen2.5:7b"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["providers"]["ollama"]["chat_model"] == "qwen2.5:7b"


def test_generation_config_get(client: TestClient) -> None:
    resp = client.get("/api/settings/generation")
    assert resp.status_code == 200
    data = resp.json()
    assert "output_format" in data
    assert "word_template_path" in data


def test_generation_config_update(client: TestClient) -> None:
    resp = client.put(
        "/api/settings/generation",
        json={"include_sources": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["include_sources"] is False


def test_browse_directory(client: TestClient) -> None:
    resp = client.get("/api/settings/files/browse", params={"path": "."})
    assert resp.status_code == 200
    data = resp.json()
    assert "children" in data

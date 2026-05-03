from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.config import OnlineSearchConfig
from app.models.search import ConnectionTestResult


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("{}")

    from app.main import create_app

    app = create_app()

    # Override app.state services with mocks
    mock_settings = Mock()
    mock_settings.get_online_search_config.return_value = OnlineSearchConfig(
        enabled=True,
        provider="baidu",
        api_key="test-key",
        base_url="https://api.tavily.com",
        domains=["gov.cn"],
        max_results=5,
    )
    mock_settings.update_online_search_config.return_value = OnlineSearchConfig(
        enabled=False,
        provider="baidu",
        api_key="new-key",
        base_url="",
        domains=["gov.cn"],
        max_results=3,
    )
    mock_settings.test_connection = AsyncMock(
        return_value=ConnectionTestResult(success=True, message="连接成功"),
    )

    app.state.retriever = AsyncMock()
    app.state.file_service = AsyncMock()
    app.state.settings_service = mock_settings

    return TestClient(app)


def test_get_online_search_config(client: TestClient) -> None:
    response = client.get("/api/settings/online-search")
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["provider"] == "baidu"
    assert data["api_key"] == "********"


def test_update_online_search_config(client: TestClient) -> None:
    response = client.put(
        "/api/settings/online-search",
        json={"enabled": False, "api_key": "new-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    assert data["api_key"] == "********"


def test_test_connection(client: TestClient) -> None:
    response = client.post(
        "/api/settings/online-search/test-connection",
        json={"provider": "tavily", "api_key": "test-key", "base_url": "https://api.tavily.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "连接成功"

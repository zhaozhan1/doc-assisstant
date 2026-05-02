from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("{}")

    from app.main import create_app

    app = create_app()

    mock_task_manager = MagicMock()
    mock_task_manager.get_progress.side_effect = KeyError("nonexistent-id")
    app.state.task_manager = mock_task_manager

    return TestClient(app)


def test_ws_nonexistent_task_returns_error(client):
    with client.websocket_connect("/ws/tasks/nonexistent-id") as ws:
        data = ws.receive_json()
        assert data["type"] == "error"

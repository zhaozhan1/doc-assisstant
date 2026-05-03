from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "config.yaml"
    config_file.write_text('server:\n  cors_origins:\n    - "http://127.0.0.1:8000"')

    from app.main import create_app

    app = create_app()

    mock_task_manager = MagicMock()
    mock_task_manager.get_progress.side_effect = KeyError("nonexistent-id")
    app.state.task_manager = mock_task_manager

    # Ensure config is available on app.state (lifespan may not run in TestClient)
    if not hasattr(app.state, "config"):
        from app.config import AppConfig

        app.state.config = AppConfig(_yaml_file=str(config_file))

    return TestClient(app)


def test_ws_nonexistent_task_returns_error(client):
    with client.websocket_connect("/ws/tasks/nonexistent-id") as ws:
        data = ws.receive_json()
        assert data["type"] == "error"


class TestWsOriginValidation:
    def test_ws_valid_origin_accepted(self, client) -> None:
        """Origin matching cors_origins should be accepted."""
        with client.websocket_connect("/ws/tasks/test-id", headers={"origin": "http://127.0.0.1:8000"}) as ws:
            data = ws.receive_json()
            # Should get task error, not origin rejection
            assert data["type"] == "error"

    def test_ws_invalid_origin_rejected(self, client) -> None:
        """Origin not in cors_origins should be rejected with code 4001."""
        from starlette.websockets import WebSocketDisconnect

        with pytest.raises(WebSocketDisconnect):  # noqa: SIM117
            with client.websocket_connect("/ws/tasks/test-id", headers={"origin": "http://evil.example.com"}) as ws:
                ws.receive_json()

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.config import AppConfig, OnlineSearchConfig
from app.models.search import OnlineSearchConfigUpdate
from app.settings_service import SettingsService


@pytest.fixture
def config_yaml(tmp_path: Path) -> Path:
    """Create a temporary config.yaml for isolation."""
    data = {
        "online_search": {
            "enabled": False,
            "provider": "baidu",
            "api_key": "",
            "domains": ["gov.cn"],
            "max_results": 3,
        }
    }
    p = tmp_path / "config.yaml"
    p.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return p


@pytest.fixture
def service(config_yaml: Path) -> SettingsService:
    config = AppConfig(_yaml_file=str(config_yaml))
    return SettingsService(config, config_path=config_yaml)


def test_get_online_search_config(service: SettingsService) -> None:
    """Returns config with default values (enabled=False)."""
    result = service.get_online_search_config()
    assert isinstance(result, OnlineSearchConfig)
    assert result.enabled is False
    assert result.provider == "baidu"


def test_update_online_search_config(service: SettingsService) -> None:
    """Update enabled + api_key, verify changed."""
    update = OnlineSearchConfigUpdate(enabled=True, api_key="sk-test-key")
    result = service.update_online_search_config(update)
    assert result.enabled is True
    assert result.api_key == "sk-test-key"
    # Also verify persistence: reload from disk
    config2 = AppConfig(_yaml_file=str(service._config_path))
    assert config2.online_search.enabled is True
    assert config2.online_search.api_key == "sk-test-key"


def test_update_preserves_unchanged_fields(service: SettingsService) -> None:
    """Update only enabled=True, provider stays 'baidu'."""
    update = OnlineSearchConfigUpdate(enabled=True)
    result = service.update_online_search_config(update)
    assert result.enabled is True
    assert result.provider == "baidu"
    assert result.api_key == ""

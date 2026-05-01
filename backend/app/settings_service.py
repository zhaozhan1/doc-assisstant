from __future__ import annotations

import logging
from pathlib import Path

import yaml

from app.config import AppConfig, OnlineSearchConfig
from app.models.search import OnlineSearchConfigUpdate, TestConnectionResult

logger = logging.getLogger(__name__)


class SettingsService:
    def __init__(self, config: AppConfig, config_path: Path | str = "config.yaml") -> None:
        self._config = config
        self._config_path = Path(config_path)

    def get_online_search_config(self) -> OnlineSearchConfig:
        return self._config.online_search

    def update_online_search_config(self, update: OnlineSearchConfigUpdate) -> OnlineSearchConfig:
        current = self._config.online_search
        update_data = update.model_dump(exclude_none=True)
        for key, value in update_data.items():
            setattr(current, key, value)
        self._write_config()
        return current

    async def test_connection(self, config: OnlineSearchConfigUpdate) -> TestConnectionResult:
        return TestConnectionResult(
            success=False,
            message=f"Provider '{self._config.online_search.provider}' 尚未实现，无法测试连接",
        )

    def _write_config(self) -> None:
        if not self._config_path.exists():
            return
        with open(self._config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        data["online_search"] = self._config.online_search.model_dump()
        with open(self._config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

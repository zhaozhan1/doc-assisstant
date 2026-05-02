from __future__ import annotations

import logging
from pathlib import Path

import yaml

from app.config import AppConfig, GenerationConfig, KnowledgeBaseConfig, OnlineSearchConfig
from app.models.search import (
    ConnectionTestResult,
    GenerationSettingsUpdate,
    KBSettingsUpdate,
    LLMSettingsUpdate,
    OnlineSearchConfigUpdate,
)

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

    async def test_connection(self, config: OnlineSearchConfigUpdate) -> ConnectionTestResult:
        return ConnectionTestResult(
            success=False,
            message=f"Provider '{self._config.online_search.provider}' 尚未实现，无法测试连接",
        )

    def _write_config(self) -> None:
        data: dict = {}
        if self._config_path.exists():
            with open(self._config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        data["knowledge_base"] = self._config.knowledge_base.model_dump()
        data["llm"] = {
            "default_provider": self._config.llm.default_provider,
            "embed_provider": self._config.llm.embed_provider,
            "providers": {k: v.model_dump() for k, v in self._config.llm.providers.items()},
        }
        data["online_search"] = self._config.online_search.model_dump()
        data["generation"] = self._config.generation.model_dump()
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    # ── Knowledge Base ──────────────────────────────────────────

    def get_kb_config(self) -> KnowledgeBaseConfig:
        return self._config.knowledge_base

    def update_kb_config(self, update: KBSettingsUpdate) -> KnowledgeBaseConfig:
        current = self._config.knowledge_base
        for key, value in update.model_dump(exclude_none=True).items():
            setattr(current, key, value)
        self._write_config()
        return current

    # ── LLM ─────────────────────────────────────────────────────

    def get_llm_config(self) -> dict:
        """Return LLM config dict with api_key masked."""
        llm = self._config.llm
        providers: dict = {}
        for name, prov in llm.providers.items():
            prov_data = prov.model_dump()
            if prov_data.get("api_key"):
                prov_data["api_key"] = "********"
            providers[name] = prov_data
        return {
            "default_provider": llm.default_provider,
            "embed_provider": llm.embed_provider,
            "providers": providers,
        }

    def update_llm_config(self, update: LLMSettingsUpdate) -> dict:
        """Update LLM config, mapping flat field names to nested provider configs."""
        update_data = update.model_dump(exclude_none=True)
        llm = self._config.llm

        if "default_provider" in update_data:
            llm.default_provider = update_data.pop("default_provider")

        # Map flattened provider fields to nested config
        provider_fields: dict[str, dict[str, str]] = {}
        for flat_key, value in update_data.items():
            if flat_key.startswith("ollama_"):
                provider_fields.setdefault("ollama", {})[flat_key.removeprefix("ollama_")] = value
            elif flat_key.startswith("claude_"):
                provider_fields.setdefault("claude", {})[flat_key.removeprefix("claude_")] = value

        from app.config import ClaudeConfig, OllamaConfig

        for provider_name, fields in provider_fields.items():
            if provider_name not in llm.providers:
                if provider_name == "ollama":
                    llm.providers[provider_name] = OllamaConfig()
                elif provider_name == "claude":
                    llm.providers[provider_name] = ClaudeConfig()
            for key, value in fields.items():
                setattr(llm.providers[provider_name], key, value)

        self._write_config()
        return self.get_llm_config()

    # ── Generation ───────────────────────────────────────────────

    def get_generation_config(self) -> GenerationConfig:
        return self._config.generation

    def update_generation_config(self, update: GenerationSettingsUpdate) -> GenerationConfig:
        current = self._config.generation
        for key, value in update.model_dump(exclude_none=True).items():
            setattr(current, key, value)
        self._write_config()
        return current

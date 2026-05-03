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
from app.paths import resolve_path

logger = logging.getLogger(__name__)


class SettingsService:
    def __init__(self, config: AppConfig, config_path: Path | str = "config.yaml") -> None:
        self._config = config
        self._config_path = Path(resolve_path(str(config_path)))

    def get_online_search_config(self) -> OnlineSearchConfig:
        return self._config.online_search

    def update_online_search_config(self, update: OnlineSearchConfigUpdate) -> OnlineSearchConfig:
        update_data = update.model_dump(exclude_none=True)
        self._config.online_search = self._config.online_search.model_copy(update=update_data)
        self._write_config()
        return self._config.online_search

    async def test_connection(self, config: OnlineSearchConfigUpdate) -> ConnectionTestResult:
        provider = self._config.online_search.provider
        try:
            if provider == "baidu":
                from app.retrieval.baidu_provider import BaiduSearchProvider

                prov = BaiduSearchProvider()
                results = await prov.search("测试", max_results=1)
                return ConnectionTestResult(
                    success=True,
                    message=f"连接成功，返回 {len(results)} 条结果",
                )
            return ConnectionTestResult(
                success=False,
                message=f"Provider '{provider}' 尚未实现",
            )
        except Exception as e:
            logger.warning("连接测试失败: %s", e, exc_info=True)
            return ConnectionTestResult(
                success=False,
                message=f"连接失败: {e}",
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
        update_data = update.model_dump(exclude_none=True)
        self._config.knowledge_base = self._config.knowledge_base.model_copy(update=update_data)
        self._write_config()
        return self._config.knowledge_base

    # ── LLM ─────────────────────────────────────────────────────

    def get_llm_config(self) -> dict:
        """Return LLM config dict with api_key masked, providers flattened."""
        llm = self._config.llm
        result: dict = {
            "default_provider": llm.default_provider,
            "embed_provider": llm.embed_provider,
        }
        for name, prov in llm.providers.items():
            prov_data = prov.model_dump()
            if prov_data.get("api_key"):
                prov_data["api_key"] = "********"
            for field, value in prov_data.items():
                result[f"{name}_{field}"] = value
        return result

    def update_llm_config(self, update: LLMSettingsUpdate) -> dict:
        """Update LLM config, mapping flat field names to nested provider configs."""
        update_data = update.model_dump(exclude_none=True)
        llm = self._config.llm

        if "default_provider" in update_data:
            llm.default_provider = update_data.pop("default_provider")
        if "embed_provider" in update_data:
            llm.embed_provider = update_data.pop("embed_provider")

        # Map flattened provider fields to nested config
        provider_fields: dict[str, dict[str, str]] = {}
        for flat_key, value in update_data.items():
            for prefix in ("ollama", "claude", "openai"):
                if flat_key.startswith(f"{prefix}_"):
                    # Skip empty api_key — frontend sends "" for unchanged passwords
                    if flat_key.endswith("_api_key") and value == "":
                        break
                    provider_fields.setdefault(prefix, {})[flat_key.removeprefix(f"{prefix}_")] = value
                    break

        from app.config import ClaudeConfig, OllamaConfig, OpenAICompatibleConfig

        provider_defaults = {
            "ollama": OllamaConfig,
            "claude": ClaudeConfig,
            "openai": OpenAICompatibleConfig,
        }
        for provider_name, fields in provider_fields.items():
            if provider_name not in llm.providers:
                llm.providers[provider_name] = provider_defaults[provider_name]()
            llm.providers[provider_name] = llm.providers[provider_name].model_copy(update=fields)

        self._write_config()
        return self.get_llm_config()

    # ── Generation ───────────────────────────────────────────────

    def get_generation_config(self) -> GenerationConfig:
        return self._config.generation

    def update_generation_config(self, update: GenerationSettingsUpdate) -> GenerationConfig:
        update_data = update.model_dump(exclude_none=True)
        self._config.generation = self._config.generation.model_copy(update=update_data)
        self._write_config()
        return self._config.generation

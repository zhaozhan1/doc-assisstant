from __future__ import annotations

import os
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, YamlConfigSettingsSource


class KnowledgeBaseConfig(BaseModel):
    source_folder: str = ""
    db_path: str = "./data/chroma_db"
    metadata_path: str = "./data/metadata"
    chunk_size: int = Field(default=500, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=200)
    enable_query_rewrite: bool = True
    smart_chunking: bool = False


class OllamaConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    chat_model: str = "qwen2.5:14b"
    embed_model: str = "bge-large-zh-v1.5"


class OpenAICompatibleConfig(BaseModel):
    base_url: str = "http://localhost:18008/v1"
    api_key: str = ""
    chat_model: str = "qwen3"
    embed_model: str = "bge-m3"


class ClaudeConfig(BaseModel):
    base_url: str = "https://api.anthropic.com"
    api_key: str = ""
    chat_model: str = "claude-sonnet-4-20250514"

    @model_validator(mode="after")
    def _resolve_api_key(self) -> ClaudeConfig:
        if not self.api_key:
            self.api_key = os.environ.get("CLAUDE_API_KEY", "")
        return self


class LLMConfig(BaseModel):
    default_provider: Literal["ollama", "claude", "openai"] = "ollama"
    embed_provider: Literal["ollama", "openai"] = "ollama"
    providers: dict[str, OllamaConfig | ClaudeConfig | OpenAICompatibleConfig] = {
        "ollama": OllamaConfig(),
    }


class OCRConfig(BaseModel):
    tesseract_cmd: str = ""


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "./logs/app.log"


class OnlineSearchConfig(BaseModel):
    enabled: bool = False
    provider: str = "tavily"
    api_key: str = ""
    base_url: str = ""
    domains: list[str] = ["gov.cn"]
    max_results: int = Field(default=3, ge=1, le=10)


class GenerationConfig(BaseModel):
    output_format: str = "docx"
    save_path: str = "./output"
    include_sources: bool = True
    max_prompt_tokens: int = 4096
    word_template_path: str = ""


class ServerConfig(BaseModel):
    cors_origins: list[str] = ["http://localhost:5173"]
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 1


class AppConfig(BaseSettings):
    knowledge_base: KnowledgeBaseConfig = KnowledgeBaseConfig()
    llm: LLMConfig = LLMConfig()
    ocr: OCRConfig = OCRConfig()
    logging: LoggingConfig = LoggingConfig()
    online_search: OnlineSearchConfig = OnlineSearchConfig()
    generation: GenerationConfig = GenerationConfig()
    server: ServerConfig = ServerConfig()

    model_config = SettingsConfigDict(
        yaml_file="config.yaml",
        yaml_file_encoding="utf-8",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, /, _yaml_file: str | None = None, **values: Any) -> None:
        super().__init__(**values, _yaml_file=_yaml_file)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        yaml_file = init_settings.init_kwargs.get("_yaml_file") if hasattr(init_settings, "init_kwargs") else None
        return (
            init_settings,
            env_settings,
            YamlConfigSettingsSource(settings_cls, yaml_file=yaml_file),
            file_secret_settings,
        )

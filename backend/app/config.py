from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, YamlConfigSettingsSource


class KnowledgeBaseConfig(BaseModel):
    source_folder: str = ""
    db_path: str = "./data/chroma_db"
    metadata_path: str = "./data/metadata"
    chunk_size: int = Field(default=500, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=200)


class OllamaConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    chat_model: str = "qwen2.5:14b"
    embed_model: str = "bge-large-zh-v1.5"


class ClaudeConfig(BaseModel):
    base_url: str = "https://api.anthropic.com"
    api_key: str = ""
    chat_model: str = "claude-sonnet-4-20250514"


class LLMConfig(BaseModel):
    default_provider: Literal["ollama", "claude"] = "ollama"
    providers: dict[str, OllamaConfig | ClaudeConfig] = {
        "ollama": OllamaConfig(),
    }


class OCRConfig(BaseModel):
    tesseract_cmd: str = ""


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "./logs/app.log"


class AppConfig(BaseSettings):
    knowledge_base: KnowledgeBaseConfig = KnowledgeBaseConfig()
    llm: LLMConfig = LLMConfig()
    ocr: OCRConfig = OCRConfig()
    logging: LoggingConfig = LoggingConfig()

    model_config = SettingsConfigDict(
        yaml_file="config.yaml",
        yaml_file_encoding="utf-8",
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

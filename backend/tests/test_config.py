from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import AppConfig, ServerConfig


class TestAppConfig:
    def test_load_from_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
knowledge_base:
  source_folder: "/tmp/docs"
  db_path: "./data/chroma_db"
  chunk_size: 500
  chunk_overlap: 50

llm:
  default_provider: "ollama"
  providers:
    ollama:
      base_url: "http://localhost:11434"
      chat_model: "qwen2.5:14b"
      embed_model: "bge-large-zh-v1.5"

logging:
  level: "DEBUG"
  file: "./logs/test.log"
""")
        config = AppConfig(_yaml_file=str(config_file))
        assert config.knowledge_base.source_folder == "/tmp/docs"
        assert config.knowledge_base.chunk_size == 500
        assert config.llm.default_provider == "ollama"
        assert config.logging.level == "DEBUG"

    def test_default_values(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("{}")
        config = AppConfig(_yaml_file=str(config_file))
        assert config.knowledge_base.chunk_size == 500
        assert config.llm.default_provider == "openai"
        assert config.ocr.tesseract_cmd == ""

    def test_chunk_size_validation(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
knowledge_base:
  chunk_size: 50
""")
        with pytest.raises(ValidationError):
            AppConfig(_yaml_file=str(config_file))

    def test_chunk_overlap_validation(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
knowledge_base:
  chunk_overlap: 300
""")
        with pytest.raises(ValidationError):
            AppConfig(_yaml_file=str(config_file))


class TestClaudeApiKey:
    def test_api_key_from_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLAUDE_API_KEY", "sk-test-123")
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
llm:
  providers:
    claude:
      api_key: ""
""")
        config = AppConfig(_yaml_file=str(config_file))
        claude_cfg = config.llm.providers.get("claude")
        assert claude_cfg is not None
        assert claude_cfg.api_key == "sk-test-123"

    def test_yaml_api_key_takes_precedence(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLAUDE_API_KEY", "from-env")
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
llm:
  providers:
    claude:
      api_key: "from-yaml"
""")
        config = AppConfig(_yaml_file=str(config_file))
        claude_cfg = config.llm.providers.get("claude")
        assert claude_cfg is not None
        assert claude_cfg.api_key == "from-yaml"

    def test_no_api_key_defaults_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
        config_file = tmp_path / "config.yaml"
        config_file.write_text("{}")
        config = AppConfig(_yaml_file=str(config_file))
        assert config.llm.default_provider == "openai"


class TestEmbedProvider:
    def test_llm_config_has_embed_provider(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("{}")
        config = AppConfig(_yaml_file=str(config_file))
        assert config.llm.embed_provider == "openai"

    def test_embed_provider_from_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
llm:
  embed_provider: "ollama"
""")
        config = AppConfig(_yaml_file=str(config_file))
        assert config.llm.embed_provider == "ollama"


class TestOnlineSearchConfig:
    def test_online_search_config_defaults(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("{}")
        config = AppConfig(_yaml_file=str(config_file))
        assert config.online_search.enabled is False
        assert config.online_search.provider == "baidu"
        assert config.online_search.api_key == ""
        assert config.online_search.base_url == ""
        assert config.online_search.domains == ["gov.cn"]
        assert config.online_search.max_results == 3

    def test_app_config_has_online_search(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
online_search:
  enabled: true
  provider: "tavily"
  api_key: "tvly-test-key"
  domains:
    - "gov.cn"
    - "edu.cn"
  max_results: 5
""")
        config = AppConfig(_yaml_file=str(config_file))
        assert config.online_search.enabled is True
        assert config.online_search.api_key == "tvly-test-key"
        assert config.online_search.domains == ["gov.cn", "edu.cn"]
        assert config.online_search.max_results == 5


class TestGenerationConfig:
    def test_generation_config_defaults(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("{}")
        config = AppConfig(_yaml_file=str(config_file))
        assert config.generation.output_format == "docx"
        assert config.generation.save_path == "./output"
        assert config.generation.include_sources is True
        assert config.generation.max_prompt_tokens == 4096


class TestServerConfig:
    def test_default_cors_origins(self) -> None:
        config = ServerConfig()
        assert config.cors_origins == ["http://127.0.0.1:8000"]

    def test_custom_cors_origins(self) -> None:
        config = ServerConfig(cors_origins=["https://example.com", "https://app.example.com"])
        assert config.cors_origins == ["https://example.com", "https://app.example.com"]

    def test_default_host_and_port(self) -> None:
        config = ServerConfig()
        assert config.host == "127.0.0.1"
        assert config.port == 8000

    def test_custom_host_and_port(self) -> None:
        config = ServerConfig(host="0.0.0.0", port=9000)
        assert config.host == "0.0.0.0"
        assert config.port == 9000

    def test_default_workers(self) -> None:
        config = ServerConfig()
        assert config.workers == 1

    def test_server_config_in_app_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("{}")
        config = AppConfig(_yaml_file=str(config_file))
        assert isinstance(config.server, ServerConfig)
        assert config.server.cors_origins == ["http://127.0.0.1:8000"]

    def test_server_config_from_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
server:
  cors_origins:
    - https://prod.example.com
    - https://admin.example.com
  host: "0.0.0.0"
  port: 9000
  workers: 4
"""
        )
        config = AppConfig(_yaml_file=str(config_file))
        assert config.server.cors_origins == ["https://prod.example.com", "https://admin.example.com"]
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 9000
        assert config.server.workers == 4

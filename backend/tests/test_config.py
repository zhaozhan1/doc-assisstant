from __future__ import annotations

from pathlib import Path

import pytest

from app.config import AppConfig


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
        assert config.llm.default_provider == "ollama"
        assert config.ocr.tesseract_cmd == ""

    def test_chunk_size_validation(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
knowledge_base:
  chunk_size: 50
""")
        with pytest.raises(Exception):
            AppConfig(_yaml_file=str(config_file))

    def test_chunk_overlap_validation(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
knowledge_base:
  chunk_overlap: 300
""")
        with pytest.raises(Exception):
            AppConfig(_yaml_file=str(config_file))

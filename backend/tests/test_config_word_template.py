from __future__ import annotations

from app.config import GenerationConfig


def test_default_word_template_path_is_empty():
    config = GenerationConfig()
    assert config.word_template_path == ""


def test_word_template_path_can_be_set():
    config = GenerationConfig(word_template_path="/path/to/template.dotx")
    assert config.word_template_path == "/path/to/template.dotx"

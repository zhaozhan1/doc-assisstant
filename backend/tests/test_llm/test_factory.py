from __future__ import annotations

import pytest

from app.config import ClaudeConfig, LLMConfig, OllamaConfig
from app.llm.claude_provider import ClaudeProvider
from app.llm.factory import create_provider
from app.llm.ollama_provider import OllamaProvider


class TestFactory:
    def test_creates_ollama_provider(self) -> None:
        config = LLMConfig(
            default_provider="ollama",
            providers={"ollama": OllamaConfig()},
        )
        provider = create_provider(config)
        assert isinstance(provider, OllamaProvider)

    def test_creates_claude_provider(self) -> None:
        config = LLMConfig(
            default_provider="claude",
            providers={"claude": ClaudeConfig(api_key="test-key")},
        )
        provider = create_provider(config)
        assert isinstance(provider, ClaudeProvider)

    def test_raises_on_unknown_provider(self) -> None:
        # Pydantic Literal 会阻止无效值，使用 model_construct 绕过验证以测试 factory 防御分支
        config = LLMConfig.model_construct(
            default_provider="unknown",
            providers={"unknown": OllamaConfig()},
        )
        with pytest.raises(ValueError, match="未知 Provider"):
            create_provider(config)

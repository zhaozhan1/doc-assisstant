from __future__ import annotations

from app.config import ClaudeConfig, LLMConfig, OllamaConfig
from app.llm.base import BaseLLMProvider
from app.llm.claude_provider import ClaudeProvider
from app.llm.ollama_provider import OllamaProvider


def create_provider(config: LLMConfig) -> BaseLLMProvider:
    name = config.default_provider
    provider_config = config.providers[name]

    if name == "ollama" and isinstance(provider_config, OllamaConfig):
        return OllamaProvider(
            base_url=provider_config.base_url,
            chat_model=provider_config.chat_model,
            embed_model=provider_config.embed_model,
        )
    elif name == "claude" and isinstance(provider_config, ClaudeConfig):
        return ClaudeProvider(
            api_key=provider_config.api_key,
            base_url=provider_config.base_url,
            chat_model=provider_config.chat_model,
        )
    raise ValueError(f"未知 Provider: {name}")


def create_embed_provider(config: LLMConfig) -> BaseLLMProvider:
    name = config.embed_provider
    provider_config = config.providers[name]

    if name == "ollama" and isinstance(provider_config, OllamaConfig):
        return OllamaProvider(
            base_url=provider_config.base_url,
            chat_model=provider_config.chat_model,
            embed_model=provider_config.embed_model,
        )
    elif name == "claude" and isinstance(provider_config, ClaudeConfig):
        return ClaudeProvider(
            api_key=provider_config.api_key,
            base_url=provider_config.base_url,
            chat_model=provider_config.chat_model,
        )
    raise ValueError(f"未知 Embed Provider: {name}")

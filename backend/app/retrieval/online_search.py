from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.config import OnlineSearchConfig
from app.models.search import OnlineSearchItem, SourceType, UnifiedSearchResult

logger = logging.getLogger(__name__)


class BaseOnlineSearchProvider(ABC):
    """Abstract base class for online search providers."""

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 3,
        domains: list[str] | None = None,
    ) -> list[OnlineSearchItem]: ...


class OnlineSearchFactory:
    """Factory that creates an online search provider from config."""

    @staticmethod
    def create(config: OnlineSearchConfig) -> BaseOnlineSearchProvider | None:
        if not config.enabled:
            return None
        if config.provider == "baidu":
            from app.retrieval.baidu_provider import BaiduSearchProvider

            return BaiduSearchProvider(api_key=config.api_key, base_url=config.base_url)
        raise ValueError(f"未实现的在线搜索 Provider: {config.provider}")


class OnlineSearchService:
    """Service that wraps an online search provider and returns unified results."""

    def __init__(
        self,
        provider: BaseOnlineSearchProvider | None,
        config: OnlineSearchConfig,
    ) -> None:
        self._provider = provider
        self._config = config

    @classmethod
    def from_config(cls, config: OnlineSearchConfig) -> OnlineSearchService:
        provider = OnlineSearchFactory.create(config)
        return cls(provider=provider, config=config)

    async def search(self, query: str) -> list[UnifiedSearchResult]:
        if self._provider is None:
            logger.info("online search skipped: provider is None")
            return []
        try:
            items = await self._provider.search(
                query,
                self._config.max_results,
                self._config.domains or None,
            )
            logger.info("online search: query=%s items=%d", query, len(items))
            return [self._to_unified(item) for item in items]
        except Exception:
            logger.warning("online search failed", exc_info=True)
            return []

    def _to_unified(self, item: OnlineSearchItem) -> UnifiedSearchResult:
        return UnifiedSearchResult(
            source_type=SourceType.ONLINE,
            title=item.title,
            content=item.snippet,
            score=item.score,
            metadata={"url": item.url},
        )

from __future__ import annotations

import pytest

from app.config import OnlineSearchConfig
from app.models.search import OnlineSearchItem, SourceType
from app.retrieval.online_search import (
    BaseOnlineSearchProvider,
    OnlineSearchFactory,
    OnlineSearchService,
)


class MockProvider(BaseOnlineSearchProvider):
    """Test helper that returns canned results."""

    def __init__(self, items: list[OnlineSearchItem] | None = None) -> None:
        self._items = items or []

    async def search(
        self,
        query: str,
        max_results: int = 3,
        domains: list[str] | None = None,
    ) -> list[OnlineSearchItem]:
        return self._items[:max_results]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestOnlineSearchService:
    async def test_service_disabled_returns_empty(self) -> None:
        config = OnlineSearchConfig(enabled=False)
        service = OnlineSearchService(provider=None, config=config)
        results = await service.search("test query")
        assert results == []

    async def test_service_returns_unified_results(self) -> None:
        items = [
            OnlineSearchItem(
                title="Test Title",
                snippet="Test snippet content",
                url="https://example.com/page",
                score=0.9,
            ),
        ]
        config = OnlineSearchConfig(enabled=True, max_results=3)
        provider = MockProvider(items)
        service = OnlineSearchService(provider=provider, config=config)

        results = await service.search("test")

        assert len(results) == 1
        r = results[0]
        assert r.source_type == SourceType.ONLINE
        assert r.title == "Test Title"
        assert r.content == "Test snippet content"
        assert r.score == 0.9
        assert r.metadata["url"] == "https://example.com/page"


class TestOnlineSearchFactory:
    def test_factory_disabled_returns_none(self) -> None:
        config = OnlineSearchConfig(enabled=False)
        result = OnlineSearchFactory.create(config)
        assert result is None

    def test_factory_unimplemented_provider_raises(self) -> None:
        config = OnlineSearchConfig(enabled=True, provider="baidu")
        with pytest.raises(ValueError, match="未实现的在线搜索 Provider"):
            OnlineSearchFactory.create(config)

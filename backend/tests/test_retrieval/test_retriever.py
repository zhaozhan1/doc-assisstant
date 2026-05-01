from __future__ import annotations

from unittest.mock import AsyncMock, Mock

from app.models.search import SearchRequest, SourceType, UnifiedSearchResult
from app.retrieval.retriever import Retriever

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_local(title: str, score: float) -> UnifiedSearchResult:
    return UnifiedSearchResult(
        source_type=SourceType.LOCAL,
        title=title,
        content=f"local content for {title}",
        score=score,
    )


def _make_online(title: str, score: float) -> UnifiedSearchResult:
    return UnifiedSearchResult(
        source_type=SourceType.ONLINE,
        title=title,
        content=f"online content for {title}",
        score=score,
        metadata={"url": "https://example.com"},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRetriever:
    async def test_search_combines_local_and_online(self) -> None:
        local = AsyncMock()
        online = AsyncMock()
        fusion = Mock()

        local_result = _make_local("local doc", 0.9)
        online_result = _make_online("web page", 0.7)
        merged = [local_result, online_result]

        local.search.return_value = [local_result]
        online.search.return_value = [online_result]
        fusion.merge.return_value = merged

        retriever = Retriever(local_search=local, online_search=online, fusion=fusion)
        request = SearchRequest(query="test", top_k=10, local_only=False)

        results = await retriever.search(request)

        assert len(results) == 2
        local.search.assert_awaited_once_with("test", 10, None)
        online.search.assert_awaited_once_with("test")
        fusion.merge.assert_called_once_with([local_result], [online_result])

    async def test_search_local_only_skips_online(self) -> None:
        local = AsyncMock()
        online = AsyncMock()
        fusion = Mock()

        local_result = _make_local("local doc", 0.9)
        local.search.return_value = [local_result]
        fusion.merge.return_value = [local_result]

        retriever = Retriever(local_search=local, online_search=online, fusion=fusion)
        request = SearchRequest(query="test", top_k=5, local_only=True)

        results = await retriever.search(request)

        assert len(results) == 1
        local.search.assert_awaited_once()
        online.search.assert_not_awaited()
        fusion.merge.assert_called_once_with([local_result], [])

    async def test_search_local_directly(self) -> None:
        local = AsyncMock()
        online = AsyncMock()
        fusion = Mock()

        local_result = _make_local("local doc", 0.8)
        local.search.return_value = [local_result]

        retriever = Retriever(local_search=local, online_search=online, fusion=fusion)
        request = SearchRequest(query="test", top_k=3)

        results = await retriever.search_local(request)

        assert len(results) == 1
        assert results[0] == local_result
        local.search.assert_awaited_once_with("test", 3, None)
        online.search.assert_not_awaited()
        fusion.merge.assert_not_called()

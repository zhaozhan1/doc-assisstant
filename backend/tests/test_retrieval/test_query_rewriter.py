from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.llm.base import BaseLLMProvider
from app.retrieval.query_rewriter import QueryRewriter


@pytest.fixture
def mock_llm() -> AsyncMock:
    return AsyncMock(spec=BaseLLMProvider)


class TestQueryRewriter:
    async def test_rewrite_returns_improved_query(self, mock_llm: AsyncMock) -> None:
        mock_llm.chat.return_value = "关于加强政务公开工作的实施意见"
        rewriter = QueryRewriter(mock_llm)
        result = await rewriter.rewrite("加强政务公开")
        assert result == "关于加强政务公开工作的实施意见"
        mock_llm.chat.assert_called_once()

    async def test_rewrite_preserves_original_on_empty_response(self, mock_llm: AsyncMock) -> None:
        mock_llm.chat.return_value = "   "
        rewriter = QueryRewriter(mock_llm)
        result = await rewriter.rewrite("测试查询")
        assert result == "测试查询"

    async def test_rewrite_preserves_original_on_llm_error(self, mock_llm: AsyncMock) -> None:
        mock_llm.chat.side_effect = RuntimeError("LLM unavailable")
        rewriter = QueryRewriter(mock_llm)
        result = await rewriter.rewrite("测试查询")
        assert result == "测试查询"

    async def test_rewrite_uses_chat_not_classify(self, mock_llm: AsyncMock) -> None:
        mock_llm.chat.return_value = "改写结果"
        rewriter = QueryRewriter(mock_llm)
        await rewriter.rewrite("查询")
        mock_llm.chat.assert_called_once()
        assert not hasattr(mock_llm, "classify") or mock_llm.classify.call_count == 0


class TestQueryRewriterIntegration:
    async def test_retriever_calls_rewriter_when_enabled(self) -> None:
        """Verify Retriever uses QueryRewriter when provided."""
        from app.config import AppConfig, KnowledgeBaseConfig, LLMConfig, OnlineSearchConfig
        from app.retrieval.fusion import Fusion
        from app.retrieval.local_search import LocalSearch
        from app.retrieval.online_search import OnlineSearchService
        from app.retrieval.retriever import Retriever
        from app.models.search import SearchRequest

        mock_llm = AsyncMock(spec=BaseLLMProvider)
        mock_llm.chat.return_value = "改写后的查询"

        mock_local = AsyncMock(spec=LocalSearch)
        mock_local.search.return_value = []

        mock_online = AsyncMock(spec=OnlineSearchService)
        mock_online.search.return_value = []

        rewriter = QueryRewriter(mock_llm)
        retriever = Retriever(mock_local, mock_online, Fusion(), query_rewriter=rewriter)

        await retriever.search(SearchRequest(query="原始查询"))

        mock_llm.chat.assert_called_once()
        mock_local.search.assert_called_once_with("改写后的查询", 10, None)

    async def test_retriever_skips_rewriter_when_none(self) -> None:
        """Verify Retriever works without QueryRewriter (backward compatible)."""
        from app.retrieval.fusion import Fusion
        from app.retrieval.local_search import LocalSearch
        from app.retrieval.online_search import OnlineSearchService
        from app.retrieval.retriever import Retriever
        from app.models.search import SearchRequest

        mock_local = AsyncMock(spec=LocalSearch)
        mock_local.search.return_value = []

        mock_online = AsyncMock(spec=OnlineSearchService)
        mock_online.search.return_value = []

        retriever = Retriever(mock_local, mock_online, Fusion())

        await retriever.search(SearchRequest(query="原始查询"))

        mock_local.search.assert_called_once_with("原始查询", 10, None)

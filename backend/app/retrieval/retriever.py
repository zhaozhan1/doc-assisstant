from __future__ import annotations

import logging

from app.config import OnlineSearchConfig
from app.models.search import SearchRequest, UnifiedSearchResult
from app.retrieval.fusion import Fusion
from app.retrieval.local_search import LocalSearch
from app.retrieval.online_search import OnlineSearchService
from app.retrieval.query_rewriter import QueryRewriter

logger = logging.getLogger(__name__)


class Retriever:
    """Facade that coordinates local search, online search, and fusion."""

    def __init__(
        self,
        local_search: LocalSearch,
        online_search: OnlineSearchService,
        fusion: Fusion,
        query_rewriter: QueryRewriter | None = None,
    ) -> None:
        self._local = local_search
        self._online = online_search
        self._fusion = fusion
        self._query_rewriter = query_rewriter

    async def search(self, request: SearchRequest) -> list[UnifiedSearchResult]:
        query = request.query
        if self._query_rewriter:
            query = await self._query_rewriter.rewrite(request.query)
        local_results = await self._local.search(query, request.top_k, request.filter)
        online_results = [] if request.local_only else await self._online.search(query)
        logger.info("search: local=%d online=%d", len(local_results), len(online_results))
        return self._fusion.merge(local_results, online_results)

    async def search_local(self, request: SearchRequest) -> list[UnifiedSearchResult]:
        return await self._local.search(request.query, request.top_k, request.filter)

    def update_online_search(self, config: OnlineSearchConfig) -> None:
        self._online = OnlineSearchService.from_config(config)
        logger.info(
            "update_online_search: enabled=%s provider=%s",
            config.enabled, type(self._online._provider).__name__,
        )

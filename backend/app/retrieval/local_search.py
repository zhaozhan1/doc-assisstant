from __future__ import annotations

import logging
from collections import defaultdict

from app.db.vector_store import VectorStore
from app.llm.base import BaseLLMProvider
from app.models.search import SearchFilter, SourceType, UnifiedSearchResult

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 2000


class LocalSearch:
    def __init__(self, vector_store: VectorStore, llm: BaseLLMProvider) -> None:
        self._vs = vector_store
        self._llm = llm

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: SearchFilter | None = None,
    ) -> list[UnifiedSearchResult]:
        where = self._build_where(filters)
        raw_results = await self._vs.search(query, top_k=top_k * 3, filters=where)
        return self._deduplicate(raw_results, top_k)

    def _build_where(self, filters: SearchFilter | None) -> dict | None:
        if filters is None:
            return None
        conditions: list[dict] = []
        if filters.doc_types:
            conditions.append({"doc_type": {"$in": filters.doc_types}})
        if filters.date_from:
            conditions.append({"doc_date": {"$gte": filters.date_from.isoformat()}})
        if filters.date_to:
            conditions.append({"doc_date": {"$lte": filters.date_to.isoformat()}})
        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def _deduplicate(self, results: list, top_k: int) -> list[UnifiedSearchResult]:
        groups: dict[str, list] = defaultdict(list)
        for r in results:
            src = r.metadata.get("source_file", "")
            groups[src].append(r)

        file_results: list[UnifiedSearchResult] = []
        for _src, chunks in groups.items():
            chunks.sort(key=lambda c: c.score)
            best = chunks[0]
            score = max(0.0, 1.0 - best.score)
            combined = best.text
            for c in chunks[1:]:
                combined += "\n" + c.text
            combined = combined[:MAX_CONTENT_LENGTH]
            file_results.append(
                UnifiedSearchResult(
                    source_type=SourceType.LOCAL,
                    title=best.metadata.get("file_name", ""),
                    content=combined,
                    score=score,
                    metadata={k: v for k, v in best.metadata.items() if k in ("doc_type", "doc_date", "file_name")},
                )
            )
        file_results.sort(key=lambda r: r.score, reverse=True)
        return file_results[:top_k]

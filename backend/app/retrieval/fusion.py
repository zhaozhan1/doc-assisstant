from __future__ import annotations

from app.models.search import UnifiedSearchResult

LOCAL_WEIGHT = 1.1


class Fusion:
    """Merge local and online search results with local-priority weighting."""

    def __init__(self, max_results: int = 10) -> None:
        self._max_results = max_results

    def merge(
        self,
        local_results: list[UnifiedSearchResult],
        online_results: list[UnifiedSearchResult],
    ) -> list[UnifiedSearchResult]:
        scored: list[tuple[float, UnifiedSearchResult]] = []
        for r in local_results:
            scored.append((r.score * LOCAL_WEIGHT, r))
        for r in online_results:
            scored.append((r.score, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[: self._max_results]]

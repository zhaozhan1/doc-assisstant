from __future__ import annotations

from app.models.search import UnifiedSearchResult

LOCAL_WEIGHT = 1.1
MIN_PER_SOURCE = 3


class Fusion:
    """Merge local and online search results with per-source guarantee."""

    def __init__(self, max_results: int = 10) -> None:
        self._max_results = max_results

    def merge(
        self,
        local_results: list[UnifiedSearchResult],
        online_results: list[UnifiedSearchResult],
    ) -> list[UnifiedSearchResult]:
        # Sort each source by weighted score descending
        local_sorted = sorted(
            local_results, key=lambda r: r.score * LOCAL_WEIGHT, reverse=True,
        )
        online_sorted = sorted(
            online_results, key=lambda r: r.score, reverse=True,
        )

        # Guarantee top MIN_PER_SOURCE from each (fewer if source has less)
        local_guaranteed = local_sorted[:MIN_PER_SOURCE]
        online_guaranteed = online_sorted[:MIN_PER_SOURCE]
        guaranteed = local_guaranteed + online_guaranteed

        remaining_slots = self._max_results - len(guaranteed)
        if remaining_slots <= 0:
            return guaranteed[: self._max_results]

        # Fill remaining slots from non-guaranteed results by weighted score
        local_rest = local_sorted[MIN_PER_SOURCE:]
        online_rest = online_sorted[MIN_PER_SOURCE:]
        scored: list[tuple[float, UnifiedSearchResult]] = []
        for r in local_rest:
            scored.append((r.score * LOCAL_WEIGHT, r))
        for r in online_rest:
            scored.append((r.score, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        fill = [r for _, r in scored[:remaining_slots]]
        return guaranteed + fill

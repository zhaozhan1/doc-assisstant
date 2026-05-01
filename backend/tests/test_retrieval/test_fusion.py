from __future__ import annotations

from app.models.search import SourceType, UnifiedSearchResult
from app.retrieval.fusion import Fusion

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_local(title: str, score: float) -> UnifiedSearchResult:
    return UnifiedSearchResult(
        source_type=SourceType.LOCAL,
        title=title,
        content=f"content of {title}",
        score=score,
    )


def _make_online(title: str, score: float) -> UnifiedSearchResult:
    return UnifiedSearchResult(
        source_type=SourceType.ONLINE,
        title=title,
        content=f"content of {title}",
        score=score,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFusion:
    def test_merge_mixed_results(self) -> None:
        """Local + online merged and sorted by weighted score descending."""
        local = [
            _make_local("Local-A", 0.8),
            _make_local("Local-B", 0.5),
        ]
        online = [
            _make_online("Online-C", 0.9),
            _make_online("Online-D", 0.3),
        ]

        fusion = Fusion(max_results=10)
        results = fusion.merge(local, online)

        # All 4 results present, sorted by weighted score desc
        # Online-C (0.9) > Local-A (0.88) > Local-B (0.55) > Online-D (0.3)
        assert len(results) == 4
        assert results[0].title == "Online-C"  # 0.9
        assert results[1].title == "Local-A"  # 0.8 * 1.1 = 0.88
        assert results[2].title == "Local-B"  # 0.5 * 1.1 = 0.55
        assert results[3].title == "Online-D"  # 0.3

    def test_merge_local_priority(self) -> None:
        """Same raw score: local wins because of LOCAL_WEIGHT boost."""
        local = [_make_local("Local-A", 0.7)]
        online = [_make_online("Online-B", 0.7)]

        fusion = Fusion()
        results = fusion.merge(local, online)

        assert len(results) == 2
        assert results[0].source_type == SourceType.LOCAL
        assert results[1].source_type == SourceType.ONLINE

    def test_merge_truncates_to_max_results(self) -> None:
        """Fusion(max_results=2) truncates to top-2."""
        local = [
            _make_local("L1", 0.9),
            _make_local("L2", 0.8),
        ]
        online = [
            _make_online("O1", 0.85),
            _make_online("O2", 0.7),
        ]

        fusion = Fusion(max_results=2)
        results = fusion.merge(local, online)

        assert len(results) == 2
        # L1 (0.99) > L2 (0.88) > O1 (0.85) > O2 (0.7) => top 2 are L1, L2
        assert results[0].title == "L1"
        assert results[1].title == "L2"

    def test_merge_empty_inputs(self) -> None:
        """Empty lists produce empty output."""
        fusion = Fusion()
        assert fusion.merge([], []) == []

    def test_merge_only_local(self) -> None:
        """Only local results: sorted by weighted score descending."""
        local = [
            _make_local("Low", 0.4),
            _make_local("High", 0.9),
            _make_local("Mid", 0.6),
        ]

        fusion = Fusion()
        results = fusion.merge(local, [])

        assert len(results) == 3
        assert results[0].title == "High"
        assert results[1].title == "Mid"
        assert results[2].title == "Low"

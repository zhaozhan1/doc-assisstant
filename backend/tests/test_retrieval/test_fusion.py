from __future__ import annotations

from app.models.search import SourceType, UnifiedSearchResult
from app.retrieval.fusion import Fusion


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


class TestFusion:
    def test_guaranteed_top_3_per_source(self) -> None:
        """Each source contributes its top-3 by score, even if unsorted."""
        local = [
            _make_local("L-low", 0.3),
            _make_local("L-high", 0.9),
            _make_local("L-mid", 0.6),
            _make_local("L-extra", 0.2),
        ]
        online = [
            _make_online("O-low", 0.4),
            _make_online("O-high", 0.95),
            _make_online("O-mid", 0.7),
            _make_online("O-extra", 0.1),
        ]

        fusion = Fusion(max_results=10)
        results = fusion.merge(local, online)

        assert len(results) == 8
        local_titles = [r.title for r in results if r.source_type == SourceType.LOCAL]
        online_titles = [r.title for r in results if r.source_type == SourceType.ONLINE]
        # Top 3 local by score: L-high, L-mid, L-low
        assert local_titles == ["L-high", "L-mid", "L-low", "L-extra"]
        # Top 3 online by score: O-high, O-mid, O-low
        assert online_titles == ["O-high", "O-mid", "O-low", "O-extra"]

    def test_fallback_when_source_has_fewer_than_3(self) -> None:
        """If one source has < 3 results, remaining slots go to the other."""
        local = [_make_local("L1", 0.8)]
        online = [
            _make_online("O1", 0.9),
            _make_online("O2", 0.7),
            _make_online("O3", 0.5),
            _make_online("O4", 0.3),
        ]

        fusion = Fusion(max_results=10)
        results = fusion.merge(local, online)

        # 1 local + 3 online guaranteed + 1 online fill = 5
        assert len(results) == 5
        local_titles = [r.title for r in results if r.source_type == SourceType.LOCAL]
        online_titles = [r.title for r in results if r.source_type == SourceType.ONLINE]
        assert local_titles == ["L1"]
        assert online_titles == ["O1", "O2", "O3", "O4"]

    def test_truncates_to_max_results(self) -> None:
        """max_results caps total output."""
        local = [_make_local(f"L{i}", 0.9 - i * 0.05) for i in range(5)]
        online = [_make_online(f"O{i}", 0.85 - i * 0.05) for i in range(5)]

        fusion = Fusion(max_results=4)
        results = fusion.merge(local, online)

        assert len(results) == 4

    def test_empty_inputs(self) -> None:
        fusion = Fusion()
        assert fusion.merge([], []) == []

    def test_only_local(self) -> None:
        """Only local: sorted by weighted score descending."""
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

    def test_only_online(self) -> None:
        """Only online: sorted by score descending."""
        online = [
            _make_online("A", 0.3),
            _make_online("C", 0.9),
            _make_online("B", 0.6),
        ]

        fusion = Fusion()
        results = fusion.merge([], online)

        assert len(results) == 3
        assert results[0].title == "C"
        assert results[1].title == "B"
        assert results[2].title == "A"

    def test_local_priority_in_fill(self) -> None:
        """When filling remaining slots, local gets 1.1x weight."""
        local = [_make_local(f"L{i}", 0.5) for i in range(5)]
        online = [_make_online(f"O{i}", 0.5) for i in range(5)]

        fusion = Fusion(max_results=8)
        results = fusion.merge(local, online)

        # 3 local guaranteed + 3 online guaranteed = 6
        # 2 fill slots: local (0.55) beats online (0.5)
        assert len(results) == 8
        fill = results[6:]
        assert all(r.source_type == SourceType.LOCAL for r in fill)

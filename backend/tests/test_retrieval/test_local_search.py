from __future__ import annotations

from unittest.mock import AsyncMock

from app.db.vector_store import SearchResult, VectorStore
from app.llm.base import BaseLLMProvider
from app.models.search import SearchFilter, SourceType
from app.retrieval.local_search import LocalSearch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_vs(results: list[SearchResult]) -> AsyncMock:
    """Create a mock VectorStore whose search() returns the given results."""
    vs = AsyncMock(spec=VectorStore)
    vs.search = AsyncMock(return_value=results)
    return vs


def _make_mock_llm() -> AsyncMock:
    """Create a mock LLM provider (not directly used by LocalSearch)."""
    return AsyncMock(spec=BaseLLMProvider)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLocalSearch:
    async def test_basic_search(self) -> None:
        """Mock VectorStore.search returns 2 chunks from same file,
        verify result has correct source_type=LOCAL and score > 0."""
        vs = _make_mock_vs(
            [
                SearchResult(
                    text="关于XX的通知",
                    metadata={"source_file": "doc1.docx", "file_name": "doc1.docx"},
                    score=0.10,
                ),
                SearchResult(
                    text="各有关单位：",
                    metadata={"source_file": "doc1.docx", "file_name": "doc1.docx"},
                    score=0.20,
                ),
            ]
        )
        llm = _make_mock_llm()
        ls = LocalSearch(vector_store=vs, llm=llm)

        results = await ls.search("通知", top_k=5)

        assert len(results) == 1
        assert results[0].source_type == SourceType.LOCAL
        assert results[0].score > 0
        assert results[0].title == "doc1.docx"

    async def test_search_score_normalization(self) -> None:
        """Raw distance 0.15 -> score = 1 - 0.15 = 0.85."""
        vs = _make_mock_vs(
            [
                SearchResult(
                    text="内容",
                    metadata={"source_file": "a.docx", "file_name": "a.docx"},
                    score=0.15,
                ),
            ]
        )
        llm = _make_mock_llm()
        ls = LocalSearch(vector_store=vs, llm=llm)

        results = await ls.search("测试", top_k=5)

        assert len(results) == 1
        assert abs(results[0].score - 0.85) < 1e-6

    async def test_search_dedup_by_source_file(self) -> None:
        """3 chunks from 2 files -> 2 results, one per file."""
        vs = _make_mock_vs(
            [
                SearchResult(
                    text="通知正文A",
                    metadata={"source_file": "file_a.docx", "file_name": "file_a.docx"},
                    score=0.10,
                ),
                SearchResult(
                    text="通知正文B",
                    metadata={"source_file": "file_b.docx", "file_name": "file_b.docx"},
                    score=0.12,
                ),
                SearchResult(
                    text="通知续A",
                    metadata={"source_file": "file_a.docx", "file_name": "file_a.docx"},
                    score=0.25,
                ),
            ]
        )
        llm = _make_mock_llm()
        ls = LocalSearch(vector_store=vs, llm=llm)

        results = await ls.search("通知", top_k=5)

        assert len(results) == 2
        source_files = {r.metadata.get("file_name") for r in results}
        assert source_files == {"file_a.docx", "file_b.docx"}

    async def test_search_with_filters(self) -> None:
        """Pass SearchFilter, verify vs.search is called with filters dict."""
        vs = _make_mock_vs([])
        llm = _make_mock_llm()
        ls = LocalSearch(vector_store=vs, llm=llm)

        filters = SearchFilter(doc_types=["通知"])
        await ls.search("测试", top_k=5, filters=filters)

        vs.search.assert_called_once()
        call_kwargs = vs.search.call_args
        assert call_kwargs.kwargs.get("filters") == {"doc_type": {"$in": ["通知"]}}

    async def test_search_empty_results(self) -> None:
        """No results from VectorStore returns empty list."""
        vs = _make_mock_vs([])
        llm = _make_mock_llm()
        ls = LocalSearch(vector_store=vs, llm=llm)

        results = await ls.search("不存在的查询", top_k=5)

        assert results == []

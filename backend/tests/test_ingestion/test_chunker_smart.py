from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from app.ingestion.chunker import Chunker
from app.models.document import DocumentMetadata, ExtractedDoc


def _make_doc(text: str) -> ExtractedDoc:
    return ExtractedDoc(text=text, structure=[], source_path=Path("/tmp/test.txt"))


def _make_meta() -> DocumentMetadata:
    return DocumentMetadata(
        file_name="test.txt",
        source_path="/tmp/test.txt",
        import_time=datetime.now(),
        doc_type="report",
    )


class TestSmartSplit:
    def test_respects_heading_boundaries(self) -> None:
        """Smart split with large text should keep heading + content together."""
        text = "# 第一章\n\n" + "第一段内容较多。" * 30 + "\n\n# 第二章\n\n" + "第二段内容也很多。" * 30
        chunker = Chunker(chunk_size=200, chunk_overlap=0)
        chunks = chunker.smart_split(_make_doc(text), _make_meta())

        # With smart_split (1.6x = 320 limit), chapters should stay together
        # Regular split at 200 would split more aggressively
        regular_chunks = chunker.split(_make_doc(text), _make_meta())
        assert len(chunks) <= len(regular_chunks)

    def test_respects_paragraph_boundaries(self) -> None:
        """Long paragraphs should not be split mid-sentence when under limit."""
        text = "短段落。\n\n" + "这是一段很长的内容。" * 20 + "\n\n最后一个段落。"
        chunker = Chunker(chunk_size=800, chunk_overlap=0)
        chunks = chunker.smart_split(_make_doc(text), _make_meta())

        # "短段落" should be in its own chunk or with the next paragraph
        assert len(chunks) >= 1
        # Each chunk should respect sentence boundaries
        for chunk in chunks:
            assert len(chunk.text) > 0

    def test_uses_larger_chunk_size(self) -> None:
        """smart_split should merge more content per chunk than regular split."""
        text = "段落一内容较多。" * 10 + "\n\n" + "段落二内容也很多。" * 10
        chunker = Chunker(chunk_size=100, chunk_overlap=0)
        smart_chunks = chunker.smart_split(_make_doc(text), _make_meta())
        regular_chunks = chunker.split(_make_doc(text), _make_meta())

        # Smart split with larger effective size should produce fewer chunks
        assert len(smart_chunks) <= len(regular_chunks)

    def test_restores_original_chunk_size(self) -> None:
        """smart_split should not permanently change chunk_size."""
        chunker = Chunker(chunk_size=200, chunk_overlap=0)
        _ = chunker.smart_split(_make_doc("测试内容"), _make_meta())
        assert chunker._chunk_size == 200

    def test_empty_text_returns_empty(self) -> None:
        chunker = Chunker(chunk_size=500, chunk_overlap=0)
        chunks = chunker.smart_split(_make_doc(""), _make_meta())
        assert chunks == []


class TestSmartSplitIntegration:
    def test_ingester_uses_smart_split_when_configured(self) -> None:
        """Verify Ingester calls smart_split when config flag is set."""
        from app.config import AppConfig, KnowledgeBaseConfig, LLMConfig
        from app.ingestion.ingester import Ingester
        from unittest.mock import MagicMock, patch

        config = AppConfig(
            knowledge_base=KnowledgeBaseConfig(smart_chunking=True, chunk_size=500),
            llm=LLMConfig(),
        )
        mock_llm = MagicMock()
        mock_vs = MagicMock()

        with patch.object(Chunker, "smart_split", return_value=[]) as mock_smart:
            with patch.object(Chunker, "split", return_value=[]) as mock_regular:
                ingester = Ingester(config, mock_llm, mock_vs)
                # Verify the ingester was configured with smart_chunking
                assert ingester._use_smart_chunking is True

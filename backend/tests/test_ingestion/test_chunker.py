from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from app.ingestion.chunker import Chunker
from app.models.chunk import Chunk
from app.models.document import DocumentMetadata, ExtractedDoc


@pytest.fixture
def chunker() -> Chunker:
    return Chunker(chunk_size=100, chunk_overlap=20)


@pytest.fixture
def sample_meta() -> DocumentMetadata:
    return DocumentMetadata(
        file_name="test.txt",
        source_path="/tmp/test.txt",
        import_time=datetime.now(),
        doc_type="通知",
        doc_date=datetime(2024, 1, 1),
        file_created_time=datetime(2024, 1, 1, 10, 30, 0),
    )


def _make_doc(text: str) -> ExtractedDoc:
    return ExtractedDoc(text=text, structure=[], source_path=Path("/tmp/test.txt"))


class TestNormalChunking:
    def test_splits_into_chunks(self, chunker: Chunker, sample_meta: DocumentMetadata) -> None:
        text = "段落一。" + "字" * 80 + "\n\n段落二。" + "字" * 80
        doc = _make_doc(text)
        chunks = chunker.split(doc, sample_meta)
        assert len(chunks) >= 2
        for c in chunks:
            assert isinstance(c, Chunk)
            assert c.source_file == "/tmp/test.txt"

    def test_chunk_metadata(self, chunker: Chunker, sample_meta: DocumentMetadata) -> None:
        doc = _make_doc("测试内容")
        chunks = chunker.split(doc, sample_meta)
        assert chunks[0].metadata["doc_type"] == "通知"
        assert chunks[0].metadata["doc_date"] == "2024-01-01T00:00:00"
        assert chunks[0].metadata["file_created_time"] == "2024-01-01T10:30:00"
        assert chunks[0].chunk_index == 0


class TestEdgeCases:
    def test_short_text_produces_single_chunk(self, chunker: Chunker, sample_meta: DocumentMetadata) -> None:
        doc = _make_doc("短文本")
        chunks = chunker.split(doc, sample_meta)
        assert len(chunks) == 1
        assert chunks[0].text == "短文本"

    def test_empty_text_produces_no_chunks(self, chunker: Chunker, sample_meta: DocumentMetadata) -> None:
        doc = _make_doc("")
        chunks = chunker.split(doc, sample_meta)
        assert chunks == []

    def test_long_paragraph_is_split(self, chunker: Chunker, sample_meta: DocumentMetadata) -> None:
        text = "字" * 300
        doc = _make_doc(text)
        chunks = chunker.split(doc, sample_meta)
        assert len(chunks) >= 2

    def test_chunk_indices_sequential(self, chunker: Chunker, sample_meta: DocumentMetadata) -> None:
        text = "段一。" + "字" * 90 + "\n\n段二。" + "字" * 90 + "\n\n段三。" + "字" * 90
        doc = _make_doc(text)
        chunks = chunker.split(doc, sample_meta)
        for i, c in enumerate(chunks):
            assert c.chunk_index == i

    def test_force_split_long_paragraph(self, chunker: Chunker, sample_meta: DocumentMetadata) -> None:
        """A single paragraph > 2x chunk_size is force-split into multiple chunks at sentence boundaries."""
        # chunk_size=100, so create a paragraph with 300+ chars and sentence-ending punctuation
        sentence = "这是一句话，用来测试分块。"  # 13 chars per sentence
        long_text = sentence * 25  # ~325 chars, well over 2x chunk_size
        doc = _make_doc(long_text)
        chunks = chunker.split(doc, sample_meta)

        assert len(chunks) >= 3, f"Expected >= 3 chunks from long paragraph, got {len(chunks)}"
        # Every chunk should be under chunk_size (plus some tolerance for overlap)
        for c in chunks:
            assert len(c.text) <= chunker._chunk_size * 1.1, (
                f"Chunk too long: {len(c.text)} chars (chunk_size={chunker._chunk_size})"
            )
        # Reassembled text should preserve the original content (no data loss)
        reassembled = "".join(c.text for c in chunks)
        assert reassembled == long_text

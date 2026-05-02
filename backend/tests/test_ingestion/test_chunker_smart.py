from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.ingestion.chunker import Chunker
from app.models.document import DocumentMetadata, ExtractedDoc


def _make_doc(text: str) -> ExtractedDoc:
    return ExtractedDoc(text=text, structure=[], source_path=Path("test.txt"))


def _make_meta() -> DocumentMetadata:
    return DocumentMetadata(
        file_name="test.txt",
        source_path="test.txt",
        import_time=datetime(2026, 1, 1),
        doc_type="notice",
    )


class TestChunkerSmartSplit:
    def test_smart_split_uses_larger_chunk_size(self):
        chunker = Chunker(chunk_size=500, chunk_overlap=50)
        text = "第一段内容。" * 100 + "\n\n" + "第二段内容。" * 100
        doc = _make_doc(text)
        meta = _make_meta()
        chunks = chunker.smart_split(doc, meta)
        # smart_split should produce fewer chunks than regular split
        regular = chunker.split(doc, meta)
        assert len(chunks) <= len(regular)

    def test_chunk_size_restored_after_smart_split(self):
        chunker = Chunker(chunk_size=500, chunk_overlap=50)
        doc = _make_doc("测试内容")
        meta = _make_meta()
        chunker.smart_split(doc, meta)
        assert chunker._chunk_size == 500

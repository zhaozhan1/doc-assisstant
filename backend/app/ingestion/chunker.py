from __future__ import annotations

import re

from app.models.chunk import Chunk
from app.models.document import DocumentMetadata, ExtractedDoc


class Chunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def split(self, doc: ExtractedDoc, meta: DocumentMetadata) -> list[Chunk]:
        if not doc.text.strip():
            return []
        paragraphs = self._split_by_paragraph(doc.text)
        merged = self._merge_paragraphs(paragraphs)
        return [
            Chunk(
                text=text,
                source_file=str(doc.source_path),
                chunk_index=i,
                metadata={
                    "doc_type": meta.doc_type,
                    "doc_date": meta.doc_date.isoformat() if meta.doc_date else "",
                    "file_name": meta.file_name,
                },
            )
            for i, text in enumerate(merged)
        ]

    def _split_by_paragraph(self, text: str) -> list[str]:
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _merge_paragraphs(self, paragraphs: list[str]) -> list[str]:
        if not paragraphs:
            return []

        chunks: list[str] = []
        current = ""

        for para in paragraphs:
            if len(para) > self._chunk_size:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(self._split_long_text(para))
            elif len(current) + len(para) + 1 <= self._chunk_size:
                current = current + "\n\n" + para if current else para
            else:
                if current:
                    chunks.append(current)
                current = self._take_overlap(current) + para if chunks else para

        if current:
            chunks.append(current)

        return chunks if chunks else paragraphs

    def _split_long_text(self, text: str) -> list[str]:
        sentences = re.split(r"(?<=[。！？；\n])", text)
        chunks: list[str] = []
        current = ""
        for s in sentences:
            if not s:
                continue
            if len(s) > self._chunk_size:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(self._hard_split(s))
            elif len(current) + len(s) <= self._chunk_size:
                current += s
            else:
                if current:
                    chunks.append(current)
                current = s
        if current:
            chunks.append(current)
        return chunks

    def _hard_split(self, text: str) -> list[str]:
        return [text[i : i + self._chunk_size] for i in range(0, len(text), self._chunk_size)]

    def smart_split(self, doc: ExtractedDoc, meta: DocumentMetadata) -> list[Chunk]:
        """按段落+标题自然分块，增大 chunk_size 上限"""
        old_size = self._chunk_size
        self._chunk_size = min(int(old_size * 1.6), 800)
        try:
            return self.split(doc, meta)
        finally:
            self._chunk_size = old_size

    def _take_overlap(self, text: str) -> str:
        if not text or self._chunk_overlap <= 0:
            return ""
        return text[-self._chunk_overlap :]

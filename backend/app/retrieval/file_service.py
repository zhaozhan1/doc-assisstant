from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from app.db.vector_store import VectorStore
from app.ingestion.ingester import Ingester
from app.models.search import FileListRequest, IndexedFile
from app.models.task import FileResult

logger = logging.getLogger(__name__)


class FileService:
    def __init__(self, vector_store: VectorStore, ingester: Ingester) -> None:
        self._vs = vector_store
        self._ingester = ingester

    async def list_files(self, request: FileListRequest) -> list[IndexedFile]:
        all_chunks = await self._vs.list_all_chunks()
        groups: dict[str, list] = defaultdict(list)
        for chunk in all_chunks:
            src = chunk.metadata.get("source_file", "")
            if src:
                groups[src].append(chunk)

        files = []
        for src, chunks in groups.items():
            meta = chunks[0].metadata
            files.append(
                IndexedFile(
                    source_file=src,
                    file_name=meta.get("file_name", ""),
                    doc_type=meta.get("doc_type", ""),
                    doc_date=meta.get("doc_date") or None,
                    file_md5=meta.get("file_md5", ""),
                    chunk_count=len(chunks),
                )
            )

        files = self._filter(files, request)
        files = self._sort(files, request)
        return files

    async def delete_file(self, source_file: str) -> None:
        await self._vs.delete_by_file(source_file)

    async def reindex_file(self, source_file: str) -> FileResult:
        return await self._ingester.process_file(Path(source_file))

    async def update_classification(self, source_file: str, doc_type: str) -> None:
        await self._vs.update_file_metadata(source_file, {"doc_type": doc_type})

    def _filter(self, files: list[IndexedFile], request: FileListRequest) -> list[IndexedFile]:
        result = files
        if request.doc_types:
            result = [f for f in result if f.doc_type in request.doc_types]
        if request.date_from:
            result = [f for f in result if f.doc_date and f.doc_date >= request.date_from.isoformat()]
        if request.date_to:
            result = [f for f in result if f.doc_date and f.doc_date <= request.date_to.isoformat()]
        return result

    def _sort(self, files: list[IndexedFile], request: FileListRequest) -> list[IndexedFile]:
        if request.sort_by == "chunk_count":
            return sorted(files, key=lambda f: f.chunk_count, reverse=request.sort_order == "desc")
        key = request.sort_by
        return sorted(files, key=lambda f: getattr(f, key) or "", reverse=request.sort_order == "desc")

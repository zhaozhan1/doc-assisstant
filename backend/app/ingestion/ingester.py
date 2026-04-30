from __future__ import annotations

import logging
from pathlib import Path

from app.config import AppConfig
from app.db.vector_store import VectorStore
from app.ingestion.chunker import Chunker
from app.ingestion.classifier import Classifier, MetadataExtractor
from app.ingestion.decompressor import Decompressor
from app.ingestion.extractor import Extractor
from app.llm.base import BaseLLMProvider
from app.models.task import FileResult

logger = logging.getLogger(__name__)


class Ingester:
    def __init__(self, config: AppConfig, llm: BaseLLMProvider, vector_store: VectorStore) -> None:
        self.decompressor = Decompressor()
        self.extractor = Extractor(config.ocr)
        self.metadata_extractor = MetadataExtractor()
        self.classifier = Classifier(llm)
        self.chunker = Chunker(
            config.knowledge_base.chunk_size,
            config.knowledge_base.chunk_overlap,
        )
        self.vector_store = vector_store

    async def process_file(self, path: Path) -> FileResult:
        try:
            file_infos = self.decompressor.extract(path)
            if not file_infos:
                return FileResult(path=str(path), status="skipped", error="无支持的文件格式")

            total_chunks = 0
            for fi in file_infos:
                doc = self.extractor.extract(fi)
                meta = self.metadata_extractor.extract(doc)
                meta.doc_type = await self.classifier.classify(doc.text)

                existing = await self.vector_store.check_file_exists(
                    str(fi.path), meta.file_md5
                )
                if existing:
                    continue

                chunks = self.chunker.split(doc, meta)
                for c in chunks:
                    c.metadata["file_md5"] = meta.file_md5
                await self.vector_store.delete_by_file(str(fi.path))
                await self.vector_store.upsert(chunks)
                total_chunks += len(chunks)

            return FileResult(path=str(path), status="success", chunks_count=total_chunks)

        except Exception as e:
            logger.exception("处理文件失败: %s", path)
            return FileResult(path=str(path), status="failed", error=str(e))

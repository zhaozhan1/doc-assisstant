from __future__ import annotations

import logging
from dataclasses import dataclass

import chromadb

from app.llm.base import BaseLLMProvider
from app.models.chunk import Chunk

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    text: str
    metadata: dict
    score: float


class VectorStore:
    def __init__(self, db_path: str, llm: BaseLLMProvider) -> None:
        self._client = chromadb.PersistentClient(path=db_path)
        self._collection = self._client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"},
        )
        self._llm = llm

    async def upsert(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        embeddings = await self._llm.embed([c.text for c in chunks])
        ids = [f"{c.source_file}::{c.chunk_index}" for c in chunks]
        metadatas = [{"source_file": c.source_file, **c.metadata} for c in chunks]
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            metadatas=metadatas,
        )

    async def delete_by_file(self, source_file: str) -> None:
        self._collection.delete(where={"source_file": source_file})

    async def search(self, query: str, top_k: int = 10, filters: dict | None = None) -> list[SearchResult]:
        query_embedding = (await self._llm.embed([query]))[0]
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filters,
        )
        if not results["documents"] or not results["documents"][0]:
            return []
        return [
            SearchResult(text=doc, metadata=meta, score=dist)
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
                strict=False,
            )
        ]

    async def check_file_exists(self, source_file: str, file_md5: str) -> bool:
        results = self._collection.get(where={"source_file": source_file})
        if not results["ids"]:
            return False
        existing_md5 = results["metadatas"][0].get("file_md5", "")
        return existing_md5 == file_md5

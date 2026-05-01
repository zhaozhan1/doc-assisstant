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

    async def list_all_chunks(self, include_documents: bool = True) -> list[SearchResult]:
        includes: list[str] = ["metadatas"]
        if include_documents:
            includes.append("documents")
        results = self._collection.get(include=includes)
        if not results["ids"]:
            return []
        docs = results.get("documents") or [""] * len(results["ids"])
        return [
            SearchResult(text=doc, metadata=meta or {}, score=0.0)
            for doc, meta in zip(docs, results["metadatas"], strict=False)
        ]

    async def update_file_metadata(self, source_file: str, updates: dict) -> None:
        results = self._collection.get(where={"source_file": source_file})
        if not results["ids"]:
            return
        self._collection.update(
            ids=results["ids"],
            metadatas=[updates] * len(results["ids"]),
        )

    async def file_exists(self, source_file: str) -> bool:
        results = self._collection.get(where={"source_file": source_file}, limit=1)
        return bool(results["ids"])

    async def find_by_md5(self, file_md5: str) -> str | None:
        results = self._collection.get(where={"file_md5": file_md5})
        if not results["ids"]:
            return None
        return results["metadatas"][0].get("source_file")

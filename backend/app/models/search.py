from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class SearchFilter(BaseModel):
    doc_types: list[str] = Field(default_factory=list)
    date_from: date | None = None
    date_to: date | None = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    local_only: bool = False
    filter: SearchFilter | None = None


class SourceType(str, Enum):
    LOCAL = "local"
    ONLINE = "online"


class UnifiedSearchResult(BaseModel):
    source_type: SourceType
    title: str
    content: str
    score: float
    metadata: dict = Field(default_factory=dict)


class OnlineSearchItem(BaseModel):
    title: str
    snippet: str
    url: str
    score: float = 0.5


class FileListRequest(BaseModel):
    doc_types: list[str] = Field(default_factory=list)
    date_from: date | None = None
    date_to: date | None = None
    sort_by: Literal["file_name", "doc_date", "chunk_count"] = "file_name"
    sort_order: Literal["asc", "desc"] = "asc"


class IndexedFile(BaseModel):
    source_file: str
    file_name: str
    doc_type: str
    doc_date: str | None = None
    file_md5: str
    chunk_count: int
    duplicate_with: str | None = None


class ClassificationUpdate(BaseModel):
    doc_type: str


class OnlineSearchConfigUpdate(BaseModel):
    enabled: bool | None = None
    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    domains: list[str] | None = None
    max_results: int | None = None


class ConnectionTestResult(BaseModel):
    success: bool
    message: str

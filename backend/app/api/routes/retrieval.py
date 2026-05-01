from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_retriever
from app.models.search import SearchRequest, UnifiedSearchResult
from app.retrieval.retriever import Retriever

router = APIRouter(prefix="/api", tags=["retrieval"])

_retriever_dep = Depends(get_retriever)


@router.post("/search", response_model=list[UnifiedSearchResult])
async def search(
    request: SearchRequest,
    retriever: Retriever = _retriever_dep,
) -> list[UnifiedSearchResult]:
    return await retriever.search(request)


@router.post("/search/local", response_model=list[UnifiedSearchResult])
async def search_local(
    request: SearchRequest,
    retriever: Retriever = _retriever_dep,
) -> list[UnifiedSearchResult]:
    return await retriever.search_local(request)

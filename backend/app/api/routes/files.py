from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_file_service
from app.models.search import ClassificationUpdate, FileListRequest, IndexedFile
from app.retrieval.file_service import FileService

router = APIRouter(prefix="/api/files", tags=["files"])

_file_service_dep = Depends(get_file_service)


@router.get("", response_model=list[IndexedFile])
async def list_files(
    doc_types: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str = "file_name",
    sort_order: str = "asc",
    file_service: FileService = _file_service_dep,
) -> list[IndexedFile]:
    request = FileListRequest(
        doc_types=doc_types.split(",") if doc_types else [],
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return await file_service.list_files(request)


@router.delete("/{source_file:path}")
async def delete_file(
    source_file: str,
    file_service: FileService = _file_service_dep,
) -> dict:
    await file_service.delete_file(source_file)
    return {"status": "deleted"}


@router.post("/{source_file:path}/reindex")
async def reindex_file(
    source_file: str,
    file_service: FileService = _file_service_dep,
) -> dict:
    result = await file_service.reindex_file(source_file)
    return {"status": result.status, "chunks_count": result.chunks_count}


@router.put("/{source_file:path}/classification")
async def update_classification(
    source_file: str,
    body: ClassificationUpdate,
    file_service: FileService = _file_service_dep,
) -> dict:
    await file_service.update_classification(source_file, body.doc_type)
    return {"status": "updated"}

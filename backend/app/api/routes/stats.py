from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_file_service
from app.models.search import FileListRequest
from app.retrieval.file_service import FileService

router = APIRouter(prefix="/api", tags=["stats"])

_file_service_dep = Depends(get_file_service)


@router.get("/stats")
async def get_stats(file_service: FileService = _file_service_dep) -> dict:
    files = await file_service.list_files(FileListRequest())
    type_dist: dict[str, int] = {}
    last_updated = ""
    for f in files:
        type_dist[f.doc_type] = type_dist.get(f.doc_type, 0) + 1
        if f.import_date and f.import_date > last_updated:
            last_updated = f.import_date
    return {
        "total_files": len(files),
        "type_distribution": type_dist,
        "last_updated": last_updated or None,
    }

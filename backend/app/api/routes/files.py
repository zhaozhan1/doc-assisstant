from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import get_file_service, get_task_manager
from app.models.search import ClassificationUpdate, FileListRequest, IndexedFile
from app.retrieval.file_service import FileService
from app.task_manager import TaskManager

router = APIRouter(prefix="/api/files", tags=["files"])

_file_service_dep = Depends(get_file_service)
_task_mgr_dep = Depends(get_task_manager)
_file_required = File(...)


@router.get("", response_model=list[IndexedFile])
async def list_files(
    doc_types: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: Literal["file_name", "doc_date", "chunk_count"] = "file_name",
    sort_order: Literal["asc", "desc"] = "asc",
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
    try:
        await file_service.delete_file(source_file)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"status": "deleted"}


@router.post("/{source_file:path}/reindex")
async def reindex_file(
    source_file: str,
    file_service: FileService = _file_service_dep,
) -> dict:
    try:
        result = await file_service.reindex_file(source_file)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"status": result.status, "chunks_count": result.chunks_count}


@router.put("/{source_file:path}/classification")
async def update_classification(
    source_file: str,
    body: ClassificationUpdate,
    file_service: FileService = _file_service_dep,
) -> dict:
    await file_service.update_classification(source_file, body.doc_type)
    return {"status": "updated"}


@router.post("/upload")
async def upload_files(
    files: list[UploadFile] = _file_required,
    task_manager: TaskManager = _task_mgr_dep,
) -> dict:
    upload_dir = Path(tempfile.mkdtemp(prefix="doc_upload_"))
    paths: list[Path] = []
    for f in files:
        dest = upload_dir / f.filename
        content = await f.read()
        if not content:
            continue
        dest.write_bytes(content)
        paths.append(dest)

    if not paths:
        raise HTTPException(status_code=422, detail="未提供有效文件")

    task_id = await task_manager.start_import(paths)
    return {"task_id": task_id}


@router.get("/download/{file_path:path}")
async def download_file(file_path: str) -> FileResponse:
    if ".." in Path(file_path).parts:
        raise HTTPException(status_code=400, detail="非法路径")
    path = Path(file_path).resolve()
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")
    return FileResponse(path, filename=path.name)

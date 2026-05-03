from __future__ import annotations

import shutil
import tempfile
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import get_config, get_file_service, get_task_manager
from app.config import AppConfig
from app.models.search import ClassificationUpdate, FileListRequest, IndexedFile
from app.retrieval.file_service import FileService
from app.task_manager import TaskManager

router = APIRouter(prefix="/api/files", tags=["files"])

_file_service_dep = Depends(get_file_service)
_task_mgr_dep = Depends(get_task_manager)
_config_dep = Depends(get_config)
_file_required = File(...)


@router.get("", response_model=list[IndexedFile])
async def list_files(
    doc_types: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: Literal["file_name", "import_date", "chunk_count"] = "import_date",
    sort_order: Literal["asc", "desc"] = "desc",
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


_MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB

_ZIP_MAGIC = b"PK\x03\x04"
_OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_PDF_MAGIC = b"%PDF"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPG_MAGIC = b"\xff\xd8\xff"

_MAGIC_MAP: dict[str, bytes] = {
    ".docx": _ZIP_MAGIC,
    ".xlsx": _ZIP_MAGIC,
    ".pptx": _ZIP_MAGIC,
    ".doc": _OLE2_MAGIC,
    ".xls": _OLE2_MAGIC,
    ".ppt": _OLE2_MAGIC,
    ".pdf": _PDF_MAGIC,
    ".png": _PNG_MAGIC,
    ".jpg": _JPG_MAGIC,
    ".jpeg": _JPG_MAGIC,
}


def _validate_file_type(filename: str, content: bytes) -> str | None:
    """Return an error message if file type is invalid, or None if OK."""
    ext = Path(filename).suffix.lower()
    expected = _MAGIC_MAP.get(ext)
    if expected is None:
        return None
    if content[: len(expected)] != expected:
        return f"文件格式不匹配: {filename} 不是有效的文件"
    return None


@router.post("/upload")
async def upload_files(
    files: list[UploadFile] = _file_required,
    task_manager: TaskManager = _task_mgr_dep,
) -> dict:
    upload_dir = Path(tempfile.mkdtemp(prefix="doc_upload_"))
    paths: list[Path] = []
    for f in files:
        safe_name = Path(f.filename).name
        if not safe_name:
            continue
        dest = upload_dir / safe_name
        content = await f.read()
        if not content:
            continue
        if len(content) > _MAX_UPLOAD_SIZE:
            shutil.rmtree(upload_dir, ignore_errors=True)
            raise HTTPException(status_code=413, detail=f"文件过大: {safe_name}（上限 50MB）")
        type_error = _validate_file_type(safe_name, content)
        if type_error:
            shutil.rmtree(upload_dir, ignore_errors=True)
            raise HTTPException(status_code=422, detail=type_error)
        dest.write_bytes(content)
        paths.append(dest)

    if not paths:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(status_code=422, detail="未提供有效文件")

    task_id = await task_manager.start_import(paths)
    return {"task_id": task_id}


@router.get("/download/{file_path:path}")
async def download_file(
    file_path: str,
    config: AppConfig = _config_dep,
) -> FileResponse:
    if ".." in Path(file_path).parts:
        raise HTTPException(status_code=400, detail="非法路径")
    p = Path(file_path)
    for part in p.parents:
        if part.exists() and part.is_symlink():
            raise HTTPException(status_code=403, detail="非法路径")
    if p.exists() and p.is_symlink():
        raise HTTPException(status_code=403, detail="非法路径")
    path = p.resolve()
    allowed_root = Path(config.generation.save_path).resolve()
    try:
        path.relative_to(allowed_root)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="无权访问该路径") from exc
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")
    return FileResponse(path, filename=path.name)

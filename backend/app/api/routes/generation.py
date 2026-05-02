from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import get_config, get_pptx_generator, get_pptx_task_manager, get_writer_service
from app.config import AppConfig
from app.generation.pptx_generator import PptxGenerator
from app.generation.pptx_task_manager import PptxTaskManager
from app.generation.word_parser import WordParseError
from app.generation.writer_service import WriterService
from app.models.generation import GenerationRequest, GenerationResult

router = APIRouter(prefix="/api/generation", tags=["generation"])

logger = logging.getLogger(__name__)


def _validate_path(file_path: str, config: AppConfig, label: str = "文件") -> Path:
    """Validate a user-supplied path against allowed directories.

    Allows paths under generation save_path or knowledge_base source_folder.
    Raises HTTPException on path traversal, symlink, or access denial.
    """
    if ".." in Path(file_path).parts:
        raise HTTPException(status_code=400, detail=f"非法{label}路径")
    p = Path(file_path)
    # Check for symlinks in the path chain
    for part in p.parents:
        candidate = part
        if candidate.exists() and candidate.is_symlink():
            raise HTTPException(status_code=403, detail=f"非法{label}路径（符号链接）")
    if p.exists() and p.is_symlink():
        raise HTTPException(status_code=403, detail=f"非法{label}路径（符号链接）")
    resolved = p.resolve()
    allowed_dirs = [
        Path(config.generation.save_path).resolve(),
        Path(config.knowledge_base.source_folder).resolve(),
    ]
    for allowed in allowed_dirs:
        try:
            resolved.relative_to(allowed)
            return resolved
        except ValueError:
            continue
    raise HTTPException(status_code=403, detail=f"无权访问该{label}路径")


_writer_service_dep = Depends(get_writer_service)


@router.post("/generate", response_model=GenerationResult)
async def generate(
    req: GenerationRequest,
    service: WriterService = _writer_service_dep,
) -> GenerationResult:
    return await service.generate_from_description(req)


@router.post("/generate/stream")
async def generate_stream(
    req: GenerationRequest,
    service: WriterService = _writer_service_dep,
):
    async def event_generator():
        async for token in service.generate_stream(req):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


class PptxRequest(BaseModel):
    source_type: Literal["upload", "kb", "session"]
    file_path: str | None = Field(default=None, min_length=1, max_length=500)
    template_path: str | None = Field(default=None, min_length=1, max_length=500)


_pptx_gen_dep = Depends(get_pptx_generator)
_pptx_task_dep = Depends(get_pptx_task_manager)
_config_dep = Depends(get_config)


@router.post("/generate-pptx")
async def generate_pptx(
    req: PptxRequest,
    pptx_gen: PptxGenerator = _pptx_gen_dep,
    task_mgr: PptxTaskManager = _pptx_task_dep,
    config: AppConfig = _config_dep,
):
    if not req.file_path:
        raise HTTPException(status_code=400, detail="必须提供 file_path")

    if not task_mgr.can_start():
        raise HTTPException(status_code=429, detail="当前生成任务过多，请稍后重试")

    source = _validate_path(req.file_path, config, label="源文件")
    template = _validate_path(req.template_path, config, label="模板") if req.template_path else None
    task_id = task_mgr.create_task(source)

    output_path_holder: list[str] = []

    async def _run():
        try:

            def on_step(step_name: str, step_index: int) -> None:
                task_mgr.update_step(task_id, step_name, step_index)

            result = await pptx_gen.generate(source, template, on_step=on_step)
            output_path_holder.append(str(result.output_path))
            task_mgr.complete_task(
                task_id,
                output_path=str(result.output_path),
                slide_count=result.slide_count,
                slides_data=[
                    {"slide_type": s.slide_type, "title": s.title, "bullets": s.bullets} for s in result.slides
                ],
                source_doc=result.source_doc,
                duration_ms=result.duration_ms,
            )
        except WordParseError as e:
            task_mgr.fail_task(task_id, f"文档解析失败: {e.reason}")
        except Exception:
            logger.exception("PPT 生成失败: task_id=%s", task_id)
            # Clean up partial output if it was created
            for p in output_path_holder:
                Path(p).unlink(missing_ok=True)
            task_mgr.fail_task(task_id, "PPT 生成失败，请稍后重试")

    asyncio.create_task(_run())
    return {"task_id": task_id}


@router.get("/pptx-result/{task_id}")
async def get_pptx_result(
    task_id: str,
    task_mgr: PptxTaskManager = _pptx_task_dep,
):
    try:
        progress = task_mgr.get_progress(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="任务不存在") from None
    return {
        "status": progress.status.value,
        "current_step": progress.current_step,
        "step_index": progress.step_index,
        "total_steps": progress.total_steps,
        "output_path": progress.output_path,
        "slide_count": progress.slide_count,
        "slides": progress.slides_data,
        "source_doc": progress.source_doc,
        "duration_ms": progress.duration_ms,
        "error": progress.error,
    }

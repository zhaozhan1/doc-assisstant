from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import get_pptx_generator, get_pptx_task_manager, get_writer_service
from app.generation.pptx_generator import PptxGenerator
from app.generation.pptx_task_manager import PptxTaskManager
from app.generation.word_parser import WordParseError
from app.generation.writer_service import WriterService
from app.models.generation import GenerationRequest, GenerationResult

router = APIRouter(prefix="/api/generation", tags=["generation"])

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
    source_type: str  # upload | kb | session
    file_path: str | None = None
    template_path: str | None = None


_pptx_gen_dep = Depends(get_pptx_generator)
_pptx_task_dep = Depends(get_pptx_task_manager)


@router.post("/generate-pptx")
async def generate_pptx(
    req: PptxRequest,
    pptx_gen: PptxGenerator = _pptx_gen_dep,
    task_mgr: PptxTaskManager = _pptx_task_dep,
):
    if not req.file_path:
        raise HTTPException(status_code=400, detail="必须提供 file_path")

    source = Path(req.file_path)
    template = Path(req.template_path) if req.template_path else None
    task_id = task_mgr.create_task(source)

    async def _run():
        try:
            task_mgr.update_step(task_id, "parsing", 1)
            result = await pptx_gen.generate(source, template)
            task_mgr.update_step(task_id, "summarizing", 2)
            task_mgr.update_step(task_id, "generating", 3)
            task_mgr.complete_task(
                task_id,
                output_path=str(result.output_path),
                slide_count=result.slide_count,
                slides_data=[{"slide_type": s.slide_type, "title": s.title, "bullets": s.bullets} for s in result.slides],
                source_doc=result.source_doc,
                duration_ms=result.duration_ms,
            )
        except WordParseError as e:
            task_mgr.fail_task(task_id, f"文档解析失败: {e}")
        except Exception as e:
            task_mgr.fail_task(task_id, f"生成失败: {e}")

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

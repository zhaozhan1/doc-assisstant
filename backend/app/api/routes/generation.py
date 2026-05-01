from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_writer_service
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

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.api.deps import get_template_manager
from app.generation.template_manager import TemplateManager
from app.models.generation import TemplateDef

router = APIRouter(prefix="/api/templates", tags=["templates"])

_tm_dep = Depends(get_template_manager)


@router.get("", response_model=list[TemplateDef])
async def list_templates(
    doc_type: str | None = Query(default=None),
    tm: TemplateManager = _tm_dep,
) -> list[TemplateDef]:
    return tm.list_templates(doc_type=doc_type)


@router.get("/{template_id}", response_model=TemplateDef)
async def get_template(
    template_id: str,
    tm: TemplateManager = _tm_dep,
) -> TemplateDef:
    try:
        return tm.get_template(template_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("", response_model=TemplateDef, status_code=201)
async def create_template(
    template: TemplateDef,
    tm: TemplateManager = _tm_dep,
) -> TemplateDef:
    try:
        return tm.create_template(template)
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.put("/{template_id}", response_model=TemplateDef)
async def update_template(
    template_id: str,
    template: TemplateDef,
    tm: TemplateManager = _tm_dep,
) -> TemplateDef:
    try:
        return tm.update_template(template_id, template)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: str,
    tm: TemplateManager = _tm_dep,
) -> Response:
    try:
        tm.delete_template(template_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    return Response(status_code=204)

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_config, get_settings_service
from app.config import AppConfig, OnlineSearchConfig
from app.models.search import (
    ConnectionTestResult,
    GenerationSettingsUpdate,
    KBSettingsUpdate,
    LLMSettingsUpdate,
    OnlineSearchConfigUpdate,
)
from app.settings_service import SettingsService

router = APIRouter(prefix="/api/settings", tags=["settings"])

_settings_dep = Depends(get_settings_service)
_config_dep = Depends(get_config)


def _mask_config(config: OnlineSearchConfig) -> dict:
    data = config.model_dump()
    if data.get("api_key"):
        data["api_key"] = "********"
    return data


@router.get("/online-search")
async def get_online_search_config(
    service: SettingsService = _settings_dep,
) -> dict:
    return _mask_config(service.get_online_search_config())


@router.put("/online-search")
async def update_online_search_config(
    update: OnlineSearchConfigUpdate,
    service: SettingsService = _settings_dep,
) -> dict:
    return _mask_config(service.update_online_search_config(update))


@router.post("/online-search/test-connection", response_model=ConnectionTestResult)
async def test_connection(
    config: OnlineSearchConfigUpdate,
    service: SettingsService = _settings_dep,
) -> ConnectionTestResult:
    return await service.test_connection(config)


# ── Knowledge Base Settings ──────────────────────────────────


@router.get("/knowledge-base")
async def get_kb_config(service: SettingsService = _settings_dep) -> dict:
    return service.get_kb_config().model_dump()


@router.put("/knowledge-base")
async def update_kb_config(
    update: KBSettingsUpdate,
    service: SettingsService = _settings_dep,
) -> dict:
    return service.update_kb_config(update).model_dump()


# ── LLM Settings ─────────────────────────────────────────────


@router.get("/llm")
async def get_llm_config(service: SettingsService = _settings_dep) -> dict:
    return service.get_llm_config()


@router.put("/llm")
async def update_llm_config(
    request: Request,
    update: LLMSettingsUpdate,
    service: SettingsService = _settings_dep,
) -> dict:
    result = service.update_llm_config(update)
    # Recreate LLM providers with updated config
    config = service._config
    from app.llm.factory import create_embed_provider, create_provider

    request.app.state.llm = create_provider(config.llm)
    request.app.state.embed_llm = create_embed_provider(config.llm)
    return result


# ── Generation Settings ──────────────────────────────────────


@router.get("/generation")
async def get_generation_config(service: SettingsService = _settings_dep) -> dict:
    return service.get_generation_config().model_dump()


@router.put("/generation")
async def update_generation_config(
    update: GenerationSettingsUpdate,
    service: SettingsService = _settings_dep,
) -> dict:
    return service.update_generation_config(update).model_dump()


# ── File Browser ─────────────────────────────────────────────


@router.get("/files/browse")
async def browse_directory(
    path: str = ".",
    config: AppConfig = _config_dep,
) -> dict:
    target = Path(path).resolve()
    # Restrict browsing to user home and configured paths
    allowed_prefixes = [
        Path.home().resolve(),
        Path(config.knowledge_base.source_folder).resolve(),
        Path(config.generation.save_path).resolve(),
        Path(".").resolve(),
    ]
    if not any(str(target).startswith(str(prefix)) for prefix in allowed_prefixes):
        return {"path": str(target), "children": []}
    if not target.is_dir():
        return {"path": str(target), "children": []}
    children = []
    for child in sorted(target.iterdir()):
        if child.name.startswith("."):
            continue
        children.append({"name": child.name, "path": str(child), "is_dir": child.is_dir()})
    return {"path": str(target), "children": children}

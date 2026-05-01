from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_settings_service
from app.config import OnlineSearchConfig
from app.models.search import ConnectionTestResult, OnlineSearchConfigUpdate
from app.settings_service import SettingsService

router = APIRouter(prefix="/api/settings", tags=["settings"])

_settings_dep = Depends(get_settings_service)


@router.get("/online-search", response_model=OnlineSearchConfig)
async def get_online_search_config(
    service: SettingsService = _settings_dep,
) -> OnlineSearchConfig:
    return service.get_online_search_config()


@router.put("/online-search", response_model=OnlineSearchConfig)
async def update_online_search_config(
    update: OnlineSearchConfigUpdate,
    service: SettingsService = _settings_dep,
) -> OnlineSearchConfig:
    return service.update_online_search_config(update)


@router.post("/online-search/test-connection", response_model=ConnectionTestResult)
async def test_connection(
    config: OnlineSearchConfigUpdate,
    service: SettingsService = _settings_dep,
) -> ConnectionTestResult:
    return await service.test_connection(config)

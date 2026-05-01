from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI

from app.api.routes import files, health, retrieval, settings
from app.config import AppConfig, LoggingConfig
from app.db.vector_store import VectorStore
from app.ingestion.ingester import Ingester
from app.llm.factory import create_embed_provider, create_provider
from app.retrieval.file_service import FileService
from app.retrieval.fusion import Fusion
from app.retrieval.local_search import LocalSearch
from app.retrieval.online_search import OnlineSearchService
from app.retrieval.retriever import Retriever
from app.settings_service import SettingsService
from app.task_manager import TaskManager

logger = logging.getLogger(__name__)


def setup_logging(config: LoggingConfig) -> None:
    log_format = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
    log_level = getattr(logging, config.level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)

    log_path = Path(config.file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(config.file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(file_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = AppConfig()
    llm = create_provider(config.llm)
    embed_llm = create_embed_provider(config.llm)
    vector_store = VectorStore(config.knowledge_base.db_path, embed_llm)
    ingester = Ingester(config, llm, vector_store)
    task_manager = TaskManager(ingester)
    local_search = LocalSearch(vector_store, embed_llm)
    online_search = OnlineSearchService.from_config(config.online_search)
    fusion = Fusion()
    retriever = Retriever(local_search, online_search, fusion)
    file_service = FileService(vector_store, ingester)
    settings_service = SettingsService(config)

    app.state.config = config
    app.state.llm = llm
    app.state.embed_llm = embed_llm
    app.state.vector_store = vector_store
    app.state.ingester = ingester
    app.state.task_manager = task_manager
    app.state.retriever = retriever
    app.state.file_service = file_service
    app.state.settings_service = settings_service

    yield


def create_app() -> FastAPI:
    config = AppConfig()
    setup_logging(config.logging)
    logger.info("应用启动")

    app = FastAPI(title="公文助手", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(retrieval.router)
    app.include_router(files.router)
    app.include_router(settings.router)

    return app


app = create_app()

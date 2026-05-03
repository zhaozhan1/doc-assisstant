from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI

from app.api.middleware import register_exception_handlers
from app.api.routes import files, generation, health, retrieval, settings, stats, templates, ws
from app.config import AppConfig, LoggingConfig
from app.db.vector_store import VectorStore
from app.generation.docx_formatter import DocxFormatter
from app.generation.intent_parser import IntentParser
from app.generation.pptx_generator import PptxGenerator
from app.generation.pptx_task_manager import PptxTaskManager
from app.generation.prompt_builder import PromptBuilder
from app.generation.template_manager import TemplateManager
from app.generation.writer import Writer
from app.generation.writer_service import WriterService
from app.ingestion.ingester import Ingester
from app.llm.factory import create_embed_provider, create_provider
from app.paths import resolve_path
from app.retrieval.file_service import FileService
from app.retrieval.fusion import Fusion
from app.retrieval.local_search import LocalSearch
from app.retrieval.online_search import OnlineSearchService
from app.retrieval.retriever import Retriever
from app.settings_service import SettingsService
from app.task_manager import TaskManager

logger = logging.getLogger(__name__)


def setup_logging(config: LoggingConfig, *, _force: bool = False) -> None:
    import structlog

    log_level = getattr(logging, config.level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid re-adding handlers if they already exist (e.g. during hot reload)
    if _force or not root_logger.handlers:
        if _force:
            for h in root_logger.handlers[:]:
                root_logger.removeHandler(h)

        shared_processors: list = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
        ]

        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processors=[
                    *shared_processors,
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.dev.ConsoleRenderer(),
                ],
                foreign_pre_chain=shared_processors,
            )
        )
        root_logger.addHandler(console_handler)

        log_path = Path(config.file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(config.file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processors=[
                    *shared_processors,
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.processors.JSONRenderer(),
                ],
                foreign_pre_chain=shared_processors,
            )
        )
        root_logger.addHandler(file_handler)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def _find_frontend_dir() -> Path | None:
    import sys

    if getattr(sys, "frozen", False):
        candidate = Path(sys._MEIPASS) / "frontend"
    else:
        candidate = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    return candidate if (candidate / "index.html").exists() else None


def create_app() -> FastAPI:
    config = AppConfig(_yaml_file=resolve_path("config.yaml"))
    config.knowledge_base.db_path = resolve_path(config.knowledge_base.db_path)
    config.knowledge_base.metadata_path = resolve_path(config.knowledge_base.metadata_path)
    config.logging.file = resolve_path(config.logging.file)
    config.generation.save_path = resolve_path(config.generation.save_path)
    setup_logging(config.logging)
    logger.info("应用启动")
    provider_cfg = config.llm.providers.get(config.llm.default_provider)
    logger.info("配置加载: provider=%s, api_key_set=%s, base_url=%s",
                config.llm.default_provider,
                bool(getattr(provider_cfg, "api_key", "")),
                getattr(provider_cfg, "base_url", ""))

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        llm = create_provider(config.llm)
        embed_llm = create_embed_provider(config.llm)
        vector_store = VectorStore(config.knowledge_base.db_path, embed_llm)
        ingester = Ingester(config, llm, vector_store)
        task_manager = TaskManager(ingester)
        local_search = LocalSearch(vector_store, embed_llm)
        online_search = OnlineSearchService.from_config(config.online_search)
        fusion = Fusion()
        query_rewriter = None
        if config.knowledge_base.enable_query_rewrite:
            from app.retrieval.query_rewriter import QueryRewriter

            query_rewriter = QueryRewriter(llm)
        retriever = Retriever(local_search, online_search, fusion, query_rewriter=query_rewriter)
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

        intent_parser = IntentParser(llm)
        template_mgr = TemplateManager(
            builtin_dir=Path(__file__).parent / "generation" / "templates",
            custom_dir=Path(config.generation.save_path) / "templates",
        )
        prompt_builder = PromptBuilder(max_tokens=config.generation.max_prompt_tokens)
        gen_writer = Writer(llm)
        docx_formatter = DocxFormatter(output_dir=Path(config.generation.save_path))
        writer_service = WriterService(
            intent_parser,
            prompt_builder,
            template_mgr,
            gen_writer,
            docx_formatter,
            retriever,
        )

        app.state.writer_service = writer_service
        app.state.template_mgr = template_mgr

        pptx_generator = PptxGenerator(llm=llm, output_dir=Path(config.generation.save_path))
        pptx_task_manager = PptxTaskManager()
        app.state.pptx_generator = pptx_generator
        app.state.pptx_task_manager = pptx_task_manager

        yield

    app = FastAPI(title="公文助手", version="0.1.0", lifespan=_lifespan)
    register_exception_handlers(app)

    from starlette.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.server.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(retrieval.router)
    app.include_router(files.router)
    app.include_router(settings.router)
    app.include_router(generation.router)
    app.include_router(templates.router)
    app.include_router(stats.router)
    app.include_router(ws.router)

    # Serve frontend static files (for bundled app deployment)
    frontend_dir = _find_frontend_dir()
    if frontend_dir is not None:
        from fastapi.responses import FileResponse, JSONResponse
        from fastapi.staticfiles import StaticFiles

        app.mount("/assets", StaticFiles(directory=frontend_dir / "assets"), name="static_assets")

        _API_PREFIXES = ("api/", "ws/", "health")

        @app.get("/")
        async def serve_index():
            return FileResponse(frontend_dir / "index.html")

        @app.get("/{filename:path}")
        async def spa_fallback(filename: str):
            if filename.startswith(_API_PREFIXES):
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            file_path = frontend_dir / filename
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(frontend_dir / "index.html")

    return app


app = create_app()

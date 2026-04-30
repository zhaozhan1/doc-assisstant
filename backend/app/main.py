from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI

from app.config import AppConfig, LoggingConfig

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


def create_app() -> FastAPI:
    config = AppConfig()
    setup_logging(config.logging)
    logger.info("应用启动")

    app = FastAPI(title="公文助手", version="0.1.0")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()

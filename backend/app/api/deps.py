from __future__ import annotations

from fastapi import Request

from app.config import AppConfig
from app.generation.template_manager import TemplateManager
from app.generation.writer_service import WriterService
from app.retrieval.file_service import FileService
from app.retrieval.retriever import Retriever
from app.settings_service import SettingsService
from app.task_manager import TaskManager


def get_config(request: Request) -> AppConfig:
    return request.app.state.config


def get_retriever(request: Request) -> Retriever:
    return request.app.state.retriever


def get_file_service(request: Request) -> FileService:
    return request.app.state.file_service


def get_settings_service(request: Request) -> SettingsService:
    return request.app.state.settings_service


def get_writer_service(request: Request) -> WriterService:
    return request.app.state.writer_service


def get_template_manager(request: Request) -> TemplateManager:
    return request.app.state.template_mgr


def get_task_manager(request: Request) -> TaskManager:
    return request.app.state.task_manager

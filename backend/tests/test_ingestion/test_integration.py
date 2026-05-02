"""端到端集成测试：文件导入 → 入库 → 检索"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.config import OCRConfig
from app.db.vector_store import VectorStore
from app.ingestion.ingester import Ingester
from app.llm.base import BaseLLMProvider
from app.task_manager import TaskManager


class MockLLMProvider(BaseLLMProvider):
    async def chat(self, messages: list[dict], **kwargs) -> str:
        return "通知"

    async def chat_stream(self, messages: list[dict], **kwargs):
        yield "通"
        yield "知"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 8 for _ in texts]


class MockConfig:
    class KnowledgeBase:
        chunk_size = 100
        chunk_overlap = 20
        smart_chunking = False

    knowledge_base = KnowledgeBase()
    ocr = OCRConfig()


@pytest.fixture
def integration_env(tmp_path: Path) -> tuple[Ingester, VectorStore, TaskManager]:
    llm = MockLLMProvider()
    vector_store = VectorStore(db_path=str(tmp_path / "db"), llm=llm)
    ingester = Ingester(config=MockConfig(), llm=llm, vector_store=vector_store)

    task_manager = TaskManager(ingester)
    task_manager.TASKS_DIR = str(tmp_path / "tasks")

    return ingester, vector_store, task_manager


class TestEndToEnd:
    @pytest.mark.asyncio
    async def test_full_import_and_search(self, integration_env: tuple, tmp_path: Path) -> None:
        ingester, vector_store, task_manager = integration_env

        txt = tmp_path / "通知.txt"
        txt.write_text(
            "关于召开年度工作总结会议的通知\n\n各部门：\n请于本周五前提交工作总结。",
            encoding="utf-8",
        )

        task_id = await task_manager.start_import([txt])
        await asyncio.sleep(1.0)

        progress = task_manager.get_progress(task_id)
        assert progress.status.value == "completed"
        assert progress.success == 1

        results = await vector_store.search("工作总结", top_k=5)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_batch_import_with_failure(self, integration_env: tuple, tmp_path: Path) -> None:
        ingester, vector_store, task_manager = integration_env

        good = tmp_path / "good.txt"
        good.write_text("正常文件内容", encoding="utf-8")

        bad = tmp_path / "bad.xyz"
        bad.write_text("不支持的格式")

        task_id = await task_manager.start_import([good, bad])
        await asyncio.sleep(1.0)

        progress = task_manager.get_progress(task_id)
        assert progress.status.value == "completed"
        assert progress.success == 1
        assert progress.skipped == 1

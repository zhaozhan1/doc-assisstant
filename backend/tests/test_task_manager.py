from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.models.task import FileResult, TaskStatus
from app.task_manager import TaskManager


@pytest.fixture
def mock_ingester() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def tmp_tasks_dir(tmp_path: Path) -> str:
    return str(tmp_path / "tasks")


@pytest.fixture
def task_manager(mock_ingester: AsyncMock, tmp_tasks_dir: str) -> TaskManager:
    with patch.object(TaskManager, "TASKS_DIR", tmp_tasks_dir):
        tm = TaskManager(mock_ingester)
        tm.TASKS_DIR = tmp_tasks_dir
        return tm


class TestStartImport:
    @pytest.mark.asyncio
    async def test_completes_successfully(
        self, task_manager: TaskManager, mock_ingester: AsyncMock, tmp_path: Path
    ) -> None:
        files = [tmp_path / "a.txt", tmp_path / "b.txt"]
        for f in files:
            f.write_text("test")

        mock_ingester.process_file.side_effect = [
            FileResult(path=str(files[0]), status="success", chunks_count=3),
            FileResult(path=str(files[1]), status="success", chunks_count=2),
        ]

        task_id = await task_manager.start_import(files)
        await asyncio.sleep(0.5)

        progress = task_manager.get_progress(task_id)
        assert progress.status == TaskStatus.COMPLETED
        assert progress.success == 2
        assert progress.total == 2

    @pytest.mark.asyncio
    async def test_failed_file_does_not_block_others(
        self, task_manager: TaskManager, mock_ingester: AsyncMock, tmp_path: Path
    ) -> None:
        files = [tmp_path / "a.txt", tmp_path / "b.txt"]
        for f in files:
            f.write_text("test")

        mock_ingester.process_file.side_effect = [
            FileResult(path=str(files[0]), status="failed", error="解析错误"),
            FileResult(path=str(files[1]), status="success", chunks_count=2),
        ]

        task_id = await task_manager.start_import(files)
        await asyncio.sleep(0.5)

        progress = task_manager.get_progress(task_id)
        assert progress.status == TaskStatus.COMPLETED
        assert progress.failed == 1
        assert progress.success == 1
        assert len(progress.failed_files) == 1
        assert "解析错误" in progress.failed_files[0].error


class TestCancelTask:
    @pytest.mark.asyncio
    async def test_cancel_stops_processing(
        self, task_manager: TaskManager, mock_ingester: AsyncMock, tmp_path: Path
    ) -> None:
        files = [tmp_path / f"{i}.txt" for i in range(10)]
        for f in files:
            f.write_text("test")

        async def slow_process(path):
            await asyncio.sleep(0.2)
            return FileResult(path=str(path), status="success")

        mock_ingester.process_file.side_effect = slow_process

        task_id = await task_manager.start_import(files)
        await asyncio.sleep(0.3)
        await task_manager.cancel_task(task_id)
        await asyncio.sleep(0.5)

        progress = task_manager.get_progress(task_id)
        assert progress.status == TaskStatus.CANCELLED
        assert progress.processed < 10


class TestGetUnfinishedTasks:
    @pytest.mark.asyncio
    async def test_completed_not_in_unfinished(
        self, task_manager: TaskManager, mock_ingester: AsyncMock, tmp_path: Path
    ) -> None:
        files = [tmp_path / "a.txt"]
        files[0].write_text("test")

        mock_ingester.process_file.return_value = FileResult(path=str(files[0]), status="success")

        task_id = await task_manager.start_import(files)
        await asyncio.sleep(0.5)

        unfinished = task_manager.get_unfinished_tasks()
        assert task_id not in [t.task_id for t in unfinished]


class TestPersistence:
    @pytest.mark.asyncio
    async def test_saves_and_loads_tasks(self, mock_ingester: AsyncMock, tmp_tasks_dir: str, tmp_path: Path) -> None:
        files = [tmp_path / "a.txt"]
        files[0].write_text("test")

        mock_ingester.process_file.return_value = FileResult(path=str(files[0]), status="success")

        with patch.object(TaskManager, "TASKS_DIR", tmp_tasks_dir):
            tm1 = TaskManager(mock_ingester)
            tm1.TASKS_DIR = tmp_tasks_dir
            task_id = await tm1.start_import(files)
            await asyncio.sleep(0.5)

        with patch.object(TaskManager, "TASKS_DIR", tmp_tasks_dir):
            tm2 = TaskManager(mock_ingester)
            tm2.TASKS_DIR = tmp_tasks_dir

        progress = tm2.get_progress(task_id)
        assert progress.status == TaskStatus.COMPLETED
        assert progress.success == 1


class TestSecurity:
    @pytest.mark.asyncio
    async def test_invalid_resume_task_id_rejected(self, task_manager: TaskManager, tmp_path: Path) -> None:
        files = [tmp_path / "a.txt"]
        files[0].write_text("test")
        with pytest.raises(ValueError, match="非法任务 ID"):
            await task_manager.start_import(files, resume_task_id="../../etc/passwd")

    @pytest.mark.asyncio
    async def test_nonexistent_resume_task_id_raises(self, task_manager: TaskManager, tmp_path: Path) -> None:
        files = [tmp_path / "a.txt"]
        files[0].write_text("test")
        with pytest.raises(KeyError, match="任务不存在"):
            await task_manager.start_import(files, resume_task_id="00000000-0000-0000-0000-000000000000")

    def test_malformed_json_skipped(self, mock_ingester: AsyncMock, tmp_tasks_dir: str) -> None:
        tasks_dir = Path(tmp_tasks_dir)
        tasks_dir.mkdir(parents=True, exist_ok=True)
        bad_file = tasks_dir / "bad.json"
        bad_file.write_text("not valid json{{{")

        with patch.object(TaskManager, "TASKS_DIR", tmp_tasks_dir):
            tm = TaskManager(mock_ingester)
            tm.TASKS_DIR = tmp_tasks_dir
        assert len(tm._tasks) == 0

    def test_missing_fields_json_skipped(self, mock_ingester: AsyncMock, tmp_tasks_dir: str) -> None:
        tasks_dir = Path(tmp_tasks_dir)
        tasks_dir.mkdir(parents=True, exist_ok=True)
        bad_file = tasks_dir / "missing.json"
        bad_file.write_text('{"task_id": "abc"}')

        with patch.object(TaskManager, "TASKS_DIR", tmp_tasks_dir):
            tm = TaskManager(mock_ingester)
            tm.TASKS_DIR = tmp_tasks_dir
        assert len(tm._tasks) == 0

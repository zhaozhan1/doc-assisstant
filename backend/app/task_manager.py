from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.models.task import FileResult, TaskProgress, TaskStatus

logger = logging.getLogger(__name__)


class TaskManager:
    TASKS_DIR = "./data/tasks"

    def __init__(self, ingester: object) -> None:
        self._ingester = ingester
        self._tasks: dict[str, TaskProgress] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._load_tasks()

    def get_unfinished_tasks(self) -> list[TaskProgress]:
        return [
            t for t in self._tasks.values()
            if t.status in (TaskStatus.RUNNING, TaskStatus.PENDING)
        ]

    async def start_import(
        self, paths: list[Path], resume_task_id: str | None = None
    ) -> str:
        if resume_task_id:
            task = self._tasks[resume_task_id]
            task.status = TaskStatus.RUNNING
            remaining = [Path(p) for p in task.pending_files]
        else:
            task = TaskProgress(
                task_id=str(uuid4()),
                status=TaskStatus.PENDING,
                total=len(paths),
                pending_files=[str(p) for p in paths],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            )
            remaining = paths

        self._cancel_events[task.task_id] = asyncio.Event()
        self._tasks[task.task_id] = task
        self._save_task(task)
        asyncio.create_task(self._run(task, remaining))
        return task.task_id

    async def _run(self, task: TaskProgress, paths: list[Path]) -> None:
        task.status = TaskStatus.RUNNING
        self._save_task(task)

        for path in paths:
            if self._cancel_events[task.task_id].is_set():
                task.status = TaskStatus.CANCELLED
                self._save_task(task)
                return

            result = await self._ingester.process_file(path)
            task.processed += 1

            if result.status == "success":
                task.success += 1
            elif result.status == "failed":
                task.failed += 1
                task.failed_files.append(result)
            else:
                task.skipped += 1

            task.pending_files = [str(p) for p in paths[task.processed:]]
            task.updated_at = datetime.now().isoformat()
            self._save_task(task)

        task.status = TaskStatus.COMPLETED
        task.updated_at = datetime.now().isoformat()
        self._save_task(task)

    async def cancel_task(self, task_id: str) -> None:
        if task_id in self._cancel_events:
            self._cancel_events[task_id].set()

    def get_progress(self, task_id: str) -> TaskProgress:
        return self._tasks[task_id]

    def _save_task(self, task: TaskProgress) -> None:
        path = Path(self.TASKS_DIR) / f"{task.task_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(task)
        data["status"] = task.status.value
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))

    def _load_tasks(self) -> None:
        tasks_dir = Path(self.TASKS_DIR)
        if not tasks_dir.exists():
            return
        for f in tasks_dir.glob("*.json"):
            try:
                task = self._parse_task(f.read_text(encoding="utf-8"))
                if task.status == TaskStatus.RUNNING:
                    task.status = TaskStatus.PENDING
                self._tasks[task.task_id] = task
            except Exception as e:
                logger.warning("加载任务文件失败 %s: %s", f, e)

    def _parse_task(self, json_str: str) -> TaskProgress:
        data = json.loads(json_str)
        data["status"] = TaskStatus(data["status"])
        data["failed_files"] = [
            FileResult(**fr) for fr in data.get("failed_files", [])
        ]
        return TaskProgress(**data)

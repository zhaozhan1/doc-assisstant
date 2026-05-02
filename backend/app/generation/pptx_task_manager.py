"""PptxTaskManager — async PPT generation task tracking."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from uuid import uuid4


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PptxTaskProgress:
    task_id: str
    status: TaskStatus
    source_file: str
    created_at: float = field(default_factory=time.time)
    current_step: str = "pending"
    step_index: int = 0
    total_steps: int = 4
    output_path: str | None = None
    slide_count: int = 0
    slides_data: list[dict] = field(default_factory=list)
    source_doc: str = ""
    duration_ms: int = 0
    error: str | None = None


class PptxTaskManager:
    """In-memory tracker for async PPT generation tasks."""

    MAX_CONCURRENT = 2
    MAX_TASK_AGE_SECONDS = 3600  # 1 hour

    def __init__(self) -> None:
        self._tasks: dict[str, PptxTaskProgress] = {}

    @property
    def running_count(self) -> int:
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING)

    def can_start(self) -> bool:
        """Check if a new task can be started."""
        self._cleanup_expired()
        return self.running_count < self.MAX_CONCURRENT

    def create_task(self, source_file: Path) -> str:
        """Create a new task, return task_id (uuid4)."""
        task_id = str(uuid4())
        self._tasks[task_id] = PptxTaskProgress(
            task_id=task_id,
            status=TaskStatus.PENDING,
            source_file=str(source_file),
        )
        return task_id

    def update_step(self, task_id: str, step_name: str, step_index: int) -> None:
        """Update current step, set status to RUNNING."""
        task = self._tasks[task_id]
        task.current_step = step_name
        task.step_index = step_index
        task.status = TaskStatus.RUNNING

    def complete_task(
        self,
        task_id: str,
        output_path: str,
        slide_count: int,
        slides_data: list[dict] | None = None,
        source_doc: str = "",
        duration_ms: int = 0,
    ) -> None:
        """Mark task completed with results."""
        task = self._tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.output_path = output_path
        task.slide_count = slide_count
        task.slides_data = slides_data if slides_data is not None else []
        task.source_doc = source_doc
        task.duration_ms = duration_ms

    def fail_task(self, task_id: str, error: str) -> None:
        """Mark task failed with error message."""
        task = self._tasks[task_id]
        task.status = TaskStatus.FAILED
        task.error = error

    def get_progress(self, task_id: str) -> PptxTaskProgress:
        """Get task progress. Raise KeyError if not found."""
        return self._tasks[task_id]

    def _cleanup_expired(self) -> None:
        """Remove tasks older than MAX_TASK_AGE_SECONDS."""
        now = time.time()
        expired = [tid for tid, t in self._tasks.items() if now - t.created_at > self.MAX_TASK_AGE_SECONDS]
        for tid in expired:
            del self._tasks[tid]

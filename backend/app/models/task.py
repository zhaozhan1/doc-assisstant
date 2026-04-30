from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class FileResult:
    path: str
    status: Literal["success", "failed", "skipped"]
    error: str | None = None
    chunks_count: int = 0


@dataclass
class TaskProgress:
    task_id: str
    status: TaskStatus
    total: int = 0
    processed: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    failed_files: list[FileResult] = field(default_factory=list)
    pending_files: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

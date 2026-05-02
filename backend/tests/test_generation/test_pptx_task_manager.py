"""Tests for PptxTaskManager — async PPT generation task tracking."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.generation.pptx_task_manager import (
    PptxTaskManager,
    PptxTaskProgress,
    TaskStatus,
)


class TestCreateTask:
    """Test 1: create_task returns a task_id and get_progress returns
    PptxTaskProgress with status PENDING."""

    def test_returns_uuid_string(self) -> None:
        mgr = PptxTaskManager()
        task_id = mgr.create_task(Path("/tmp/test.docx"))
        assert isinstance(task_id, str)
        assert len(task_id) == 36  # uuid4 format: 8-4-4-4-12

    def test_get_progress_returns_pending(self) -> None:
        mgr = PptxTaskManager()
        task_id = mgr.create_task(Path("/tmp/test.docx"))
        progress = mgr.get_progress(task_id)
        assert isinstance(progress, PptxTaskProgress)
        assert progress.status is TaskStatus.PENDING
        assert progress.task_id == task_id
        assert progress.source_file == "/tmp/test.docx"
        assert progress.current_step == "pending"
        assert progress.step_index == 0
        assert progress.total_steps == 4


class TestUpdateStep:
    """Test 2: update_step changes step_name and step_index, sets status RUNNING."""

    def test_updates_step_and_status(self) -> None:
        mgr = PptxTaskManager()
        task_id = mgr.create_task(Path("/tmp/test.docx"))

        mgr.update_step(task_id, "parsing", 1)

        progress = mgr.get_progress(task_id)
        assert progress.status is TaskStatus.RUNNING
        assert progress.current_step == "parsing"
        assert progress.step_index == 1

    def test_multiple_updates(self) -> None:
        mgr = PptxTaskManager()
        task_id = mgr.create_task(Path("/tmp/test.docx"))

        mgr.update_step(task_id, "parsing", 1)
        mgr.update_step(task_id, "analysis", 2)
        mgr.update_step(task_id, "summarizing", 3)

        progress = mgr.get_progress(task_id)
        assert progress.current_step == "summarizing"
        assert progress.step_index == 3
        assert progress.status is TaskStatus.RUNNING


class TestCompleteTask:
    """Test 3: complete_task sets status COMPLETED with output_path and slide_count."""

    def test_completes_with_results(self) -> None:
        mgr = PptxTaskManager()
        task_id = mgr.create_task(Path("/tmp/test.docx"))

        slides_data = [{"title": "Slide 1"}, {"title": "Slide 2"}]
        mgr.complete_task(
            task_id,
            output_path="/tmp/output.pptx",
            slide_count=2,
            slides_data=slides_data,
            source_doc="测试文档",
            duration_ms=1500,
        )

        progress = mgr.get_progress(task_id)
        assert progress.status is TaskStatus.COMPLETED
        assert progress.output_path == "/tmp/output.pptx"
        assert progress.slide_count == 2
        assert progress.slides_data == slides_data
        assert progress.source_doc == "测试文档"
        assert progress.duration_ms == 1500

    def test_completes_with_defaults(self) -> None:
        mgr = PptxTaskManager()
        task_id = mgr.create_task(Path("/tmp/test.docx"))

        mgr.complete_task(
            task_id,
            output_path="/tmp/output.pptx",
            slide_count=5,
        )

        progress = mgr.get_progress(task_id)
        assert progress.status is TaskStatus.COMPLETED
        assert progress.slides_data == []
        assert progress.source_doc == ""
        assert progress.duration_ms == 0


class TestFailTask:
    """Test 4: fail_task sets status FAILED with error."""

    def test_fails_with_error(self) -> None:
        mgr = PptxTaskManager()
        task_id = mgr.create_task(Path("/tmp/test.docx"))

        mgr.fail_task(task_id, "模板文件损坏")

        progress = mgr.get_progress(task_id)
        assert progress.status is TaskStatus.FAILED
        assert progress.error == "模板文件损坏"


class TestGetProgressNotFound:
    """Test 5: get_progress raises KeyError for non-existent task_id."""

    def test_raises_key_error(self) -> None:
        mgr = PptxTaskManager()
        with pytest.raises(KeyError):
            mgr.get_progress("non-existent-id")

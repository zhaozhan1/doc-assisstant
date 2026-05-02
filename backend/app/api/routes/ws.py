from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.task_manager import TaskManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

_ALLOWED_ORIGINS = frozenset(
    {
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    }
)


def _validate_origin(websocket: WebSocket) -> bool:
    origin = websocket.headers.get("origin", "")
    return origin in _ALLOWED_ORIGINS or not origin


@router.websocket("/ws/tasks/{task_id}")
async def task_progress_ws(websocket: WebSocket, task_id: str) -> None:
    if not _validate_origin(websocket):
        await websocket.close(code=4001, reason="Invalid origin")
        return
    await websocket.accept()
    task_manager: TaskManager = websocket.app.state.task_manager

    try:
        task_manager.get_progress(task_id)
    except KeyError:
        await websocket.send_json({"type": "error", "data": {"message": f"任务不存在: {task_id}"}})
        await websocket.close()
        return

    async def send_progress():
        last_processed = -1
        while True:
            try:
                progress = task_manager.get_progress(task_id)
            except KeyError:
                return
            if progress.processed != last_processed or progress.status.value in ("completed", "cancelled", "failed"):
                last_processed = progress.processed
                msg_data = asdict(progress)
                msg_data["status"] = progress.status.value
                msg_type = "completed" if progress.status.value == "completed" else "progress"
                await websocket.send_json({"type": msg_type, "data": msg_data})
                if progress.status.value in ("completed", "cancelled", "failed"):
                    return
            await asyncio.sleep(0.3)

    async def receive_commands():
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "cancel":
                await task_manager.cancel_task(task_id)

    send_task = asyncio.create_task(send_progress())
    recv_task = asyncio.create_task(receive_commands())

    try:
        done, pending = await asyncio.wait([send_task, recv_task], return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
    except WebSocketDisconnect:
        send_task.cancel()
        recv_task.cancel()


@router.websocket("/ws/pptx-tasks/{task_id}")
async def pptx_task_ws(websocket: WebSocket, task_id: str) -> None:
    if not _validate_origin(websocket):
        await websocket.close(code=4001, reason="Invalid origin")
        return
    await websocket.accept()
    pptx_task_manager = websocket.app.state.pptx_task_manager

    try:
        pptx_task_manager.get_progress(task_id)
    except KeyError:
        await websocket.send_json({"type": "error", "data": {"message": f"任务不存在: {task_id}"}})
        await websocket.close()
        return

    try:
        last_step = -1
        while True:
            progress = pptx_task_manager.get_progress(task_id)
            if progress.step_index != last_step or progress.status.value in ("completed", "failed"):
                last_step = progress.step_index
                data = {
                    "task_id": progress.task_id,
                    "status": progress.status.value,
                    "current_step": progress.current_step,
                    "step_index": progress.step_index,
                    "total_steps": progress.total_steps,
                    "slide_count": progress.slide_count,
                    "slides": progress.slides_data,
                    "source_doc": progress.source_doc,
                    "duration_ms": progress.duration_ms,
                    "error": progress.error,
                }
                # Convert server output_path to download URL for client
                if progress.output_path:
                    filename = (
                        progress.output_path.rsplit("/", 1)[-1] if "/" in progress.output_path else progress.output_path
                    )
                    data["output_path"] = filename
                    data["download_url"] = f"/api/files/download/{progress.output_path}"
                else:
                    data["output_path"] = None
                    data["download_url"] = None
                await websocket.send_json({"type": progress.status.value, "data": data})
                if progress.status.value in ("completed", "failed"):
                    return
            await asyncio.sleep(0.3)
    except WebSocketDisconnect:
        pass

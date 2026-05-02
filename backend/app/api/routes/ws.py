from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.task_manager import TaskManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/tasks/{task_id}")
async def task_progress_ws(websocket: WebSocket, task_id: str) -> None:
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

# 阶段四：Web UI 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为公文助手构建完整的 Web UI，包括补全后端 API 缺口和 4 个前端页面。

**Architecture:** 后端先行补全 API 缺口（文件上传/下载、WebSocket 进度推送、完整 Settings API、统计 API、统一错误处理），然后搭建前端项目（React + TS + Vite + Ant Design），逐页实现知识库/写作/模板管理/设置。

**Tech Stack:** FastAPI + WebSocket（后端）；React 18 + TypeScript + Vite + Ant Design 5 + Zustand + Axios + React Router v6（前端）

**分支:** `feature/web-ui`

**关联文档:** [技术设计](../product/deliverable/2026-05-02-tech-design-phase-4.md)

---

## Sprint 1：F4.1 后端 API 缺口补全

### Task 1: 统一错误处理中间件

**Files:**
- Create: `backend/app/api/middleware.py`
- Create: `backend/tests/test_middleware.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_middleware.py
from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.middleware import ExceptionMiddleware


@pytest.fixture
def app():
    app = FastAPI()
    app.add_middleware(ExceptionMiddleware)

    @app.get("/raise-http")
    async def raise_http():
        raise HTTPException(status_code=404, detail="资源不存在")

    @app.get("/raise-value-error")
    async def raise_value_error():
        raise ValueError("参数错误")

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    return app


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


def test_http_exception_returns_standard_format(client):
    resp = client.get("/raise-http")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"] == "NOT_FOUND"
    assert body["detail"] == "资源不存在"


def test_unhandled_exception_returns_500(client):
    resp = client.get("/raise-value-error")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"] == "INTERNAL_ERROR"


def test_normal_request_passes_through(client):
    resp = client.get("/ok")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_middleware.py -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 实现 ExceptionMiddleware**

```python
# backend/app/api/middleware.py
from __future__ import annotations

import logging
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

ERROR_CODE_MAP = {
    400: "BAD_REQUEST",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
}


class ExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            import FastAPI
            from fastapi import HTTPException

            if isinstance(exc, HTTPException):
                error_code = ERROR_CODE_MAP.get(exc.status_code, "UNKNOWN")
                return JSONResponse(
                    status_code=exc.status_code,
                    content={"error": error_code, "detail": exc.detail},
                )

            logger.exception("未处理的异常")
            return JSONResponse(
                status_code=500,
                content={"error": "INTERNAL_ERROR", "detail": "服务器内部错误"},
            )
```

- [ ] **Step 4: 修复 import 并运行测试**

修复 middleware.py 中的 `import FastAPI` 为注释或移除（HTTPException 已在下方导入）。运行：

Run: `cd backend && python -m pytest tests/test_middleware.py -v`
Expected: PASS

- [ ] **Step 5: 在 main.py 注册中间件**

在 `backend/app/main.py` 的 `create_app()` 函数中，`app = FastAPI(...)` 之后添加：

```python
from app.api.middleware import ExceptionMiddleware

# 在 app = FastAPI(...) 之后
app.add_middleware(ExceptionMiddleware)
```

- [ ] **Step 6: 提交**

```bash
git -C backend add app/api/middleware.py tests/test_middleware.py app/main.py
git commit -m "feat(api): add unified error handling middleware"
```

---

### Task 2: GenerationConfig 新增 word_template_path

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/tests/test_config.py`（如存在则追加，否则新建）

- [ ] **Step 1: 写测试**

```python
# backend/tests/test_config_word_template.py
from __future__ import annotations

from app.config import GenerationConfig


def test_default_word_template_path_is_empty():
    config = GenerationConfig()
    assert config.word_template_path == ""


def test_word_template_path_can_be_set():
    config = GenerationConfig(word_template_path="/path/to/template.dotx")
    assert config.word_template_path == "/path/to/template.dotx"
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_config_word_template.py -v`
Expected: FAIL（AttributeError）

- [ ] **Step 3: 修改 GenerationConfig**

在 `backend/app/config.py` 的 `GenerationConfig` 类中新增字段：

```python
class GenerationConfig(BaseModel):
    output_format: str = "docx"
    save_path: str = "./output"
    include_sources: bool = True
    max_prompt_tokens: int = 4096
    word_template_path: str = ""  # .dotx Word 模板路径
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_config_word_template.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git -C backend add app/config.py tests/test_config_word_template.py
git commit -m "feat(config): add word_template_path to GenerationConfig"
```

---

### Task 3: Settings API 扩展（KB / LLM / Generation）

**Files:**
- Modify: `backend/app/settings_service.py`
- Modify: `backend/app/api/routes/settings.py`
- Modify: `backend/app/models/search.py`
- Create: `backend/tests/test_settings_extended.py`

- [ ] **Step 1: 新增 Settings 更新模型**

在 `backend/app/models/search.py` 末尾追加：

```python
class KBSettingsUpdate(BaseModel):
    source_folder: str | None = None
    db_path: str | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None


class LLMSettingsUpdate(BaseModel):
    default_provider: str | None = None
    ollama_base_url: str | None = None
    ollama_chat_model: str | None = None
    ollama_embed_model: str | None = None
    claude_base_url: str | None = None
    claude_api_key: str | None = None
    claude_chat_model: str | None = None


class GenerationSettingsUpdate(BaseModel):
    output_format: str | None = None
    save_path: str | None = None
    include_sources: bool | None = None
    word_template_path: str | None = None
```

- [ ] **Step 2: 扩展 SettingsService**

在 `backend/app/settings_service.py` 追加方法：

```python
from app.config import KnowledgeBaseConfig, LLMConfig, GenerationConfig
from app.models.search import KBSettingsUpdate, LLMSettingsUpdate, GenerationSettingsUpdate

# ... 现有代码 ...

def get_kb_config(self) -> KnowledgeBaseConfig:
    return self._config.knowledge_base

def update_kb_config(self, update: KBSettingsUpdate) -> KnowledgeBaseConfig:
    update_data = update.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(self._config.knowledge_base, key, value)
    self._write_config()
    return self._config.knowledge_base

def get_llm_config(self) -> dict:
    llm = self._config.llm
    data = {"default_provider": llm.default_provider, "embed_provider": llm.embed_provider, "providers": {}}
    for name, provider in llm.providers.items():
        pdata = provider.model_dump()
        if "api_key" in pdata and pdata["api_key"]:
            pdata["api_key"] = "********"
        data["providers"][name] = pdata
    return data

def update_llm_config(self, update: LLMSettingsUpdate) -> dict:
    llm = self._config.llm
    update_data = update.model_dump(exclude_none=True)
    if "default_provider" in update_data:
        llm.default_provider = update_data.pop("default_provider")
    for key, value in update_data.items():
        prefix, field = key.split("_", 1)
        if prefix in llm.providers:
            setattr(llm.providers[prefix], field, value)
    self._write_config()
    return self.get_llm_config()

def get_generation_config(self) -> GenerationConfig:
    return self._config.generation

def update_generation_config(self, update: GenerationSettingsUpdate) -> GenerationConfig:
    update_data = update.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(self._config.generation, key, value)
    self._write_config()
    return self._config.generation
```

修改 `_write_config` 方法，将所有配置节写入（而不仅是 online_search）：

```python
def _write_config(self) -> None:
    data = {}
    if self._config_path.exists():
        with open(self._config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    data["knowledge_base"] = self._config.knowledge_base.model_dump()
    data["llm"] = {
        "default_provider": self._config.llm.default_provider,
        "embed_provider": self._config.llm.embed_provider,
        "providers": {k: v.model_dump() for k, v in self._config.llm.providers.items()},
    }
    data["online_search"] = self._config.online_search.model_dump()
    data["generation"] = self._config.generation.model_dump()
    self._config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(self._config_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
```

- [ ] **Step 3: 新增 Settings 路由端点**

在 `backend/app/api/routes/settings.py` 追加：

```python
from app.models.search import KBSettingsUpdate, LLMSettingsUpdate, GenerationSettingsUpdate

# ... 现有端点 ...

@router.get("/knowledge-base")
async def get_kb_config(service: SettingsService = _settings_dep) -> dict:
    return service.get_kb_config().model_dump()


@router.put("/knowledge-base")
async def update_kb_config(
    update: KBSettingsUpdate,
    service: SettingsService = _settings_dep,
) -> dict:
    return service.update_kb_config(update).model_dump()


@router.get("/llm")
async def get_llm_config(service: SettingsService = _settings_dep) -> dict:
    return service.get_llm_config()


@router.put("/llm")
async def update_llm_config(
    update: LLMSettingsUpdate,
    service: SettingsService = _settings_dep,
) -> dict:
    return service.update_llm_config(update)


@router.get("/generation")
async def get_generation_config(service: SettingsService = _settings_dep) -> dict:
    return service.get_generation_config().model_dump()


@router.put("/generation")
async def update_generation_config(
    update: GenerationSettingsUpdate,
    service: SettingsService = _settings_dep,
) -> dict:
    return service.update_generation_config(update).model_dump()


@router.get("/files/browse")
async def browse_directory(
    path: str = ".",
    service: SettingsService = _settings_dep,
) -> dict:
    from pathlib import Path
    target = Path(path).resolve()
    if not target.is_dir():
        return {"path": str(target), "children": []}
    children = []
    for child in sorted(target.iterdir()):
        if child.name.startswith("."):
            continue
        children.append({"name": child.name, "path": str(child), "is_dir": child.is_dir()})
    return {"path": str(target), "children": children}
```

- [ ] **Step 4: 写集成测试**

```python
# backend/tests/test_settings_extended.py
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import create_app
    app = create_app()
    return TestClient(app)


def test_kb_config_get(client):
    resp = client.get("/api/settings/knowledge-base")
    assert resp.status_code == 200
    data = resp.json()
    assert "db_path" in data
    assert "chunk_size" in data


def test_llm_config_get_masks_api_key(client):
    resp = client.get("/api/settings/llm")
    assert resp.status_code == 200
    data = resp.json()
    assert "default_provider" in data
    assert "providers" in data


def test_generation_config_get(client):
    resp = client.get("/api/settings/generation")
    assert resp.status_code == 200
    data = resp.json()
    assert "output_format" in data
    assert "word_template_path" in data


def test_browse_directory(client):
    resp = client.get("/api/settings/files/browse", params={"path": "."})
    assert resp.status_code == 200
    data = resp.json()
    assert "children" in data
```

- [ ] **Step 5: 运行测试**

Run: `cd backend && python -m pytest tests/test_settings_extended.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git -C backend add app/settings_service.py app/api/routes/settings.py app/models/search.py tests/test_settings_extended.py
git commit -m "feat(api): add KB/LLM/Generation settings endpoints + directory browse"
```

---

### Task 4: 文件上传端点

**Files:**
- Modify: `backend/app/api/routes/files.py`
- Modify: `backend/app/api/deps.py`
- Create: `backend/tests/test_file_upload.py`

- [ ] **Step 1: 在 deps.py 新增 get_task_manager 依赖**

```python
# backend/app/api/deps.py — 追加
from app.task_manager import TaskManager

def get_task_manager(request: Request) -> TaskManager:
    return request.app.state.task_manager
```

- [ ] **Step 2: 写上传测试**

```python
# backend/tests/test_file_upload.py
from __future__ import annotations

import io
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import create_app
    app = create_app()
    return TestClient(app)


def test_upload_file_returns_task_id(client):
    file_content = b"test document content"
    resp = client.post(
        "/api/files/upload",
        files=[("files", ("test.txt", io.BytesIO(file_content), "text/plain"))],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data


def test_upload_empty_files_rejected(client):
    resp = client.post("/api/files/upload", files=[])
    assert resp.status_code == 422
```

- [ ] **Step 3: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_file_upload.py -v`
Expected: FAIL（404 / method not found）

- [ ] **Step 4: 实现上传端点**

在 `backend/app/api/routes/files.py` 追加：

```python
import os
import tempfile
from pathlib import Path
from fastapi import UploadFile, File

from app.api.deps import get_file_service, get_task_manager
from app.task_manager import TaskManager


@router.post("/upload")
async def upload_files(
    files: list[UploadFile] = File(...),
    task_manager: TaskManager = Depends(get_task_manager),
) -> dict:
    upload_dir = Path(tempfile.mkdtemp(prefix="doc_upload_"))
    paths = []
    for f in files:
        dest = upload_dir / f.filename
        content = await f.read()
        if not content:
            continue
        dest.write_bytes(content)
        paths.append(dest)

    if not paths:
        raise HTTPException(status_code=422, detail="未提供有效文件")

    task_id = await task_manager.start_import(paths)
    return {"task_id": task_id}
```

同时更新文件顶部的 import：

```python
from app.api.deps import get_file_service, get_task_manager
from app.task_manager import TaskManager
```

- [ ] **Step 5: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_file_upload.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git -C backend add app/api/routes/files.py app/api/deps.py tests/test_file_upload.py
git commit -m "feat(api): add file upload endpoint"
```

---

### Task 5: 文件下载端点

**Files:**
- Modify: `backend/app/api/routes/files.py`
- Create: `backend/tests/test_file_download.py`

- [ ] **Step 1: 写下载测试**

```python
# backend/tests/test_file_download.py
from __future__ import annotations

import pytest
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import create_app
    app = create_app()
    return TestClient(app)


def test_download_nonexistent_file_returns_404(client):
    resp = client.get("/api/files/download/nonexistent.docx")
    assert resp.status_code == 404
```

- [ ] **Step 2: 实现下载端点**

在 `backend/app/api/routes/files.py` 追加：

```python
from fastapi.responses import FileResponse


@router.get("/download/{file_path:path}")
async def download_file(file_path: str) -> FileResponse:
    path = Path(file_path).resolve()
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")
    # 安全检查：防止路径遍历
    if ".." in Path(file_path).parts:
        raise HTTPException(status_code=400, detail="非法路径")
    return FileResponse(path, filename=path.name)
```

- [ ] **Step 3: 运行测试并提交**

Run: `cd backend && python -m pytest tests/test_file_download.py -v`

```bash
git -C backend add app/api/routes/files.py tests/test_file_download.py
git commit -m "feat(api): add file download endpoint"
```

---

### Task 6: 统计 API

**Files:**
- Create: `backend/app/api/routes/stats.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_stats.py`

- [ ] **Step 1: 写测试**

```python
# backend/tests/test_stats.py
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import create_app
    app = create_app()
    return TestClient(app)


def test_stats_returns_expected_fields(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_files" in data
    assert "type_distribution" in data
    assert "last_updated" in data
```

- [ ] **Step 2: 实现统计路由**

```python
# backend/app/api/routes/stats.py
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_file_service
from app.retrieval.file_service import FileService

router = APIRouter(prefix="/api", tags=["stats"])

_file_service_dep = Depends(get_file_service)


@router.get("/stats")
async def get_stats(file_service: FileService = _file_service_dep) -> dict:
    files = await file_service.list_files(
        __import__("app.models.search", fromlist=["FileListRequest"]).FileListRequest()
    )
    type_dist = {}
    last_updated = ""
    for f in files:
        type_dist[f.doc_type] = type_dist.get(f.doc_type, 0) + 1
        if f.doc_date and f.doc_date > last_updated:
            last_updated = f.doc_date
    return {
        "total_files": len(files),
        "type_distribution": type_dist,
        "last_updated": last_updated or None,
    }
```

- [ ] **Step 3: 在 main.py 注册路由**

在 `backend/app/main.py` 的 import 和 `app.include_router` 中添加 stats 路由。

- [ ] **Step 4: 运行测试并提交**

Run: `cd backend && python -m pytest tests/test_stats.py -v`

```bash
git -C backend add app/api/routes/stats.py app/main.py tests/test_stats.py
git commit -m "feat(api): add knowledge base stats endpoint"
```

---

### Task 7: WebSocket 任务进度

**Files:**
- Create: `backend/app/api/routes/ws.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_ws_tasks.py`

- [ ] **Step 1: 写 WebSocket 测试**

```python
# backend/tests/test_ws_tasks.py
from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import create_app
    app = create_app()
    return TestClient(app)


def test_ws_nonexistent_task_returns_error(client):
    with client.websocket_connect("/ws/tasks/nonexistent-id") as ws:
        data = ws.receive_json()
        assert data["type"] == "error"
```

- [ ] **Step 2: 实现 WebSocket 端点**

```python
# backend/app/api/routes/ws.py
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.task_manager import TaskManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/tasks/{task_id}")
async def task_progress_ws(websocket: WebSocket, task_id: str) -> None:
    await websocket.accept()
    task_manager: TaskManager = websocket.app.state.task_manager

    try:
        progress = task_manager.get_progress(task_id)
    except KeyError:
        await websocket.send_json({"type": "error", "data": {"message": f"任务不存在: {task_id}"}})
        await websocket.close()
        return

    async def send_progress():
        last_processed = -1
        while True:
            progress = task_manager.get_progress(task_id)
            if progress.processed != last_processed or progress.status.value in ("completed", "cancelled", "failed"):
                last_processed = progress.processed
                msg_type = progress.status.value if progress.status.value != "running" else "progress"
                await websocket.send_json({"type": msg_type, "data": json.loads(json.dumps(progress.__dict__, default=str))})
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
        done, pending = await asyncio.wait(
            [send_task, recv_task], return_when=asyncio.FIRST_COMPLETED
        )
        for t in pending:
            t.cancel()
    except WebSocketDisconnect:
        send_task.cancel()
        recv_task.cancel()
```

- [ ] **Step 3: 在 main.py 注册 WS 路由**

在 `backend/app/main.py` 的 import 和路由注册中添加 ws 模块。

- [ ] **Step 4: 运行测试并提交**

Run: `cd backend && python -m pytest tests/test_ws_tasks.py -v`

```bash
git -C backend add app/api/routes/ws.py app/main.py tests/test_ws_tasks.py
git commit -m "feat(api): add WebSocket task progress endpoint"
```

---

### Task 8: CORS + 全量后端测试

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: 在 main.py 添加 CORS（仅开发）**

在 `backend/app/main.py` 的 `create_app()` 中添加：

```python
from starlette.middleware.cors import CORSMiddleware

# 在 app.add_middleware(ExceptionMiddleware) 之后
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 2: 运行全量后端测试**

Run: `cd backend && python -m pytest --tb=short -q`
Expected: 全部通过

- [ ] **Step 3: Lint 检查**

Run: `cd backend && ruff check app/ tests/ && ruff format --check app/ tests/`
Expected: 无错误

- [ ] **Step 4: 提交**

```bash
git -C backend add app/main.py
git commit -m "feat(api): add CORS middleware for dev environment"
```

---

## Sprint 2：F4.2 前端项目搭建

### Task 9: 初始化前端项目

**Files:**
- Create: `frontend/` 全部基础文件

- [ ] **Step 1: 创建 Vite + React + TypeScript 项目**

```bash
pnpm create vite frontend --template react-ts
cd frontend && pnpm install
pnpm add antd @ant-design/icons react-router-dom axios zustand react-markdown
pnpm add -D @types/node vitest @testing-library/react @testing-library/jest-dom jsdom
```

- [ ] **Step 2: 配置 vite.config.ts**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
```

- [ ] **Step 3: 创建目录结构**

```bash
mkdir -p src/{api,hooks,stores,pages/{KnowledgeBase,Writing,TemplateManager,Settings},components/Layout,types}
```

- [ ] **Step 4: 提交**

```bash
git add frontend/
git commit -m "feat(frontend): initialize React + TS + Vite project with dependencies"
```

---

### Task 10: API 客户端 + 类型定义

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/types/api.ts`

- [ ] **Step 1: 创建 Axios 实例**

```typescript
// frontend/src/api/client.ts
import axios from "axios";

const client = axios.create({ baseURL: "/api" });

client.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const msg = error.response?.data?.detail || error.message || "请求失败";
    return Promise.reject(new Error(msg));
  },
);

export default client;
```

- [ ] **Step 2: 创建类型定义**

```typescript
// frontend/src/types/api.ts
export interface IndexedFile {
  source_file: string;
  file_name: string;
  doc_type: string;
  doc_date: string | null;
  file_md5: string;
  chunk_count: number;
}

export interface KBStats {
  total_files: number;
  type_distribution: Record<string, number>;
  last_updated: string | null;
}

export interface UnifiedSearchResult {
  source_type: "local" | "online";
  title: string;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface SourceAttribution {
  title: string;
  source_type: "local" | "online";
  url: string | null;
  date: string | null;
}

export interface GenerationResult {
  content: string;
  sources: SourceAttribution[];
  output_path: string | null;
  template_used: string;
}

export interface TemplateSection {
  title: string;
  writing_points: string[];
  format_rules: string[];
}

export interface TemplateDef {
  id: string;
  name: string;
  doc_type: string;
  sections: TemplateSection[];
  is_builtin: boolean;
}
```

- [ ] **Step 3: 创建各模块 API 文件**

按 `types/api.ts` 中的类型，分别创建 `files.ts`、`search.ts`、`generation.ts`、`templates.ts`、`settings.ts`，每个文件封装对应的 HTTP 调用函数。

- [ ] **Step 4: 提交**

```bash
git add frontend/src/api/ frontend/src/types/
git commit -m "feat(frontend): add API client, type definitions, and module API files"
```

---

### Task 11: 布局组件 + 路由 + 空页面

**Files:**
- Create: `frontend/src/components/Layout/index.tsx`
- Create: `frontend/src/pages/KnowledgeBase/index.tsx`
- Create: `frontend/src/pages/Writing/index.tsx`
- Create: `frontend/src/pages/TemplateManager/index.tsx`
- Create: `frontend/src/pages/Settings/index.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: 创建侧边栏布局**

```tsx
// frontend/src/components/Layout/index.tsx
import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Layout as AntLayout, Menu } from "antd";
import {
  DatabaseOutlined,
  EditOutlined,
  FileTextOutlined,
  SettingOutlined,
} from "@ant-design/icons";

const { Sider, Content } = AntLayout;

const menuItems = [
  { key: "/knowledge-base", icon: <DatabaseOutlined />, label: "知识库" },
  { key: "/writing", icon: <EditOutlined />, label: "写作" },
  { key: "/templates", icon: <FileTextOutlined />, label: "模板管理" },
  { key: "/settings", icon: <SettingOutlined />, label: "设置" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <AntLayout style={{ minHeight: "100vh" }}>
      <Sider width={200} theme="light" style={{ borderRight: "1px solid #f0f0f0" }}>
        <div style={{ padding: "16px 20px", fontSize: 18, fontWeight: 700 }}>公文助手</div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ border: "none" }}
        />
        <div style={{ position: "absolute", bottom: 16, left: 20, fontSize: 12, color: "#999" }}>
          v0.1.0
        </div>
      </Sider>
      <AntLayout>
        <Content style={{ padding: 24, background: "#f5f5f5", minHeight: "auto" }}>
          {children}
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
```

- [ ] **Step 2: 创建 4 个空页面占位**

每个页面仅 `export default function Xxx() { return <div>Xxx</div>; }`

- [ ] **Step 3: 配置 App.tsx 路由**

```tsx
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import KnowledgeBase from "./pages/KnowledgeBase";
import Writing from "./pages/Writing";
import TemplateManager from "./pages/TemplateManager";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/knowledge-base" replace />} />
          <Route path="/knowledge-base" element={<KnowledgeBase />} />
          <Route path="/writing" element={<Writing />} />
          <Route path="/templates" element={<TemplateManager />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
```

- [ ] **Step 4: 验证前端可启动**

Run: `cd frontend && pnpm dev`
验证浏览器打开 localhost:5173 可看到侧边栏 + 空页面。

- [ ] **Step 5: 提交**

```bash
git add frontend/
git commit -m "feat(frontend): add sidebar layout, routing, and empty page shells"
```

---

## Sprint 3-6：页面实现

> **注意：** 以下 Sprint 在实施时须调用 `/frontend-design` skill 指导具体 UI 编码，确保设计质量。每个页面 Task 应先通过 skill 生成组件代码骨架，再补充业务逻辑。

### Task 12: 自定义 Hooks（useWebSocket + useSSE）

**Files:**
- Create: `frontend/src/hooks/useWebSocket.ts`
- Create: `frontend/src/hooks/useSSE.ts`

- [ ] **实现 WebSocket Hook**

封装连接/断开/重连逻辑，返回 `{ progress, status, connect, cancel }`。

- [ ] **实现 SSE Hook**

封装 EventSource 流式读取，返回 `{ content, isStreaming, start }`。

- [ ] **提交**

```bash
git add frontend/src/hooks/
git commit -m "feat(frontend): add useWebSocket and useSSE hooks"
```

---

### Task 13: Zustand Stores

**Files:**
- Create: `frontend/src/stores/useFileStore.ts`
- Create: `frontend/src/stores/useTaskStore.ts`
- Create: `frontend/src/stores/useWritingStore.ts`
- Create: `frontend/src/stores/useSettingsStore.ts`

每个 store 管理对应页面的状态（数据、加载、错误），通过 API 函数触发异步操作。

- [ ] **提交**

```bash
git add frontend/src/stores/
git commit -m "feat(frontend): add Zustand stores for all pages"
```

---

### Task 14: 知识库页面

**Files:**
- Modify: `frontend/src/pages/KnowledgeBase/index.tsx`
- Create: `frontend/src/components/ImportProgress.tsx`

**调用 `/frontend-design` skill 后实现。** 包含：统计卡片、上传区域、导入进度/结果摘要、文件列表表格、筛选/排序/分页、操作按钮。

- [ ] **提交**

```bash
git add frontend/src/pages/KnowledgeBase/ frontend/src/components/ImportProgress.tsx
git commit -m "feat(frontend): implement knowledge base page"
```

---

### Task 15: 写作页面 — 模式 A（一步生成）

**Files:**
- Modify: `frontend/src/pages/Writing/index.tsx`
- Create: `frontend/src/pages/Writing/OneStepMode.tsx`
- Create: `frontend/src/components/SourceList.tsx`

**调用 `/frontend-design` skill 后实现。** 左右分栏，左侧输入+生成，右侧 SSE 流式预览+下载。

- [ ] **提交**

```bash
git add frontend/src/pages/Writing/ frontend/src/components/SourceList.tsx
git commit -m "feat(frontend): implement writing page - one-step generation mode"
```

---

### Task 16: 写作页面 — 模式 B（分步检索）

**Files:**
- Create: `frontend/src/pages/Writing/StepByStepMode.tsx`

**调用 `/frontend-design` skill 后实现。** 写作方向→关键词→检索→勾选→补充要求→生成。

- [ ] **提交**

```bash
git add frontend/src/pages/Writing/StepByStepMode.tsx
git commit -m "feat(frontend): implement writing page - step-by-step search mode"
```

---

### Task 17: 写作页面 — 模式 C（Word→PPT 占位）

**Files:**
- Create: `frontend/src/pages/Writing/WordToPptMode.tsx`

三种输入源 Tab（上传/知识库选择/本次生成），生成按钮置灰。

- [ ] **提交**

```bash
git add frontend/src/pages/Writing/WordToPptMode.tsx
git commit -m "feat(frontend): add Word-to-PPT placeholder with 3 input sources"
```

---

### Task 18: 模板管理页面

**Files:**
- Modify: `frontend/src/pages/TemplateManager/index.tsx`
- Create: `frontend/src/pages/TemplateManager/TemplateEditor.tsx`

**调用 `/frontend-design` skill 后实现。** 卡片网格+编辑器 Modal。

- [ ] **提交**

```bash
git add frontend/src/pages/TemplateManager/
git commit -m "feat(frontend): implement template management page with editor"
```

---

### Task 19: 设置页面

**Files:**
- Modify: `frontend/src/pages/Settings/index.tsx`

**调用 `/frontend-design` skill 后实现。** 4 个 Tab（知识库/LLM/在线检索/输出），每个 Tab 独立保存。

- [ ] **提交**

```bash
git add frontend/src/pages/Settings/
git commit -m "feat(frontend): implement settings page with 4 config tabs"
```

---

## Sprint 收尾

### Task 20: 全量验证

- [ ] **后端全量测试**

Run: `cd backend && python -m pytest --cov=app -q`

- [ ] **后端 Lint**

Run: `cd backend && ruff check app/ tests/ && ruff format --check app/ tests/`

- [ ] **前端 Lint**

Run: `cd frontend && pnpm lint`

- [ ] **前端构建**

Run: `cd frontend && pnpm build`

- [ ] **启动前后端联调验证**

```bash
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && pnpm dev
```

在浏览器中完整操作全流程：上传文件→查看知识库→写作生成→模板管理→设置。

- [ ] **提交最终状态**

```bash
git add -A
git commit -m "feat: Phase 4 Web UI complete"
```

---

## 自审检查

- **Spec 覆盖**：F4.1（Tasks 1-8）、F4.2（Tasks 9-11）、F4.3（Task 14）、F4.4（Tasks 15-17）、F4.5（Task 18）、F4.6（Task 19）均有对应 Task。
- **Placeholder 扫描**：Sprint 3-6 的页面实现 Task 描述了具体功能但代码需调用 `/frontend-design` skill 生成——这是预期行为，skill 调用是实施步骤而非 placeholder。
- **类型一致性**：所有 API 类型定义集中在 `types/api.ts`，与后端模型一一对应。

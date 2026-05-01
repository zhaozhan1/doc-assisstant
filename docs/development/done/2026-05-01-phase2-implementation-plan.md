# 阶段二实施计划 — 检索引擎 + 知识库管理

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现本地向量检索（F2.1）、在线资料检索抽象（F2.2）、检索结果融合排序（F2.3）、知识库文件管理（F2.4），以及支撑这些功能的 API 层和配置扩展。

**Architecture:** Facade 模式 — Retriever 门面类协调 LocalSearch / OnlineSearch / Fusion，FileService 管理知识库文件。API 层通过 FastAPI Lifespan + deps.py 注入组件。

**Tech Stack:** FastAPI, ChromaDB, Pydantic v2, pytest + pytest-asyncio

**Spec:** `docs/product/deliverable/2026-05-01-tech-design-phase-2.md`

---

## File Structure

### 新建文件

| 文件 | 职责 |
|------|------|
| `backend/app/models/search.py` | 检索相关 Pydantic 模型 |
| `backend/app/retrieval/__init__.py` | 包初始化 |
| `backend/app/retrieval/fusion.py` | F2.3 结果融合排序 |
| `backend/app/retrieval/local_search.py` | F2.1 本地向量检索 |
| `backend/app/retrieval/online_search.py` | F2.2 在线检索抽象 + 工厂 + 服务 |
| `backend/app/retrieval/retriever.py` | Facade 统一检索入口 |
| `backend/app/retrieval/file_service.py` | F2.4 知识库文件管理 |
| `backend/app/api/__init__.py` | 包初始化 |
| `backend/app/api/deps.py` | FastAPI 依赖注入 |
| `backend/app/api/routes/__init__.py` | 包初始化 |
| `backend/app/api/routes/health.py` | /health 端点 |
| `backend/app/api/routes/retrieval.py` | 检索 API |
| `backend/app/api/routes/files.py` | 文件管理 API |
| `backend/app/api/routes/settings.py` | 设置 API |
| `backend/app/settings_service.py` | 设置服务 |
| `backend/tests/test_retrieval/__init__.py` | 包初始化 |
| `backend/tests/test_retrieval/test_fusion.py` | Fusion 测试 |
| `backend/tests/test_retrieval/test_local_search.py` | LocalSearch 测试 |
| `backend/tests/test_retrieval/test_online_search.py` | OnlineSearch 测试 |
| `backend/tests/test_retrieval/test_retriever.py` | Retriever Facade 测试 |
| `backend/tests/test_retrieval/test_file_service.py` | FileService 测试 |
| `backend/tests/test_api/__init__.py` | 包初始化 |
| `backend/tests/test_api/test_retrieval_routes.py` | 检索路由测试 |
| `backend/tests/test_api/test_file_routes.py` | 文件路由测试 |
| `backend/tests/test_api/test_settings_routes.py` | 设置路由测试 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/app/config.py` | LLMConfig 增加 embed_provider；新增 OnlineSearchConfig；AppConfig 增加 online_search 字段 |
| `backend/app/llm/factory.py` | 新增 create_embed_provider() |
| `backend/app/db/vector_store.py` | 新增 list_all_chunks() / update_file_metadata() / find_by_md5() |
| `backend/app/ingestion/ingester.py` | MD5 全局去重 + import_time 注入 |
| `backend/app/main.py` | 重构为 lifespan + 路由注册 |

---

## Task 1: 配置扩展 + 数据模型 + 工厂扩展

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/llm/factory.py`
- Create: `backend/app/models/search.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: 扩展 config.py — 添加 embed_provider 和 OnlineSearchConfig**

在 `LLMConfig` 类中添加 `embed_provider` 字段；新增 `OnlineSearchConfig` 类；在 `AppConfig` 中添加 `online_search` 字段。

```python
# backend/app/config.py — 修改后的完整文件

from __future__ import annotations

import os
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, YamlConfigSettingsSource


class KnowledgeBaseConfig(BaseModel):
    source_folder: str = ""
    db_path: str = "./data/chroma_db"
    metadata_path: str = "./data/metadata"
    chunk_size: int = Field(default=500, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=200)


class OllamaConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    chat_model: str = "qwen2.5:14b"
    embed_model: str = "bge-large-zh-v1.5"


class ClaudeConfig(BaseModel):
    base_url: str = "https://api.anthropic.com"
    api_key: str = ""
    chat_model: str = "claude-sonnet-4-20250514"

    @model_validator(mode="after")
    def _resolve_api_key(self) -> ClaudeConfig:
        if not self.api_key:
            self.api_key = os.environ.get("CLAUDE_API_KEY", "")
        return self


class LLMConfig(BaseModel):
    default_provider: Literal["ollama", "claude"] = "ollama"
    embed_provider: Literal["ollama"] = "ollama"
    providers: dict[str, OllamaConfig | ClaudeConfig] = {
        "ollama": OllamaConfig(),
    }


class OnlineSearchConfig(BaseModel):
    enabled: bool = False
    provider: str = "tavily"
    api_key: str = ""
    base_url: str = ""
    domains: list[str] = ["gov.cn"]
    max_results: int = 3


class OCRConfig(BaseModel):
    tesseract_cmd: str = ""


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "./logs/app.log"


class AppConfig(BaseSettings):
    knowledge_base: KnowledgeBaseConfig = KnowledgeBaseConfig()
    llm: LLMConfig = LLMConfig()
    online_search: OnlineSearchConfig = OnlineSearchConfig()
    ocr: OCRConfig = OCRConfig()
    logging: LoggingConfig = LoggingConfig()

    model_config = SettingsConfigDict(
        yaml_file="config.yaml",
        yaml_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, /, _yaml_file: str | None = None, **values: Any) -> None:
        super().__init__(**values, _yaml_file=_yaml_file)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        yaml_file = init_settings.init_kwargs.get("_yaml_file") if hasattr(init_settings, "init_kwargs") else None
        return (
            init_settings,
            env_settings,
            YamlConfigSettingsSource(settings_cls, yaml_file=yaml_file),
            file_secret_settings,
        )
```

- [ ] **Step 2: 扩展 factory.py — 添加 create_embed_provider()**

在现有 `create_provider()` 函数之后新增 `create_embed_provider()` 函数，逻辑相同但使用 `config.embed_provider`。

```python
# 在 backend/app/llm/factory.py 末尾追加

def create_embed_provider(config: LLMConfig) -> BaseLLMProvider:
    """创建专用于 embedding 的 Provider 实例。"""
    name = config.embed_provider
    provider_config = config.providers[name]

    if name == "ollama" and isinstance(provider_config, OllamaConfig):
        return OllamaProvider(
            base_url=provider_config.base_url,
            chat_model=provider_config.chat_model,
            embed_model=provider_config.embed_model,
        )
    raise ValueError(f"不支持 embed provider: {name}")
```

- [ ] **Step 3: 创建 models/search.py**

```python
# backend/app/models/search.py

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel


class SearchFilter(BaseModel):
    doc_types: list[str] | None = None
    date_from: date | None = None
    date_to: date | None = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    local_only: bool = False
    filter: SearchFilter | None = None


class SourceType(str, Enum):
    LOCAL = "local"
    ONLINE = "online"


class UnifiedSearchResult(BaseModel):
    source_type: SourceType
    title: str
    content: str
    score: float
    metadata: dict


class OnlineSearchItem(BaseModel):
    title: str
    snippet: str
    url: str
    score: float = 0.5


class FileListRequest(BaseModel):
    doc_types: list[str] | None = None
    date_from: date | None = None
    date_to: date | None = None
    sort_by: Literal["file_name", "doc_date", "chunk_count"] = "file_name"
    sort_order: Literal["asc", "desc"] = "asc"


class IndexedFile(BaseModel):
    source_file: str
    file_name: str
    doc_type: str
    doc_date: str | None
    file_md5: str
    chunk_count: int
    duplicate_with: str | None = None


class ClassificationUpdate(BaseModel):
    doc_type: str


class OnlineSearchConfigUpdate(BaseModel):
    enabled: bool | None = None
    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    domains: list[str] | None = None
    max_results: int | None = None


class TestConnectionResult(BaseModel):
    success: bool
    message: str
```

- [ ] **Step 4: 编写配置扩展测试**

在 `backend/tests/test_config.py` 中追加测试：

```python
# 追加到 backend/tests/test_config.py 末尾

def test_llm_config_has_embed_provider():
    from app.config import LLMConfig
    config = LLMConfig()
    assert config.embed_provider == "ollama"


def test_online_search_config_defaults():
    from app.config import OnlineSearchConfig
    config = OnlineSearchConfig()
    assert config.enabled is False
    assert config.provider == "tavily"
    assert config.domains == ["gov.cn"]
    assert config.max_results == 3


def test_app_config_has_online_search():
    from app.config import AppConfig
    config = AppConfig(_yaml_file=None)
    assert config.online_search.enabled is False
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && pytest tests/test_config.py -v`
Expected: 所有新测试 PASS，原有测试不受影响

- [ ] **Step 6: 创建 __init__.py 文件**

```bash
touch backend/app/retrieval/__init__.py
touch backend/app/api/__init__.py
touch backend/app/api/routes/__init__.py
touch backend/tests/test_retrieval/__init__.py
touch backend/tests/test_api/__init__.py
```

- [ ] **Step 7: 运行 ruff 检查**

Run: `cd backend && ruff check app/config.py app/llm/factory.py app/models/search.py`
Expected: 无错误

- [ ] **Step 8: Commit**

```bash
git add backend/app/config.py backend/app/llm/factory.py backend/app/models/search.py backend/app/retrieval/__init__.py backend/app/api/__init__.py backend/app/api/routes/__init__.py backend/tests/test_retrieval/__init__.py backend/tests/test_api/__init__.py tests/test_config.py
git commit -m "feat(phase2): 配置扩展 + 检索数据模型 + 工厂 embed_provider"
```

---

## Task 2: VectorStore 扩展

**Files:**
- Modify: `backend/app/db/vector_store.py`
- Test: `backend/tests/test_db/test_vector_store.py`

- [ ] **Step 1: 编写 VectorStore 新方法的失败测试**

在 `backend/tests/test_db/test_vector_store.py` 中追加：

```python
# 追加到 backend/tests/test_db/test_vector_store.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.db.vector_store import VectorStore, SearchResult


@pytest.fixture
def mock_vector_store(tmp_path):
    """创建使用 mock collection 的 VectorStore"""
    llm = AsyncMock()
    vs = VectorStore(str(tmp_path / "test_db"), llm)
    vs._collection = MagicMock()
    return vs


@pytest.mark.asyncio
async def test_list_all_chunks(mock_vector_store):
    mock_vector_store._collection.get.return_value = {
        "ids": ["f1::0", "f1::1", "f2::0"],
        "documents": ["text1", "text2", "text3"],
        "metadatas": [
            {"source_file": "f1.docx", "doc_type": "通知", "file_name": "f1.docx", "file_md5": "abc", "doc_date": "2025-01-01"},
            {"source_file": "f1.docx", "doc_type": "通知", "file_name": "f1.docx", "file_md5": "abc", "doc_date": "2025-01-01"},
            {"source_file": "f2.docx", "doc_type": "决定", "file_name": "f2.docx", "file_md5": "def", "doc_date": "2025-02-01"},
        ],
    }
    results = await mock_vector_store.list_all_chunks()
    assert len(results) == 3
    assert all(isinstance(r, SearchResult) for r in results)


@pytest.mark.asyncio
async def test_update_file_metadata(mock_vector_store):
    await mock_vector_store.update_file_metadata("f1.docx", {"doc_type": "批复"})
    mock_vector_store._collection.update.assert_called_once()
    call_kwargs = mock_vector_store._collection.update.call_args
    assert call_kwargs.kwargs["where"] == {"source_file": "f1.docx"}
    assert call_kwargs.kwargs["metadatas"] == [{"doc_type": "批复"}]


@pytest.mark.asyncio
async def test_find_by_md5_found(mock_vector_store):
    mock_vector_store._collection.get.return_value = {
        "ids": ["f1::0"],
        "metadatas": [{"source_file": "/old/path/f1.docx", "file_md5": "abc123"}],
    }
    result = await mock_vector_store.find_by_md5("abc123")
    assert result == "/old/path/f1.docx"


@pytest.mark.asyncio
async def test_find_by_md5_not_found(mock_vector_store):
    mock_vector_store._collection.get.return_value = {
        "ids": [],
        "metadatas": [],
    }
    result = await mock_vector_store.find_by_md5("nonexistent")
    assert result is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_db/test_vector_store.py::test_list_all_chunks -v`
Expected: FAIL — `AttributeError: 'VectorStore' object has no attribute 'list_all_chunks'`

- [ ] **Step 3: 实现 VectorStore 新方法**

在 `backend/app/db/vector_store.py` 的 `VectorStore` 类末尾追加三个方法：

```python
    async def list_all_chunks(self) -> list[SearchResult]:
        results = self._collection.get(include=["documents", "metadatas"])
        if not results["ids"]:
            return []
        return [
            SearchResult(text=doc or "", metadata=meta or {}, score=0.0)
            for doc, meta in zip(results["documents"], results["metadatas"], strict=False)
        ]

    async def update_file_metadata(self, source_file: str, updates: dict) -> None:
        results = self._collection.get(where={"source_file": source_file})
        if not results["ids"]:
            return
        self._collection.update(
            ids=results["ids"],
            metadatas=[updates] * len(results["ids"]),
        )

    async def find_by_md5(self, file_md5: str) -> str | None:
        results = self._collection.get(where={"file_md5": file_md5})
        if not results["ids"]:
            return None
        return results["metadatas"][0].get("source_file")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && pytest tests/test_db/test_vector_store.py -v`
Expected: 所有测试 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/vector_store.py backend/tests/test_db/test_vector_store.py
git commit -m "feat(phase2): VectorStore 扩展 — list_all_chunks / update_file_metadata / find_by_md5"
```

---

## Task 3: Fusion（F2.3 结果融合排序）

**Files:**
- Create: `backend/app/retrieval/fusion.py`
- Test: `backend/tests/test_retrieval/test_fusion.py`

- [ ] **Step 1: 编写 Fusion 测试**

```python
# backend/tests/test_retrieval/test_fusion.py

from __future__ import annotations

from app.models.search import SourceType, UnifiedSearchResult
from app.retrieval.fusion import Fusion


def _make_local(title: str, score: float) -> UnifiedSearchResult:
    return UnifiedSearchResult(
        source_type=SourceType.LOCAL,
        title=title,
        content=f"content of {title}",
        score=score,
        metadata={"doc_type": "通知"},
    )


def _make_online(title: str, score: float) -> UnifiedSearchResult:
    return UnifiedSearchResult(
        source_type=SourceType.ONLINE,
        title=title,
        content=f"snippet of {title}",
        score=score,
        metadata={"url": "https://example.com"},
    )


def test_merge_mixed_results():
    fusion = Fusion(max_results=10)
    local = [_make_local("A", 0.9), _make_local("B", 0.7)]
    online = [_make_online("C", 0.8)]
    result = fusion.merge(local, online)
    assert len(result) == 3
    # 本地 A score=0.9×1.1=0.99 → 排第一
    assert result[0].title == "A"
    assert result[0].source_type == SourceType.LOCAL


def test_merge_local_priority():
    fusion = Fusion()
    local = [_make_local("L", 0.8)]
    online = [_make_online("O", 0.8)]
    result = fusion.merge(local, online)
    # 本地 ×1.1 = 0.88 > 0.8，本地排前面
    assert result[0].source_type == SourceType.LOCAL
    assert result[1].source_type == SourceType.ONLINE


def test_merge_truncates_to_max_results():
    fusion = Fusion(max_results=2)
    local = [_make_local(f"L{i}", 0.9 - i * 0.1) for i in range(5)]
    online = [_make_online(f"O{i}", 0.5) for i in range(3)]
    result = fusion.merge(local, online)
    assert len(result) == 2


def test_merge_empty_inputs():
    fusion = Fusion()
    assert fusion.merge([], []) == []
    assert len(fusion.merge([_make_local("A", 0.5)], [])) == 1
    assert len(fusion.merge([], [_make_online("B", 0.5)])) == 1


def test_merge_only_local():
    fusion = Fusion()
    local = [_make_local("A", 0.9), _make_local("B", 0.5)]
    result = fusion.merge(local, [])
    assert len(result) == 2
    assert result[0].score >= result[1].score
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_retrieval/test_fusion.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.retrieval'`

- [ ] **Step 3: 实现 Fusion**

```python
# backend/app/retrieval/fusion.py

from __future__ import annotations

from app.models.search import SourceType, UnifiedSearchResult

LOCAL_WEIGHT = 1.1


class Fusion:
    def __init__(self, max_results: int = 10) -> None:
        self._max_results = max_results

    def merge(
        self,
        local_results: list[UnifiedSearchResult],
        online_results: list[UnifiedSearchResult],
    ) -> list[UnifiedSearchResult]:
        scored: list[tuple[float, UnifiedSearchResult]] = []
        for r in local_results:
            weighted_score = r.score * LOCAL_WEIGHT
            scored.append((weighted_score, r))
        for r in online_results:
            scored.append((r.score, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[: self._max_results]]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && pytest tests/test_retrieval/test_fusion.py -v`
Expected: 所有 5 个测试 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/retrieval/fusion.py backend/tests/test_retrieval/test_fusion.py
git commit -m "feat(phase2): F2.3 检索结果融合排序"
```

---

## Task 4: LocalSearch（F2.1 本地向量检索）

**Files:**
- Create: `backend/app/retrieval/local_search.py`
- Test: `backend/tests/test_retrieval/test_local_search.py`

- [ ] **Step 1: 编写 LocalSearch 测试**

```python
# backend/tests/test_retrieval/test_local_search.py

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.db.vector_store import SearchResult
from app.models.search import SearchFilter, SourceType
from app.retrieval.local_search import LocalSearch


@pytest.fixture
def mock_components():
    vs = AsyncMock()
    llm = AsyncMock()
    return vs, llm


@pytest.mark.asyncio
async def test_basic_search(mock_components):
    vs, llm = mock_components
    vs.search.return_value = [
        SearchResult(text="内容A", metadata={"source_file": "/a.docx", "file_name": "a.docx", "doc_type": "通知", "doc_date": "2025-01-01"}, score=0.2),
        SearchResult(text="内容B", metadata={"source_file": "/a.docx", "file_name": "a.docx", "doc_type": "通知", "doc_date": "2025-01-01"}, score=0.3),
    ]
    local = LocalSearch(vs, llm)
    results = await local.search("测试查询")
    assert len(results) >= 1
    assert results[0].source_type == SourceType.LOCAL
    assert results[0].score > 0


@pytest.mark.asyncio
async def test_search_score_normalization(mock_components):
    vs, llm = mock_components
    vs.search.return_value = [
        SearchResult(text="t", metadata={"source_file": "/a.docx", "file_name": "a.docx", "doc_type": "通知"}, score=0.15),
    ]
    local = LocalSearch(vs, llm)
    results = await local.search("q")
    # score = max(0, 1 - 0.15) = 0.85
    assert abs(results[0].score - 0.85) < 0.01


@pytest.mark.asyncio
async def test_search_dedup_by_source_file(mock_components):
    vs, llm = mock_components
    vs.search.return_value = [
        SearchResult(text="chunk1", metadata={"source_file": "/a.docx", "file_name": "a.docx", "doc_type": "通知"}, score=0.1),
        SearchResult(text="chunk2", metadata={"source_file": "/a.docx", "file_name": "a.docx", "doc_type": "通知"}, score=0.3),
        SearchResult(text="chunk3", metadata={"source_file": "/b.docx", "file_name": "b.docx", "doc_type": "决定"}, score=0.2),
    ]
    local = LocalSearch(vs, llm)
    results = await local.search("q")
    # a.docx (2 chunks) 和 b.docx (1 chunk) → 2 条结果
    files = {r.title for r in results}
    assert len(files) == 2
    assert "a.docx" in files
    assert "b.docx" in files


@pytest.mark.asyncio
async def test_search_with_filters(mock_components):
    vs, llm = mock_components
    vs.search.return_value = []
    local = LocalSearch(vs, llm)
    filters = SearchFilter(doc_types=["通知"], date_from="2025-01-01")
    await local.search("q", filters=filters)
    vs.search.assert_called_once()
    call_kwargs = vs.search.call_args
    assert call_kwargs.kwargs.get("filters") is not None or len(call_kwargs.args) > 2


@pytest.mark.asyncio
async def test_search_empty_results(mock_components):
    vs, llm = mock_components
    vs.search.return_value = []
    local = LocalSearch(vs, llm)
    results = await local.search("不存在的查询")
    assert results == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_retrieval/test_local_search.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.retrieval.local_search'`

- [ ] **Step 3: 实现 LocalSearch**

```python
# backend/app/retrieval/local_search.py

from __future__ import annotations

import logging
from collections import defaultdict

from app.db.vector_store import VectorStore
from app.llm.base import BaseLLMProvider
from app.models.search import SearchFilter, SourceType, UnifiedSearchResult

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 2000


class LocalSearch:
    def __init__(self, vector_store: VectorStore, llm: BaseLLMProvider) -> None:
        self._vs = vector_store
        self._llm = llm

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: SearchFilter | None = None,
    ) -> list[UnifiedSearchResult]:
        where = self._build_where(filters)
        raw_results = await self._vs.search(query, top_k=top_k * 3, filters=where)
        return self._deduplicate(raw_results, top_k)

    def _build_where(self, filters: SearchFilter | None) -> dict | None:
        if filters is None:
            return None
        conditions: list[dict] = []
        if filters.doc_types:
            conditions.append({"doc_type": {"$in": filters.doc_types}})
        if filters.date_from:
            conditions.append({"doc_date": {"$gte": filters.date_from.isoformat()}})
        if filters.date_to:
            conditions.append({"doc_date": {"$lte": filters.date_to.isoformat()}})
        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def _deduplicate(self, results: list, top_k: int) -> list[UnifiedSearchResult]:
        groups: dict[str, list] = defaultdict(list)
        for r in results:
            src = r.metadata.get("source_file", "")
            groups[src].append(r)

        file_results: list[UnifiedSearchResult] = []
        for src, chunks in groups.items():
            chunks.sort(key=lambda c: c.score)
            best = chunks[0]
            score = max(0.0, 1.0 - best.score)
            combined = best.text
            for c in chunks[1:]:
                combined += "\n" + c.text
            combined = combined[:MAX_CONTENT_LENGTH]

            file_results.append(UnifiedSearchResult(
                source_type=SourceType.LOCAL,
                title=best.metadata.get("file_name", ""),
                content=combined,
                score=score,
                metadata={
                    k: v for k, v in best.metadata.items()
                    if k in ("doc_type", "doc_date", "file_name")
                },
            ))

        file_results.sort(key=lambda r: r.score, reverse=True)
        return file_results[:top_k]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && pytest tests/test_retrieval/test_local_search.py -v`
Expected: 所有 5 个测试 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/retrieval/local_search.py backend/tests/test_retrieval/test_local_search.py
git commit -m "feat(phase2): F2.1 本地向量检索"
```

---

## Task 5: OnlineSearch（F2.2 在线检索抽象）

**Files:**
- Create: `backend/app/retrieval/online_search.py`
- Test: `backend/tests/test_retrieval/test_online_search.py`

- [ ] **Step 1: 编写 OnlineSearch 测试**

```python
# backend/tests/test_retrieval/test_online_search.py

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import OnlineSearchConfig
from app.models.search import SourceType
from app.retrieval.online_search import (
    BaseOnlineSearchProvider,
    OnlineSearchFactory,
    OnlineSearchService,
)


class MockProvider(BaseOnlineSearchProvider):
    def __init__(self, results=None):
        self._results = results or []

    async def search(self, query, max_results=3, domains=None):
        return self._results[:max_results]


@pytest.mark.asyncio
async def test_service_disabled_returns_empty():
    service = OnlineSearchService(provider=None, config=OnlineSearchConfig(enabled=False))
    results = await service.search("查询")
    assert results == []


@pytest.mark.asyncio
async def test_service_returns_unified_results():
    from app.models.search import OnlineSearchItem
    items = [
        OnlineSearchItem(title="标题", snippet="摘要", url="https://example.com", score=0.6),
    ]
    provider = MockProvider(items)
    service = OnlineSearchService(provider=provider, config=OnlineSearchConfig(enabled=True, max_results=3))
    results = await service.search("查询")
    assert len(results) == 1
    assert results[0].source_type == SourceType.ONLINE
    assert results[0].title == "标题"
    assert results[0].metadata["url"] == "https://example.com"


def test_factory_disabled_returns_none():
    config = OnlineSearchConfig(enabled=False)
    assert OnlineSearchFactory.create(config) is None


def test_factory_unimplemented_provider_raises():
    config = OnlineSearchConfig(enabled=True, provider="baidu")
    with pytest.raises(ValueError, match="未实现"):
        OnlineSearchFactory.create(config)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_retrieval/test_online_search.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 OnlineSearch**

```python
# backend/app/retrieval/online_search.py

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.config import OnlineSearchConfig
from app.models.search import OnlineSearchItem, SourceType, UnifiedSearchResult

logger = logging.getLogger(__name__)


class BaseOnlineSearchProvider(ABC):
    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 3,
        domains: list[str] | None = None,
    ) -> list[OnlineSearchItem]: ...


class OnlineSearchFactory:
    @staticmethod
    def create(config: OnlineSearchConfig) -> BaseOnlineSearchProvider | None:
        if not config.enabled:
            return None
        raise ValueError(f"未实现的在线搜索 Provider: {config.provider}")


class OnlineSearchService:
    def __init__(self, provider: BaseOnlineSearchProvider | None, config: OnlineSearchConfig) -> None:
        self._provider = provider
        self._config = config

    @classmethod
    def from_config(cls, config: OnlineSearchConfig) -> OnlineSearchService:
        provider = OnlineSearchFactory.create(config)
        return cls(provider=provider, config=config)

    async def search(self, query: str) -> list[UnifiedSearchResult]:
        if self._provider is None:
            return []
        items = await self._provider.search(
            query,
            self._config.max_results,
            self._config.domains or None,
        )
        return [self._to_unified(item) for item in items]

    def _to_unified(self, item: OnlineSearchItem) -> UnifiedSearchResult:
        return UnifiedSearchResult(
            source_type=SourceType.ONLINE,
            title=item.title,
            content=item.snippet,
            score=item.score,
            metadata={"url": item.url},
        )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && pytest tests/test_retrieval/test_online_search.py -v`
Expected: 所有 4 个测试 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/retrieval/online_search.py backend/tests/test_retrieval/test_online_search.py
git commit -m "feat(phase2): F2.2 在线检索抽象接口 + 工厂 + 服务"
```

---

## Task 6: Retriever Facade

**Files:**
- Create: `backend/app/retrieval/retriever.py`
- Test: `backend/tests/test_retrieval/test_retriever.py`

- [ ] **Step 1: 编写 Retriever 测试**

```python
# backend/tests/test_retrieval/test_retriever.py

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.models.search import SearchRequest, SourceType, UnifiedSearchResult
from app.retrieval.fusion import Fusion
from app.retrieval.retriever import Retriever


@pytest.fixture
def mock_components():
    local = AsyncMock()
    online = AsyncMock()
    fusion = Fusion(max_results=10)
    return local, online, fusion


def _make_local(title: str, score: float) -> UnifiedSearchResult:
    return UnifiedSearchResult(source_type=SourceType.LOCAL, title=title, content="", score=score, metadata={})


def _make_online(title: str, score: float) -> UnifiedSearchResult:
    return UnifiedSearchResult(source_type=SourceType.ONLINE, title=title, content="", score=score, metadata={})


@pytest.mark.asyncio
async def test_search_combines_local_and_online(mock_components):
    local, online, fusion = mock_components
    local.search.return_value = [_make_local("L1", 0.9)]
    online.search.return_value = [_make_online("O1", 0.5)]
    retriever = Retriever(local, online, fusion)
    request = SearchRequest(query="测试")
    results = await retriever.search(request)
    assert len(results) == 2
    local.search.assert_called_once_with("测试", 10, None)
    online.search.assert_called_once_with("测试")


@pytest.mark.asyncio
async def test_search_local_only_skips_online(mock_components):
    local, online, fusion = mock_components
    local.search.return_value = [_make_local("L1", 0.8)]
    retriever = Retriever(local, online, fusion)
    request = SearchRequest(query="测试", local_only=True)
    results = await retriever.search(request)
    assert len(results) == 1
    online.search.assert_not_called()


@pytest.mark.asyncio
async def test_search_local_directly(mock_components):
    local, online, fusion = mock_components
    local.search.return_value = [_make_local("L1", 0.7)]
    retriever = Retriever(local, online, fusion)
    request = SearchRequest(query="测试")
    results = await retriever.search_local(request)
    assert len(results) == 1
    online.search.assert_not_called()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_retrieval/test_retriever.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 Retriever**

```python
# backend/app/retrieval/retriever.py

from __future__ import annotations

from app.models.search import SearchRequest, UnifiedSearchResult
from app.retrieval.fusion import Fusion
from app.retrieval.local_search import LocalSearch
from app.retrieval.online_search import OnlineSearchService


class Retriever:
    def __init__(
        self,
        local_search: LocalSearch,
        online_search: OnlineSearchService,
        fusion: Fusion,
    ) -> None:
        self._local = local_search
        self._online = online_search
        self._fusion = fusion

    async def search(self, request: SearchRequest) -> list[UnifiedSearchResult]:
        local_results = await self._local.search(
            request.query, request.top_k, request.filter
        )
        online_results = (
            [] if request.local_only else await self._online.search(request.query)
        )
        return self._fusion.merge(local_results, online_results)

    async def search_local(self, request: SearchRequest) -> list[UnifiedSearchResult]:
        return await self._local.search(request.query, request.top_k, request.filter)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && pytest tests/test_retrieval/test_retriever.py -v`
Expected: 所有 3 个测试 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/retrieval/retriever.py backend/tests/test_retrieval/test_retriever.py
git commit -m "feat(phase2): Retriever Facade 统一检索入口"
```

---

## Task 7: FileService（F2.4 知识库文件管理）

**Files:**
- Create: `backend/app/retrieval/file_service.py`
- Test: `backend/tests/test_retrieval/test_file_service.py`

- [ ] **Step 1: 编写 FileService 测试**

```python
# backend/tests/test_retrieval/test_file_service.py

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.vector_store import SearchResult
from app.models.search import FileListRequest
from app.models.task import FileResult
from app.retrieval.file_service import FileService


@pytest.fixture
def mock_components():
    vs = AsyncMock()
    ingester = AsyncMock()
    return vs, ingester


@pytest.mark.asyncio
async def test_list_files_aggregates_by_source(mock_components):
    vs, ingester = mock_components
    vs.list_all_chunks.return_value = [
        SearchResult(text="t1", metadata={"source_file": "/a.docx", "file_name": "a.docx", "doc_type": "通知", "doc_date": "2025-01-01", "file_md5": "abc"}, score=0.0),
        SearchResult(text="t2", metadata={"source_file": "/a.docx", "file_name": "a.docx", "doc_type": "通知", "doc_date": "2025-01-01", "file_md5": "abc"}, score=0.0),
        SearchResult(text="t3", metadata={"source_file": "/b.docx", "file_name": "b.docx", "doc_type": "决定", "doc_date": "2025-06-01", "file_md5": "def"}, score=0.0),
    ]
    svc = FileService(vs, ingester)
    files = await svc.list_files(FileListRequest())
    assert len(files) == 2
    a_file = next(f for f in files if f.file_name == "a.docx")
    assert a_file.chunk_count == 2
    assert a_file.doc_type == "通知"


@pytest.mark.asyncio
async def test_list_files_filters_by_type(mock_components):
    vs, ingester = mock_components
    vs.list_all_chunks.return_value = [
        SearchResult(text="t", metadata={"source_file": "/a.docx", "file_name": "a.docx", "doc_type": "通知", "doc_date": "", "file_md5": "a"}, score=0.0),
        SearchResult(text="t", metadata={"source_file": "/b.docx", "file_name": "b.docx", "doc_type": "决定", "doc_date": "", "file_md5": "b"}, score=0.0),
    ]
    svc = FileService(vs, ingester)
    files = await svc.list_files(FileListRequest(doc_types=["通知"]))
    assert len(files) == 1
    assert files[0].doc_type == "通知"


@pytest.mark.asyncio
async def test_delete_file(mock_components):
    vs, ingester = mock_components
    svc = FileService(vs, ingester)
    await svc.delete_file("/a.docx")
    vs.delete_by_file.assert_called_once_with("/a.docx")


@pytest.mark.asyncio
async def test_reindex_file(mock_components):
    vs, ingester = mock_components
    ingester.process_file.return_value = FileResult(path="/a.docx", status="success", chunks_count=5)
    svc = FileService(vs, ingester)
    result = await svc.reindex_file("/a.docx")
    assert result.chunks_count == 5
    ingester.process_file.assert_called_once()


@pytest.mark.asyncio
async def test_update_classification(mock_components):
    vs, ingester = mock_components
    svc = FileService(vs, ingester)
    await svc.update_classification("/a.docx", "批复")
    vs.update_file_metadata.assert_called_once_with("/a.docx", {"doc_type": "批复"})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_retrieval/test_file_service.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 FileService**

```python
# backend/app/retrieval/file_service.py

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from app.db.vector_store import VectorStore
from app.ingestion.ingester import Ingester
from app.models.search import FileListRequest, IndexedFile
from app.models.task import FileResult

logger = logging.getLogger(__name__)


class FileService:
    def __init__(self, vector_store: VectorStore, ingester: Ingester) -> None:
        self._vs = vector_store
        self._ingester = ingester

    async def list_files(self, request: FileListRequest) -> list[IndexedFile]:
        all_chunks = await self._vs.list_all_chunks()
        groups: dict[str, list] = defaultdict(list)
        for chunk in all_chunks:
            src = chunk.metadata.get("source_file", "")
            if src:
                groups[src].append(chunk)

        files: list[IndexedFile] = []
        for src, chunks in groups.items():
            meta = chunks[0].metadata
            indexed = IndexedFile(
                source_file=src,
                file_name=meta.get("file_name", ""),
                doc_type=meta.get("doc_type", ""),
                doc_date=meta.get("doc_date") or None,
                file_md5=meta.get("file_md5", ""),
                chunk_count=len(chunks),
            )
            files.append(indexed)

        files = self._filter(files, request)
        files = self._sort(files, request)
        return files

    async def delete_file(self, source_file: str) -> None:
        await self._vs.delete_by_file(source_file)

    async def reindex_file(self, source_file: str) -> FileResult:
        return await self._ingester.process_file(Path(source_file))

    async def update_classification(self, source_file: str, doc_type: str) -> None:
        await self._vs.update_file_metadata(source_file, {"doc_type": doc_type})

    def _filter(self, files: list[IndexedFile], request: FileListRequest) -> list[IndexedFile]:
        result = files
        if request.doc_types:
            result = [f for f in result if f.doc_type in request.doc_types]
        if request.date_from:
            result = [f for f in result if f.doc_date and f.doc_date >= request.date_from.isoformat()]
        if request.date_to:
            result = [f for f in result if f.doc_date and f.doc_date <= request.date_to.isoformat()]
        return result

    def _sort(self, files: list[IndexedFile], request: FileListRequest) -> list[IndexedFile]:
        key_map = {"file_name": "file_name", "doc_date": "doc_date", "chunk_count": "chunk_count"}
        key = key_map.get(request.sort_by, "file_name")
        reverse = request.sort_order == "desc"
        return sorted(files, key=lambda f: getattr(f, key) or "", reverse=reverse)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && pytest tests/test_retrieval/test_file_service.py -v`
Expected: 所有 5 个测试 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/retrieval/file_service.py backend/tests/test_retrieval/test_file_service.py
git commit -m "feat(phase2): F2.4 知识库文件管理"
```

---

## Task 8: Ingester 扩展（MD5 去重 + import_time）

**Files:**
- Modify: `backend/app/ingestion/ingester.py`
- Test: `backend/tests/test_ingestion/test_ingester.py`

- [ ] **Step 1: 编写 Ingester 扩展测试**

在 `backend/tests/test_ingestion/test_ingester.py` 中追加：

```python
# 追加到 backend/tests/test_ingestion/test_ingester.py

@pytest.mark.asyncio
async def test_process_file_md5_global_dedup_new_path():
    """同 MD5 不同路径 → 删除旧 chunk，新路径入库"""
    config = _make_config()
    llm = AsyncMock()
    llm.chat.return_value = "通知"
    vs = AsyncMock()
    vs.check_file_exists.return_value = False
    vs.find_by_md5.return_value = "/old/path/a.docx"
    vs.list_all_chunks.return_value = []

    ingester = Ingester(config, llm, vs)
    with patch.object(ingester, 'decompressor') as mock_decomp, \
         patch.object(ingester, 'extractor') as mock_ext, \
         patch.object(ingester, 'metadata_extractor') as mock_meta:
        mock_decomp.extract.return_value = [FileInfo(path=Path("/new/a.docx"), format="docx")]
        mock_ext.extract.return_value = ExtractedDoc(text="测试内容", structure=[])
        mock_meta.extract.return_value = DocumentMetadata(
            file_name="a.docx", source_path="/new/a.docx",
            import_time=datetime.now(), doc_type="通知", file_md5="abc123",
        )
        result = await ingester.process_file(Path("/new/a.docx"))
    assert result.status == "success"
    vs.delete_by_file.assert_any_call("/old/path/a.docx")


@pytest.mark.asyncio
async def test_process_file_injects_import_time():
    """chunk metadata 应包含 import_time"""
    config = _make_config()
    llm = AsyncMock()
    llm.chat.return_value = "通知"
    vs = AsyncMock()
    vs.check_file_exists.return_value = False
    vs.find_by_md5.return_value = None

    ingester = Ingester(config, llm, vs)
    import_time = datetime(2025, 5, 1, 12, 0, 0)
    with patch.object(ingester, 'decompressor') as mock_decomp, \
         patch.object(ingester, 'extractor') as mock_ext, \
         patch.object(ingester, 'metadata_extractor') as mock_meta:
        mock_decomp.extract.return_value = [FileInfo(path=Path("/a.docx"), format="docx")]
        mock_ext.extract.return_value = ExtractedDoc(text="测试内容", structure=[])
        mock_meta.extract.return_value = DocumentMetadata(
            file_name="a.docx", source_path="/a.docx",
            import_time=import_time, doc_type="通知", file_md5="abc",
        )
        await ingester.process_file(Path("/a.docx"))

    upsert_call = vs.upsert.call_args
    chunks = upsert_call.args[0]
    assert chunks[0].metadata.get("import_time") == import_time.isoformat()
```

注意：`_make_config` 和相关 import 如果原测试文件不存在，需要创建辅助函数：

```python
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch
from app.config import AppConfig
from app.models.document import DocumentMetadata, ExtractedDoc, FileInfo
from app.ingestion.ingester import Ingester


def _make_config() -> AppConfig:
    return AppConfig(_yaml_file=None)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_ingestion/test_ingester.py::test_process_file_md5_global_dedup_new_path -v`
Expected: FAIL — `AttributeError: 'VectorStore' object has no attribute 'find_by_md5'`（mock 场景下可能是其他错误）

- [ ] **Step 3: 修改 Ingester — MD5 全局去重 + import_time 注入**

替换 `backend/app/ingestion/ingester.py` 中 `process_file` 方法的核心逻辑：

```python
# backend/app/ingestion/ingester.py — 替换整个 process_file 方法

    async def process_file(self, path: Path) -> FileResult:
        try:
            file_infos = self.decompressor.extract(path)
            if not file_infos:
                return FileResult(path=str(path), status="skipped", error="无支持的文件格式")

            total_chunks = 0
            for fi in file_infos:
                doc = self.extractor.extract(fi)
                meta = self.metadata_extractor.extract(doc)
                meta.doc_type = await self.classifier.classify(doc.text)

                # MD5 全局去重：同内容不同路径 → 删除旧路径
                existing_path = await self.vector_store.find_by_md5(meta.file_md5)
                if existing_path and existing_path != str(fi.path):
                    logger.info("MD5 去重: 删除旧路径 %s → 新路径 %s", existing_path, fi.path)
                    await self.vector_store.delete_by_file(existing_path)

                existing = await self.vector_store.check_file_exists(str(fi.path), meta.file_md5)
                if existing:
                    continue

                chunks = self.chunker.split(doc, meta)
                for c in chunks:
                    c.metadata["file_md5"] = meta.file_md5
                    c.metadata["import_time"] = meta.import_time.isoformat()
                await self.vector_store.delete_by_file(str(fi.path))
                await self.vector_store.upsert(chunks)
                total_chunks += len(chunks)

            return FileResult(path=str(path), status="success", chunks_count=total_chunks)

        except Exception as e:
            logger.exception("处理文件失败: %s", path)
            return FileResult(path=str(path), status="failed", error=str(e))
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && pytest tests/test_ingestion/test_ingester.py -v`
Expected: 所有测试 PASS（包括原有测试）

- [ ] **Step 5: Commit**

```bash
git add backend/app/ingestion/ingester.py backend/tests/test_ingestion/test_ingester.py
git commit -m "feat(phase2): MD5 全局去重 + import_time 注入 chunk metadata"
```

---

## Task 9: SettingsService（设置服务）

**Files:**
- Create: `backend/app/settings_service.py`
- Test: `backend/tests/test_settings_service.py`

- [ ] **Step 1: 编写 SettingsService 测试**

```python
# backend/tests/test_settings_service.py

from __future__ import annotations

import pytest

from app.config import AppConfig, OnlineSearchConfig
from app.models.search import OnlineSearchConfigUpdate, TestConnectionResult
from app.settings_service import SettingsService


@pytest.fixture
def service(tmp_path):
    config = AppConfig(_yaml_file=None)
    return SettingsService(config, config_path=tmp_path / "test_config.yaml")


def test_get_online_search_config(service):
    result = service.get_online_search_config()
    assert result.enabled is False
    assert result.provider == "tavily"


def test_update_online_search_config(service):
    update = OnlineSearchConfigUpdate(enabled=True, api_key="test-key")
    result = service.update_online_search_config(update)
    assert result.enabled is True
    assert result.api_key == "test-key"


def test_update_preserves_unchanged_fields(service):
    update = OnlineSearchConfigUpdate(enabled=True)
    result = service.update_online_search_config(update)
    assert result.provider == "tavily"  # 未修改字段保持原值
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_settings_service.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 SettingsService**

```python
# backend/app/settings_service.py

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from app.config import AppConfig, OnlineSearchConfig
from app.models.search import OnlineSearchConfigUpdate, TestConnectionResult

logger = logging.getLogger(__name__)


class SettingsService:
    def __init__(self, config: AppConfig, config_path: Path | str = "config.yaml") -> None:
        self._config = config
        self._config_path = Path(config_path)

    def get_online_search_config(self) -> OnlineSearchConfig:
        return self._config.online_search

    def update_online_search_config(self, update: OnlineSearchConfigUpdate) -> OnlineSearchConfig:
        current = self._config.online_search
        update_data = update.model_dump(exclude_none=True)
        for key, value in update_data.items():
            setattr(current, key, value)
        self._write_config()
        return current

    async def test_connection(self, config: OnlineSearchConfigUpdate) -> TestConnectionResult:
        return TestConnectionResult(
            success=False,
            message=f"Provider '{self._config.online_search.provider}' 尚未实现，无法测试连接",
        )

    def _write_config(self) -> None:
        if not self._config_path.exists():
            return
        with open(self._config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        data["online_search"] = self._config.online_search.model_dump()
        with open(self._config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && pytest tests/test_settings_service.py -v`
Expected: 所有 3 个测试 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/settings_service.py backend/tests/test_settings_service.py
git commit -m "feat(phase2): SettingsService 设置管理服务"
```

---

## Task 10: API 层（Lifespan + Deps + Routes）

**Files:**
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/routes/health.py`
- Create: `backend/app/api/routes/retrieval.py`
- Create: `backend/app/api/routes/files.py`
- Create: `backend/app/api/routes/settings.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_api/test_retrieval_routes.py`
- Test: `backend/tests/test_api/test_file_routes.py`
- Test: `backend/tests/test_api/test_settings_routes.py`

- [ ] **Step 1: 创建 deps.py**

```python
# backend/app/api/deps.py

from __future__ import annotations

from fastapi import Request

from app.config import AppConfig
from app.retrieval.file_service import FileService
from app.retrieval.retriever import Retriever
from app.settings_service import SettingsService


def get_config(request: Request) -> AppConfig:
    return request.app.state.config


def get_retriever(request: Request) -> Retriever:
    return request.app.state.retriever


def get_file_service(request: Request) -> FileService:
    return request.app.state.file_service


def get_settings_service(request: Request) -> SettingsService:
    return request.app.state.settings_service
```

- [ ] **Step 2: 迁移 health 端点**

```python
# backend/app/api/routes/health.py

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 3: 创建检索路由**

```python
# backend/app/api/routes/retrieval.py

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_retriever
from app.models.search import SearchRequest, UnifiedSearchResult
from app.retrieval.retriever import Retriever

router = APIRouter(prefix="/api", tags=["retrieval"])


@router.post("/search", response_model=list[UnifiedSearchResult])
async def search(
    request: SearchRequest,
    retriever: Retriever = Depends(get_retriever),
) -> list[UnifiedSearchResult]:
    return await retriever.search(request)


@router.post("/search/local", response_model=list[UnifiedSearchResult])
async def search_local(
    request: SearchRequest,
    retriever: Retriever = Depends(get_retriever),
) -> list[UnifiedSearchResult]:
    return await retriever.search_local(request)
```

- [ ] **Step 4: 创建文件管理路由**

```python
# backend/app/api/routes/files.py

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_file_service
from app.models.search import ClassificationUpdate, FileListRequest, IndexedFile
from app.retrieval.file_service import FileService

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("", response_model=list[IndexedFile])
async def list_files(
    doc_types: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str = "file_name",
    sort_order: str = "asc",
    file_service: FileService = Depends(get_file_service),
) -> list[IndexedFile]:
    request = FileListRequest(
        doc_types=doc_types.split(",") if doc_types else None,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return await file_service.list_files(request)


@router.delete("/{source_file:path}")
async def delete_file(
    source_file: str,
    file_service: FileService = Depends(get_file_service),
) -> dict:
    await file_service.delete_file(source_file)
    return {"status": "deleted"}


@router.post("/{source_file:path}/reindex")
async def reindex_file(
    source_file: str,
    file_service: FileService = Depends(get_file_service),
) -> dict:
    result = await file_service.reindex_file(source_file)
    return {"status": result.status, "chunks_count": result.chunks_count}


@router.put("/{source_file:path}/classification")
async def update_classification(
    source_file: str,
    body: ClassificationUpdate,
    file_service: FileService = Depends(get_file_service),
) -> dict:
    await file_service.update_classification(source_file, body.doc_type)
    return {"status": "updated"}
```

- [ ] **Step 5: 创建设置路由**

```python
# backend/app/api/routes/settings.py

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_settings_service
from app.config import OnlineSearchConfig
from app.models.search import OnlineSearchConfigUpdate, TestConnectionResult
from app.settings_service import SettingsService

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/online-search", response_model=OnlineSearchConfig)
async def get_online_search_config(
    service: SettingsService = Depends(get_settings_service),
) -> OnlineSearchConfig:
    return service.get_online_search_config()


@router.put("/online-search", response_model=OnlineSearchConfig)
async def update_online_search_config(
    update: OnlineSearchConfigUpdate,
    service: SettingsService = Depends(get_settings_service),
) -> OnlineSearchConfig:
    return service.update_online_search_config(update)


@router.post("/online-search/test-connection", response_model=TestConnectionResult)
async def test_connection(
    config: OnlineSearchConfigUpdate,
    service: SettingsService = Depends(get_settings_service),
) -> TestConnectionResult:
    return await service.test_connection(config)
```

- [ ] **Step 6: 重构 main.py**

```python
# backend/app/main.py

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI

from app.api.routes import files, health, retrieval, settings
from app.config import AppConfig, LoggingConfig
from app.db.vector_store import VectorStore
from app.ingestion.ingester import Ingester
from app.llm.factory import create_embed_provider, create_provider
from app.retrieval.file_service import FileService
from app.retrieval.fusion import Fusion
from app.retrieval.local_search import LocalSearch
from app.retrieval.online_search import OnlineSearchService
from app.retrieval.retriever import Retriever
from app.settings_service import SettingsService
from app.task_manager import TaskManager

logger = logging.getLogger(__name__)


def setup_logging(config: LoggingConfig) -> None:
    log_format = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
    log_level = getattr(logging, config.level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)

    log_path = Path(config.file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(config.file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(file_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = AppConfig()

    llm = create_provider(config.llm)
    embed_llm = create_embed_provider(config.llm)
    vector_store = VectorStore(config.knowledge_base.db_path, embed_llm)
    ingester = Ingester(config, llm, vector_store)
    task_manager = TaskManager(ingester)

    local_search = LocalSearch(vector_store, embed_llm)
    online_search = OnlineSearchService.from_config(config.online_search)
    fusion = Fusion()
    retriever = Retriever(local_search, online_search, fusion)
    file_service = FileService(vector_store, ingester)
    settings_service = SettingsService(config)

    app.state.config = config
    app.state.llm = llm
    app.state.embed_llm = embed_llm
    app.state.vector_store = vector_store
    app.state.ingester = ingester
    app.state.task_manager = task_manager
    app.state.retriever = retriever
    app.state.file_service = file_service
    app.state.settings_service = settings_service

    yield


def create_app() -> FastAPI:
    config = AppConfig()
    setup_logging(config.logging)
    logger.info("应用启动")

    app = FastAPI(title="公文助手", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(retrieval.router)
    app.include_router(files.router)
    app.include_router(settings.router)

    return app


app = create_app()
```

- [ ] **Step 7: 编写检索路由测试**

```python
# backend/tests/test_api/test_retrieval_routes.py

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.models.search import SourceType, UnifiedSearchResult


@pytest.fixture
def client_with_mock_retriever():
    from app.main import create_app
    app = create_app()
    mock_retriever = AsyncMock()
    mock_retriever.search.return_value = [
        UnifiedSearchResult(source_type=SourceType.LOCAL, title="test.docx", content="内容", score=0.85, metadata={})
    ]
    app.state.retriever = mock_retriever
    return TestClient(app)


def test_search_endpoint(client_with_mock_retriever):
    resp = client_with_mock_retriever.post(
        "/api/search",
        json={"query": "测试", "top_k": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["source_type"] == "local"


def test_search_local_endpoint(client_with_mock_retriever):
    resp = client_with_mock_retriever.post(
        "/api/search/local",
        json={"query": "测试", "local_only": True},
    )
    assert resp.status_code == 200


def test_health_still_works(client_with_mock_retriever):
    resp = client_with_mock_retriever.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 8: 编写文件路由测试**

```python
# backend/tests/test_api/test_file_routes.py

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.models.search import IndexedFile
from app.models.task import FileResult


@pytest.fixture
def client_with_mock_file_service():
    from app.main import create_app
    app = create_app()
    mock_fs = AsyncMock()
    mock_fs.list_files.return_value = [
        IndexedFile(source_file="/a.docx", file_name="a.docx", doc_type="通知", doc_date="2025-01-01", file_md5="abc", chunk_count=3)
    ]
    mock_fs.delete_file.return_value = None
    mock_fs.reindex_file.return_value = FileResult(path="/a.docx", status="success", chunks_count=5)
    mock_fs.update_classification.return_value = None
    app.state.file_service = mock_fs
    return TestClient(app)


def test_list_files(client_with_mock_file_service):
    resp = client_with_mock_file_service.get("/api/files")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["file_name"] == "a.docx"


def test_delete_file(client_with_mock_file_service):
    resp = client_with_mock_file_service.delete("/api/files/a.docx")
    assert resp.status_code == 200


def test_reindex_file(client_with_mock_file_service):
    resp = client_with_mock_file_service.post("/api/files/a.docx/reindex")
    assert resp.status_code == 200
    assert resp.json()["chunks_count"] == 5


def test_update_classification(client_with_mock_file_service):
    resp = client_with_mock_file_service.put(
        "/api/files/a.docx/classification",
        json={"doc_type": "批复"},
    )
    assert resp.status_code == 200
```

- [ ] **Step 9: 编写设置路由测试**

```python
# backend/tests/test_api/test_settings_routes.py

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.config import OnlineSearchConfig
from app.models.search import TestConnectionResult


@pytest.fixture
def client_with_mock_settings():
    from app.main import create_app
    app = create_app()
    mock_svc = AsyncMock()
    mock_svc.get_online_search_config.return_value = OnlineSearchConfig()
    mock_svc.update_online_search_config.return_value = OnlineSearchConfig(enabled=True, api_key="test")
    mock_svc.test_connection.return_value = TestConnectionResult(success=False, message="未实现")
    app.state.settings_service = mock_svc
    return TestClient(app)


def test_get_online_search_config(client_with_mock_settings):
    resp = client_with_mock_settings.get("/api/settings/online-search")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


def test_update_online_search_config(client_with_mock_settings):
    resp = client_with_mock_settings.put(
        "/api/settings/online-search",
        json={"enabled": True, "api_key": "test"},
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True


def test_test_connection(client_with_mock_settings):
    resp = client_with_mock_settings.post(
        "/api/settings/online-search/test-connection",
        json={"provider": "tavily"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False
```

- [ ] **Step 10: 运行所有 API 测试**

Run: `cd backend && pytest tests/test_api/ -v`
Expected: 所有测试 PASS

- [ ] **Step 11: 运行全部测试确认无回归**

Run: `cd backend && pytest -v`
Expected: 所有测试 PASS

- [ ] **Step 12: 运行 ruff 检查**

Run: `cd backend && ruff check app/ tests/ && ruff format --check app/ tests/`
Expected: 无错误

- [ ] **Step 13: Commit**

```bash
git add backend/app/main.py backend/app/api/ backend/tests/test_api/
git commit -m "feat(phase2): API 层 — Lifespan + Deps + 检索/文件/设置路由"
```

---

## Task 11: 集成验证

- [ ] **Step 1: 运行全部测试**

Run: `cd backend && pytest --tb=short`
Expected: 全部 PASS

- [ ] **Step 2: 运行覆盖率检查**

Run: `cd backend && pytest --cov=app --cov-report=term-missing`
Expected: 覆盖率 ≥ 80%

- [ ] **Step 3: 运行 ruff 全量检查**

Run: `cd backend && ruff check app/ tests/ && ruff format --check app/ tests/`
Expected: 无错误

- [ ] **Step 4: 验证应用启动**

Run: `cd backend && python -c "from app.main import app; print('OK')"`
Expected: 输出 `OK`

- [ ] **Step 5: Final commit（如有 lint 修复）**

```bash
git add -A
git commit -m "chore(phase2): lint 修复 + 集成验证"
```

---

## Plan Self-Review

### 1. Spec Coverage

| Spec 章节 | 对应 Task |
|-----------|-----------|
| 核心设计决策 | Task 1 (config), Task 3 (Fusion), Task 6 (Facade), Task 10 (lifespan) |
| F2.1 本地向量检索 | Task 4 |
| F2.2 在线资料检索 | Task 5 |
| F2.3 检索结果融合排序 | Task 3 |
| F2.4 知识库文件管理 | Task 7, Task 8 |
| 数据模型 | Task 1 |
| API 路由 | Task 10 |
| 配置扩展 | Task 1 |
| 测试策略 | 每个 Task 内含 TDD |
| SettingsService | Task 9 |

**无遗漏**。

### 2. Placeholder Scan

已检查：无 TBD / TODO / "implement later" / "fill in details" 等占位符。

### 3. Type Consistency

- `SearchFilter` → `LocalSearch._build_where()` → `VectorStore.search(filters=)`
- `UnifiedSearchResult` → `LocalSearch._deduplicate()` → `Fusion.merge()` → `Retriever.search()`
- `IndexedFile` → `FileService.list_files()` → `/api/files` response
- `OnlineSearchConfig` → `OnlineSearchService.from_config()` → `SettingsService`
- 所有方法签名和返回类型在上下游一致

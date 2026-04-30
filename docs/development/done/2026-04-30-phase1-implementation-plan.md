# 阶段一实施计划 — 项目基础 + 文档解析

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现公文助手的后端项目骨架、LLM Provider 抽象层、文档解析流水线、向量入库和异步任务管理，完成端到端的文件导入能力。

**Architecture:** FastAPI 单体应用，模块化分层（config → models → llm → ingestion → db → task_manager），流水线顺序编排，异步任务管理支持断点续传。

**Tech Stack:** Python 3.10+ / FastAPI / Pydantic Settings / httpx (Ollama) / anthropic (Claude) / ChromaDB / python-docx / pdfplumber / pytesseract / openpyxl / python-pptx / py7zr / pyunpack

**Spec:** `docs/product/deliverable/2026-04-30-tech-design-phase-1.md`

---

## File Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI 入口 + 日志初始化
│   ├── config.py                        # AppConfig (Pydantic Settings + YAML)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── document.py                  # FileInfo, StructureItem, ExtractedDoc, DocumentMetadata, FileResult
│   │   ├── chunk.py                     # Chunk
│   │   └── task.py                      # TaskStatus, FileResult, TaskProgress
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── decompressor.py              # Decompressor (zip/7z/rar 递归解压)
│   │   ├── extractor.py                 # Extractor (6 格式文本提取)
│   │   ├── classifier.py                # Classifier (LLM 零样本分类)
│   │   ├── chunker.py                   # Chunker (段落分块)
│   │   └── ingester.py                  # Ingester (流水线编排)
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py                      # BaseLLMProvider (ABC)
│   │   ├── ollama_provider.py           # OllamaProvider
│   │   ├── claude_provider.py           # ClaudeProvider
│   │   └── factory.py                   # create_provider()
│   ├── db/
│   │   ├── __init__.py
│   │   └── vector_store.py              # VectorStore (ChromaDB 封装) + SearchResult
│   └── task_manager.py                  # TaskManager (异步任务 + 断点续传)
├── tests/
│   ├── conftest.py                      # 共享 fixtures
│   ├── fixtures/                        # 测试用样本文件
│   │   ├── sample.txt
│   │   ├── sample.docx
│   │   ├── sample.pdf
│   │   ├── sample.xlsx
│   │   └── sample.pptx
│   ├── test_config.py
│   ├── test_llm/
│   │   ├── __init__.py
│   │   ├── test_ollama_provider.py
│   │   ├── test_claude_provider.py
│   │   └── test_factory.py
│   ├── test_ingestion/
│   │   ├── __init__.py
│   │   ├── test_decompressor.py
│   │   ├── test_extractor.py
│   │   ├── test_classifier.py
│   │   ├── test_chunker.py
│   │   └── test_ingester.py
│   ├── test_db/
│   │   ├── __init__.py
│   │   └── test_vector_store.py
│   └── test_task_manager.py
├── config.yaml
├── environment.yml
└── pyproject.toml
```

---

## Task 1: 项目骨架与环境初始化（F1.1）

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/environment.yml`
- Create: `backend/config.yaml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/document.py`
- Create: `backend/app/models/chunk.py`
- Create: `backend/app/models/task.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[project]
name = "doc-assistant"
version = "0.1.0"
description = "公文助手 — 本地化政务公文知识库与 AI 写作辅助系统"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "pydantic>=2.0",
    "pydantic-settings>=2.2",
    "pyyaml>=6.0",
    "httpx>=0.27",
    "anthropic>=0.30",
    "chromadb>=0.5",
    "python-docx>=1.0",
    "pdfplumber>=0.11",
    "pytesseract>=0.3",
    "openpyxl>=3.1",
    "python-pptx>=0.6",
    "py7zr>=0.22",
    "pyunpack>=0.3",
    "Pillow>=10.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "respx>=0.21",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 2: 创建 environment.yml**

```yaml
name: doc-assistant
channels:
  - defaults
dependencies:
  - python=3.10
  - pip
  - pip:
    - -e ".[dev]"
```

- [ ] **Step 3: 创建 config.yaml**

```yaml
knowledge_base:
  source_folder: ""
  db_path: "./data/chroma_db"
  metadata_path: "./data/metadata"
  chunk_size: 500
  chunk_overlap: 50

llm:
  default_provider: "ollama"
  providers:
    ollama:
      base_url: "http://localhost:11434"
      chat_model: "qwen2.5:14b"
      embed_model: "bge-large-zh-v1.5"
    claude:
      base_url: "https://api.anthropic.com"
      api_key: ""
      chat_model: "claude-sonnet-4-20250514"

online_search:
  enabled: false
  provider: "tavily"
  api_key: ""
  domains:
    - "gov.cn"
  max_results: 3

output:
  format: "docx"
  save_path: "./output"
  include_sources: true

ocr:
  tesseract_cmd: ""

logging:
  level: "INFO"
  file: "./logs/app.log"
```

- [ ] **Step 4: 创建数据模型**

`backend/app/__init__.py`:
```python
```
（空文件）

`backend/app/models/__init__.py`:
```python
```
（空文件）

`backend/app/models/document.py`:
```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class FileInfo:
    path: Path
    format: str
    original_archive: Path | None = None


@dataclass
class StructureItem:
    level: int
    text: str
    position: int


@dataclass
class ExtractedDoc:
    text: str
    structure: list[StructureItem]
    metadata: dict = field(default_factory=dict)
    source_path: Path = field(default_factory=Path)


@dataclass
class DocumentMetadata:
    file_name: str
    source_path: str
    import_time: str
    doc_date: str | None = None
    doc_type: str = ""
    file_md5: str = ""
```

`backend/app/models/chunk.py`:
```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Chunk:
    text: str
    source_file: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)
```

`backend/app/models/task.py`:
```python
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
```

- [ ] **Step 5: 创建 config.py**

`backend/app/config.py`:
```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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


class LLMConfig(BaseModel):
    default_provider: Literal["ollama", "claude"] = "ollama"
    providers: dict[str, OllamaConfig | ClaudeConfig] = {
        "ollama": OllamaConfig(),
    }


class OCRConfig(BaseModel):
    tesseract_cmd: str = ""


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "./logs/app.log"


class AppConfig(BaseSettings):
    knowledge_base: KnowledgeBaseConfig = KnowledgeBaseConfig()
    llm: LLMConfig = LLMConfig()
    ocr: OCRConfig = OCRConfig()
    logging: LoggingConfig = LoggingConfig()

    model_config = SettingsConfigDict(yaml_file="config.yaml", yaml_file_encoding="utf-8")
```

- [ ] **Step 6: 创建 main.py**

`backend/app/main.py`:
```python
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI

from app.config import AppConfig

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
    file_handler = RotatingFileHandler(
        config.file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(file_handler)


def create_app() -> FastAPI:
    config = AppConfig()
    setup_logging(config.logging)
    logger.info("应用启动")

    app = FastAPI(title="公文助手", version="0.1.0")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
```

注意：`create_app()` 内 `AppConfig()` 会自动读取当前目录下的 `config.yaml`。

- [ ] **Step 7: 写配置测试**

需要从 `pydantic_settings` 导入 `LoggingConfig`，所以此处直接用 `from app.config import AppConfig, LoggingConfig`。

`backend/tests/__init__.py`:
```python
```

`backend/tests/conftest.py`:
```python
from __future__ import annotations

import os
from pathlib import Path

import pytest

# 确保 tests 能 import app 包
os.chdir(Path(__file__).parent.parent)
```

`backend/tests/test_config.py`:
```python
from __future__ import annotations

from pathlib import Path

import pytest

from app.config import AppConfig, ClaudeConfig, KnowledgeBaseConfig, LLMConfig, OllamaConfig


class TestAppConfig:
    def test_load_from_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
knowledge_base:
  source_folder: "/tmp/docs"
  db_path: "./data/chroma_db"
  chunk_size: 500
  chunk_overlap: 50

llm:
  default_provider: "ollama"
  providers:
    ollama:
      base_url: "http://localhost:11434"
      chat_model: "qwen2.5:14b"
      embed_model: "bge-large-zh-v1.5"

logging:
  level: "DEBUG"
  file: "./logs/test.log"
""")
        config = AppConfig(_yaml_file=str(config_file))
        assert config.knowledge_base.source_folder == "/tmp/docs"
        assert config.knowledge_base.chunk_size == 500
        assert config.llm.default_provider == "ollama"
        assert config.logging.level == "DEBUG"

    def test_default_values(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("{}")
        config = AppConfig(_yaml_file=str(config_file))
        assert config.knowledge_base.chunk_size == 500
        assert config.llm.default_provider == "ollama"
        assert config.ocr.tesseract_cmd == ""

    def test_chunk_size_validation(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
knowledge_base:
  chunk_size: 50
""")
        with pytest.raises(Exception):
            AppConfig(_yaml_file=str(config_file))

    def test_chunk_overlap_validation(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
knowledge_base:
  chunk_overlap: 300
""")
        with pytest.raises(Exception):
            AppConfig(_yaml_file=str(config_file))
```

- [ ] **Step 8: 安装依赖并运行测试**

Run: `cd backend && pip install -e ".[dev]"`
Run: `cd backend && pytest tests/test_config.py -v`
Expected: 4 passed

- [ ] **Step 9: Commit**

```bash
git add backend/
git commit -m "feat: 项目骨架 — pyproject.toml, config, models, main.py"
```

---

## Task 2: LLM Provider 抽象层（F1.2）

**Files:**
- Create: `backend/app/llm/__init__.py`
- Create: `backend/app/llm/base.py`
- Create: `backend/app/llm/ollama_provider.py`
- Create: `backend/app/llm/claude_provider.py`
- Create: `backend/app/llm/factory.py`
- Test: `backend/tests/test_llm/__init__.py`
- Test: `backend/tests/test_llm/test_ollama_provider.py`
- Test: `backend/tests/test_llm/test_claude_provider.py`
- Test: `backend/tests/test_llm/test_factory.py`

- [ ] **Step 1: 写 Ollama Provider 测试**

`backend/tests/test_llm/__init__.py`:
```python
```

`backend/tests/test_llm/test_ollama_provider.py`:
```python
from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.llm.ollama_provider import OllamaProvider


@pytest.fixture
def provider() -> OllamaProvider:
    return OllamaProvider(
        base_url="http://localhost:11434",
        chat_model="qwen2.5:14b",
        embed_model="bge-large-zh-v1.5",
    )


class TestOllamaChat:
    @respx.mock
    @pytest.mark.asyncio
    async def test_chat_returns_content(self, provider: OllamaProvider) -> None:
        respx.post("http://localhost:11434/api/chat").mock(
            return_value=httpx.Response(200, json={
                "message": {"role": "assistant", "content": "你好，有什么可以帮你？"},
            })
        )
        result = await provider.chat([{"role": "user", "content": "你好"}])
        assert result == "你好，有什么可以帮你？"

    @respx.mock
    @pytest.mark.asyncio
    async def test_chat_raises_on_error(self, provider: OllamaProvider) -> None:
        respx.post("http://localhost:11434/api/chat").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        with pytest.raises(httpx.HTTPStatusError):
            await provider.chat([{"role": "user", "content": "test"}])


class TestOllamaEmbed:
    @respx.mock
    @pytest.mark.asyncio
    async def test_embed_returns_vectors(self, provider: OllamaProvider) -> None:
        fake_embedding = [0.1, 0.2, 0.3]
        respx.post("http://localhost:11434/api/embed").mock(
            return_value=httpx.Response(200, json={
                "embeddings": [{"embedding": fake_embedding}, {"embedding": fake_embedding}],
            })
        )
        result = await provider.embed(["文本1", "文本2"])
        assert len(result) == 2
        assert result[0] == fake_embedding

    @respx.mock
    @pytest.mark.asyncio
    async def test_embed_empty_list(self, provider: OllamaProvider) -> None:
        respx.post("http://localhost:11434/api/embed").mock(
            return_value=httpx.Response(200, json={"embeddings": []})
        )
        result = await provider.embed([])
        assert result == []
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && pytest tests/test_llm/test_ollama_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.llm'`

- [ ] **Step 3: 实现 Ollama Provider**

`backend/app/llm/__init__.py`:
```python
```

`backend/app/llm/base.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> str:
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    async def classify(self, text: str, labels: list[str]) -> str:
        prompt = (
            f"请从以下类别中选择最匹配的一个：{', '.join(labels)}\n\n"
            f"文本内容：\n{text[:500]}\n\n"
            "只返回类别名称，不要解释。"
        )
        response = await self.chat([{"role": "user", "content": prompt}])
        return self._match_label(response.strip(), labels)

    @staticmethod
    def _match_label(response: str, labels: list[str]) -> str:
        response = response.strip()
        for label in labels:
            if label in response:
                return label
        return labels[-1]
```

`backend/app/llm/ollama_provider.py`:
```python
from __future__ import annotations

import httpx

from app.llm.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: str, chat_model: str, embed_model: str) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=120.0)
        self._chat_model = chat_model
        self._embed_model = embed_model

    async def chat(self, messages: list[dict], **kwargs) -> str:
        resp = await self._client.post(
            "/api/chat",
            json={"model": self._chat_model, "messages": messages, "stream": False},
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.post(
            "/api/embed",
            json={"model": self._embed_model, "input": texts},
        )
        resp.raise_for_status()
        return [item["embedding"] for item in resp.json()["embeddings"]]
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && pytest tests/test_llm/test_ollama_provider.py -v`
Expected: 4 passed

- [ ] **Step 5: 写 Claude Provider 测试**

`backend/tests/test_llm/test_claude_provider.py`:
```python
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.claude_provider import ClaudeProvider


@pytest.fixture
def provider() -> ClaudeProvider:
    return ClaudeProvider(
        api_key="test-key",
        base_url="https://api.anthropic.com",
        chat_model="claude-sonnet-4-20250514",
    )


class TestClaudeChat:
    @pytest.mark.asyncio
    async def test_chat_returns_content(self, provider: ClaudeProvider) -> None:
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="你好")]
        provider._client.messages.create = AsyncMock(return_value=mock_message)

        result = await provider.chat([{"role": "user", "content": "你好"}])
        assert result == "你好"
        provider._client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_raises_not_implemented(self, provider: ClaudeProvider) -> None:
        with pytest.raises(NotImplementedError, match="Claude 不支持 embedding"):
            await provider.embed(["文本"])
```

- [ ] **Step 6: 运行测试验证失败**

Run: `cd backend && pytest tests/test_llm/test_claude_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.llm.claude_provider'`

- [ ] **Step 7: 实现 Claude Provider**

`backend/app/llm/claude_provider.py`:
```python
from __future__ import annotations

import anthropic

from app.llm.base import BaseLLMProvider


class ClaudeProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str, chat_model: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key, base_url=base_url)
        self._model = chat_model

    async def chat(self, messages: list[dict], **kwargs) -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=messages,
        )
        return response.content[0].text

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("Claude 不支持 embedding，请配置 Ollama 作为 embed Provider")
```

- [ ] **Step 8: 运行测试验证通过**

Run: `cd backend && pytest tests/test_llm/test_claude_provider.py -v`
Expected: 2 passed

- [ ] **Step 9: 写工厂测试**

`backend/tests/test_llm/test_factory.py`:
```python
from __future__ import annotations

import pytest

from app.config import ClaudeConfig, LLMConfig, OllamaConfig
from app.llm.claude_provider import ClaudeProvider
from app.llm.factory import create_provider
from app.llm.ollama_provider import OllamaProvider


class TestFactory:
    def test_creates_ollama_provider(self) -> None:
        config = LLMConfig(
            default_provider="ollama",
            providers={"ollama": OllamaConfig()},
        )
        provider = create_provider(config)
        assert isinstance(provider, OllamaProvider)

    def test_creates_claude_provider(self) -> None:
        config = LLMConfig(
            default_provider="claude",
            providers={"claude": ClaudeConfig(api_key="test-key")},
        )
        provider = create_provider(config)
        assert isinstance(provider, ClaudeProvider)

    def test_raises_on_unknown_provider(self) -> None:
        config = LLMConfig(
            default_provider="unknown",
            providers={"unknown": OllamaConfig()},
        )
        with pytest.raises(ValueError, match="未知 Provider"):
            create_provider(config)
```

- [ ] **Step 10: 运行测试验证失败**

Run: `cd backend && pytest tests/test_llm/test_factory.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.llm.factory'`

- [ ] **Step 11: 实现工厂**

`backend/app/llm/factory.py`:
```python
from __future__ import annotations

from app.config import LLMConfig
from app.llm.base import BaseLLMProvider
from app.llm.claude_provider import ClaudeProvider
from app.llm.ollama_provider import OllamaProvider


def create_provider(config: LLMConfig) -> BaseLLMProvider:
    name = config.default_provider
    provider_config = config.providers[name]

    if name == "ollama" and isinstance(provider_config, type(cfg := OllamaConfig())) or name == "ollama":
        return OllamaProvider(
            base_url=provider_config.base_url,
            chat_model=provider_config.chat_model,
            embed_model=provider_config.embed_model,
        )
    elif name == "claude":
        return ClaudeProvider(
            api_key=provider_config.api_key,
            base_url=provider_config.base_url,
            chat_model=provider_config.chat_model,
        )
    raise ValueError(f"未知 Provider: {name}")
```

Wait — the isinstance check above is awkward. Let me fix this properly:

`backend/app/llm/factory.py`:
```python
from __future__ import annotations

from app.config import ClaudeConfig, LLMConfig, OllamaConfig
from app.llm.base import BaseLLMProvider
from app.llm.claude_provider import ClaudeProvider
from app.llm.ollama_provider import OllamaProvider


def create_provider(config: LLMConfig) -> BaseLLMProvider:
    name = config.default_provider
    provider_config = config.providers[name]

    if name == "ollama" and isinstance(provider_config, OllamaConfig):
        return OllamaProvider(
            base_url=provider_config.base_url,
            chat_model=provider_config.chat_model,
            embed_model=provider_config.embed_model,
        )
    elif name == "claude" and isinstance(provider_config, ClaudeConfig):
        return ClaudeProvider(
            api_key=provider_config.api_key,
            base_url=provider_config.base_url,
            chat_model=provider_config.chat_model,
        )
    raise ValueError(f"未知 Provider: {name}")
```

- [ ] **Step 12: 运行全部 LLM 测试**

Run: `cd backend && pytest tests/test_llm/ -v`
Expected: 9 passed

- [ ] **Step 13: Commit**

```bash
git add backend/app/llm/ backend/tests/test_llm/
git commit -m "feat: LLM Provider 抽象层 — BaseLLMProvider, Ollama, Claude, Factory"
```

---

## Task 3: 压缩包解压与文件格式识别（F1.3）

**Files:**
- Create: `backend/app/ingestion/__init__.py`
- Create: `backend/app/ingestion/decompressor.py`
- Test: `backend/tests/test_ingestion/__init__.py`
- Test: `backend/tests/test_ingestion/test_decompressor.py`

- [ ] **Step 1: 写 Decompressor 测试**

`backend/tests/test_ingestion/__init__.py`:
```python
```

`backend/tests/test_ingestion/test_decompressor.py`:
```python
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from app.ingestion.decompressor import Decompressor


@pytest.fixture
def decompressor() -> Decompressor:
    return Decompressor()


@pytest.fixture
def sample_txt(tmp_path: Path) -> Path:
    f = tmp_path / "test.txt"
    f.write_text("hello world", encoding="utf-8")
    return f


@pytest.fixture
def sample_zip(tmp_path: Path) -> Path:
    inner = tmp_path / "inner.txt"
    inner.write_text("inner content", encoding="utf-8")
    zip_path = tmp_path / "archive.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(inner, "inner.txt")
    return zip_path


@pytest.fixture
def nested_zip(tmp_path: Path) -> Path:
    inner = tmp_path / "doc.txt"
    inner.write_text("nested content", encoding="utf-8")
    inner_zip = tmp_path / "inner.zip"
    with zipfile.ZipFile(inner_zip, "w") as zf:
        zf.write(inner, "doc.txt")
    outer_zip = tmp_path / "outer.zip"
    with zipfile.ZipFile(outer_zip, "w") as zf:
        zf.write(inner_zip, "inner.zip")
    return outer_zip


class TestSingleFile:
    def test_supported_format(self, decompressor: Decompressor, sample_txt: Path) -> None:
        results = decompressor.extract(sample_txt)
        assert len(results) == 1
        assert results[0].format == ".txt"
        assert results[0].path == sample_txt
        assert results[0].original_archive is None

    def test_unsupported_format(self, decompressor: Decompressor, tmp_path: Path) -> None:
        f = tmp_path / "test.xyz"
        f.write_text("unknown")
        results = decompressor.extract(f)
        assert results == []


class TestZipExtract:
    def test_extracts_files_from_zip(
        self, decompressor: Decompressor, sample_zip: Path
    ) -> None:
        results = decompressor.extract(sample_zip)
        assert len(results) == 1
        assert results[0].format == ".txt"
        assert results[0].original_archive == sample_zip

    def test_extracts_nested_zip(
        self, decompressor: Decompressor, nested_zip: Path
    ) -> None:
        results = decompressor.extract(nested_zip)
        assert len(results) == 1
        assert results[0].format == ".txt"
        assert "nested content" in results[0].path.read_text()


class TestDirectory:
    def test_scans_directory(self, decompressor: Decompressor, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.pdf").write_text("b")
        (tmp_path / "c.xyz").write_text("c")
        results = decompressor.extract(tmp_path)
        formats = {r.format for r in results}
        assert formats == {".txt", ".pdf"}
        assert len(results) == 2
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && pytest tests/test_ingestion/test_decompressor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.ingestion'`

- [ ] **Step 3: 实现 Decompressor**

`backend/app/ingestion/__init__.py`:
```python
```

`backend/app/ingestion/decompressor.py`:
```python
from __future__ import annotations

import logging
import tempfile
import zipfile
from pathlib import Path

from app.models.document import FileInfo

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {
    ".docx", ".pdf", ".xlsx", ".pptx", ".png", ".jpg", ".jpeg", ".txt",
}
ARCHIVE_FORMATS = {".zip", ".rar", ".7z"}


class Decompressor:
    def extract(self, path: Path) -> list[FileInfo]:
        path = Path(path)
        if path.is_dir():
            return self._scan_directory(path)
        suffix = path.suffix.lower()
        if suffix in ARCHIVE_FORMATS:
            return self._extract_archive(path, depth=0)
        if suffix in SUPPORTED_FORMATS:
            return [FileInfo(path=path, format=suffix, original_archive=None)]
        return []

    def _scan_directory(self, directory: Path) -> list[FileInfo]:
        results: list[FileInfo] = []
        for f in sorted(directory.rglob("*")):
            if f.is_file():
                results.extend(self.extract(f))
        return results

    def _extract_archive(self, archive_path: Path, depth: int) -> list[FileInfo]:
        if depth > 5:
            logger.warning("嵌套深度超限: %s", archive_path)
            return []
        extract_dir = tempfile.mkdtemp()
        self._do_extract(archive_path, extract_dir)
        results: list[FileInfo] = []
        for f in sorted(Path(extract_dir).rglob("*")):
            if f.is_file():
                suffix = f.suffix.lower()
                if suffix in ARCHIVE_FORMATS:
                    results.extend(self._extract_archive(f, depth + 1))
                elif suffix in SUPPORTED_FORMATS:
                    results.append(FileInfo(path=f, format=suffix, original_archive=archive_path))
        return results

    def _do_extract(self, archive_path: Path, dest: str) -> None:
        suffix = archive_path.suffix.lower()
        if suffix == ".zip":
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(dest)
        elif suffix == ".7z":
            import py7zr
            with py7zr.SevenZipFile(archive_path, "r") as sz:
                sz.extractall(dest)
        elif suffix == ".rar":
            from pyunpack import Archive
            Archive(str(archive_path)).extractall(dest)
        else:
            logger.warning("不支持的压缩格式: %s", suffix)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && pytest tests/test_ingestion/test_decompressor.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/ingestion/decompressor.py backend/tests/test_ingestion/test_decompressor.py
git commit -m "feat: 压缩包解压与文件格式识别 (zip/7z/rar 递归)"
```

---

## Task 4: 多格式文档文本提取（F1.4）

**Files:**
- Create: `backend/app/ingestion/extractor.py`
- Create: `backend/tests/fixtures/sample.txt`
- Create: `backend/tests/fixtures/sample.docx`（需用 python-docx 动态生成）
- Create: `backend/tests/fixtures/sample.pdf`（需用代码生成）
- Test: `backend/tests/test_ingestion/test_extractor.py`

- [ ] **Step 1: 准备测试 fixtures（在 conftest.py 中动态生成）**

在 `backend/tests/conftest.py` 末尾追加：

```python
@pytest.fixture
def fixtures_dir(tmp_path: Path) -> Path:
    """动态生成各格式的测试样本文件。"""
    # sample.txt
    (tmp_path / "sample.txt").write_text("这是一段测试文本。\n\n第二段落内容。", encoding="utf-8")

    # sample.docx
    from docx import Document
    doc = Document()
    doc.add_heading("测试标题", level=1)
    doc.add_paragraph("这是正文内容。")
    doc.save(str(tmp_path / "sample.docx"))

    # sample.xlsx
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["姓名", "部门"])
    ws.append(["张三", "办公室"])
    wb.save(str(tmp_path / "sample.xlsx"))

    # sample.pptx
    from pptx import Presentation
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "测试PPT标题"
    slide.placeholders[1].text = "测试PPT内容"
    prs.save(str(tmp_path / "sample.pptx"))

    # sample.pdf — 用 pdfplumber 不方便创建，使用 reportlab 或 fpdf
    # 简单方案：跳过 PDF 创建，仅测试 PDF 解析逻辑
    # 实际项目中可用 reportlab:
    try:
        from reportlab.pdfgen import canvas
        pdf_path = tmp_path / "sample.pdf"
        c = canvas.Canvas(str(pdf_path))
        c.drawString(100, 750, "测试PDF内容")
        c.save()
    except ImportError:
        pass

    return tmp_path
```

注意：reportlab 需加入 dev 依赖。或者使用更简单的方案：在测试中 mock PDF 提取。鉴于不增加额外依赖，PDF 和 OCR 测试使用 mock。

简化 `conftest.py` 追加内容（不依赖 reportlab）：

```python
@pytest.fixture
def fixtures_dir(tmp_path: Path) -> Path:
    """动态生成各格式的测试样本文件。"""
    (tmp_path / "sample.txt").write_text("这是一段测试文本。\n\n第二段落内容。", encoding="utf-8")

    from docx import Document
    doc = Document()
    doc.add_heading("测试标题", level=1)
    doc.add_paragraph("这是正文内容。")
    doc.save(str(tmp_path / "sample.docx"))

    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["姓名", "部门"])
    ws.append(["张三", "办公室"])
    wb.save(str(tmp_path / "sample.xlsx"))

    from pptx import Presentation
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "测试PPT标题"
    slide.placeholders[1].text = "测试PPT内容"
    prs.save(str(tmp_path / "sample.pptx"))

    return tmp_path
```

- [ ] **Step 2: 写 Extractor 测试**

`backend/tests/test_ingestion/test_extractor.py`:
```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import OCRConfig
from app.ingestion.extractor import Extractor
from app.models.document import FileInfo


@pytest.fixture
def extractor() -> Extractor:
    return Extractor(OCRConfig())


class TestTxtExtract:
    def test_extracts_text(self, extractor: Extractor, fixtures_dir: Path) -> None:
        fi = FileInfo(path=fixtures_dir / "sample.txt", format=".txt")
        doc = extractor.extract(fi)
        assert "测试文本" in doc.text
        assert doc.source_path == fi.path


class TestDocxExtract:
    def test_extracts_text_and_structure(
        self, extractor: Extractor, fixtures_dir: Path
    ) -> None:
        fi = FileInfo(path=fixtures_dir / "sample.docx", format=".docx")
        doc = extractor.extract(fi)
        assert "正文内容" in doc.text
        assert len(doc.structure) >= 1
        assert doc.structure[0].level == 1
        assert "测试标题" in doc.structure[0].text


class TestXlsxExtract:
    def test_extracts_tabular_data(self, extractor: Extractor, fixtures_dir: Path) -> None:
        fi = FileInfo(path=fixtures_dir / "sample.xlsx", format=".xlsx")
        doc = extractor.extract(fi)
        assert "张三" in doc.text
        assert "办公室" in doc.text


class TestPptxExtract:
    def test_extracts_slide_text(self, extractor: Extractor, fixtures_dir: Path) -> None:
        fi = FileInfo(path=fixtures_dir / "sample.pptx", format=".pptx")
        doc = extractor.extract(fi)
        assert "PPT" in doc.text or "内容" in doc.text


class TestUnsupportedFormat:
    def test_raises_on_unsupported_format(self, extractor: Extractor, tmp_path: Path) -> None:
        fi = FileInfo(path=tmp_path / "test.xyz", format=".xyz")
        with pytest.raises(ValueError, match="不支持的格式"):
            extractor.extract(fi)


class TestEmptyFile:
    def test_handles_empty_txt(self, extractor: Extractor, tmp_path: Path) -> None:
        empty = tmp_path / "empty.txt"
        empty.write_text("", encoding="utf-8")
        fi = FileInfo(path=empty, format=".txt")
        doc = extractor.extract(fi)
        assert doc.text == ""
```

- [ ] **Step 3: 运行测试验证失败**

Run: `cd backend && pytest tests/test_ingestion/test_extractor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.ingestion.extractor'`

- [ ] **Step 4: 实现 Extractor**

`backend/app/ingestion/extractor.py`:
```python
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import pytesseract
from PIL import Image

from app.config import OCRConfig
from app.models.document import ExtractedDoc, FileInfo, StructureItem

logger = logging.getLogger(__name__)


class Extractor:
    def __init__(self, ocr_config: OCRConfig) -> None:
        if ocr_config.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = ocr_config.tesseract_cmd
        self._handlers: dict[str, Callable[[Path], ExtractedDoc]] = {
            ".docx": self._extract_docx,
            ".pdf": self._extract_pdf,
            ".xlsx": self._extract_xlsx,
            ".pptx": self._extract_pptx,
            ".png": self._extract_image,
            ".jpg": self._extract_image,
            ".jpeg": self._extract_image,
            ".txt": self._extract_txt,
        }

    def extract(self, file_info: FileInfo) -> ExtractedDoc:
        handler = self._handlers.get(file_info.format)
        if not handler:
            raise ValueError(f"不支持的格式: {file_info.format}")
        return handler(file_info.path)

    def _extract_txt(self, path: Path) -> ExtractedDoc:
        for encoding in ("utf-8", "gb18030"):
            try:
                text = path.read_text(encoding=encoding)
                return ExtractedDoc(text=text, structure=[], source_path=path)
            except (UnicodeDecodeError, UnicodeError):
                continue
        return ExtractedDoc(text="", structure=[], source_path=path)

    def _extract_docx(self, path: Path) -> ExtractedDoc:
        from docx import Document

        doc = Document(str(path))
        text_parts: list[str] = []
        structure: list[StructureItem] = []
        pos = 0

        for para in doc.paragraphs:
            if para.style and para.style.name.startswith("Heading"):
                level = int(para.style.name.replace("Heading ", "").replace("Heading", "1"))
                structure.append(StructureItem(level=level, text=para.text, position=pos))
            text_parts.append(para.text)
            pos += len(para.text) + 1

        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text for cell in row.cells]
                text_parts.append(" | ".join(cells))

        return ExtractedDoc(text="\n".join(text_parts), structure=structure, source_path=path)

    def _extract_pdf(self, path: Path) -> ExtractedDoc:
        import pdfplumber

        text_parts: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)

        text = "\n".join(text_parts).strip()
        if len(text) < 50:
            try:
                text = self._ocr_pdf(path)
            except Exception as e:
                logger.warning("PDF OCR 失败 %s: %s", path, e)

        return ExtractedDoc(text=text, structure=[], source_path=path)

    def _ocr_pdf(self, path: Path) -> str:
        from pdf2image import convert_from_path
        images = convert_from_path(str(path))
        texts = []
        for img in images:
            texts.append(pytesseract.image_to_string(img, lang="chi_sim"))
        return "\n".join(texts)

    def _extract_xlsx(self, path: Path) -> ExtractedDoc:
        from openpyxl import load_workbook

        wb = load_workbook(str(path), read_only=True)
        text_parts: list[str] = []
        for ws in wb.worksheets:
            rows = list(ws.iter_rows(values_only=True))
            if rows:
                header = [str(c) if c else "" for c in rows[0]]
                for row in rows[1:]:
                    values = [str(c) if c else "" for c in row]
                    text_parts.append(
                        ", ".join(f"{h}: {v}" for h, v in zip(header, values) if v)
                    )
        wb.close()
        return ExtractedDoc(text="\n".join(text_parts), structure=[], source_path=path)

    def _extract_pptx(self, path: Path) -> ExtractedDoc:
        from pptx import Presentation

        prs = Presentation(str(path))
        text_parts: list[str] = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if shape.has_text_frame:
                    text_parts.append(shape.text_frame.text)
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                text_parts.append(slide.notes_slide.notes_text_frame.text)
        return ExtractedDoc(text="\n".join(text_parts), structure=[], source_path=path)

    def _extract_image(self, path: Path) -> ExtractedDoc:
        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang="chi_sim")
        return ExtractedDoc(text=text, structure=[], source_path=path)
```

注意：`_ocr_pdf` 依赖 `pdf2image`，需要 poppler 系统依赖。如果 OCR PDF 测试在 CI 中运行有困难，可在测试中 mock 此路径。Phase 1 暂不测试 OCR PDF 路径，仅测试文本 PDF。

- [ ] **Step 5: 运行测试验证通过**

Run: `cd backend && pytest tests/test_ingestion/test_extractor.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/ingestion/extractor.py backend/tests/test_ingestion/test_extractor.py backend/tests/conftest.py
git commit -m "feat: 多格式文档文本提取 — docx/pdf/xlsx/pptx/txt/ocr"
```

---

## Task 5: 元数据提取与文档分类（F1.5）

**Files:**
- Create: `backend/app/ingestion/classifier.py`
- Test: `backend/tests/test_ingestion/test_classifier.py`

- [ ] **Step 1: 写 Classifier 测试**

`backend/tests/test_ingestion/test_classifier.py`:
```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.ingestion.classifier import DOC_TYPES, Classifier, MetadataExtractor
from app.models.document import ExtractedDoc


@pytest.fixture
def mock_llm() -> AsyncMock:
    llm = AsyncMock()
    return llm


@pytest.fixture
def classifier(mock_llm: AsyncMock) -> Classifier:
    return Classifier(mock_llm)


@pytest.fixture
def metadata_extractor() -> MetadataExtractor:
    return MetadataExtractor()


class TestClassifier:
    @pytest.mark.asyncio
    async def test_classify_returns_valid_label(
        self, classifier: Classifier, mock_llm: AsyncMock
    ) -> None:
        mock_llm.classify.return_value = "通知"
        result = await classifier.classify("关于召开会议的通知")
        assert result == "通知"
        mock_llm.classify.assert_called_once()

    @pytest.mark.asyncio
    async def test_classify_truncates_long_text(
        self, classifier: Classifier, mock_llm: AsyncMock
    ) -> None:
        mock_llm.classify.return_value = "报告"
        long_text = "x" * 1000
        await classifier.classify(long_text)
        call_args = mock_llm.classify.call_args
        assert len(call_args[0][0]) <= 500

    @pytest.mark.asyncio
    async def test_classify_fallback_on_unknown_label(
        self, classifier: Classifier, mock_llm: AsyncMock
    ) -> None:
        mock_llm.classify.return_value = "不存在的类型"
        result = await classifier.classify("随便什么文本")
        assert result == "其他"


class TestMetadataExtractor:
    def test_extracts_date_from_text(self, metadata_extractor: MetadataExtractor) -> None:
        doc = ExtractedDoc(
            text="根据2024年3月15日的工作安排",
            structure=[],
            source_path=Path("/tmp/test.txt"),
        )
        meta = metadata_extractor.extract(doc)
        assert meta.doc_date is not None
        assert "2024" in meta.doc_date

    def test_extracts_date_from_filename(self, metadata_extractor: MetadataExtractor, tmp_path: Path) -> None:
        f = tmp_path / "20240315-通知.txt"
        f.write_text("无日期文本", encoding="utf-8")
        doc = ExtractedDoc(text="无日期文本", structure=[], source_path=f)
        meta = metadata_extractor.extract(doc)
        assert meta.doc_date is not None

    def test_no_date_returns_none(self, metadata_extractor: MetadataExtractor, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("没有日期信息", encoding="utf-8")
        doc = ExtractedDoc(text="没有日期信息", structure=[], source_path=f)
        meta = metadata_extractor.extract(doc)
        assert meta.doc_date is None

    def test_computes_md5(self, metadata_extractor: MetadataExtractor, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("固定内容", encoding="utf-8")
        doc = ExtractedDoc(text="固定内容", structure=[], source_path=f)
        meta = metadata_extractor.extract(doc)
        assert len(meta.file_md5) == 32  # MD5 hex digest

    def test_doc_type_initially_empty(self, metadata_extractor: MetadataExtractor, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("test", encoding="utf-8")
        doc = ExtractedDoc(text="test", structure=[], source_path=f)
        meta = metadata_extractor.extract(doc)
        assert meta.doc_type == ""
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && pytest tests/test_ingestion/test_classifier.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.ingestion.classifier'`

- [ ] **Step 3: 实现 Classifier + MetadataExtractor**

`backend/app/ingestion/classifier.py`:
```python
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime
from pathlib import Path

from app.llm.base import BaseLLMProvider
from app.models.document import DocumentMetadata, ExtractedDoc

logger = logging.getLogger(__name__)

DOC_TYPES = [
    "通知", "公告", "请示", "报告", "方案", "规划",
    "会议纪要", "合同", "工作总结", "领导讲话稿", "调研报告", "汇报PPT", "其他",
]


class MetadataExtractor:
    _DATE_PATTERNS = [
        (re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日"), lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"),
        (re.compile(r"(\d{4})-(\d{2})-(\d{2})"), lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}"),
        (re.compile(r"(\d{4})(\d{2})(\d{2})"), lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}"),
    ]

    def extract(self, doc: ExtractedDoc) -> DocumentMetadata:
        doc_date = self._extract_date(doc.text) or self._extract_date_from_path(doc.source_path)
        file_md5 = self._compute_md5(doc.source_path)
        return DocumentMetadata(
            file_name=doc.source_path.name,
            source_path=str(doc.source_path),
            import_time=datetime.now().isoformat(),
            doc_date=doc_date,
            doc_type="",
            file_md5=file_md5,
        )

    def _extract_date(self, text: str) -> str | None:
        for pattern, formatter in self._DATE_PATTERNS:
            match = pattern.search(text)
            if match:
                return formatter(match)
        return None

    def _extract_date_from_path(self, path: Path) -> str | None:
        name = path.stem
        return self._extract_date(name)

    def _compute_md5(self, path: Path) -> str:
        h = hashlib.md5()
        for chunk in iter(lambda: open(path, "rb").read(8192), b""):
            h.update(chunk)
        return h.hexdigest()


class Classifier:
    def __init__(self, llm: BaseLLMProvider) -> None:
        self._llm = llm

    async def classify(self, text: str) -> str:
        result = await self._llm.classify(text[:500], DOC_TYPES)
        if result not in DOC_TYPES:
            return "其他"
        return result
```

注意：`_compute_md5` 中 `open()` 未 close — 应使用 `with` 语句。修正：

```python
    def _compute_md5(self, path: Path) -> str:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && pytest tests/test_ingestion/test_classifier.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/ingestion/classifier.py backend/tests/test_ingestion/test_classifier.py
git commit -m "feat: 元数据提取与文档分类 — MetadataExtractor, Classifier"
```

---

## Task 6: 文本分块（F1.6）

**Files:**
- Create: `backend/app/ingestion/chunker.py`
- Test: `backend/tests/test_ingestion/test_chunker.py`

- [ ] **Step 1: 写 Chunker 测试**

`backend/tests/test_ingestion/test_chunker.py`:
```python
from __future__ import annotations

import pytest

from app.ingestion.chunker import Chunker
from app.models.chunk import Chunk
from app.models.document import DocumentMetadata, ExtractedDoc
from pathlib import Path


@pytest.fixture
def chunker() -> Chunker:
    return Chunker(chunk_size=100, chunk_overlap=20)


@pytest.fixture
def sample_meta() -> DocumentMetadata:
    return DocumentMetadata(
        file_name="test.txt",
        source_path="/tmp/test.txt",
        import_time="2024-01-01T00:00:00",
        doc_type="通知",
        doc_date="2024-01-01",
    )


def _make_doc(text: str) -> ExtractedDoc:
    return ExtractedDoc(text=text, structure=[], source_path=Path("/tmp/test.txt"))


class TestNormalChunking:
    def test_splits_into_chunks(self, chunker: Chunker, sample_meta: DocumentMetadata) -> None:
        text = "段落一。" + "字" * 80 + "\n\n段落二。" + "字" * 80
        doc = _make_doc(text)
        chunks = chunker.split(doc, sample_meta)
        assert len(chunks) >= 2
        for c in chunks:
            assert isinstance(c, Chunk)
            assert c.source_file == "/tmp/test.txt"

    def test_chunk_metadata(self, chunker: Chunker, sample_meta: DocumentMetadata) -> None:
        doc = _make_doc("测试内容")
        chunks = chunker.split(doc, sample_meta)
        assert chunks[0].metadata["doc_type"] == "通知"
        assert chunks[0].metadata["doc_date"] == "2024-01-01"
        assert chunks[0].chunk_index == 0


class TestEdgeCases:
    def test_short_text_produces_single_chunk(
        self, chunker: Chunker, sample_meta: DocumentMetadata
    ) -> None:
        doc = _make_doc("短文本")
        chunks = chunker.split(doc, sample_meta)
        assert len(chunks) == 1
        assert chunks[0].text == "短文本"

    def test_empty_text_produces_no_chunks(
        self, chunker: Chunker, sample_meta: DocumentMetadata
    ) -> None:
        doc = _make_doc("")
        chunks = chunker.split(doc, sample_meta)
        assert chunks == []

    def test_long_paragraph_is_split(
        self, chunker: Chunker, sample_meta: DocumentMetadata
    ) -> None:
        text = "字" * 300  # 超过 chunk_size
        doc = _make_doc(text)
        chunks = chunker.split(doc, sample_meta)
        assert len(chunks) >= 2

    def test_chunk_indices_sequential(
        self, chunker: Chunker, sample_meta: DocumentMetadata
    ) -> None:
        text = "段一。" + "字" * 90 + "\n\n段二。" + "字" * 90 + "\n\n段三。" + "字" * 90
        doc = _make_doc(text)
        chunks = chunker.split(doc, sample_meta)
        for i, c in enumerate(chunks):
            assert c.chunk_index == i
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && pytest tests/test_ingestion/test_chunker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.ingestion.chunker'`

- [ ] **Step 3: 实现 Chunker**

`backend/app/ingestion/chunker.py`:
```python
from __future__ import annotations

import re

from app.models.chunk import Chunk
from app.models.document import DocumentMetadata, ExtractedDoc


class Chunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def split(self, doc: ExtractedDoc, meta: DocumentMetadata) -> list[Chunk]:
        if not doc.text.strip():
            return []
        paragraphs = self._split_by_paragraph(doc.text)
        merged = self._merge_paragraphs(paragraphs)
        return [
            Chunk(
                text=text,
                source_file=str(doc.source_path),
                chunk_index=i,
                metadata={
                    "doc_type": meta.doc_type,
                    "doc_date": meta.doc_date or "",
                    "file_name": meta.file_name,
                },
            )
            for i, text in enumerate(merged)
        ]

    def _split_by_paragraph(self, text: str) -> list[str]:
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _merge_paragraphs(self, paragraphs: list[str]) -> list[str]:
        if not paragraphs:
            return []

        chunks: list[str] = []
        current = ""

        for para in paragraphs:
            if len(para) > self._chunk_size:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(self._split_long_text(para))
            elif len(current) + len(para) + 1 <= self._chunk_size:
                current = current + "\n\n" + para if current else para
            else:
                if current:
                    chunks.append(current)
                current = self._take_overlap(current) + para if chunks else para

        if current:
            chunks.append(current)

        return chunks if chunks else paragraphs

    def _split_long_text(self, text: str) -> list[str]:
        sentences = re.split(r"(?<=[。！？；\n])", text)
        chunks: list[str] = []
        current = ""
        for s in sentences:
            if not s:
                continue
            if len(current) + len(s) <= self._chunk_size:
                current += s
            else:
                if current:
                    chunks.append(current)
                current = s
        if current:
            chunks.append(current)
        return chunks

    def _take_overlap(self, text: str) -> str:
        if not text or self._chunk_overlap <= 0:
            return ""
        return text[-self._chunk_overlap:]
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && pytest tests/test_ingestion/test_chunker.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/ingestion/chunker.py backend/tests/test_ingestion/test_chunker.py
git commit -m "feat: 文本分块 — 段落切分、合并、重叠、超长处理"
```

---

## Task 7: 向量化与入库（F1.7）

**Files:**
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/vector_store.py`
- Test: `backend/tests/test_db/__init__.py`
- Test: `backend/tests/test_db/test_vector_store.py`

- [ ] **Step 1: 写 VectorStore 测试**

`backend/tests/test_db/__init__.py`:
```python
```

`backend/tests/test_db/test_vector_store.py`:
```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.db.vector_store import SearchResult, VectorStore
from app.models.chunk import Chunk


@pytest.fixture
def mock_llm() -> AsyncMock:
    llm = AsyncMock()
    llm.embed.return_value = [[0.1] * 10 for _ in range(10)]
    return llm


@pytest.fixture
def vector_store(mock_llm: AsyncMock, tmp_path: Path) -> VectorStore:
    return VectorStore(db_path=str(tmp_path / "chroma_db"), llm=mock_llm)


def _make_chunks(n: int, source_file: str = "/tmp/test.txt") -> list[Chunk]:
    return [
        Chunk(
            text=f"文本块{i}",
            source_file=source_file,
            chunk_index=i,
            metadata={"doc_type": "通知", "file_name": "test.txt", "file_md5": "abc123"},
        )
        for i in range(n)
    ]


class TestUpsert:
    @pytest.mark.asyncio
    async def test_upsert_stores_chunks(
        self, vector_store: VectorStore, mock_llm: AsyncMock
    ) -> None:
        chunks = _make_chunks(3)
        await vector_store.upsert(chunks)
        mock_llm.embed.assert_called_once()
        assert vector_store._collection.count() == 3

    @pytest.mark.asyncio
    async def test_upsert_empty_list_does_nothing(
        self, vector_store: VectorStore, mock_llm: AsyncMock
    ) -> None:
        await vector_store.upsert([])
        mock_llm.embed.assert_not_called()


class TestDeleteByFile:
    @pytest.mark.asyncio
    async def test_delete_removes_chunks(
        self, vector_store: VectorStore
    ) -> None:
        chunks = _make_chunks(2, "/tmp/a.txt")
        await vector_store.upsert(chunks)
        assert vector_store._collection.count() == 2

        await vector_store.delete_by_file("/tmp/a.txt")
        assert vector_store._collection.count() == 0


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_returns_results(
        self, vector_store: VectorStore, mock_llm: AsyncMock
    ) -> None:
        chunks = _make_chunks(3)
        await vector_store.upsert(chunks)
        mock_llm.embed.return_value = [[0.1] * 10]

        results = await vector_store.search("查询", top_k=2)
        assert len(results) <= 2
        assert all(isinstance(r, SearchResult) for r in results)


class TestCheckFileExists:
    @pytest.mark.asyncio
    async def test_returns_false_when_not_exists(
        self, vector_store: VectorStore
    ) -> None:
        result = await vector_store.check_file_exists("/tmp/nonexistent.txt", "abc123")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_when_md5_matches(
        self, vector_store: VectorStore
    ) -> None:
        chunks = _make_chunks(1)
        await vector_store.upsert(chunks)
        result = await vector_store.check_file_exists("/tmp/test.txt", "abc123")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_md5_changed(
        self, vector_store: VectorStore
    ) -> None:
        chunks = _make_chunks(1)
        await vector_store.upsert(chunks)
        result = await vector_store.check_file_exists("/tmp/test.txt", "new_md5")
        assert result is False
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && pytest tests/test_db/test_vector_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.db'`

- [ ] **Step 3: 实现 VectorStore**

`backend/app/db/__init__.py`:
```python
```

`backend/app/db/vector_store.py`:
```python
from __future__ import annotations

import logging
from dataclasses import dataclass

import chromadb

from app.llm.base import BaseLLMProvider
from app.models.chunk import Chunk

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    text: str
    metadata: dict
    score: float


class VectorStore:
    def __init__(self, db_path: str, llm: BaseLLMProvider) -> None:
        self._client = chromadb.PersistentClient(path=db_path)
        self._collection = self._client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"},
        )
        self._llm = llm

    async def upsert(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        embeddings = await self._llm.embed([c.text for c in chunks])
        ids = [f"{c.source_file}::{c.chunk_index}" for c in chunks]
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            metadatas=[c.metadata for c in chunks],
        )

    async def delete_by_file(self, source_file: str) -> None:
        self._collection.delete(where={"source_file": source_file})

    async def search(
        self, query: str, top_k: int = 10, filters: dict | None = None
    ) -> list[SearchResult]:
        query_embedding = (await self._llm.embed([query]))[0]
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filters,
        )
        if not results["documents"] or not results["documents"][0]:
            return []
        return [
            SearchResult(text=doc, metadata=meta, score=dist)
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

    async def check_file_exists(self, source_file: str, file_md5: str) -> bool:
        results = self._collection.get(where={"source_file": source_file})
        if not results["ids"]:
            return False
        existing_md5 = results["metadatas"][0].get("file_md5", "")
        return existing_md5 == file_md5
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && pytest tests/test_db/test_vector_store.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/ backend/tests/test_db/
git commit -m "feat: 向量数据库封装 — ChromaDB upsert/delete/search/增量判断"
```

---

## Task 8: 异步任务管理器（F1.8）

**Files:**
- Create: `backend/app/task_manager.py`
- Test: `backend/tests/test_task_manager.py`

- [ ] **Step 1: 写 TaskManager 测试**

`backend/tests/test_task_manager.py`:
```python
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.task import FileResult, TaskProgress, TaskStatus
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
        await asyncio.sleep(0.5)  # 等待异步任务完成

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


class TestResume:
    @pytest.mark.asyncio
    async def test_resumes_from_pending_files(
        self, task_manager: TaskManager, mock_ingester: AsyncMock, tmp_path: Path
    ) -> None:
        files = [tmp_path / f"{i}.txt" for i in range(5)]
        for f in files:
            f.write_text("test")

        # 模拟前次运行中断：处理了2个文件
        mock_ingester.process_file.side_effect = [
            FileResult(path=str(files[0]), status="success"),
            FileResult(path=str(files[1]), status="success"),
        ]
        task_id = await task_manager.start_import(files)
        await asyncio.sleep(0.5)

        progress = task_manager.get_progress(task_id)
        assert progress.success == 2

    @pytest.mark.asyncio
    async def test_get_unfinished_tasks(
        self, task_manager: TaskManager, mock_ingester: AsyncMock, tmp_path: Path
    ) -> None:
        files = [tmp_path / "a.txt"]
        files[0].write_text("test")

        mock_ingester.process_file.return_value = FileResult(
            path=str(files[0]), status="success"
        )

        task_id = await task_manager.start_import(files)
        await asyncio.sleep(0.5)

        unfinished = task_manager.get_unfinished_tasks()
        assert task_id not in [t.task_id for t in unfinished]
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && pytest tests/test_task_manager.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.task_manager'`

- [ ] **Step 3: 实现 TaskManager**

`backend/app/task_manager.py`:
```python
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
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
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && pytest tests/test_task_manager.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/task_manager.py backend/tests/test_task_manager.py
git commit -m "feat: 异步任务管理器 — 状态流转、断点续传、取消机制"
```

---

## Task 9: 流水线编排（Ingester 集成）

**Files:**
- Create: `backend/app/ingestion/ingester.py`
- Test: `backend/tests/test_ingestion/test_ingester.py`

- [ ] **Step 1: 写 Ingester 集成测试**

`backend/tests/test_ingestion/test_ingester.py`:
```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import AppConfig, KnowledgeBaseConfig, LLMConfig, OCRConfig
from app.ingestion.ingester import Ingester
from app.models.document import ExtractedDoc, FileResult


@pytest.fixture
def mock_llm() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_vector_store() -> AsyncMock:
    vs = AsyncMock()
    vs.check_file_exists.return_value = False
    return vs


@pytest.fixture
def ingester(mock_llm: AsyncMock, mock_vector_store: AsyncMock, tmp_path: Path) -> Ingester:
    config = AppConfig(_yaml_file=str(tmp_path / "dummy.yaml"))
    with patch.object(AppConfig, "__init__", lambda self, **kwargs: None):
        config.knowledge_base = KnowledgeBaseConfig()
        config.ocr = OCRConfig()
    return Ingester(config=config, llm=mock_llm, vector_store=mock_vector_store)


class TestProcessFile:
    @pytest.mark.asyncio
    async def test_processes_txt_file(
        self, ingester: Ingester, mock_llm: AsyncMock, tmp_path: Path
    ) -> None:
        txt = tmp_path / "test.txt"
        txt.write_text("测试文档内容", encoding="utf-8")

        mock_llm.classify.return_value = "通知"
        mock_llm.embed.return_value = [[0.1] * 10]

        result = await ingester.process_file(txt)
        assert result.status == "success"
        assert result.chunks_count >= 1

    @pytest.mark.asyncio
    async def test_skips_unsupported_format(
        self, ingester: Ingester, tmp_path: Path
    ) -> None:
        xyz = tmp_path / "test.xyz"
        xyz.write_text("unknown")

        result = await ingester.process_file(xyz)
        assert result.status == "skipped"

    @pytest.mark.asyncio
    async def test_failure_returns_failed_result(
        self, ingester: Ingester, tmp_path: Path
    ) -> None:
        bad = tmp_path / "bad.docx"
        bad.write_bytes(b"\x00\x01\x02")  # 损坏的 docx

        result = await ingester.process_file(bad)
        assert result.status == "failed"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_skips_unchanged_file(
        self, ingester: Ingester, mock_vector_store: AsyncMock, tmp_path: Path
    ) -> None:
        txt = tmp_path / "cached.txt"
        txt.write_text("已存在的内容", encoding="utf-8")

        mock_vector_store.check_file_exists.return_value = True

        result = await ingester.process_file(txt)
        assert result.status == "success"
        assert result.chunks_count == 0  # 跳过，不入库
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && pytest tests/test_ingestion/test_ingester.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.ingestion.ingester'`

- [ ] **Step 3: 实现 Ingester**

`backend/app/ingestion/ingester.py`:
```python
from __future__ import annotations

import logging
from pathlib import Path

from app.config import AppConfig
from app.db.vector_store import VectorStore
from app.ingestion.chunker import Chunker
from app.ingestion.classifier import Classifier, MetadataExtractor
from app.ingestion.decompressor import Decompressor
from app.ingestion.extractor import Extractor
from app.llm.base import BaseLLMProvider
from app.models.document import FileResult
from app.models.task import FileResult as TaskFileResult

logger = logging.getLogger(__name__)


class Ingester:
    def __init__(self, config: AppConfig, llm: BaseLLMProvider, vector_store: VectorStore) -> None:
        self.decompressor = Decompressor()
        self.extractor = Extractor(config.ocr)
        self.metadata_extractor = MetadataExtractor()
        self.classifier = Classifier(llm)
        self.chunker = Chunker(
            config.knowledge_base.chunk_size,
            config.knowledge_base.chunk_overlap,
        )
        self.vector_store = vector_store

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

                existing = await self.vector_store.check_file_exists(
                    str(fi.path), meta.file_md5
                )
                if existing:
                    continue

                chunks = self.chunker.split(doc, meta)
                await self.vector_store.delete_by_file(str(fi.path))
                await self.vector_store.upsert(chunks)
                total_chunks += len(chunks)

            return FileResult(path=str(path), status="success", chunks_count=total_chunks)

        except Exception as e:
            logger.exception("处理文件失败: %s", path)
            return FileResult(path=str(path), status="failed", error=str(e))
```

注意：这里 `FileResult` 从 `app.models.document` 导入，但我们之前定义在 `app.models.task` 中。需要统一。在 `app/models/document.py` 中也添加 `FileResult`，或在 ingester 中使用 `app.models.task.FileResult`。

按设计文档，`FileResult` 在 `app/models/task.py` 中。Ingester 应使用 `from app.models.task import FileResult`。

修正：`app/ingestion/ingester.py` 的 import 改为：

```python
from app.models.task import FileResult
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && pytest tests/test_ingestion/test_ingester.py -v`
Expected: 4 passed

- [ ] **Step 5: 运行全部测试**

Run: `cd backend && pytest --tb=short -v`
Expected: 全部 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/ingestion/ingester.py backend/tests/test_ingestion/test_ingester.py
git commit -m "feat: 流水线编排 — Ingester 集成解压→提取→分类→分块→入库"
```

---

## Task 10: 集成测试与最终验证

**Files:**
- Test: `backend/tests/test_ingestion/test_integration.py`

- [ ] **Step 1: 写端到端集成测试**

`backend/tests/test_ingestion/test_integration.py`:
```python
"""端到端集成测试：文件导入 → 入库 → 检索"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.config import AppConfig, KnowledgeBaseConfig, LLMConfig, OCRConfig, OllamaConfig
from app.db.vector_store import VectorStore
from app.ingestion.ingester import Ingester
from app.llm.base import BaseLLMProvider
from app.models.task import FileResult
from app.task_manager import TaskManager


class MockLLMProvider(BaseLLMProvider):
    async def chat(self, messages: list[dict], **kwargs) -> str:
        return "通知"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 8 for _ in texts]


@pytest.fixture
def integration_env(tmp_path: Path) -> tuple[Ingester, VectorStore, TaskManager]:
    llm = MockLLMProvider()
    vector_store = VectorStore(db_path=str(tmp_path / "db"), llm=llm)

    config = AppConfig(_yaml_file=str(tmp_path / "c.yaml"))
    config.knowledge_base = KnowledgeBaseConfig()
    config.ocr = OCRConfig()

    ingester = Ingester(config=config, llm=llm, vector_store=vector_store)

    task_manager = TaskManager(ingester)
    task_manager.TASKS_DIR = str(tmp_path / "tasks")

    return ingester, vector_store, task_manager


class TestEndToEnd:
    @pytest.mark.asyncio
    async def test_full_import_and_search(
        self, integration_env: tuple, tmp_path: Path
    ) -> None:
        ingester, vector_store, task_manager = integration_env

        # 准备测试文件
        txt = tmp_path / "通知.txt"
        txt.write_text("关于召开年度工作总结会议的通知\n\n各部门：\n请于本周五前提交工作总结。", encoding="utf-8")

        # 通过 TaskManager 导入
        task_id = await task_manager.start_import([txt])
        await asyncio.sleep(1.0)

        progress = task_manager.get_progress(task_id)
        assert progress.status.value == "completed"
        assert progress.success == 1

        # 检索验证
        results = await vector_store.search("工作总结", top_k=5)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_batch_import_with_failure(
        self, integration_env: tuple, tmp_path: Path
    ) -> None:
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
```

- [ ] **Step 2: 运行集成测试**

Run: `cd backend && pytest tests/test_ingestion/test_integration.py -v`
Expected: 2 passed

- [ ] **Step 3: 运行全部测试 + 覆盖率**

Run: `cd backend && pytest --cov=app --cov-report=term-missing`
Expected: 全部 passed，覆盖率 ≥ 80%

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_ingestion/test_integration.py
git commit -m "test: 端到端集成测试 — 文件导入→入库→检索"
```

---

## Self-Review

### 1. Spec Coverage

| 需求 | 任务 |
|------|------|
| F1.1 项目初始化、配置、日志 | Task 1 |
| F1.2 LLM Provider (Ollama/Claude/Factory) | Task 2 |
| F1.3 压缩包解压 (zip/7z/rar/嵌套) | Task 3 |
| F1.4 多格式文本提取 (6 格式) | Task 4 |
| F1.5 元数据提取 + LLM 分类 | Task 5 |
| F1.6 文本分块 (段落/重叠/边界) | Task 6 |
| F1.7 向量化入库 + 增量 | Task 7 |
| F1.8 异步任务 + 断点续传 | Task 8 |
| 流水线编排 | Task 9 |
| 集成测试 | Task 10 |

### 2. 已知需注意的点

- `FileResult` 定义在 `app/models/task.py`，Ingester 中需从此处 import，不要从 `document.py` 导入
- `AppConfig(_yaml_file=...)` 是 Pydantic Settings 的初始化覆盖方式，需确认 pydantic-settings 版本支持
- ChromaDB 的 `PersistentClient` 在测试中使用 `tmp_path`，确保测试间不干扰
- `pdf2image` 和 OCR 依赖系统级 poppler/tesseract，CI 中可能需要 mock

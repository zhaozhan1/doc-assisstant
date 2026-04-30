# 阶段一分项技术方案 — 项目基础 + 文档解析

**版本**: v1.0
**日期**: 2026-04-30
**状态**: 待确认
**关联文档**: [功能点拆分](2026-04-30-feature-01-project-init-ingestion.md) | [技术选型方案](../deliverable/2026-04-30-tech-overview.md)

---

## 一、核心设计决策

| # | 决策点 | 方案 | 理由 |
|---|--------|------|------|
| 1 | LLM 调用模式 | 纯 async（httpx.AsyncClient / AsyncAnthropic） | 匹配 FastAPI 异步模型，不阻塞事件循环 |
| 2 | 流水线编排 | 简单顺序函数调用，不做 Pipeline/Middleware 抽象 | 单用户、串行依赖，YAGNI |
| 3 | 异步任务管理 | 内存 dict + JSON 文件持久化（逐文件记录状态） | 支持断点续传，轻量级 |
| 4 | 向量数据库 | ChromaDB 单 collection `documents`，元数据过滤 | 5000 文档规模单 collection 足够，查询简单 |
| 5 | 配置管理 | Pydantic Settings + YAML | 自动校验、类型提示、FastAPI 原生集成 |

---

## 二、项目骨架（F1.1）

### 2.1 目录结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI 入口
│   ├── config.py                   # AppConfig (Pydantic Settings)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── document.py             # ExtractedDoc, FileResult, IngestResult
│   │   ├── chunk.py                # Chunk
│   │   └── task.py                 # TaskProgress, TaskStatus
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── decompressor.py         # F1.3
│   │   ├── extractor.py            # F1.4
│   │   ├── classifier.py           # F1.5
│   │   ├── chunker.py              # F1.6
│   │   └── ingester.py             # 流水线编排
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseLLMProvider
│   │   ├── ollama_provider.py      # Ollama 实现
│   │   ├── claude_provider.py      # Claude 实现
│   │   └── factory.py              # create_provider()
│   ├── db/
│   │   ├── __init__.py
│   │   └── vector_store.py         # ChromaDB 封装
│   └── task_manager.py             # F1.8 异步任务管理
├── tests/
│   ├── conftest.py                 # 共享 fixtures
│   ├── test_config.py
│   ├── test_llm/
│   │   ├── test_base.py
│   │   ├── test_ollama_provider.py
│   │   ├── test_claude_provider.py
│   │   └── test_factory.py
│   ├── test_ingestion/
│   │   ├── test_decompressor.py
│   │   ├── test_extractor.py
│   │   ├── test_classifier.py
│   │   ├── test_chunker.py
│   │   └── test_ingester.py
│   ├── test_db/
│   │   └── test_vector_store.py
│   └── test_task_manager.py
├── config.yaml
├── environment.yml
├── pyproject.toml
└── logs/                           # 日志输出目录
```

### 2.2 配置管理

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

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

class OCRConfig(BaseModel):
    tesseract_cmd: str = ""  # 空则使用系统默认

class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "./logs/app.log"

class LLMConfig(BaseModel):
    default_provider: Literal["ollama", "claude"] = "ollama"
    providers: dict[str, OllamaConfig | ClaudeConfig]

class AppConfig(BaseSettings):
    knowledge_base: KnowledgeBaseConfig
    llm: LLMConfig
    ocr: OCRConfig
    logging: LoggingConfig

    model_config = SettingsConfigDict(yaml_file="config.yaml")
```

读取方式：`AppConfig.from_yaml("config.yaml")`，Pydantic 自动校验类型和约束。修改配置需重启生效。

### 2.3 日志

使用 Python 标准 `logging` 模块，在 `main.py` 启动时初始化：

- 控制台输出（INFO 级别）
- 文件输出（DEBUG 级别，`logs/app.log`，按 10MB 轮转，保留 5 个备份）
- 格式：`%(asctime)s [%(levelname)s] %(name)s — %(message)s`

---

## 三、LLM Provider 抽象层（F1.2）

### 3.1 接口定义

```python
# app/llm/base.py
class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> str:
        """对话接口。messages 格式: [{"role": "user", "content": "..."}]"""
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """批量文本向量化。返回与输入等长的向量列表。"""
        ...

    async def classify(self, text: str, labels: list[str]) -> str:
        """零样本分类。默认实现通过 chat + prompt 模板完成，子类可覆盖。"""
        prompt = f"请从以下类别中选择最匹配的一个：{', '.join(labels)}\n\n文本内容：\n{text[:500]}\n\n只返回类别名称，不要解释。"
        response = await self.chat([{"role": "user", "content": prompt}])
        # 模糊匹配最接近的 label
        return self._match_label(response.strip(), labels)

    @staticmethod
    def _match_label(response: str, labels: list[str]) -> str:
        """从 LLM 响应中提取匹配的标签，支持模糊匹配。"""
        response = response.strip()
        for label in labels:
            if label in response:
                return label
        return labels[-1]  # 默认返回最后一个（通常是"其他"）
```

**设计要点**：
- `chat` 和 `embed` 是原子能力，必须由子类实现
- `classify` 基于 `chat` 的默认实现，Ollama 和 Claude 无需各自实现分类逻辑
- 所有接口纯 async，不阻塞事件循环

### 3.2 Ollama Provider

```python
# app/llm/ollama_provider.py
class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: str, chat_model: str, embed_model: str):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=120.0)
        self._chat_model = chat_model
        self._embed_model = embed_model

    async def chat(self, messages: list[dict], **kwargs) -> str:
        resp = await self._client.post("/api/chat", json={
            "model": self._chat_model,
            "messages": messages,
            "stream": False,
        })
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.post("/api/embed", json={
            "model": self._embed_model,
            "input": texts,
        })
        resp.raise_for_status()
        return [item["embedding"] for item in resp.json()["embeddings"]]
```

### 3.3 Claude Provider

```python
# app/llm/claude_provider.py
class ClaudeProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str, chat_model: str):
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
        # Claude 无原生 embed 接口，回退到 Ollama embed
        raise NotImplementedError("Claude 不支持 embedding，请配置 Ollama 作为 embed Provider")
```

**注意**：Claude 无 embedding 能力，`embed()` 抛出 `NotImplementedError`。后续可支持 embed 用 Ollama、chat 用 Claude 的混合配置，但 Phase 1 不做。

### 3.4 工厂

```python
# app/llm/factory.py
def create_provider(config: LLMConfig) -> BaseLLMProvider:
    provider_name = config.default_provider
    provider_config = config.providers[provider_name]
    if provider_name == "ollama":
        return OllamaProvider(
            base_url=provider_config.base_url,
            chat_model=provider_config.chat_model,
            embed_model=provider_config.embed_model,
        )
    elif provider_name == "claude":
        return ClaudeProvider(
            api_key=provider_config.api_key,
            base_url=provider_config.base_url,
            chat_model=provider_config.chat_model,
        )
    raise ValueError(f"未知 Provider: {provider_name}")
```

---

## 四、压缩包解压与文件格式识别（F1.3）

### 4.1 格式映射

```python
SUPPORTED_FORMATS = {
    ".docx", ".pdf", ".xlsx", ".pptx", ".png", ".jpg", ".jpeg", ".txt",
}
ARCHIVE_FORMATS = {".zip", ".rar", ".7z"}
```

### 4.2 解压器

```python
# app/ingestion/decompressor.py
@dataclass
class FileInfo:
    path: Path                    # 文件实际路径
    format: str                   # 扩展名（小写，如 ".docx"）
    original_archive: Path | None # 来自哪个压缩包（顶层文件为 None）

class Decompressor:
    def extract(self, path: Path) -> list[FileInfo]:
        """解压压缩包（递归），或直接返回单文件信息。"""
        if path.is_dir():
            return self._scan_directory(path)
        if path.suffix.lower() in ARCHIVE_FORMATS:
            return self._extract_archive(path, depth=0)
        if path.suffix.lower() in SUPPORTED_FORMATS:
            return [FileInfo(path=path, format=path.suffix.lower(), original_archive=None)]
        return []  # 不支持的格式，静默跳过

    def _extract_archive(self, archive_path: Path, depth: int) -> list[FileInfo]:
        if depth > 5:
            logger.warning(f"嵌套深度超限: {archive_path}")
            return []
        extract_dir = tempfile.mkdtemp()
        self._do_extract(archive_path, extract_dir)  # zipfile/py7zr/pyunpack 按后缀分派
        # zipfile 用内置库, .7z 用 py7zr, .rar 用 pyunpack
        results = []
        for f in Path(extract_dir).rglob("*"):
            if f.suffix.lower() in ARCHIVE_FORMATS:
                results.extend(self._extract_archive(f, depth + 1))
            elif f.suffix.lower() in SUPPORTED_FORMATS:
                results.append(FileInfo(path=f, format=f.suffix.lower(), original_archive=archive_path))
        return results
```

---

## 五、多格式文档文本提取（F1.4）

### 5.1 统一输出数据结构

```python
# app/models/document.py
@dataclass
class StructureItem:
    level: int          # 标题层级：1=一级标题, 2=二级标题, ...
    text: str           # 标题文本
    position: int       # 在正文中的字符偏移

@dataclass
class ExtractedDoc:
    text: str                        # 纯文本
    structure: list[StructureItem]   # 标题层级信息
    metadata: dict                   # 提取器附加信息（如页数、表格数等）
    source_path: Path                # 源文件路径
```

### 5.2 提取器

```python
# app/ingestion/extractor.py
class Extractor:
    def __init__(self, ocr_config: OCRConfig):
        self._handlers: dict[str, Callable[[Path], ExtractedDoc]] = {
            ".docx": self._extract_docx,
            ".pdf":  self._extract_pdf,
            ".xlsx": self._extract_xlsx,
            ".pptx": self._extract_pptx,
            ".png":  self._extract_image,
            ".jpg":  self._extract_image,
            ".jpeg": self._extract_image,
            ".txt":  self._extract_txt,
        }
        self._tesseract_cmd = ocr_config.tesseract_cmd or "tesseract"

    def extract(self, file_info: FileInfo) -> ExtractedDoc:
        handler = self._handlers.get(file_info.format)
        if not handler:
            raise ValueError(f"不支持的格式: {file_info.format}")
        return handler(file_info.path)
```

各格式提取逻辑：
- **docx**：`python-docx`，遍历 paragraphs + tables，识别 Heading 样式为 structure
- **pdf**：`pdfplumber` 提取文本层；文本为空或过短时 fallback 到 `pytesseract` OCR
- **xlsx**：`openpyxl`，逐 sheet 逐行读取，转为 "表头: 值1, 值2..." 的文本描述
- **pptx**：`python-pptx`，提取每页 slide 的 title + text + notes
- **png/jpg**：`pytesseract` + 中文语言包 `chi_sim`
- **txt**：`open()` 直接读取，UTF-8 优先，fallback GB18030

---

## 六、元数据提取与文档分类（F1.5）

### 6.1 元数据提取

```python
@dataclass
class DocumentMetadata:
    file_name: str
    source_path: str
    import_time: datetime
    doc_date: datetime | None      # 从文档内容/文件名提取的日期
    doc_type: str                   # 分类标签
    file_md5: str                   # 用于增量更新判断

class MetadataExtractor:
    _DATE_PATTERNS = [
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
        r"(\d{4})-(\d{2})-(\d{2})",
        r"(\d{4})(\d{2})(\d{2})",          # 文件名中的 YYYYMMDD
    ]

    def extract(self, doc: ExtractedDoc) -> DocumentMetadata:
        doc_date = self._extract_date(doc.text) or self._extract_date_from_path(doc.source_path)
        file_md5 = self._compute_md5(doc.source_path)
        return DocumentMetadata(
            file_name=doc.source_path.name,
            source_path=str(doc.source_path),
            import_time=datetime.now(),
            doc_date=doc_date,
            doc_type="",  # 由 Classifier 填充
            file_md5=file_md5,
        )
```

### 6.2 分类器

```python
DOC_TYPES = [
    "通知", "公告", "请示", "报告", "方案", "规划",
    "会议纪要", "合同", "工作总结", "领导讲话稿", "调研报告", "汇报PPT", "其他",
]

class Classifier:
    def __init__(self, llm: BaseLLMProvider):
        self._llm = llm

    async def classify(self, text: str) -> str:
        result = await self._llm.classify(text[:500], DOC_TYPES)
        if result not in DOC_TYPES:
            return "其他"
        return result
```

---

## 七、文本分块（F1.6）

### 7.1 分块器

```python
# app/models/chunk.py
@dataclass
class Chunk:
    text: str
    source_file: str         # 来源文件路径
    chunk_index: int         # 块序号（从 0 开始）
    metadata: dict           # 包含 doc_type, doc_date 等

# app/ingestion/chunker.py
class Chunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def split(self, doc: ExtractedDoc, meta: DocumentMetadata) -> list[Chunk]:
        paragraphs = self._split_by_paragraph(doc.text)
        chunks = self._merge_paragraphs(paragraphs)
        return [
            Chunk(
                text=chunk_text,
                source_file=str(doc.source_path),
                chunk_index=i,
                metadata={"doc_type": meta.doc_type, "doc_date": str(meta.doc_date), "file_name": meta.file_name},
            )
            for i, chunk_text in enumerate(chunks)
        ]
```

分块策略：
1. 先按段落（`\n\n` 或空行）拆分
2. 将短段落合并，直到达到 `chunk_size`（400-600 字）
3. 相邻块之间保留 `chunk_overlap` 字符重叠
4. 超长段落（> chunk_size）强制按句子切分
5. 超短文本（< 50 字）作为单块保留

---

## 八、向量化与入库（F1.7）

### 8.1 向量存储封装

```python
# app/db/vector_store.py
class VectorStore:
    def __init__(self, db_path: str, llm: BaseLLMProvider):
        self._client = chromadb.PersistentClient(path=db_path)
        self._collection = self._client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"},
        )
        self._llm = llm

    async def upsert(self, chunks: list[Chunk]) -> None:
        """向量化并入库。按文件去重：已有同 file_md5 的数据先删除再插入。"""
        if not chunks:
            return
        embeddings = await self._llm.embed([c.text for c in chunks])
        ids = [f"{c.source_file}::{c.chunk_index}" for c in chunks]
        metadatas = [c.metadata for c in chunks]
        self._collection.upsert(ids=ids, embeddings=embeddings, documents=[c.text for c in chunks], metadatas=metadatas)

    async def delete_by_file(self, source_file: str) -> None:
        """删除指定文件的所有块。"""
        self._collection.delete(where={"source_file": source_file})

    async def search(self, query: str, top_k: int = 10, filters: dict | None = None) -> list[SearchResult]:
        """向量相似度检索。"""
        query_embedding = (await self._llm.embed([query]))[0]
        results = self._collection.query(query_embeddings=[query_embedding], n_results=top_k, where=filters)
        return [
            SearchResult(
                text=doc,
                metadata=meta,
                score=dist,
            )
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

    async def check_file_exists(self, source_file: str, file_md5: str) -> bool:
        """检查文件是否已入库且 MD5 未变（用于增量判断）。"""
        results = self._collection.get(where={"source_file": source_file})
        if not results["ids"]:
            return False
        existing_md5 = results["metadatas"][0].get("file_md5", "")
        return existing_md5 == file_md5

@dataclass
class SearchResult:
    text: str
    metadata: dict
    score: float
```

### 8.2 元数据 Schema

ChromaDB collection `documents` 的每条记录包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | `{source_file}::{chunk_index}` |
| document | str | 文本内容 |
| embedding | list[float] | 向量 |
| metadata.doc_type | str | 文档分类标签 |
| metadata.doc_date | str | 文档日期（ISO 格式） |
| metadata.file_name | str | 文件名 |
| metadata.source_file | str | 来源文件完整路径 |
| metadata.import_time | str | 导入时间 |
| metadata.file_md5 | str | 文件 MD5（用于增量判断） |

---

## 九、异步导入任务管理（F1.8）

### 9.1 数据模型

```python
# app/models/task.py
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
    pending_files: list[str] = field(default_factory=list)   # 尚未处理的文件
    created_at: str = ""
    updated_at: str = ""
```

### 9.2 任务管理器

```python
# app/task_manager.py
class TaskManager:
    TASKS_DIR = "./data/tasks"

    def __init__(self, ingester: Ingester, config: AppConfig):
        self._ingester = ingester
        self._config = config
        self._tasks: dict[str, TaskProgress] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._load_tasks()  # 启动时从 JSON 恢复

    def get_unfinished_tasks(self) -> list[TaskProgress]:
        """返回上次未完成的任务列表（Running/Pending），供用户选择是否续传。"""
        return [t for t in self._tasks.values() if t.status in (TaskStatus.RUNNING, TaskStatus.PENDING)]

    async def start_import(self, paths: list[Path], resume_task_id: str | None = None) -> str:
        """
        启动导入任务。
        如果 resume_task_id 不为空，则从上次中断处继续。
        """
        if resume_task_id:
            task = self._tasks[resume_task_id]
            task.status = TaskStatus.RUNNING
            remaining = [Path(p) for p in task.pending_files]
        else:
            task = TaskProgress(task_id=str(uuid4()), status=TaskStatus.PENDING, ...)
            remaining = paths

        self._cancel_events[task.task_id] = asyncio.Event()
        self._save_task(task)  # 立即持久化
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

            # 从 pending_files 中移除已处理的
            task.pending_files = [str(p) for p in paths[task.processed:]]
            self._save_task(task)  # 逐文件持久化，支持断点续传

        task.status = TaskStatus.COMPLETED
        self._save_task(task)

    async def cancel_task(self, task_id: str) -> None:
        if task_id in self._cancel_events:
            self._cancel_events[task_id].set()

    def get_progress(self, task_id: str) -> TaskProgress:
        return self._tasks[task_id]

    def _save_task(self, task: TaskProgress) -> None:
        """将任务状态序列化为 JSON 文件。"""
        path = Path(self.TASKS_DIR) / f"{task.task_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(task), ensure_ascii=False, indent=2, default=str))

    def _load_tasks(self) -> None:
        """启动时从 JSON 恢复所有任务。Running 的标记为 Pending（需用户确认续传）。"""
        tasks_dir = Path(self.TASKS_DIR)
        if not tasks_dir.exists():
            return
        for f in tasks_dir.glob("*.json"):
            task = self._parse_task(f.read_text())
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.PENDING  # 未正常结束，降级为 Pending
            self._tasks[task.task_id] = task
```

### 9.3 断点续传流程

```
用户启动导入
  │
  ├─ TaskManager 检查 get_unfinished_tasks()
  │   └─ 有未完成任务 → 提示用户：
  │       ├─ "继续上次任务" → start_import(resume_task_id=xxx)
  │       │   └─ 从 pending_files 继续，已处理的 success/failed 文件不重复
  │       └─ "开始新任务" → start_import(paths)
  │           └─ 旧任务标记为 CANCELLED
  │
  └─ 无未完成任务 → 正常开始新任务
```

**关键机制**：
- 每处理完一个文件，立即更新 `pending_files` 并持久化到 JSON
- 进程崩溃后，`pending_files` 记录了剩余未处理文件的完整列表
- 重启时，Running 状态降级为 Pending，等待用户确认
- Phase 1 通过 API 返回 `get_unfinished_tasks()` 结果，Phase 4 Web UI 展示提示弹窗

---

## 十、流水线编排（Ingester）

```python
# app/ingestion/ingester.py
class Ingester:
    def __init__(self, config: AppConfig, llm: BaseLLMProvider, vector_store: VectorStore):
        self.decompressor = Decompressor()
        self.extractor = Extractor(config.ocr)
        self.metadata_extractor = MetadataExtractor()
        self.classifier = Classifier(llm)
        self.chunker = Chunker(config.knowledge_base.chunk_size, config.knowledge_base.chunk_overlap)
        self.vector_store = vector_store

    async def process_file(self, path: Path) -> FileResult:
        """处理单个文件/压缩包。异常不外泄，返回 FileResult。"""
        try:
            # F1.3: 解压 + 格式识别
            file_infos = self.decompressor.extract(path)
            if not file_infos:
                return FileResult(path=str(path), status="skipped", error="无支持的文件格式")

            total_chunks = 0
            for fi in file_infos:
                # F1.4: 文本提取
                doc = self.extractor.extract(fi)

                # F1.5: 元数据 + 分类
                meta = self.metadata_extractor.extract(doc)
                meta.doc_type = await self.classifier.classify(doc.text)

                # 增量判断：MD5 未变则跳过
                existing = await self.vector_store.check_file_exists(str(fi.path), meta.file_md5)
                if existing:
                    continue

                # F1.6: 分块
                chunks = self.chunker.split(doc, meta)

                # F1.7: 向量化入库
                await self.vector_store.delete_by_file(str(fi.path))
                await self.vector_store.upsert(chunks)
                total_chunks += len(chunks)

            return FileResult(path=str(path), status="success", chunks_count=total_chunks)

        except Exception as e:
            logger.exception(f"处理文件失败: {path}")
            return FileResult(path=str(path), status="failed", error=str(e))
```

**错误隔离**：`process_file` 外层 `try/except` 确保单文件异常不影响批次。

---

## 十一、TDD 策略

### 11.1 开发顺序（按依赖拓扑）

| 批次 | 功能点 | 依赖 | 测试重点 |
|------|--------|------|----------|
| 1 | F1.1 项目初始化 | 无 | 配置加载/校验、日志初始化 |
| 2 | F1.2 LLM Provider | F1.1 | Mock 测试接口契约、工厂选择逻辑 |
| 3a | F1.3 压缩包解压 | F1.1 | 各格式解压、嵌套、边界 |
| 3b | F1.4 文本提取 | F1.3 | 各格式提取、OCR fallback、异常文件 |
| 4 | F1.5 元数据+分类 | F1.2, F1.4 | 日期正则、LLM 分类 Mock |
| 5 | F1.6 文本分块 | F1.5 | 正常分块、边界（超短/超长） |
| 6 | F1.7 向量化入库 | F1.2, F1.6 | ChromaDB 增删查、MD5 增量 |
| 7 | F1.8 任务管理 | F1.7 | 状态流转、断点续传、取消 |
| 8 | 集成测试 | 全部 | 端到端：文件导入 → 入库 → 查询 |

### 11.2 测试原则

- **Red-Green-Refactor**：每个功能点先写失败测试，再写实现
- **Mock 策略**：LLM 调用全部 Mock（httpx/anthropic 不实际请求），ChromaDB 用临时目录
- **测试数据**：在 `tests/fixtures/` 放置各格式的样本文件（小体积）
- **覆盖率目标**：核心模块 ≥ 80%

### 11.3 关键测试场景

| 模块 | 场景 |
|------|------|
| Decompressor | 嵌套 zip、不支持的格式、损坏的压缩包 |
| Extractor | 正常 docx/pdf/xlsx/pptx/txt、扫描件 PDF 走 OCR、空文件、损坏文件 |
| Classifier | 正常分类、LLM 返回不匹配标签时 fallback 到"其他" |
| Chunker | 正常段落分块、超短文本、超长段落、空文本 |
| VectorStore | 正常入库、按文件删除、MD5 增量跳过、查询过滤 |
| TaskManager | 正常完成、单文件失败不阻塞、取消、断点续传、崩溃恢复 |

---

## 十二、依赖包清单（pyproject.toml）

```toml
[project]
name = "doc-assistant"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
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
    "pyunpack>=0.3",        # .rar 解压
    "Pillow>=10.0",         # OCR 图像处理
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "respx>=0.21",          # httpx mock
]
```

---

*本文档为阶段一分项技术方案，确认后与功能点文档一同移入 deliverable/，随后拉取功能分支开始 TDD 编码。*

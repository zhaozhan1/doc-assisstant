# 知识库文件列表日期优化 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将文件列表的"日期"列拆分为"创建日期"(OS 文件创建时间) 和"入库日期"(import_time)，默认按入库日期倒序排列。

**Architecture:** 后端在入库时捕获 OS 文件创建时间并存入 ChromaDB 元数据；API 返回 ISO 时间戳；前端用 dayjs 格式化为 YYYY-MM-DD 展示。同时修复 `update_file_metadata` 全量覆盖 bug。

**Tech Stack:** Python/FastAPI 后端, React/Ant Design 前端, ChromaDB 向量库, dayjs 日期格式化

---

### Task 1: DocumentMetadata 新增 `file_created_time` 字段

**Files:**
- Modify: `backend/app/models/document.py:31-37`
- Test: `backend/tests/test_ingestion/test_classifier.py` (已有)

- [ ] **Step 1: 在 DocumentMetadata 新增字段**

在 `backend/app/models/document.py` 的 `DocumentMetadata` dataclass 中，在 `file_md5` 之后新增 `file_created_time` 字段：

```python
@dataclass
class DocumentMetadata:
    file_name: str
    source_path: str
    import_time: datetime
    doc_date: datetime | None = None
    doc_type: str = ""
    file_md5: str = ""
    file_created_time: datetime | None = None
```

- [ ] **Step 2: 运行现有测试确认无破坏**

Run: `cd backend && pytest tests/test_ingestion/test_classifier.py -v`
Expected: 全部 PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/document.py
git commit -m "feat: DocumentMetadata 新增 file_created_time 字段"
```

---

### Task 2: MetadataExtractor 捕获 OS 文件创建时间

**Files:**
- Modify: `backend/app/ingestion/classifier.py:41-51`
- Test: `backend/tests/test_ingestion/test_classifier.py`

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_ingestion/test_classifier.py` 的 `TestMetadataExtractor` 类末尾新增：

```python
def test_extracts_file_created_time(self, metadata_extractor: MetadataExtractor, tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text("test", encoding="utf-8")
    doc = ExtractedDoc(text="test", structure=[], source_path=f)
    meta = metadata_extractor.extract(doc)
    assert meta.file_created_time is not None
    assert isinstance(meta.file_created_time, datetime)

def test_file_created_time_none_for_missing_file(self, metadata_extractor: MetadataExtractor, tmp_path: Path) -> None:
    """如果文件已被删除，file_created_time 应为 None。"""
    f = tmp_path / "gone.txt"
    f.write_text("test", encoding="utf-8")
    doc = ExtractedDoc(text="test", structure=[], source_path=f)
    f.unlink()
    meta = metadata_extractor.extract(doc)
    assert meta.file_created_time is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_ingestion/test_classifier.py::TestMetadataExtractor::test_extracts_file_created_time -v`
Expected: FAIL (AttributeError 或 assert None)

- [ ] **Step 3: 实现最小代码**

在 `backend/app/ingestion/classifier.py` 的 `MetadataExtractor` 类中新增方法，并在 `extract()` 中调用：

```python
def _get_file_created_time(self, path: Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(path.stat().st_birthtime)
    except (OSError, AttributeError):
        return None
```

在 `extract()` 方法中，`file_md5` 行之后新增：

```python
file_created_time = self._get_file_created_time(doc.source_path),
```

并在 `DocumentMetadata(...)` 构造中加上 `file_created_time=file_created_time`：

```python
def extract(self, doc: ExtractedDoc) -> DocumentMetadata:
    doc_date = self._extract_date(doc.text) or self._extract_date_from_path(doc.source_path)
    file_md5 = self._compute_md5(doc.source_path)
    file_created_time = self._get_file_created_time(doc.source_path)
    return DocumentMetadata(
        file_name=doc.source_path.name,
        source_path=str(doc.source_path),
        import_time=datetime.now(),
        doc_date=doc_date,
        doc_type="",
        file_md5=file_md5,
        file_created_time=file_created_time,
    )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && pytest tests/test_ingestion/test_classifier.py -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/ingestion/classifier.py backend/tests/test_ingestion/test_classifier.py
git commit -m "feat: MetadataExtractor 捕获 OS 文件创建时间"
```

---

### Task 3: Chunker 传递 `file_created_time` 到 chunk 元数据

**Files:**
- Modify: `backend/app/ingestion/chunker.py:24-28`
- Test: `backend/tests/test_ingestion/test_chunker.py`

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_ingestion/test_chunker.py` 的 `TestNormalChunking` 类中新增测试（需在 `sample_meta` fixture 中添加 `file_created_time`）：

先更新 fixture：

```python
@pytest.fixture
def sample_meta() -> DocumentMetadata:
    return DocumentMetadata(
        file_name="test.txt",
        source_path="/tmp/test.txt",
        import_time=datetime.now(),
        doc_type="通知",
        doc_date=datetime(2024, 1, 1),
        file_created_time=datetime(2024, 1, 1, 10, 30, 0),
    )
```

在 `TestNormalChunking` 中新增：

```python
def test_chunk_metadata_file_created_time(self, chunker: Chunker, sample_meta: DocumentMetadata) -> None:
    doc = _make_doc("测试内容")
    chunks = chunker.split(doc, sample_meta)
    assert chunks[0].metadata["file_created_time"] == "2024-01-01T10:30:00"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_ingestion/test_chunker.py::TestNormalChunking::test_chunk_metadata_file_created_time -v`
Expected: FAIL (KeyError)

- [ ] **Step 3: 实现最小代码**

在 `backend/app/ingestion/chunker.py` 的 `split()` 方法中，metadata dict 新增一行：

```python
metadata={
    "doc_type": meta.doc_type,
    "doc_date": meta.doc_date.isoformat() if meta.doc_date else "",
    "file_name": meta.file_name,
    "file_created_time": meta.file_created_time.isoformat() if meta.file_created_time else "",
},
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && pytest tests/test_ingestion/test_chunker.py -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/ingestion/chunker.py backend/tests/test_ingestion/test_chunker.py
git commit -m "feat: Chunker 传递 file_created_time 到 chunk 元数据"
```

---

### Task 4: 修复 `update_file_metadata` 全量覆盖 bug

**Files:**
- Modify: `backend/app/db/vector_store.py:85-92`
- Test: `backend/tests/test_db/test_vector_store.py`

- [ ] **Step 1: 写失败测试**

在 `backend/tests/test_db/test_vector_store.py` 的 `TestUpdateFileMetadata` 类中新增：

```python
@pytest.mark.asyncio
async def test_merges_with_existing_metadata(
    self, vs_with_mock_collection: VectorStore, mock_collection: MagicMock
) -> None:
    """update_file_metadata 应合并而非覆盖全部元数据。"""
    mock_collection.get.return_value = {
        "ids": ["a.txt::0"],
        "metadatas": [{"source_file": "a.txt", "file_md5": "abc", "import_time": "2025-01-01T00:00:00"}],
    }

    await vs_with_mock_collection.update_file_metadata("a.txt", {"doc_type": "通知"})

    call_args = mock_collection.update.call_args
    merged_meta = call_args.kwargs["metadatas"][0]
    assert merged_meta["doc_type"] == "通知"
    assert merged_meta["file_md5"] == "abc"
    assert merged_meta["import_time"] == "2025-01-01T00:00:00"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_db/test_vector_store.py::TestUpdateFileMetadata::test_merges_with_existing_metadata -v`
Expected: FAIL (merged_meta 只含 `{"doc_type": "通知"}`，缺少 `file_md5` 和 `import_time`)

- [ ] **Step 3: 实现修复**

在 `backend/app/db/vector_store.py` 的 `update_file_metadata` 方法中，将全量覆盖改为合并更新：

```python
async def update_file_metadata(self, source_file: str, updates: dict) -> None:
    results = self._collection.get(where={"source_file": source_file})
    if not results["ids"]:
        return
    existing = results.get("metadatas") or [{}] * len(results["ids"])
    merged = [{**meta, **updates} for meta in existing]
    self._collection.update(
        ids=results["ids"],
        metadatas=merged,
    )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && pytest tests/test_db/test_vector_store.py -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/vector_store.py backend/tests/test_db/test_vector_store.py
git commit -m "fix: update_file_metadata 改为合并更新，避免丢失已有元数据"
```

---

### Task 5: IndexedFile 模型更新 + FileListRequest 排序参数更新

**Files:**
- Modify: `backend/app/models/search.py:43-58`
- Test: `backend/tests/test_retrieval/test_file_service.py` (将在 Task 6 验证)

- [ ] **Step 1: 更新 IndexedFile 和 FileListRequest**

在 `backend/app/models/search.py` 中：

`FileListRequest` — 将 `sort_by` 的默认值和选项改为 `import_date`：

```python
class FileListRequest(BaseModel):
    doc_types: list[str] = Field(default_factory=list)
    date_from: date | None = None
    date_to: date | None = None
    sort_by: Literal["file_name", "import_date", "chunk_count"] = "import_date"
    sort_order: Literal["asc", "desc"] = "desc"
```

`IndexedFile` — 移除 `doc_date`，新增 `created_date` 和 `import_date`：

```python
class IndexedFile(BaseModel):
    source_file: str
    file_name: str
    doc_type: str
    file_md5: str
    chunk_count: int
    created_date: str | None = None
    import_date: str | None = None
    duplicate_with: str | None = None
```

- [ ] **Step 2: 运行测试确认影响范围**

Run: `cd backend && pytest tests/ -v --tb=short 2>&1 | head -80`
Expected: file_service 和 file_routes 测试会失败（字段不匹配），classifier/chunker/vector_store 测试应 PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/search.py
git commit -m "feat: IndexedFile 新增 created_date/import_date，FileListRequest 排序改用 import_date"
```

---

### Task 6: FileService 读取新字段 + 排序 + 筛选

**Files:**
- Modify: `backend/app/retrieval/file_service.py:20-73`
- Test: `backend/tests/test_retrieval/test_file_service.py`

- [ ] **Step 1: 更新测试的 `_chunk` helper 和新增测试**

替换 `backend/tests/test_retrieval/test_file_service.py` 中的 `_chunk` helper，加上 `import_time` 和 `file_created_time`：

```python
def _chunk(
    source_file: str,
    file_name: str,
    doc_type: str,
    file_md5: str,
    import_time: str = "2025-01-15T10:00:00",
    file_created_time: str = "2024-12-01T08:00:00",
) -> SearchResult:
    return SearchResult(
        text="some text",
        metadata={
            "source_file": source_file,
            "file_name": file_name,
            "doc_type": doc_type,
            "file_md5": file_md5,
            "import_time": import_time,
            "file_created_time": file_created_time,
        },
        score=0.0,
    )
```

更新 `test_list_files_aggregates_by_source` 调用以适配新 `_chunk` 签名：

```python
async def test_list_files_aggregates_by_source(svc: FileService, mock_vs: AsyncMock) -> None:
    mock_vs.list_all_chunks.return_value = [
        _chunk("/data/a.docx", "a.docx", "通知", "md5_a"),
        _chunk("/data/a.docx", "a.docx", "通知", "md5_a"),
        _chunk("/data/b.docx", "b.docx", "批复", "md5_b"),
    ]

    result = await svc.list_files(FileListRequest())

    assert len(result) == 2
    by_file = {f.source_file: f for f in result}
    assert by_file["/data/a.docx"].chunk_count == 2
    assert by_file["/data/a.docx"].import_date == "2025-01-15T10:00:00"
    assert by_file["/data/a.docx"].created_date == "2024-12-01T08:00:00"
    assert by_file["/data/b.docx"].chunk_count == 1
```

更新 `test_list_files_filters_by_type`：

```python
async def test_list_files_filters_by_type(svc: FileService, mock_vs: AsyncMock) -> None:
    mock_vs.list_all_chunks.return_value = [
        _chunk("/data/a.docx", "a.docx", "通知", "md5_a"),
        _chunk("/data/b.docx", "b.docx", "批复", "md5_b"),
    ]

    result = await svc.list_files(FileListRequest(doc_types=["通知"]))

    assert len(result) == 1
    assert result[0].doc_type == "通知"
```

新增测试：

```python
async def test_list_files_sorts_by_import_date_desc(svc: FileService, mock_vs: AsyncMock) -> None:
    mock_vs.list_all_chunks.return_value = [
        _chunk("/data/a.docx", "a.docx", "通知", "md5_a", import_time="2025-01-01T00:00:00"),
        _chunk("/data/b.docx", "b.docx", "批复", "md5_b", import_time="2025-06-01T00:00:00"),
    ]

    result = await svc.list_files(FileListRequest())

    assert result[0].source_file == "/data/b.docx"
    assert result[1].source_file == "/data/a.docx"


async def test_list_files_filters_by_import_date_range(svc: FileService, mock_vs: AsyncMock) -> None:
    mock_vs.list_all_chunks.return_value = [
        _chunk("/data/a.docx", "a.docx", "通知", "md5_a", import_time="2025-01-15T00:00:00"),
        _chunk("/data/b.docx", "b.docx", "批复", "md5_b", import_time="2025-06-15T00:00:00"),
    ]

    result = await svc.list_files(
        FileListRequest(date_from=date(2025, 6, 1), date_to=date(2025, 6, 30))
    )

    assert len(result) == 1
    assert result[0].source_file == "/data/b.docx"


async def test_list_files_old_data_created_date_none(svc: FileService, mock_vs: AsyncMock) -> None:
    """旧数据无 file_created_time，created_date 应为 None。"""
    mock_vs.list_all_chunks.return_value = [
        _chunk("/data/old.docx", "old.docx", "通知", "md5_old", file_created_time=""),
    ]

    result = await svc.list_files(FileListRequest())

    assert result[0].created_date is None
    assert result[0].import_date is not None
```

在文件顶部新增 import：

```python
from datetime import date
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_retrieval/test_file_service.py -v`
Expected: FAIL（`import_date`/`created_date` 字段不存在）

- [ ] **Step 3: 实现 FileService 变更**

在 `backend/app/retrieval/file_service.py` 中更新 `list_files`、`_filter`、`_sort`：

```python
async def list_files(self, request: FileListRequest) -> list[IndexedFile]:
    all_chunks = await self._vs.list_all_chunks(include_documents=False)
    groups: dict[str, list] = defaultdict(list)
    for chunk in all_chunks:
        src = chunk.metadata.get("source_file", "")
        if src:
            groups[src].append(chunk)

    files = []
    for src, chunks in groups.items():
        meta = chunks[0].metadata
        files.append(
            IndexedFile(
                source_file=src,
                file_name=meta.get("file_name", ""),
                doc_type=meta.get("doc_type", ""),
                file_md5=meta.get("file_md5", ""),
                chunk_count=len(chunks),
                created_date=meta.get("file_created_time") or None,
                import_date=meta.get("import_time") or None,
            )
        )

    files = self._filter(files, request)
    files = self._sort(files, request)
    return files
```

更新 `_filter` — 按入库日期筛选：

```python
def _filter(self, files: list[IndexedFile], request: FileListRequest) -> list[IndexedFile]:
    result = files
    if request.doc_types:
        result = [f for f in result if f.doc_type in request.doc_types]
    if request.date_from:
        date_from_str = request.date_from.isoformat()
        result = [f for f in result if f.import_date and f.import_date >= date_from_str]
    if request.date_to:
        date_to_str = request.date_to.isoformat()
        result = [f for f in result if f.import_date and f.import_date <= date_to_str]
    return result
```

更新 `_sort` — 支持 `import_date` 排序：

```python
def _sort(self, files: list[IndexedFile], request: FileListRequest) -> list[IndexedFile]:
    if request.sort_by == "chunk_count":
        return sorted(files, key=lambda f: f.chunk_count, reverse=request.sort_order == "desc")
    key = request.sort_by
    return sorted(files, key=lambda f: getattr(f, key) or "", reverse=request.sort_order == "desc")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && pytest tests/test_retrieval/test_file_service.py -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/retrieval/file_service.py backend/tests/test_retrieval/test_file_service.py
git commit -m "feat: FileService 读取 created_date/import_date，按入库日期排序筛选"
```

---

### Task 7: API 路由更新

**Files:**
- Modify: `backend/app/api/routes/files.py:31`
- Test: `backend/tests/test_api/test_file_routes.py`

- [ ] **Step 1: 更新路由参数**

在 `backend/app/api/routes/files.py` 中更新 `list_files` 的 `sort_by` 参数：

```python
@router.get("", response_model=list[IndexedFile])
async def list_files(
    doc_types: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: Literal["file_name", "import_date", "chunk_count"] = "import_date",
    sort_order: Literal["asc", "desc"] = "desc",
    file_service: FileService = _file_service_dep,
) -> list[IndexedFile]:
```

- [ ] **Step 2: 更新 API 测试**

更新 `backend/tests/test_api/test_file_routes.py` 中的 fixture，将 `IndexedFile` 替换为新字段：

```python
mock_file_service.list_files.return_value = [
    IndexedFile(
        source_file="/a.docx",
        file_name="a.docx",
        doc_type="通知",
        file_md5="abc",
        chunk_count=3,
        created_date="2024-12-01T08:00:00",
        import_date="2025-01-15T10:00:00",
    )
]
```

更新 `test_list_files` 断言：

```python
def test_list_files(client: TestClient) -> None:
    response = client.get("/api/files")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["file_name"] == "a.docx"
    assert data[0]["doc_type"] == "通知"
    assert data[0]["created_date"] == "2024-12-01T08:00:00"
    assert data[0]["import_date"] == "2025-01-15T10:00:00"
```

- [ ] **Step 3: 运行测试确认通过**

Run: `cd backend && pytest tests/test_api/test_file_routes.py -v`
Expected: 全部 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/routes/files.py backend/tests/test_api/test_file_routes.py
git commit -m "feat: API 路由 sort_by 改为 import_date，默认倒序"
```

---

### Task 8: 后端全量测试验证

**Files:** 无新变更

- [ ] **Step 1: 运行后端全量测试**

Run: `cd backend && pytest -n 10 -v`
Expected: 全部 PASS

- [ ] **Step 2: 运行 lint 检查**

Run: `cd backend && ruff check app/ tests/ && ruff format --check app/ tests/`
Expected: 无错误

---

### Task 9: 前端类型定义更新

**Files:**
- Modify: `frontend/src/types/api.ts`

- [ ] **Step 1: 安装 dayjs**

Run: `cd frontend && pnpm add dayjs`

- [ ] **Step 2: 更新类型定义**

在 `frontend/src/types/api.ts` 中更新 `IndexedFile` 接口：

```typescript
export interface IndexedFile {
  source_file: string;
  file_name: string;
  doc_type: string;
  file_md5: string;
  chunk_count: number;
  created_date: string | null;
  import_date: string | null;
  duplicate_with: string | null;
}
```

更新 `FileListParams` 的 `sort_by` 类型：

```typescript
export interface FileListParams {
  doc_types?: string;
  date_from?: string;
  date_to?: string;
  sort_by?: "file_name" | "import_date" | "chunk_count";
  sort_order?: "asc" | "desc";
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/api.ts frontend/package.json frontend/pnpm-lock.yaml
git commit -m "feat: 前端类型定义更新，安装 dayjs"
```

---

### Task 10: 前端知识库列表组件更新

**Files:**
- Modify: `frontend/src/pages/KnowledgeBase/index.tsx`

- [ ] **Step 1: 更新排序常量**

在 `frontend/src/pages/KnowledgeBase/index.tsx` 中：

更新顶部 import，新增 dayjs：

```typescript
import dayjs from "dayjs";
```

替换 `SORT_OPTIONS` 和 `SORT_MAP`：

```typescript
const SORT_OPTIONS: { label: string; value: string }[] = [
  { label: "最近入库", value: "import_date_desc" },
  { label: "文件名", value: "file_name_asc" },
  { label: "分块数 ↓", value: "chunk_count_desc" },
];

const SORT_MAP: Record<
  string,
  { sort_by: FileListParams["sort_by"]; sort_order: "asc" | "desc" }
> = {
  import_date_desc: { sort_by: "import_date", sort_order: "desc" },
  import_date_asc: { sort_by: "import_date", sort_order: "asc" },
  file_name_asc: { sort_by: "file_name", sort_order: "asc" },
  file_name_desc: { sort_by: "file_name", sort_order: "desc" },
  chunk_count_desc: { sort_by: "chunk_count", sort_order: "desc" },
};
```

更新默认排序 state：

```typescript
const [sortValue, setSortValue] = useState("import_date_desc");
```

- [ ] **Step 2: 更新表格列定义**

替换 columns 中的"日期"列为两列：

```typescript
const columns: ColumnsType<IndexedFile> = [
  {
    title: "文件名",
    dataIndex: "file_name",
    key: "file_name",
    ellipsis: true,
  },
  {
    title: "类型",
    dataIndex: "doc_type",
    key: "doc_type",
    width: 100,
    render: (docType: string) => (
      <Tag color={TAG_COLOR_MAP[docType] || "default"}>{docType}</Tag>
    ),
  },
  {
    title: "创建日期",
    dataIndex: "created_date",
    key: "created_date",
    width: 110,
    render: (date: string | null) => (date ? dayjs(date).format("YYYY-MM-DD") : "-"),
  },
  {
    title: "入库日期",
    dataIndex: "import_date",
    key: "import_date",
    width: 110,
    render: (date: string | null) => (date ? dayjs(date).format("YYYY-MM-DD") : "-"),
  },
  {
    title: "分块数",
    dataIndex: "chunk_count",
    key: "chunk_count",
    width: 80,
  },
  {
    title: "操作",
    key: "action",
    width: 260,
    render: (_: unknown, record: IndexedFile) => (
      <Space size="small">
        <Popconfirm
          title="确定重新索引该文件吗？"
          onConfirm={() => handleReindex(record.source_file)}
          okText="确 定"
          cancelText="取 消"
        >
          <Button type="link" size="small">
            重新索引
          </Button>
        </Popconfirm>
        <Popconfirm
          title="确定删除该文件吗？"
          onConfirm={() => handleDelete(record.source_file)}
          okText="确 定"
          cancelText="取 消"
        >
          <Button type="link" size="small" danger>
            删除
          </Button>
        </Popconfirm>
        <Select
          size="small"
          value={record.doc_type}
          style={{ width: 80 }}
          onChange={(value: string) =>
            handleClassificationChange(record.source_file, value)
          }
          options={DOC_TYPE_OPTIONS.map((t) => ({ label: t, value: t }))}
        />
      </Space>
    ),
  },
];
```

- [ ] **Step 3: 运行前端 lint**

Run: `cd frontend && pnpm lint`
Expected: 无错误

- [ ] **Step 4: 运行前端 build**

Run: `cd frontend && pnpm build`
Expected: 构建成功

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/KnowledgeBase/index.tsx
git commit -m "feat: 文件列表日期列拆分为创建日期+入库日期"
```

---

### Task 11: 前端全量验证 + Dev 环境联调

**Files:** 无新变更

- [ ] **Step 1: 启动后端 dev server**

Run: `cd backend && uvicorn app.main:app --reload --port 8000`

- [ ] **Step 2: 启动前端 dev server**

Run: `cd frontend && pnpm dev`

- [ ] **Step 3: 浏览器手动验证**

在浏览器中打开知识库页面，检查：
1. 列表显示"创建日期"和"入库日期"两列
2. 日期格式为 YYYY-MM-DD
3. 默认按入库日期倒序排列
4. 已有旧文件的创建日期显示"-"
5. 排序切换（入库日期/文件名/分块数）正常
6. 日期范围筛选正常
7. 分类更新后元数据不丢失（修改分类 → 刷新 → 入库日期仍存在）

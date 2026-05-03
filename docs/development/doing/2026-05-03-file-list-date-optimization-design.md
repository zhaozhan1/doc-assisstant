# 知识库文件列表日期优化

## 需求

将文件列表中的"日期"列拆分为"创建日期"和"入库日期"两列，默认按入库日期倒序排列。

### 决策记录

| 项目 | 决策 |
|---|---|
| 创建日期 | OS 文件创建时间，入库时捕获 |
| 入库日期 | 入库时间戳（现有 `import_time`） |
| doc_date | 从列表移除（搜索/检索管线中保留） |
| 日期格式 | 后端存 ISO 时间戳，前端用 `dayjs().format('YYYY-MM-DD')` 格式化 |
| 默认排序 | 入库日期倒序 |
| 排序选项 | 3 项：入库日期、文件名、分块数 |
| 旧数据 | 创建日期显示"-" |

## 设计

### 列布局（方案 A：双列并排）

| 列名 | 字段 | 宽度 | 说明 |
|---|---|---|---|
| 文件名 | `file_name` | auto | 不变 |
| 类型 | `doc_type` | 100px | 不变 |
| 创建日期 | `created_date` | 110px | 新增，OS 文件创建时间 |
| 入库日期 | `import_date` | 110px | 新增，入库时间 |
| 分块数 | `chunk_count` | 80px | 不变 |
| 操作 | — | 260px | 不变 |

### 后端变更

#### 1. DocumentMetadata 新增字段 (`models/document.py`)

- 新增 `file_created_time: datetime | None = None`

#### 2. 入库管线捕获 OS 创建时间 (`ingestion/classifier.py`)

- `MetadataExtractor.extract()` 中用 `Path.stat().st_birthtime`（macOS）获取文件创建时间
- 填入 `DocumentMetadata.file_created_time`

#### 3. Chunker 传递新字段 (`ingestion/chunker.py`)

- chunk 元数据新增 `"file_created_time": meta.file_created_time.isoformat() if meta.file_created_time else ""`

#### 4. IndexedFile 模型更新 (`models/search.py`)

```python
class IndexedFile(BaseModel):
    source_file: str
    file_name: str
    doc_type: str
    file_md5: str
    chunk_count: int
    created_date: str | None = None    # ISO 时间戳
    import_date: str | None = None     # ISO 时间戳
    duplicate_with: str | None = None
```

移除 `doc_date`。

#### 5. FileService 读取新字段 (`retrieval/file_service.py`)

- `list_files()` 从 chunk 元数据读取 `import_time` 和 `file_created_time`，透传 ISO 字符串
- `_sort()` 支持 `import_date` 排序
- 日期筛选改为按 `import_time` 筛选

#### 6. API 路由更新 (`api/routes/files.py`)

- `sort_by` 类型改为 `Literal["file_name", "import_date", "chunk_count"]`
- 默认值改为 `"import_date"`

#### 7. 修复 update_file_metadata bug (`db/vector_store.py`)

- 将全量覆盖改为合并更新，保留现有元数据字段

### 前端变更

#### 8. 类型更新 (`types/api.ts`)

- `IndexedFile`：移除 `doc_date`，新增 `created_date?: string`、`import_date?: string`
- `FileListParams.sort_by`：`"file_name" | "import_date" | "chunk_count"`

#### 9. 知识库列表组件 (`pages/KnowledgeBase/index.tsx`)

- 移除"日期"列，新增"创建日期"和"入库日期"两列
- 日期列渲染：`dayjs(value).format('YYYY-MM-DD')`，空值显示"-"
- 排序选项更新：`doc_date_desc` → `import_date_desc`，文案"最近入库"
- 日期筛选改为按入库日期筛选

### 不做的事

- 不重新提取已有文件的 OS 创建时间
- 不改动搜索/检索管线中 `doc_date` 的使用
- 不增加按"创建日期"排序的选项
- 不修改生成管线中的日期引用逻辑

### 涉及文件

**后端（7 个文件）：**
1. `backend/app/models/document.py` — DocumentMetadata 新增字段
2. `backend/app/models/search.py` — IndexedFile 模型更新
3. `backend/app/ingestion/classifier.py` — 捕获 OS 创建时间
4. `backend/app/ingestion/chunker.py` — 传递新字段到 chunk 元数据
5. `backend/app/retrieval/file_service.py` — 读取新字段、排序、筛选
6. `backend/app/api/routes/files.py` — sort_by 参数更新
7. `backend/app/db/vector_store.py` — 修复元数据覆盖 bug

**前端（2 个文件）：**
1. `frontend/src/types/api.ts` — 类型定义更新
2. `frontend/src/pages/KnowledgeBase/index.tsx` — 列表组件更新

### 测试要点

- 新入库文件：创建日期和入库日期均正确显示
- 旧数据：创建日期显示"-"，入库日期正常显示
- 默认排序为入库日期倒序
- 日期格式为 YYYY-MM-DD
- update_file_metadata 不再丢失已有元数据

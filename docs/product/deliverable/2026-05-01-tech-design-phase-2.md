# 阶段二分项技术方案 — 检索引擎 + 知识库管理

**版本**: v1.0
**日期**: 2026-05-01
**状态**: 待确认
**关联文档**: [功能点拆分](2026-04-30-feature-02-retrieval-knowledge-mgmt.md) | [技术选型方案](2026-04-30-tech-overview.md) | [阶段一技术方案](2026-04-30-tech-design-phase-1.md)

---

## 一、核心设计决策

| # | 决策点 | 方案 | 理由 |
|---|--------|------|------|
| 1 | 检索模块架构 | Facade 模式（Retriever 门面类） | 路由层简洁、组件职责清晰、易于测试 |
| 2 | 文件级元数据存储 | 复用 ChromaDB chunk 元数据聚合 | 不引入额外存储，500 文档规模内存聚合可行 |
| 3 | Embedding Provider | 分离 embed_provider / chat_provider 配置 | Ollama 始终负责 embedding，Claude 仅用于 chat，避免 Claude 无 embed() 的限制 |
| 4 | 在线搜索 | 抽象接口 + 延迟实现，配置通过 API 驱动 | 用户在中国，具体 Provider 待网络环境确定；非技术用户通过前端 UI 配置 |
| 5 | 重复文件处理 | MD5 全局去重，路径变化时更新指向 | 同一内容只保留一份向量数据，避免重复 |
| 6 | 结果融合排序 | 加权排序（本地 ×1.1），不做复杂融合算法 | 在线搜索无精确分数，RRF 等算法不适用 |
| 7 | API 层组织 | FastAPI Lifespan + Router + deps.py | 符合 FastAPI 惯例，依赖注入清晰 |

---

## 二、目录结构

```
backend/app/
├── main.py                        # 重构: lifespan 管理组件生命周期
├── config.py                      # 扩展: embed_provider 分离 + OnlineSearchConfig
├── api/
│   ├── __init__.py
│   ├── deps.py                    # FastAPI Depends 辅助函数
│   └── routes/
│       ├── __init__.py
│       ├── health.py              # 迁移 /health 端点
│       ├── ingestion.py           # F1 导入 API（阶段二补充骨架）
│       ├── retrieval.py           # F2.1-F2.3 检索 API
│       ├── files.py               # F2.4 文件管理 API
│       └── settings.py            # 在线搜索配置 API
├── retrieval/
│   ├── __init__.py
│   ├── local_search.py            # F2.1 本地向量检索
│   ├── online_search.py           # F2.2 在线检索抽象 + 工厂 + 服务
│   ├── fusion.py                  # F2.3 结果融合排序
│   └── retriever.py               # Facade: 统一检索入口
├── models/
│   ├── search.py                  # 新增: 检索相关数据模型
│   └── ...（已有）
├── db/
│   └── vector_store.py            # 扩展: list_all_chunks / update_file_metadata / find_by_md5
└── ...（已有）
```

### 测试目录

```
backend/tests/
├── test_retrieval/
│   ├── __init__.py
│   ├── test_local_search.py       # F2.1 测试
│   ├── test_online_search.py      # F2.2 测试
│   ├── test_fusion.py             # F2.3 测试
│   ├── test_retriever.py          # Facade 测试
│   └── test_file_service.py      # F2.4 测试
├── test_api/
│   ├── __init__.py
│   ├── test_retrieval_routes.py   # 检索 API 测试
│   ├── test_file_routes.py        # 文件管理 API 测试
│   └── test_settings_routes.py    # 设置 API 测试
└── test_config.py                 # 扩展: embed_provider / OnlineSearchConfig
```

---

## 三、配置扩展

### 3.1 config.yaml 变更

```yaml
llm:
  default_provider: ollama
  embed_provider: ollama          # 新增：固定使用 Ollama 做 embedding
  providers:
    ollama:
      base_url: "http://localhost:11434"
      chat_model: "qwen2.5:14b"
      embed_model: "bge-large-zh-v1.5"
    claude:
      base_url: "https://api.anthropic.com"
      api_key: ""
      chat_model: "claude-sonnet-4-20250514"

online_search:                    # 新增：整节
  enabled: false
  provider: "tavily"
  api_key: ""
  base_url: ""
  domains: ["gov.cn"]
  max_results: 3
```

### 3.2 config.py 变更

```python
class LLMConfig(BaseModel):
    default_provider: str                         # chat provider
    embed_provider: str = "ollama"                # 新增
    providers: dict[str, OllamaConfig | ClaudeConfig]

class OnlineSearchConfig(BaseModel):
    enabled: bool = False
    provider: str = "tavily"
    api_key: str = ""
    base_url: str = ""
    domains: list[str] = ["gov.cn"]
    max_results: int = 3
```

`AppConfig` 新增 `online_search: OnlineSearchConfig = OnlineSearchConfig()` 字段。

---

## 四、数据模型（`models/search.py`）

### 4.1 检索请求模型

```python
class SearchFilter(BaseModel):
    doc_types: list[str] | None = None
    date_from: date | None = None
    date_to: date | None = None

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    local_only: bool = False
    filter: SearchFilter | None = None
```

### 4.2 检索结果模型

```python
class SourceType(str, Enum):
    LOCAL = "local"
    ONLINE = "online"

class UnifiedSearchResult(BaseModel):
    source_type: SourceType
    title: str
    content: str
    score: float                    # 归一化到 [0, 1]
    metadata: dict
```

### 4.3 在线搜索模型

```python
class OnlineSearchItem(BaseModel):
    title: str
    snippet: str
    url: str
    score: float = 0.5
```

### 4.4 文件管理模型

```python
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
    duplicate_with: str | None = None   # 同 MD5 的另一文件路径

class ClassificationUpdate(BaseModel):
    doc_type: str

class OnlineSearchConfigUpdate(BaseModel):
    """在线搜索配置更新请求（所有字段可选）"""
    enabled: bool | None = None
    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    domains: list[str] | None = None
    max_results: int | None = None

class TestConnectionResult(BaseModel):
    success: bool
    message: str              # 成功提示或错误信息
```

---

## 五、F2.1 本地向量检索（`retrieval/local_search.py`）

### 5.1 类设计

```python
class LocalSearch:
    def __init__(self, vector_store: VectorStore, llm: BaseLLMProvider):
        ...

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: SearchFilter | None = None,
    ) -> list[UnifiedSearchResult]:
        ...
```

### 5.2 处理流程

1. **过滤条件转换**：`SearchFilter` → ChromaDB `where` 字典
   - `doc_types`（多选）→ `$in` 操作符
   - `date_from` / `date_to` → `$gte` / `$lte` 对 `doc_date` 字符串比较
   - 空过滤 → 不传 `where`

2. **向量检索**：调用 `VectorStore.search(query, top_k, where_filters)`

3. **分数归一化**：`score = max(0.0, 1.0 - raw_distance)`

4. **按源文件去重合并**：
   - 按 `source_file` 分组
   - 每组取最高 score 作为文件分数
   - content 取最高分 chunk 内容，拼接同组其他 chunk（超长部分截断）
   - 按分数降序返回 top_k 个文件

---

## 六、F2.2 在线资料检索（`retrieval/online_search.py`）

### 6.1 抽象接口

```python
class BaseOnlineSearchProvider(ABC):
    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 3,
        domains: list[str] | None = None,
    ) -> list[OnlineSearchItem]:
        ...
```

### 6.2 工厂

```python
class OnlineSearchFactory:
    @staticmethod
    def create(config: OnlineSearchConfig) -> BaseOnlineSearchProvider | None:
        """enabled=False 返回 None；provider 类型未实现则抛出异常"""
```

### 6.3 搜索服务

```python
class OnlineSearchService:
    def __init__(self, provider: BaseOnlineSearchProvider | None, config: OnlineSearchConfig):
        ...

    async def search(self, query: str) -> list[UnifiedSearchResult]:
        if self._provider is None:
            return []
        items = await self._provider.search(query, self._config.max_results, self._config.domains)
        return [self._to_unified(item) for item in items]
```

### 6.4 设计要点

- **延迟实现**：阶段二只定义抽象接口和 `OnlineSearchService`，不实现具体 Provider
- **安全边界**：只发送 query 关键词，不发送本地文件内容
- **优雅降级**：`enabled=False` 或 `provider=None` 时返回空列表
- **配置通过 API**：用户通过前端 UI 配置，后端提供 REST API 读写配置

---

## 七、F2.3 检索结果融合排序（`retrieval/fusion.py`）

### 7.1 类设计

```python
class Fusion:
    def __init__(self, max_results: int = 10):
        ...

    def merge(
        self,
        local_results: list[UnifiedSearchResult],
        online_results: list[UnifiedSearchResult],
    ) -> list[UnifiedSearchResult]:
        ...
```

### 7.2 融合策略

1. 合并本地与在线结果为单一列表
2. 本地结果 score × 1.1（排名提升）
3. 按 score 降序排序
4. 截断至 `max_results`
5. 纯函数，无异步操作，无外部依赖

---

## 八、Facade（`retrieval/retriever.py`）

```python
class Retriever:
    def __init__(
        self,
        local_search: LocalSearch,
        online_search: OnlineSearchService,
        fusion: Fusion,
    ):
        ...

    async def search(self, request: SearchRequest) -> list[UnifiedSearchResult]:
        local_results = await self._local.search(request.query, request.top_k, request.filter)
        online_results = [] if request.local_only else await self._online.search(request.query)
        return self._fusion.merge(local_results, online_results)

    async def search_local(self, request: SearchRequest) -> list[UnifiedSearchResult]:
        return await self._local.search(request.query, request.top_k, request.filter)
```

---

## 九、F2.4 知识库文件管理

### 9.1 类设计

```python
class FileService:
    def __init__(self, vector_store: VectorStore, ingester: Ingester):
        ...

    async def list_files(self, request: FileListRequest) -> list[IndexedFile]:
        """从 ChromaDB 聚合文件信息，支持过滤排序"""

    async def delete_file(self, source_file: str) -> None:
        """删除文件及其所有 chunk 向量"""

    async def reindex_file(self, source_file: str) -> FileResult:
        """重新索引单个文件"""

    async def update_classification(self, source_file: str, doc_type: str) -> None:
        """修改文件分类标签（批量更新该文件所有 chunk 的 doc_type）"""
```

### 9.2 VectorStore 扩展

```python
# db/vector_store.py 新增方法

async def list_all_chunks(self) -> list[SearchResult]:
    """获取 collection 中所有 chunk 的 metadata（用于文件列表聚合）"""

async def update_file_metadata(self, source_file: str, updates: dict) -> None:
    """批量更新指定文件所有 chunk 的 metadata 字段"""

async def find_by_md5(self, file_md5: str) -> str | None:
    """按 MD5 查找已存在文件的 source_file，无则返回 None"""
```

### 9.3 MD5 全局去重（Ingester 扩展）

导入时增加 MD5 全局检查：

```
计算 file_md5
  → 查询 ChromaDB: 是否已有相同 file_md5 的 chunk？
  → 无 → 正常入库
  → 有 + 相同 source_file → 跳过
  → 有 + 不同 source_file → 删除旧路径 chunk，用新路径入库
```

同时在 `Ingester.process_file()` 中将 `import_time` 注入 chunk metadata，使文件列表可按导入时间排序。

---

## 十、API 路由设计

### 10.1 端点总览

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/search` | 统一检索（本地+在线融合） |
| POST | `/api/search/local` | 仅本地向量检索 |
| GET | `/api/files` | 列出已索引文件 |
| DELETE | `/api/files/{source_file}` | 删除文件及其向量 |
| POST | `/api/files/{source_file}/reindex` | 重新索引 |
| PUT | `/api/files/{source_file}/classification` | 修改分类标签 |
| GET | `/api/settings/online-search` | 获取在线搜索配置 |
| PUT | `/api/settings/online-search` | 更新配置 |
| POST | `/api/settings/online-search/test-connection` | 测试连接 |

### 10.2 依赖注入（`api/deps.py`）

```python
def get_config(request: Request) -> AppConfig:
    return request.app.state.config

def get_retriever(request: Request) -> Retriever:
    return request.app.state.retriever

def get_file_service(request: Request) -> FileService:
    return request.app.state.file_service

def get_settings_service(request: Request) -> SettingsService:
    return request.app.state.settings_service
```

### 10.3 应用生命周期（`main.py` 重构）

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    config = AppConfig()
    llm = create_provider(config.llm)
    embed_llm = create_embed_provider(config.llm)
    vector_store = VectorStore(config.kb.db_path, embed_llm)
    ingester = Ingester(config, llm, vector_store)
    task_manager = TaskManager(ingester)
    local_search = LocalSearch(vector_store, embed_llm)
    online_search = OnlineSearchService.from_config(config)
    fusion = Fusion()
    retriever = Retriever(local_search, online_search, fusion)
    file_service = FileService(vector_store, ingester)
    settings_service = SettingsService(config)

    app.state.config = config
    app.state.retriever = retriever
    app.state.file_service = file_service
    app.state.settings_service = settings_service
    # ... 其他 state

    yield

    # 释放资源
```

---

## 十一、SettingsService（设置服务）

```python
class SettingsService:
    def __init__(self, config: AppConfig):
        self._config = config
        self._config_path = Path("config.yaml")

    def get_online_search_config(self) -> OnlineSearchConfig:
        return self._config.online_search

    def update_online_search_config(self, update: OnlineSearchConfigUpdate) -> OnlineSearchConfig:
        """更新内存配置 + 写回 config.yaml"""

    async def test_connection(self, config: OnlineSearchConfigUpdate) -> TestConnectionResult:
        """用传入配置临时创建 Provider，验证可用性"""
```

---

## 十二、测试策略

按功能点顺序 TDD（Red-Green-Refactor）：

| 功能点 | 测试文件 | 关键用例 |
|--------|----------|----------|
| F2.1 | `test_retrieval/test_local_search.py` | 基本检索、过滤转换、分数归一化、去重合并、空结果 |
| F2.2 | `test_retrieval/test_online_search.py` | 抽象接口、disabled 返回空、工厂创建、格式转换 |
| F2.3 | `test_retrieval/test_fusion.py` | 纯本地/纯在线/混合、本地加权、截断、空列表 |
| Facade | `test_retrieval/test_retriever.py` | 统一检索、仅本地、mock 协调 |
| F2.4 | `test_retrieval/test_file_service.py` | 列表聚合、过滤排序、删除、重索引、分类修改、MD5 去重 |
| API | `test_api/test_*_routes.py` | 各端点正常/异常、参数校验、响应格式 |
| 配置 | `test_config.py` 扩展 | embed_provider 分离、OnlineSearchConfig、SettingsService 读写 |

**Mock 策略**：
- `VectorStore` / `BaseLLMProvider` 通过 mock 隔离，不依赖真实 ChromaDB / Ollama
- API 测试用 `FastAPI TestClient`，通过 `app.state` 注入 mock 组件
- `Fusion` 是纯函数，无需 mock

---

## 十三、已有文件变更汇总

| 文件 | 变更类型 | 内容 |
|------|----------|------|
| `config.py` | 修改 | `LLMConfig` 新增 `embed_provider`；`AppConfig` 新增 `online_search` |
| `main.py` | 重构 | lifespan 组件初始化、注册路由、app.state 注入 |
| `db/vector_store.py` | 扩展 | 新增 `list_all_chunks()`、`update_file_metadata()`、`find_by_md5()` |
| `ingestion/ingester.py` | 扩展 | MD5 全局去重检查、`import_time` 注入 chunk metadata |
| `models/` | 新增 | `search.py` 检索相关数据模型 |
| `llm/factory.py` | 扩展 | 新增 `create_embed_provider()` 函数 |

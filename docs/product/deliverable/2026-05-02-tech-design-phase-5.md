# 阶段五技术设计 — Word 转 PPT + 优化与加固

**版本**: v1.0
**日期**: 2026-05-02
**状态**: 已确认
**关联文档**: [阶段五功能点](2026-04-30-feature-05-optimization.md) | [阶段三功能点](2026-04-30-feature-03-generation-core.md) | [技术选型](2026-04-30-tech-overview.md)

---

## 一、架构决策

| # | 决策 | 选择 | 理由 |
|---|------|------|------|
| 1 | PPT 生成服务 | 独立 `PptxGenerator`，不扩展 WriterService | PPT 管线与 Word 管线差异大（输入源、处理流程、输出格式），独立服务符合单一职责 |
| 2 | Word 解析工具 | 共享 `WordParser` 类 | F3.6（Word→PPT）和未来「格式化公文」共用，避免重复 |
| 3 | 生成模式 | 异步任务 + WebSocket 推送 | 与文件导入一致，LLM 逐章节总结耗时长 |
| 4 | PPT 样式 | 支持模板文件，默认代码生成简洁公务风 | 满足用户灵活性需求，无模板时不影响功能 |
| 5 | 前端预览 | 幻灯片缩略图卡片 + 下载 | 用户选择，卡片式布局区分封面/目录/内容页 |

---

## 二、F3.6 Word 转 PPT

### 2.1 数据流

```
用户选择 Word 文档（上传/知识库/本次生成）
  → 后端接收文件
  → WordParser 解析文档结构（标题层级 + 段落内容）
  → PptxGenerator 调用 LLM 一次性总结所有章节为幻灯片内容
  → PptxGenerator 用 python-pptx 生成 .pptx
  → 返回结果（output_path + slides 数据）
  → 前端展示缩略图 + 下载按钮
```

### 2.2 新增文件

```
backend/app/generation/
├── word_parser.py          # Word 文档结构解析
├── pptx_generator.py       # PPT 生成服务

backend/app/api/routes/
└── generation.py           # 新增 PPT 端点（在现有文件中）
```

### 2.3 WordParser

```python
class WordParser:
    """从 .docx 文件提取结构化内容"""

    def parse(self, file_path: Path) -> WordStructure:
        """解析 Word 文档，返回标题层级 + 段落文本"""

    def validate(self, file_path: Path) -> None:
        """校验文件：格式、是否加密、是否为空，失败抛 WordParseError"""

@dataclass
class WordStructure:
    title: str                    # 文档标题（首个 Heading 或文件名）
    sections: list[Section]       # 章节列表
    total_paragraphs: int         # 段落总数（用于警告判断）

@dataclass
class Section:
    level: int                    # 1=一级标题, 2=二级, 3=三级
    heading: str
    paragraphs: list[str]

class WordParseError(Exception):
    """Word 解析失败异常"""
    def __init__(self, message: str, reason: str):
        self.reason = reason  # encrypted / corrupted / empty / unsupported
```

- 用 `python-docx` 读取段落，根据样式（Heading 1/2/3）识别标题层级
- 非 Heading 段落归入最近的上层 Section
- 无标题的纯文本文档作为一个整体 Section（level=0）

### 2.4 PptxGenerator

```python
class PptxGenerator:
    def __init__(self, llm: BaseLLMProvider, output_dir: Path) -> None

    async def generate(
        self,
        file_path: Path,
        template_path: Path | None = None,
    ) -> PptxResult:
        """完整管线：校验 → 解析 → LLM 总结 → 生成 PPT"""

    async def _summarize_sections(
        self, title: str, sections: list[Section]
    ) -> list[SlideContent]:
        """调用 LLM 将章节内容总结为幻灯片要点"""

    def _build_pptx(
        self,
        slides: list[SlideContent],
        title: str,
        template_path: Path | None,
    ) -> Path:
        """用 python-pptx 生成 .pptx 文件"""

@dataclass
class SlideContent:
    slide_type: str           # cover | toc | chapter | conclusion
    title: str
    bullets: list[str]

@dataclass
class PptxResult:
    output_path: Path
    slide_count: int
    slides: list[SlideContent]  # 返回前端用于缩略图渲染
    source_doc: str             # 源文档名
    duration_ms: int            # 生成耗时
```

**LLM 调用策略**：
- 将所有章节内容一次性发送给 LLM，Prompt 要求按章节输出 JSON 格式的标题+要点
- 不逐章节单独调用（减少 LLM 请求次数，降低总耗时）
- 超长文档（>50 章节）仅总结前 30 个主要章节，附加"内容概览"页

**PPT 样式**：
- `template_path=None` 时代码生成默认样式：
  - 封面：深蓝渐变背景，白色标题
  - 目录：浅灰背景，列表排版
  - 章节页：白底，左侧蓝色竖条装饰，标题 + 要点列表
  - 结语页：与封面呼应
- `template_path` 有值时，基于模板的 slide layout 填充内容

### 2.5 API 端点

在现有 `backend/app/api/routes/generation.py` 中新增：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/generation/generate-pptx` | 异步 PPT 生成任务 |
| GET | `/api/generation/pptx-status/{task_id}` | 查询任务状态和结果 |
| GET | `/api/files/download/{path}` | 下载 PPT（已有端点，复用） |

**请求体**（`generate-pptx`）：

```json
{
  "source_type": "upload | kb | session",
  "file_path": "string (kb/session 时必填)",
  "template_path": "string (可选)"
}
```

**文件上传流程**：
- `upload` 模式：前端先调用 `POST /api/files/upload` 上传 .docx 文件，获取服务端路径，再以该路径调用 `generate-pptx`
- `kb` 模式：直接传入知识库中已有 .docx 的路径
- `session` 模式：传入本次会话已生成 .docx 的 output_path
```

**异步任务流程**：
1. 接收请求，校验输入，创建 asyncio.Task
2. 通过 WebSocket 推送进度（解析中/总结中/生成中/完成）
3. 完成后推送 `PptxResult`，前端据此渲染缩略图

### 2.6 前端改动

#### WordToPptMode.tsx（重写）

**左面板**：
- 三个 Tab 保持不变，补全逻辑：
  - 上传文件：`beforeUpload` 存储文件到 state，格式校验（仅 .docx），文件大小显示
  - 知识库选择：调用 `GET /api/files?ext=.docx` 列出知识库中的 Word 文档
  - 本次生成：从 Zustand store 读取 `sessionGeneratedDocs`（OneStep/StepByStep 完成后写入）
- 文件选中后显示文件卡片（名称、大小、来源）
- "生成 PPT" 按钮：文件选中后可点击，调用 `POST /api/generation/generate-pptx`

**右面板**：
- 空状态：保持现有占位提示
- 生成中：步骤进度（文档解析 → 内容分析 → AI 摘要 → 生成文件），通过 WebSocket 推送
- 生成失败：步骤列表标红出错步骤 + 错误详情 + 进度条变红
- 生成成功：
  - 转换摘要（源文档 → PPT 页数 → 耗时）
  - 缩略图网格（3 列卡片），区分封面/目录/内容页/结语页
  - 下载按钮（含下载失败重试状态）

#### 新增类型

```typescript
// frontend/src/types/api.ts
interface PptxRequest {
  source_type: "upload" | "kb" | "session";
  file_path?: string;
  template_path?: string;
}

interface PptxResult {
  output_path: string;
  slide_count: number;
  slides: SlideContent[];
  source_doc: string;
  duration_ms: number;
}

interface SlideContent {
  slide_type: "cover" | "toc" | "chapter" | "conclusion";
  title: string;
  bullets: string[];
}
```

#### Store 扩展

`useWritingStore` 新增：
- `sessionGeneratedDocs: string[]` — 本次会话已生成的文档路径列表
- `startPptxGeneration(req: PptxRequest)` — 发起 PPT 异步任务
- `pptxResult: PptxResult | null` — PPT 生成结果

### 2.7 错误处理

| 场景 | 展示位置 | UI | 操作 |
|------|----------|----|------|
| 文件格式错误 | 左面板上传区 | 上传区变红 + inline alert | "重新选择" |
| 文档解析失败 | 左面板 | 文件卡片变红 + inline alert（加密/损坏/空文档） | "更换文件" |
| 超长文档警告 | 左面板 | 黄色 inline warning | 允许继续 |
| LLM 服务不可用 | 右面板 | 步骤进度标红 + 错误详情 | 左面板"重新生成" |
| PPT 文件写入失败 | 右面板 | 步骤进度标红 + 错误详情 | 左面板"重新生成" |
| 下载失败 | 右面板下载按钮 | 按钮变为"下载失败，点击重试" | 点击重试 |

---

## 三、F5.1 导入性能优化

### 3.1 文件解析并行化

修改 `ingestion/pipeline.py`：

```python
async def process_files(self, file_paths: list[Path]) -> list[ProcessResult]:
    """批量并行处理文件"""
    semaphore = asyncio.Semaphore(self.config.max_concurrent)  # 默认 4

    async def _process_with_limit(path):
        async with semaphore:
            return await self.process_file(path)

    tasks = [_process_with_limit(p) for p in file_paths]
    return await asyncio.gather(*tasks)
```

### 3.2 向量化批量入库

修改 `ingestion/vector_store.py`：

```python
async def add_documents_batch(self, chunks: list[Chunk]) -> None:
    """批量入库，按 batch_size 分批"""
    for i in range(0, len(chunks), self.batch_size):  # 默认 100
        batch = chunks[i:i + self.batch_size]
        self.collection.add(
            ids=[c.id for c in batch],
            documents=[c.text for c in batch],
            embeddings=[c.embedding for c in batch],
            metadatas=[c.metadata for c in batch],
        )
```

### 3.3 大文件分块保护

在 `extractor.py` 的文本提取后增加检查：

- 单文件提取文本 > 2MB 时，按段落边界截断，记录截断警告
- 内存监控：`resource.getrusage()` 记录峰值，超过阈值时跳过当前文件

### 3.4 配置参数

```yaml
ingestion:
  max_concurrent: 4        # 最大并发解析数
  batch_size: 100           # 向量化批量大小
  max_text_size_mb: 2       # 单文件文本上限
```

---

## 四、F5.2 检索准确率调优

### 4.1 分块策略优化

修改 `ingestion/chunker.py`：

- 当前：固定 500 字/块，重叠 0
- 优化后：按段落+标题自然分块，尊重段落边界
  - 标题（Heading）后的段落归入同一块
  - 块大小范围：200-800 字（默认上限 800 字）
  - 块间重叠：50 字（可配置）

```python
class Chunker:
    def chunk(self, text: str, structure: list[dict]) -> list[Chunk]:
        """按段落+标题自然分块"""
        # 按 heading 边界分组
        # 组内段落拼接不超过 chunk_size 上限
        # 超长段落单独切块，保留 overlap
```

### 4.2 查询改写

新增 `retrieval/query_rewriter.py`：

```python
class QueryRewriter:
    def __init__(self, llm: BaseLLMProvider) -> None

    async def rewrite(self, query: str) -> str:
        """调用 LLM 改写查询：扩展同义词 + 纠正错别字"""
```

- Prompt 要求 LLM 输出改写后的单一查询字符串
- 调用 `llm.classify()` 而非 `llm.chat()`，降低 token 开销
- 改写结果缓存（相同查询不重复调用）
- 可通过配置开关关闭（默认开启）

### 4.3 配置参数

```yaml
retrieval:
  chunk_size: 800           # 分块大小上限
  chunk_overlap: 50          # 块间重叠字数
  enable_query_rewrite: true # 是否启用查询改写
```

---

## 五、F5.3 错误处理与日志完善

### 5.1 全局异常中间件

新增 `app/middleware/error_handler.py`：

```python
class ExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            return await call_next(request)
        except AppError as e:
            return JSONResponse(status_code=e.status_code, content=e.to_dict())
        except Exception as e:
            logger.exception("unhandled_error", path=request.url.path)
            return JSONResponse(status_code=500, content={
                "code": "INTERNAL_ERROR",
                "message": "服务内部错误，请稍后重试",
                "detail": None,
            })
```

统一错误响应格式：

```json
{
  "code": "WORD_PARSE_ERROR",
  "message": "文档解析失败",
  "detail": "文件可能已加密或损坏"
}
```

### 5.2 结构化日志

引入 `structlog`：

- 关键操作（导入、生成、PPT、检索）输出 JSON 格式日志
- 包含 `timestamp`、`level`、`event`、`operation`、`duration_ms`、`trace_id`
- 错误日志额外包含 `exception` 堆栈

日志配置：

```python
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
```

### 5.3 前端错误展示

- API client 的 `axios.interceptors.response` 统一拦截非 2xx 响应
- 从 `response.data.message` 提取用户友好文案
- 用 `message.error()` 展示，5 秒自动消失
- 网络错误统一提示"网络连接异常，请检查网络"

---

## 六、F5.4 扩展性验证

### 6.1 压测方案

新增 `tests/performance/` 目录：

| 文件 | 说明 |
|------|------|
| `generate_test_data.py` | 生成 5000 条模拟文档（随机中文文本 + 元数据） |
| `bench_import.py` | 导入压测：100/500/1000/5000 文档，记录耗时和内存 |
| `bench_search.py` | 检索压测：不同数据量下检索延迟 |
| `report.md` | 测试报告模板 |

### 6.2 验收指标

- 5000 文档可正常导入和检索
- 检索延迟 < 5 秒
- 导入过程无 OOM
- 产出扩展性测试报告和 TODO 清单

---

## 七、实施顺序与依赖

```
F3.6（Word→PPT）────────────────────────────┐
F5.3（错误处理与日志）← 可并行               │
     ↓                                      │
F5.1（导入性能优化）← 依赖 F3.6 完成         │
     ↓                                      │
F5.2（检索准确率调优）                        │
     ↓                                      │
F5.4（扩展性验证）← 依赖 F5.1 + F5.2        │
```

| 阶段 | 功能 | 预估工作量 |
|------|------|-----------|
| Sprint 1 | F3.6 后端（WordParser + PptxGenerator + API） | 大 |
| Sprint 2 | F3.6 前端（WordToPptMode 重写 + 缩略图） | 中 |
| Sprint 3 | F5.3 错误处理与日志（可与 Sprint 1/2 并行） | 中 |
| Sprint 4 | F5.1 导入性能优化 | 中 |
| Sprint 5 | F5.2 检索准确率调优 | 中 |
| Sprint 6 | F5.4 扩展性验证 | 小 |

---

## 八、不做什么

- 不做 PPT 样式自定义编辑器
- 不做 PPT 在线编辑
- 不做分布式导入处理
- 不做复杂 RAG 流程（重排序模型等）
- 不做日志分析平台
- 不做分布式架构改造

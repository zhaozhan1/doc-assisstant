# 阶段三分项技术方案 — 写作辅助核心

**版本**: v1.0
**日期**: 2026-05-01
**状态**: 待确认
**关联文档**: [功能点拆分](2026-04-30-feature-03-generation-core.md) | [技术选型方案](2026-04-30-tech-overview.md) | [阶段二技术方案](2026-05-01-tech-design-phase-2.md)

---

## 一、核心设计决策

| # | 决策点 | 方案 | 理由 |
|---|--------|------|------|
| 1 | 意图解析方式 | LLM 解析 | 准确度高、适应性强，复用现有 chat provider |
| 2 | 流式输出 | 扩展 BaseLLMProvider 新增 chat_stream() | 保持 provider 抽象一致性，writer 无需关心底层实现 |
| 3 | 模板存储格式 | YAML 文件（内置只读 + 用户自定义可 CRUD） | 可读性好，与项目 YAML 风格一致 |
| 4 | Word 排版字体 | 优先方正字体，未安装则降级为系统字体 | 兼顾国标合规与用户环境差异 |
| 5 | F3.6 Word→PPT | 推迟到阶段五 | 功能独立，缩小阶段三范围，更快进入 Web UI |
| 6 | 模块架构 | 分层模块化（5 个独立类 + WriterService 门面） | 与阶段二 Retriever 门面模式一致，职责单一，易于测试 |

---

## 二、目录结构

```
backend/app/
├── generation/                    # 新增：写作辅助模块
│   ├── __init__.py
│   ├── intent_parser.py           # F3.1 意图解析
│   ├── prompt_builder.py          # F3.2 Prompt 构建
│   ├── template_manager.py        # F3.3 模板管理
│   ├── writer.py                  # F3.4 LLM 生成
│   ├── writer_service.py          # 门面编排
│   ├── docx_formatter.py          # F3.5 Word 格式化
│   └── templates/                 # 12 个内置 YAML 模板
│       ├── notice.yaml
│       ├── announcement.yaml
│       ├── request.yaml
│       ├── report.yaml
│       ├── plan.yaml
│       ├── program.yaml
│       ├── minutes.yaml
│       ├── contract.yaml
│       ├── work_summary.yaml
│       ├── speech.yaml
│       ├── research_report.yaml
│       └── presentation.yaml
├── api/routes/
│   ├── generation.py              # 新增：写作 API
│   └── templates.py               # 新增：模板管理 API
├── models/
│   └── generation.py              # 新增：生成相关数据模型
├── llm/
│   ├── base.py                    # 修改：新增 chat_stream() 抽象方法
│   ├── ollama_provider.py         # 修改：实现流式 chat_stream()
│   └── claude_provider.py         # 修改：实现流式 chat_stream()
├── config.py                      # 修改：新增 GenerationConfig
└── main.py                        # 修改：lifespan 新增服务实例化 + 路由注册
```

---

## 三、配置变更

### config.yaml 新增节

```yaml
generation:
  output_format: "docx"        # docx | md
  save_path: "./output"
  include_sources: true
  max_prompt_tokens: 4096
```

### AppConfig 代码变更

```python
class GenerationConfig(BaseModel):
    output_format: str = "docx"
    save_path: str = "./output"
    include_sources: bool = True
    max_prompt_tokens: int = 4096

class AppConfig(BaseSettings):
    # ... 现有字段 ...
    generation: GenerationConfig = GenerationConfig()
```

---

## 四、数据模型（models/generation.py）

```python
class ParsedIntent(BaseModel):
    doc_type: str                    # 公文类型标识
    topic: str                       # 主题
    keywords: list[str]              # 关键词列表
    raw_input: str                   # 原始用户输入

class TemplateSection(BaseModel):
    title: str                       # 段落标题
    writing_points: list[str]        # 写作要点
    format_rules: list[str]          # 格式规范

class TemplateDef(BaseModel):
    id: str                          # 模板 ID
    name: str                        # 显示名称
    doc_type: str                    # 关联公文类型
    sections: list[TemplateSection]  # 结构大纲
    is_builtin: bool = True          # 内置/自定义

class PromptContext(BaseModel):
    intent: ParsedIntent
    style_refs: list[UnifiedSearchResult]
    policy_refs: list[UnifiedSearchResult]
    template: TemplateDef

class SourceAttribution(BaseModel):
    title: str
    source_type: SourceType          # LOCAL / ONLINE
    url: str | None = None
    date: str | None = None

class GenerationRequest(BaseModel):
    description: str                 # 模式 A：用户描述
    selected_refs: list[str] | None = None   # 模式 B：选择的素材 ID
    requirements: str | None = None           # 模式 B：补充要求
    template_id: str | None = None            # 指定模板

class GenerationResult(BaseModel):
    content: str
    sources: list[SourceAttribution]
    output_path: str | None
    template_used: str
```

---

## 五、F3.1 意图解析 — IntentParser

### 类设计

```python
class IntentParser:
    DOC_TYPES = [
        "notice", "announcement", "request", "report", "plan",
        "program", "minutes", "contract", "work_summary",
        "speech", "research_report", "presentation"
    ]

    def __init__(self, llm: BaseLLMProvider):
        self._llm = llm

    async def parse(self, user_input: str) -> ParsedIntent:
        """调用 LLM 从用户描述提取结构化意图"""
```

### 处理流程

1. 构建 system prompt：列出 12 种公文类型及说明，要求 LLM 返回 JSON（doc_type, topic, keywords）
2. 调用 `self._llm.chat(messages)`
3. 解析 LLM 返回的 JSON，构造 `ParsedIntent`
4. 未识别到 doc_type 时默认为 `"report"`

### 设计说明

- 意图解析复用 chat provider，不引入新的 LLM 调用方式
- 12 种公文类型作为常量维护，Prompt 中枚举给 LLM 参考
- LLM 返回格式异常时做容错处理，保证至少返回默认值

---

## 六、F3.2 Prompt 构建 — PromptBuilder

### 类设计

```python
class PromptBuilder:
    def __init__(self, max_tokens: int = 4096):
        self._max_tokens = max_tokens

    def build(self, context: PromptContext) -> list[dict]:
        """组装 5 部分 Prompt，超限时按优先级截断"""

    def _estimate_tokens(self, text: str) -> int:
        """估算文本 token 数（粗粒度：1 字 ≈ 1 token）"""
```

### Prompt 结构

| 部分 | 来源 | 截断优先级 |
|------|------|------------|
| 角色设定 | 固定模板 | 不截断 |
| 写作任务 | 用户输入 | 最高（不截断） |
| 格式要求 | 模板 sections | 中 |
| 文风参考 | 检索结果 top-5 | 低 |
| 政策依据 | 在线检索结果 | 最低 |

### 截断策略

1. 计算角色设定 + 写作任务的 token 量（必保留部分）
2. 剩余配额按优先级依次填充：格式要求 → 文风参考 → 政策依据
3. 文风参考按条目粒度截断（去掉最低分的检索结果）
4. 政策依据整体截断或截断单条内容

---

## 七、F3.3 模板管理 — TemplateManager

### 类设计

```python
class TemplateManager:
    def __init__(self, builtin_dir: Path, custom_dir: Path):
        self._builtin_dir = builtin_dir
        self._custom_dir = custom_dir
        self._custom_dir.mkdir(parents=True, exist_ok=True)

    def list_templates(self, doc_type: str | None = None) -> list[TemplateDef]
    def get_template(self, template_id: str) -> TemplateDef
    def create_template(self, template: TemplateDef) -> TemplateDef
    def update_template(self, template_id: str, data: TemplateDef) -> TemplateDef
    def delete_template(self, template_id: str) -> None
```

### 模板 YAML 格式示例

```yaml
id: notice
name: 通知
doc_type: notice
sections:
  - title: 标题
    writing_points:
      - 发文机关名称
      - 事由概括
    format_rules:
      - 居中排版
  - title: 正文
    writing_points:
      - 通知背景和目的
      - 具体事项和要求
      - 执行时间和范围
    format_rules:
      - 首行缩进两字
  - title: 落款
    writing_points:
      - 发文单位
      - 成文日期
    format_rules:
      - 右对齐
```

### 设计说明

- 内置模板（`builtin_dir`）只读，update/delete 抛异常
- 自定义模板（`custom_dir`）完整 CRUD，ID 带 `custom_` 前缀避免冲突
- `list_templates()` 合并返回内置 + 自定义，内置在前
- 按 `doc_type` 过滤时两类模板统一过滤

---

## 八、F3.4 LLM 生成 — Writer

### 类设计

```python
class Writer:
    def __init__(self, llm: BaseLLMProvider):
        self._llm = llm

    async def generate(self, messages: list[dict]) -> str:
        """同步生成完整文本"""
        return await self._llm.chat(messages)

    async def generate_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        """流式生成，逐 token 返回"""
        async for token in self._llm.chat_stream(messages):
            yield token
```

### LLM Provider 流式扩展

`base.py` 新增：

```python
@abstractmethod
async def chat_stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
    """流式对话，逐 token 返回"""
```

`ollama_provider.py` 实现：请求 `/api/chat` 时 `"stream": True`，逐行读取 SSE 并 yield content token。

`claude_provider.py` 实现：使用 `messages.stream()` API，逐事件 yield text delta。

---

## 九、F3.5 Word 格式化 — DocxFormatter

### 类设计

```python
class DocxFormatter:
    FONT_MAP = {
        "title": ("方正小标宋简体", "宋体"),          # 二号/居中
        "heading1": ("方正黑体_GBK", "黑体"),         # 三号/首行空两字
        "heading2": ("方正楷体_GBK", "楷体"),         # 三号/首行空两字
        "heading3": ("方正仿宋_GBK", "仿宋"),         # 三号/首行空两字
        "body": ("方正仿宋_GBK", "仿宋"),             # 三号/首行空两字
        "en_num": ("Times New Roman", "Times New Roman"),
    }

    def __init__(self, output_dir: Path):
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._font_map = self._detect_fonts()

    def format(self, content: str, doc_type: str, topic: str) -> Path:
        """将生成文本格式化为 .docx"""

    def _detect_fonts(self) -> dict:
        """检测方正字体是否可用，返回实际使用的字体映射"""

    def _parse_structure(self, content: str) -> list[dict]:
        """解析文本中的标题层级结构"""

    def _apply_formatting(self, doc, structure: list[dict]):
        """应用字体/字号/行距/缩进"""

    def _apply_en_num_font(self, paragraph):
        """在 run 级别为英文/数字设置 Times New Roman"""
```

### 排版规范（GB/T 9704-2012）

| 元素 | 字体 | 字号 | 对齐 | 缩进 | 行距 |
|------|------|------|------|------|------|
| 文件标题 | 方正小标宋简体 | 二号（22pt） | 居中 | 无 | 28 磅 |
| 一级标题 | 方正黑体_GBK | 三号（16pt） | 左对齐 | 首行两字 | 28 磅 |
| 二级标题 | 方正楷体_GBK | 三号（16pt） | 左对齐 | 首行两字 | 28 磅 |
| 三级标题 | 方正仿宋_GBK | 三号（16pt） | 左对齐 | 首行两字 | 28 磅 |
| 正文 | 方正仿宋_GBK | 三号（16pt） | 左对齐 | 首行两字 | 28 磅 |
| 英文/数字 | Times New Roman | 同所在段落 | — | — | — |

### 字体降级策略

1. 启动时检测方正字体是否可用（遍历系统字体列表）
2. 可用 → 使用方正字体
3. 不可用 → 降级为系统字体（宋体/黑体/楷体/仿宋）
4. 降级信息记录日志，不阻断流程

### 文件命名

`{doc_type}_{topic_keywords}_{YYYY-MM-DD}.docx`，topic 超过 20 字符时截断。

---

## 十、WriterService 门面

### 类设计

```python
class WriterService:
    def __init__(self, intent_parser: IntentParser,
                 prompt_builder: PromptBuilder,
                 template_mgr: TemplateManager,
                 writer: Writer,
                 docx_formatter: DocxFormatter,
                 retriever: Retriever):
        ...

    async def generate_from_description(self, req: GenerationRequest) -> GenerationResult:
        """模式 A：描述 → 自动检索 → 生成 → 格式化"""

    async def generate_from_selection(self, req: GenerationRequest) -> GenerationResult:
        """模式 B：用户选择素材 + 补充要求 → 生成 → 格式化"""

    async def generate_stream(self, req: GenerationRequest) -> AsyncGenerator[str, None]:
        """流式生成（仅返回 token 流，不生成文件）"""
```

### 模式 A 流程

```
用户描述
  → IntentParser.parse() → ParsedIntent
  → TemplateManager.get_template(doc_type) → TemplateDef
  → Retriever.search(keywords, top_k=5) → list[UnifiedSearchResult]
  → PromptBuilder.build(PromptContext) → messages
  → Writer.generate(messages) → content
  → DocxFormatter.format(content) → Path
  → GenerationResult
```

### 模式 B 流程

```
用户选择素材 + 补充要求
  → IntentParser.parse(requirements) → ParsedIntent
  → TemplateManager.get_template(template_id) → TemplateDef
  → Retriever.search_local(selected_refs 作为 query) 或 VectorStore 按 chunk ID 查询 → list[UnifiedSearchResult]
  → PromptBuilder.build(PromptContext) → messages
  → Writer.generate(messages) → content
  → DocxFormatter.format(content) → Path
  → GenerationResult
```

### 素材来源清单

从检索结果的 `UnifiedSearchResult` 中提取：
- 本地来源：title + metadata 中的文件日期
- 在线来源：title + url

---

## 十一、API 路由设计

### 端点列表

| 方法 | 路径 | 功能 | 请求体 | 响应 |
|------|------|------|--------|------|
| POST | `/api/generation/generate` | 生成公文（模式 A/B） | GenerationRequest | GenerationResult |
| POST | `/api/generation/generate/stream` | 流式生成 | GenerationRequest | SSE (text/event-stream) |
| GET | `/api/templates` | 列出模板 | query: doc_type? | list[TemplateDef] |
| GET | `/api/templates/{id}` | 获取模板详情 | — | TemplateDef |
| POST | `/api/templates` | 创建自定义模板 | TemplateDef | TemplateDef |
| PUT | `/api/templates/{id}` | 更新自定义模板 | TemplateDef | TemplateDef |
| DELETE | `/api/templates/{id}` | 删除自定义模板 | — | 204 |

### 流式输出实现

`/api/generation/generate/stream` 使用 FastAPI `StreamingResponse`：

```python
@router.post("/generation/generate/stream")
async def generate_stream(req: GenerationRequest, ...):
    async def event_generator():
        async for token in writer_service.generate_stream(req):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### 依赖注入（deps.py 新增）

```python
def get_writer_service(request: Request) -> WriterService:
    return request.app.state.writer_service

def get_template_manager(request: Request) -> TemplateManager:
    return request.app.state.template_mgr
```

### Lifespan 注册（main.py）

```python
# 在 _lifespan 中新增
intent_parser = IntentParser(chat_provider)
template_mgr = TemplateManager(
    builtin_dir=Path(__file__).parent / "generation" / "templates",
    custom_dir=Path(config.generation.save_path) / "templates"
)
prompt_builder = PromptBuilder(max_tokens=config.generation.max_prompt_tokens)
writer = Writer(chat_provider)
docx_formatter = DocxFormatter(output_dir=Path(config.generation.save_path))
writer_service = WriterService(
    intent_parser, prompt_builder, template_mgr,
    writer, docx_formatter, retriever
)
app.state.writer_service = writer_service
app.state.template_mgr = template_mgr

# 路由注册
app.include_router(generation.router)
app.include_router(templates.router)
```

---

## 十二、测试策略

| 模块 | 测试文件 | 关键用例 |
|------|----------|----------|
| IntentParser | test_intent_parser.py | 12 种类型识别、默认值兜底、JSON 解析容错、LLM mock |
| PromptBuilder | test_prompt_builder.py | 5 部分组装验证、截断优先级（逐级去掉）、空检索结果 |
| TemplateManager | test_template_manager.py | 12 个内置模板加载、自定义模板 CRUD、内置只读保护、doc_type 过滤 |
| Writer | test_writer.py | 同步生成、流式生成、LLM mock |
| DocxFormatter | test_docx_formatter.py | 字体降级逻辑、标题层级解析、run 级英文/数字字体、文件命名、行距/缩进 |
| WriterService | test_writer_service.py | 模式 A 全链路、模式 B 全链路、流式生成、素材来源清单、全部 mock |
| API 路由 | test_generation_routes.py | generate 端点、stream 端点、模板 CRUD 端点、参数校验、内置模板保护 |
| LLM Provider | test_ollama_provider.py 等 | chat_stream 新增流式测试 |

### Mock 策略

- LLM 调用：mock `BaseLLMProvider.chat()` 和 `chat_stream()`
- 检索结果：构造 `UnifiedSearchResult` 列表作为 fixture
- 文件操作：使用 `tmp_path` fixture，不写真实文件系统

---

## 十三、现有文件变更汇总

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `llm/base.py` | 修改 | 新增 `chat_stream()` 抽象方法 |
| `llm/ollama_provider.py` | 修改 | 实现流式 `chat_stream()` |
| `llm/claude_provider.py` | 修改 | 实现流式 `chat_stream()` |
| `config.py` | 修改 | 新增 `GenerationConfig` 配置节 |
| `main.py` | 修改 | lifespan 新增服务实例化 + 路由注册 |
| `api/deps.py` | 修改 | 新增 WriterService、TemplateManager 依赖函数 |

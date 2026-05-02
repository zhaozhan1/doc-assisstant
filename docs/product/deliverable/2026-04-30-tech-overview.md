# 公文助手 — 整体技术选型方案

**版本**: v1.0
**日期**: 2026-04-30
**状态**: 已确认
**关联文档**: [整体产品设计](../deliverable/2026-04-30-product-design.md) | [功能点拆分](2026-04-30-feature-breakdown.md)

---

## 一、技术选型原则

1. **本地优先**：所有涉及文件内容的处理必须在本地完成
2. **成熟稳定**：优先选择社区活跃、文档完善的开源组件
3. **Python 生态**：统一使用 Python 3.10+，减少技术栈复杂度
4. **可替换性**：LLM Provider、向量数据库、在线检索均通过抽象层隔离，可独立替换
5. **macOS 兼容**：确保所有依赖在 macOS 上可正常运行

---

## 二、后端技术栈

### 2.1 Web 框架：FastAPI

| 项目 | 说明 |
|------|------|
| 选型 | **FastAPI** |
| 理由 | 异步原生、自动生成 OpenAPI 文档、WebSocket 支持、Python 生态主流 |
| 替代方案 | Flask（异步支持弱）、Django（过重） |

### 2.2 文档解析

| 格式 | 库 | 说明 |
|------|-----|------|
| `.docx` | `python-docx` | 成熟稳定，支持正文/标题/表格提取 |
| `.pdf` | `pdfplumber` + `pytesseract` | pdfplumber 提取文本层，OCR 处理扫描件 |
| `.xlsx` | `openpyxl` | 读取表格数据转为文本描述 |
| `.pptx` | `python-pptx` | 提取幻灯片文本/标题/备注 |
| `.png/.jpg` | `pytesseract` + Tesseract OCR | 需用户本地安装 Tesseract + 中文语言包 |
| `.txt` | Python 内置 `open()` | 直接读取 |
| 压缩包 | `zipfile`（内置）+ `py7zr`（.7z）+ `pyunpack`（.rar） | 纯 Python 库，不依赖系统工具 |

### 2.3 向量数据库

| 项目 | 说明 |
|------|------|
| 选型 | **ChromaDB**（本地持久化模式） |
| 理由 | 轻量嵌入式、无需服务器、Python 原生、支持元数据过滤、5000 文档规模无压力 |
| 替代方案 | FAISS（更底层，需自管理持久化）、Qdrant（需独立服务） |
| 扩展考量 | 5000 文档规模 ChromaDB 足够；如未来需更大规模，可迁移至 Qdrant |

### 2.4 Embedding 模型

| 项目 | 说明 |
|------|------|
| 选型 | **BAAI/bge-large-zh-v1.5**（通过 Ollama 运行） |
| 理由 | 中文向量化效果最优之一、本地运行、Ollama 简化部署 |
| 备选 | `bge-small-zh`（更轻量，精度略低）、OpenAI embedding（云端，需网络） |
| 调用方式 | 通过 Ollama API 调用，走统一 LLM Provider 抽象层 |

### 2.5 LLM Provider 抽象层

| 项目 | 说明 |
|------|------|
| 选型 | 自定义 Provider 接口 + 工厂模式 |
| 理由 | 本地 Ollama 和云端 Claude API 差异较大，需统一抽象 |
| 默认 Provider | **Ollama**（本地部署，默认连接 `http://localhost:11434`） |
| 可选 Provider | **Claude API**（Anthropic SDK） |
| 配置方式 | config.yaml 中配置 provider / base_url / model / api_key |
| 接口定义 | `chat(messages) → str`、`classify(text, labels) → str`、`embed(text) → list[float]` |

### 2.6 在线检索

| 项目 | 说明 |
|------|------|
| 选型 | **Tavily Search API**（主选） |
| 理由 | API 简洁、专为 AI 应用设计、返回结构化摘要、支持域名过滤 |
| 备选 | Bing Search API（更通用但配置复杂） |
| 接口设计 | 统一 `search(query, max_results, domains) → list[SearchResult]`，可替换实现 |

### 2.7 输出生成

| 输出类型 | 库 | 说明 |
|----------|-----|------|
| `.docx` | `python-docx` | 同解析库，用于写入和格式化 |
| `.pptx` | `python-pptx` | 同解析库，用于写入 PPT |
| `.md` | Python 内置 | 纯文本写入 |

### 2.8 异步任务

| 项目 | 说明 |
|------|------|
| 选型 | **asyncio** + 自定义任务管理器 |
| 理由 | 单用户场景无需 Celery/Redis 等重型方案，FastAPI 原生 asyncio 足够 |
| 实现 | 后台任务用 `asyncio.create_task`，状态管理用内存字典 + 定期持久化 |
| 进度推送 | WebSocket 实时推送 |

---

## 三、前端技术栈

### 3.1 框架选型

| 项目 | 说明 |
|------|------|
| 选型 | **React + TypeScript + Vite** |
| 理由 | 生态最成熟、组件库丰富、Vite 开发体验好、TypeScript 类型安全 |
| 替代方案 | Vue 3（也可，但 React 生态更大）、纯 HTML（功能复杂度不够支撑） |

### 3.2 包管理：pnpm

| 项目 | 说明 |
|------|------|
| 选型 | **pnpm** |
| 理由 | 硬链接机制节省磁盘空间、严格的依赖隔离避免幽灵依赖、与 npm 完全兼容 |
| 隔离策略 | 使用 `pnpm` 的全局 store + 项目级 `node_modules`，避免与本机其他前端项目的依赖版本冲突 |

### 3.3 UI 组件库

| 项目 | 说明 |
|------|------|
| 选型 | **Ant Design** |
| 理由 | 中文生态最好、表格/表单组件完善、企业级风格契合公务场景 |
| 备选 | Arco Design（字节跳动，更轻量） |

### 3.4 关键前端依赖

| 功能 | 库 | 说明 |
|------|-----|------|
| 路由 | React Router | 页面切换 |
| HTTP 请求 | Axios | API 调用 |
| WebSocket | 原生 WebSocket API | 进度推送、流式输出 |
| 状态管理 | Zustand | 轻量状态管理 |
| 文件上传 | Ant Design Upload 组件 | 支持拖拽、文件夹选择 |
| Markdown 渲染 | react-markdown | 生成结果预览 |

---

## 四、项目目录结构

```
doc-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 应用入口
│   │   ├── config.py               # 配置管理
│   │   ├── models/                  # 数据模型定义
│   │   │   ├── document.py          # 文档/文件相关模型
│   │   │   ├── chunk.py             # 文本块模型
│   │   │   ├── template.py          # 模板模型
│   │   │   └── task.py              # 异步任务模型
│   │   ├── ingestion/               # 文档解析模块（F1）
│   │   │   ├── extractor.py         # 格式识别 & 文本提取
│   │   │   ├── decompressor.py      # 压缩包解压
│   │   │   ├── classifier.py        # 文档分类
│   │   │   ├── chunker.py           # 文本分块
│   │   │   └── ingester.py          # 编排：解压→提取→分类→分块→向量化→入库
│   │   ├── retrieval/               # 检索模块（F2）
│   │   │   ├── local_search.py      # 本地向量检索
│   │   │   ├── online_search.py     # 在线资料检索
│   │   │   └── fusion.py            # 结果融合排序
│   │   ├── generation/              # 写作辅助模块（F3）
│   │   │   ├── intent_parser.py     # 意图解析
│   │   │   ├── prompt_builder.py    # Prompt 构建
│   │   │   ├── writer.py            # LLM 生成调用
│   │   │   ├── docx_formatter.py    # Word 格式化输出
│   │   │   ├── pptx_generator.py    # Word 转 PPT
│   │   │   └── templates/           # 内置模板文件（JSON/YAML）
│   │   ├── llm/                     # LLM Provider 抽象层
│   │   │   ├── base.py              # 抽象接口定义
│   │   │   ├── ollama_provider.py   # Ollama 实现
│   │   │   ├── claude_provider.py   # Claude API 实现
│   │   │   └── factory.py           # Provider 工厂
│   │   ├── api/                     # Web API 层（F4）
│   │   │   ├── routes/
│   │   │   │   ├── ingestion.py     # 导入相关 API
│   │   │   │   ├── retrieval.py     # 检索相关 API
│   │   │   │   ├── generation.py    # 写作相关 API
│   │   │   │   ├── templates.py     # 模板管理 API
│   │   │   │   └── settings.py      # 设置 API
│   │   │   └── websocket.py         # WebSocket 处理
│   │   └── db/                      # 数据库相关
│   │       ├── vector_store.py      # 向量数据库操作封装
│   │       └── metadata_store.py    # 元数据存储
│   ├── tests/                       # 测试目录
│   │   ├── test_ingestion/
│   │   ├── test_retrieval/
│   │   ├── test_generation/
│   │   └── test_api/
│   ├── config.yaml                  # 配置文件
│   ├── environment.yml              # Conda 环境定义
│   ├── pyproject.toml               # 项目依赖声明
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── pages/                   # 页面组件
│   │   │   ├── KnowledgeBase.tsx    # 知识库页面
│   │   │   ├── Writing.tsx          # 写作页面
│   │   │   ├── TemplateManager.tsx  # 模板管理页面
│   │   │   └── Settings.tsx         # 设置页面
│   │   ├── components/              # 通用组件
│   │   ├── services/                # API 调用封装
│   │   ├── stores/                  # 状态管理
│   │   ├── App.tsx                  # 应用入口
│   │   └── main.tsx                 # 渲染入口
│   ├── package.json
│   ├── pnpm-lock.yaml
│   └── vite.config.ts
├── docs/                            # 项目文档（按 CLAUDE.md 规范）
└── output/                          # 默认输出目录
```

---

## 五、配置文件规格（config.yaml）

```yaml
knowledge_base:
  source_folder: ""           # 源文件夹路径（用户设置）
  db_path: "./data/chroma_db" # 向量数据库路径
  metadata_path: "./data/metadata" # 元数据存储路径
  chunk_size: 500             # 分块字数
  chunk_overlap: 50           # 重叠字数

llm:
  default_provider: "ollama"  # 默认 LLM Provider
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
  enabled: false              # 默认关闭在线检索
  provider: "tavily"
  api_key: ""
  domains:
    - "gov.cn"
    - "npc.gov.cn"
    - "moj.gov.cn"
  max_results: 3

output:
  format: "docx"              # docx | md
  save_path: "./output"
  include_sources: true

ocr:
  tesseract_cmd: ""           # Tesseract 可执行文件路径（空则使用系统默认）

logging:
  level: "INFO"
  file: "./logs/app.log"
```

---

## 六、开发环境要求

### 6.1 Python 依赖环境管理

使用 **Conda（Anaconda/Miniconda）** 创建独立虚拟环境，隔离项目依赖，避免与本机其他项目冲突。

| 项目 | 说明 |
|------|------|
| 选型 | **Miniconda**（轻量）或 Anaconda（完整） |
| 环境名 | `doc-assistant` |
| Python 版本 | 3.10+ |
| 初始化命令 | `conda create -n doc-assistant python=3.10` |
| 激活命令 | `conda activate doc-assistant` |
| 依赖管理 | `pyproject.toml` 定义依赖，`pip install` 在 conda 环境内安装 |

### 6.2 外部依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Node.js | 18+ | 前端构建 |
| pnpm | 8+ | 前端包管理，`npm install -g pnpm` 安装 |
| Tesseract OCR | 5.x + 中文语言包 | 图片 OCR（需用户自行安装） |
| Ollama | 最新版 | 本地 LLM 运行（需用户自行安装） |
| 操作系统 | macOS | 主要支持平台 |

---

## 七、开发方法论

### 7.1 测试驱动开发（TDD）

本项目采用 **测试驱动开发（Test-Driven Development）** 模式，所有功能点按 Red-Green-Refactor 循环开发：

1. **Red**：先编写失败测试，定义期望行为
2. **Green**：编写最少代码使测试通过
3. **Refactor**：在测试保护下重构优化

**要求**：
- 每个功能点必须先有测试，再写实现
- 所有 PR 必须包含对应的测试用例
- 测试覆盖率目标 ≥ 80%（核心模块）

### 7.2 前端设计流程

阶段四（Web UI）开发前，需调用 `/frontend-design` skill 指导前端界面设计，确保：
- UI 设计质量符合生产标准
- 页面布局和交互细节在编码前明确
- 设计产出物作为前端开发的输入

---

## 八、关键技术决策说明

### 8.1 为什么选择 ChromaDB 而非 FAISS？

- ChromaDB 内置持久化和元数据过滤，开箱即用
- FAISS 需要自管理索引持久化、元数据存储，开发成本更高
- 5000 文档规模两者性能差异可忽略

### 8.2 为什么前端选择 React 而非 Vue？

- React + Ant Design 生态最成熟，表格/表单组件完善
- 公务场景需要复杂的表格操作（文件列表、筛选），Ant Design 的 Table 组件最成熟

### 8.3 为什么异步任务不用 Celery？

- 单用户本地场景，Celery + Redis 是过度设计
- FastAPI 原生 asyncio + `asyncio.create_task` 可满足需求
- 任务状态管理简单，内存字典 + 定期持久化即可

### 8.4 为什么前端选择 pnpm 而非 npm？

- pnpm 使用硬链接机制，全局 store 复用已下载的包，节省磁盘空间
- 严格的依赖隔离（非扁平 node_modules），避免幽灵依赖污染
- 与 npm 脚本完全兼容，无需修改构建配置
- 与后端 Conda 隔离策略一致，前后端各自独立管理依赖，互不干扰

### 8.5 Embedding 模型为什么选 bge-large-zh？

- 中文向量化效果在开源模型中名列前茅
- 通过 Ollama 部署简单，无需额外框架
- 1024 维向量，检索精度和存储开销平衡良好

---

*本文档为整体技术选型方案，确定技术栈和架构方向。各功能点的详细技术设计在正式开发前制定。*

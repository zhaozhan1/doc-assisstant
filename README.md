# 公文助手（Doc-Assistant）

本地化政务公文知识库与 AI 写作辅助系统。从历史文档中自动构建知识库，检索相关素材，辅助生成符合公文规范的完整初稿。

## 功能概览

### 文档导入与知识库构建

- 支持 7 种格式：`.docx` / `.pdf` / `.xlsx` / `.pptx` / `.png`+`.jpg`（OCR） / `.txt` / 压缩包（`.zip` / `.rar` / `.7z`，递归解压）
- 自动分类（13 类公文类型）、元数据提取、智能分块、向量化入库
- 增量导入：MD5 去重，未变更文件自动跳过
- 异步任务 + WebSocket 实时进度推送，支持断点续传

### 双路检索

- **本地检索**：ChromaDB 向量相似度搜索，支持按类型/时间范围过滤
- **在线检索**：Tavily / 百度搜索 API，仅发送关键词，不泄露本地文件内容
- 结果融合排序，本地优先

### AI 写作辅助

三种写作模式：

| 模式 | 说明 |
|------|------|
| **一步生成** | 自然语言描述 → 自动检索 → LLM 生成 → Word 输出 |
| **分步检索** | 手动选择参考素材 → 补充要求 → LLM 生成 → Word 输出 |
| **Word 转 PPT** | 上传 .docx → 解析结构 → LLM 总结 → 生成 .pptx |

- 12 种内置公文模板（通知、公告、请示、报告、方案、会议纪要等），支持自定义
- 输出 `.docx` 符合 GB/T 9704-2012 排版标准（方正字体 + 28 磅行距）
- SSE 流式生成，实时预览

### Web UI

- React + TypeScript + Ant Design 单页应用
- 四个核心页面：知识库 / 写作 / 模板管理 / 设置
- 文件拖拽上传、分类修正、在线配置管理

## 系统架构

```
┌─────────────────────────────────────────────┐
│              Web 前端（React）                │
│   知识库管理 / 检索 / 写作辅助 / 系统设置     │
└──────────────────┬──────────────────────────┘
                   │ HTTP / WebSocket / SSE
┌──────────────────▼──────────────────────────┐
│            Web 后端（FastAPI）                │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ 文档解析  │ │ 检索引擎  │ │ 写作辅助引擎  │ │
│  └────┬─────┘ └────┬─────┘ └──────┬───────┘ │
│  ┌────▼────────────▼──────────────▼───────┐  │
│  │        ChromaDB（本地向量数据库）        │  │
│  └────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────┘
                   │
           ┌───────┴────────┐
           │  LLM / 在线检索  │
           │  Ollama / Claude │
           └────────────────┘
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + asyncio |
| 向量数据库 | ChromaDB（本地持久化） |
| Embedding | BAAI/bge-large-zh-v1.5（通过 Ollama） |
| LLM | Ollama（默认） / Claude API（可选） / OpenAI 兼容 API |
| 文档解析 | python-docx / pdfplumber / openpyxl / python-pptx / pytesseract |
| 输出格式 | python-docx（GB/T 9704-2012）/ python-pptx |
| 前端框架 | React 18 + TypeScript + Vite |
| UI 组件库 | Ant Design 5 |
| 状态管理 | Zustand |
| 包管理 | pnpm（前端）/ Conda + pip（后端） |

## 快速开始

### 环境要求

- macOS
- Python 3.10+
- Node.js 18+ & pnpm 8+
- [Ollama](https://ollama.ai)（本地 LLM 运行）
- Tesseract OCR 5.x + 中文语言包（图片 OCR，可选）

### 后端

```bash
conda create -n doc-assistant python=3.10
conda activate doc-assistant
cd backend
pip install -e ".[dev]"

# 复制并编辑配置
cp config.yaml.example config.yaml

# 启动服务
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
pnpm install
pnpm dev
```

访问 http://localhost:5173 即可使用。

### 运行测试

```bash
# 后端（10 路并行）
cd backend
pytest -n 10

# 前端
cd frontend
pnpm test
```

### 打包为 macOS .app

```bash
./build.sh      # 后端 PyInstaller 打包
./build-dmg.sh  # 生成 .dmg 安装镜像
```

## 项目结构

```
doc-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # Pydantic 配置管理
│   │   ├── ingestion/           # 文档导入模块
│   │   ├── retrieval/           # 检索模块
│   │   ├── generation/          # 写作辅助模块
│   │   ├── llm/                 # LLM Provider 抽象层
│   │   ├── api/                 # REST API 路由
│   │   └── db/                  # 向量数据库封装
│   ├── tests/                   # 测试（303 tests）
│   ├── config.yaml.example      # 配置模板
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── pages/               # 页面组件
│   │   ├── components/          # 通用组件
│   │   ├── stores/              # Zustand 状态管理
│   │   └── api/                 # API 调用封装
│   └── package.json
└── docs/                        # 项目文档
```

## 安全边界

| 原则 | 说明 |
|------|------|
| 原始文件不出本地 | 解析、向量化、索引全部本地完成 |
| 在线检索仅发关键词 | 不携带任何本地文件内容 |
| API Key 本地存储 | 配置文件中的密钥不离开本机 |

## License

MIT

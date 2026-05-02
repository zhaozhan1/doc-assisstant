# CLAUDE.md

## 项目概况

公文助手（Doc-Assistant）— 本地化政务公文知识库与 AI 写作辅助系统。单用户、单机部署，从历史文档自动构建知识库，辅助生成符合公文规范的初稿。

**当前状态**：阶段四（Web UI）编码完成，分支 `feature/web-ui` 待合并到 main。

## 常用命令

```bash
conda activate doc-assistant
cd backend
pip install -e ".[dev]"          # 安装依赖
ruff check app/ tests/           # Lint
ruff format --check app/ tests/  # 格式检查
pytest                           # 测试
pytest --cov=app                 # 覆盖率
uvicorn app.main:app --reload --port 8000  # 启动

cd frontend
pnpm install && pnpm dev         # 前端开发
pnpm build && pnpm test && pnpm lint
```

## 架构

单体 Web 应用：FastAPI 后端（ingestion/retrieval/generation/llm）+ React 前端（知识库/写作/模板/设置）+ ChromaDB 向量库。Embedding 用 Ollama（bge-large-zh-v1.5），Chat 用 Ollama（qwen2.5）或 Claude API。

数据流：文件导入 → 解压/提取/分类/分块/向量化 → 入库 → 检索 → Prompt → LLM → Word/PPT

## 关键约束

- **安全边界**：原始文件不出本地，在线检索仅发关键词
- **本地 LLM 为主**：Ollama 默认，Claude 可选
- **输出格式**：Word 须符合 GB/T 9704-2012 排版标准
- **平台**：macOS，路径用 `pathlib.Path`
- **异步任务**：asyncio + WebSocket，不用 Celery

## 代码规范

- **后端**：PEP8，`ruff` 作 Linter/Formatter，审查前须通过 `ruff check` + `ruff format --check`
- **前端**：TypeScript Strict，ESLint + Prettier，审查前须通过 `pnpm lint`
- **Shell**：禁止 `cd xxx && git ...`，用 `git -C <路径> <命令>`

## 开发方法论

- **TDD**：Red-Green-Refactor，覆盖率 ≥ 80%
- **5 阶段交付**：文档解析 → 检索引擎 → 写作辅助 → Web UI → 优化加固
- **Web UI 前**：须调用 `/frontend-design` skill

## 设计文档

`docs/product/deliverable/` — 产品设计、技术选型、各阶段技术设计
`docs/product/raw/` — 各阶段功能点拆分

## 依赖环境

Conda `doc-assistant`（Python 3.10+），pnpm（Node.js 18+），Tesseract OCR 5.x + 中文包，Ollama。

## 项目特定规则

1. **文档路径** — 不使用 skill 默认路径，须放 `docs/` 目录规范内
2. **`.claudeignore`** — 不得读取其中列出的文件内容
3. **文档语言** — zh-CN

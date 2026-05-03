# CLAUDE.md

## 项目概况

公文助手（Doc-Assistant）— 本地化政务公文知识库与 AI 写作辅助系统。单用户、单机部署，从历史文档自动构建知识库，辅助生成符合公文规范的初稿。

**当前状态**：阶段五（Word 转 PPT + 优化与加固）已完成并合并到 main。全部 5 个阶段交付完成。

## 常用命令

```bash
conda activate doc-assistant
cd backend
pip install -e ".[dev]"          # 安装依赖
ruff check app/ tests/           # Lint
ruff format --check app/ tests/  # 格式检查
pytest -n 10                     # 测试（10 路并行）
pytest --cov=app                 # 覆盖率
uvicorn app.main:app --reload --port 8000  # 启动

cd frontend
pnpm install && pnpm dev         # 前端开发
pnpm build && pnpm test && pnpm lint
```

## 架构

单体 Web 应用：FastAPI 后端（ingestion/retrieval/generation/llm）+ React 前端（知识库/写作/模板/设置/Word→PPT）+ ChromaDB 向量库。Embedding 用 Ollama（bge-large-zh-v1.5），Chat 用 Ollama（qwen2.5）或 Claude API。

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

## PyInstaller 打包规则

4. **数据文件清单** — Python 包的数据文件（模板、XML、配置）不会自动打入 .app，须在 `doc-assistant.spec` 的 `datas` 中显式声明。新增依赖后检查其是否携带数据文件。
5. **路径必须走 `resolve_path`** — 配置文件、数据库、日志等运行时路径必须通过 `app.paths.resolve_path()` 解析。`AppConfig` 须传 `_yaml_file=resolve_path("config.yaml")`，确保 .app 从 `~/Library/Application Support/doc-assistant/` 加载。
6. **绝对路径调用外部命令** — .app 环境的 PATH 仅含 `/usr/bin:/bin:/usr/sbin:/sbin`，调用系统命令（如 textutil）须用 `shutil.which()` 回退绝对路径。
7. **构建后验证** — `pyinstaller` 构建后须检查：关键数据文件是否在 bundle 中（`find dist/公文助手.app -name "..."`）、配置路径是否一致。

## Debug 规则（.app 环境）

8. **先读完整 traceback** — structlog JSON 日志中 `exc_info` 可能丢失调用栈。如果 traceback 不完整，先加 `traceback.format_exc()` 明确输出。
9. **在目标环境验证** — .app 内部环境（PyInstaller、frozen CWD、精简 PATH）与 dev 环境有本质差异。本地测试通过不等于 .app 正确。优先在 .app 日志中确认假设。
10. **逐层追踪数据流** — 从最终失败点向前追踪每一层数据流，找到第一个产出错误数据的层。禁止只看症状就假设根因。

# CLAUDE.md

## 项目概况

公文助手（Doc-Assistant）— 本地化政务公文知识库与 AI 写作辅助系统。单用户、单机部署。

**当前状态**：全部 5 阶段交付完成 + 生产部署 + .app 打包 + 流式下载 + 在线搜索修复完成。

## 常用命令

```bash
conda activate doc-assistant
cd backend
pip install -e ".[dev]"
ruff check app/ tests/ && ruff format --check app/ tests/
pytest -n 10                     # 10 路并行
uvicorn app.main:app --reload --port 8000

cd frontend
pnpm install && pnpm dev
pnpm build && pnpm test && pnpm lint
```

## 架构

单体 Web 应用：FastAPI 后端（ingestion/retrieval/generation/llm）+ React 前端 + ChromaDB 向量库。

数据流：文件导入 → 解压/提取/分类/分块/向量化 → 入库 → 检索 → Prompt → LLM → Word/PPT

## 关键约束

- **安全边界**：原始文件不出本地，在线检索仅发关键词
- **本地 LLM 为主**：Ollama 默认，Claude 可选
- **输出格式**：Word 须符合 GB/T 9704-2012 排版标准
- **平台**：macOS，`pathlib.Path`
- **异步任务**：asyncio + WebSocket，不用 Celery

## 代码规范

- **后端**：`ruff check` + `ruff format --check`
- **前端**：`pnpm lint`
- **Shell**：`git -C <路径> <命令>`，禁止 `cd && git`

## 开发方法论

- **TDD**：Red-Green-Refactor，覆盖率 ≥ 80%
- **Web UI 前**：须调用 `/frontend-design` skill

## 设计文档

`docs/product/deliverable/` — 产品设计、技术选型、各阶段技术设计

## 项目规则

1. **文档路径** — 不使用 skill 默认路径，须放 `docs/` 目录规范内
2. **`.claudeignore`** — 不得读取其中列出的文件内容

## PyInstaller 打包

3. **数据文件** — 须在 `.spec` 的 `datas` 中显式声明，新依赖后检查
4. **路径走 `resolve_path`** — 配置从 `~/Library/Application Support/doc-assistant/` 加载
5. **外部命令用绝对路径** — .app PATH 精简，用 `shutil.which()` 回退
6. **构建后验证** — `find dist/公文助手.app -name "..."` 确认关键文件

## Debug（.app 环境）

7. **逐层追踪** — 从失败点向前逐层追踪数据流，找到第一个产出错误数据的层

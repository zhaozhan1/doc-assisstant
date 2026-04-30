# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概况

公文助手（Doc-Assistant）— 本地化政务公文知识库与 AI 写作辅助系统。单用户、单机部署，从历史文档自动构建知识库，辅助生成符合公文规范的初稿。

**当前状态**：前期设计完成，尚未开始编码。

## 常用命令

```bash
# 环境准备
conda activate doc-assistant

# 后端
cd backend
pip install -e ".[dev]"          # 安装依赖（含开发依赖）
pytest                           # 运行全部测试
pytest tests/test_ingestion/     # 运行指定模块测试
pytest -x                        # 遇到失败即停止
pytest --cov=app                 # 测试覆盖率

# 后端启动
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
pnpm install                      # 安装依赖
pnpm dev                          # 开发服务器
pnpm build                        # 生产构建
pnpm test                         # 前端测试
```

## 架构

单体 Web 应用，三层结构：

- **后端（FastAPI）**：4 个核心模块 — `ingestion/`（文档解析）、`retrieval/`（检索）、`generation/`（写作辅助）、`llm/`（LLM Provider 抽象层）
- **前端（React + TypeScript + Vite + Ant Design）**：4 个页面 — 知识库、写作、模板管理、设置
- **数据层**：ChromaDB 本地向量数据库，Embedding 通过 Ollama（bge-large-zh-v1.5），Chat 通过 Ollama（qwen2.5）或 Claude API

数据流：文件导入 → 解压/提取/分类/分块/向量化 → 入库 → 检索 → Prompt 构建 → LLM 生成 → Word/PPT 输出

## 关键约束

- **安全边界**：原始文件不出本地，在线检索仅发关键词
- **本地 LLM 为主**：Ollama 默认，Claude 可选，通过 config.yaml 切换 Provider/Base URL
- **输出格式**：Word 输出须符合 GB/T 9704-2012 排版标准（字体、行距、缩进）
- **平台**：macOS，文件路径用 `pathlib.Path`，压缩包用 Python 库处理
- **异步任务**：文档导入用 asyncio + WebSocket 进度推送，不用 Celery

## 开发方法论

- **TDD**：所有功能点按 Red-Green-Refactor 循环开发，测试覆盖率 ≥ 80%
- **5 阶段交付**：项目基础+文档解析 → 检索引擎 → 写作辅助 → Web UI → 优化加固
- **阶段四 Web UI 前**：须调用 `/frontend-design` skill 指导界面设计

## 设计文档

- `docs/product/deliverable/2026-04-30-product-design.md` — 整体产品设计（功能边界、模块设计、页面设计）
- `docs/product/deliverable/2026-04-30-tech-overview.md` — 技术选型（技术栈、目录结构、config.yaml 规格）
- `docs/product/raw/2026-04-30-feature-01~05-*.md` — 各阶段功能点拆分（待分阶段审核）

## 依赖环境

Conda 环境 `doc-assistant`（Python 3.10+），前端包管理使用 pnpm（隔离依赖，避免与本机其他项目冲突）。外部依赖：Node.js 18+、pnpm 8+、Tesseract OCR 5.x + 中文语言包、Ollama。

## 文档规范

本项目使用标准文档目录结构（`docs/`），遵循全局工作流规范（见 `~/.claude/CLAUDE.md`）。

- 产品文档：`docs/product/`（context/deliverable/raw/tools）
- 开发文档：`docs/development/`（todo/doing/done）
- Debug 文档：`docs/debug/`（todo/doing/done）
- 命名规则：`YYYY-MM-DD-<topic>.md`

## 流程执行检查点

1. **分支检查** — 编码前确认：当前在 `master` → `master` 包含所有已合并功能 → 新分支 `feature/<topic>` 名称正确
2. **文档路径** — 所有文档必须放置于 `docs/` 目录规范内，不使用 skill 默认路径
3. **文档流转** — 计划文档严格执行 `todo/ → doing/ → done/` 文件移动
4. **TDD 模式** — 所有功能点按 Red-Green-Refactor 循环开发，先写测试再写实现
5. **`.claudeignore` 遵守** — 搜索和读取文件时必须遵守 `.claudeignore`，不得读取或包含其中所列文件的内容（依赖目录、构建产物、数据目录、环境变量文件等）

## 工作流步骤配置

- **语言/框架**：Python (FastAPI) + TypeScript/React (Vite + Ant Design)
- **文档语言**：zh-CN
- **排除步骤**：无（全部保留）

# 规则参考手册

CLAUDE.md 中仅保留触发器格式的精简规则和决策检查点。本文档提供详细背景、Why/How 和完整流程步骤。

---

## 决策检查点背景

### 编码前：用户已审批？

**Why**：百度搜索被实现为 HTML 爬虫（selectolax 解析 baidu.com/s），完全不可行——百度有反爬机制，HTTP 302 跳转到验证码页。该方案从未提交用户审批，违反"禁止自行编码"规则。阶段五 commit 中包含 5 个功能，百度搜索的错误方案混在批量交付中未被逐项审查。

**How**：任何功能编码前，先输出技术方案交用户确认。外部服务集成（搜索 API、OAuth、支付）尤其需要确认技术路线。一次交付多个功能时，每个功能的技术方案须单独确认，不能打包审批。

### 敏感字段修复前：全局扫描？

**Why**：LLM api_key 空字符串覆盖已修复（跳过 `""`），但同文件的 `update_online_search_config()` 遗漏了相同保护。同类问题在并行函数中一有一无。

**How**：`grep -rn 'api_key\|secret\|password' backend/app/ --include='*.py'` 扫描所有处理点，逐一确认保护状态。

### Debug 前：traceback → dev？

**Why**：在线搜索 debug 中，多次凭症状猜测根因（先是掩码、再是 auth header、再是 domain filter），没有先读完整 traceback。同时，API 401 可以 curl 在 dev 复现，却反复构建 .app 浪费大量时间。

**How**：先读完整调用栈定位真正的失败点。评估 dev 环境（curl/pytest/uvicorn）能否复现，能则先在 dev 排查。

### 诊断日志：一次加够？

**Why**：在线搜索 debug 重复了 4-5 次"加一处日志→构建→用户操作→拉日志→发现新问题"的循环，每次构建 3 分钟。

**How**：沿完整调用链（前端请求 → API 路由 → service → provider → HTTP 响应）一次加够诊断日志。

---

## Karpathy 准则

1. **Think Before Coding** — 不假设，不隐藏困惑，不确定就问，多解读全呈现
2. **Simplicity First** — 最少代码解决问题，不投机，单次使用不做抽象
3. **Surgical Changes** — 只触碰必须修改的部分，不顺手优化，匹配已有风格
4. **Goal-Driven Execution** — 定义成功标准，任务转化为可验证目标，多步骤先列计划+检查点

---

## 开发流程（完整步骤）

| 步骤 | 动作 | 产出/门禁 |
|------|------|-----------|
| 1. 需求收集 | 需求不清晰→`/brainstorming` | `docs/product/raw/` |
| 2. 需求确认 | 用户审查 | 需求文档→`deliverable/` |
| 3. 开发计划 | 拉取 `feature/<topic>` 分支 | `docs/development/todo/` |
| 4. 审批门禁 | **⚠ 用户明确同意方可编码** | 计划文档→`doing/` |
| 5. 编码实现 | 按计划实现；前端 UI→`/frontend-design` | — |
| 6. 代码审查 | `/code-review` | 通过→继续 |
| 7. 构建验证 | 运行构建命令 | 通过→继续 |
| 8. 安全审查 | **显式提示**用户是否需要 | 按用户选择 |
| 9. 完成确认 | 用户确认完成 | 文档→`done/` |
| 10. 清理归档 | **⚠ 用户确认后**：删除分支、清理、更新 memory | 环境干净 |

## Debug 流程（完整步骤）

| 步骤 | 动作 | 产出/门禁 |
|------|------|-----------|
| 1. 了解现状 | 阅读 `deliverable/`、开发文档 | — |
| 2. 系统调试 | `/systematic-debugging` | 定位根因 |
| 3. Debug 计划 | 拉取 `bugfix/<topic>` 分支 | `docs/debug/todo/` |
| 4. 审批门禁 | **⚠ 用户明确同意方可编码** | 计划文档→`doing/` |
| 5. 编码修复 | 按计划实施 | — |
| 6. 代码审查 | `/code-review` | 通过→继续 |
| 7. 构建验证 | 运行构建命令 | 通过→继续 |
| 8. 安全审查 | **显式提示**用户是否需要 | 按用户选择 |
| 9. 完成确认 | 用户确认解决 | 文档→`done/` |
| 10. 清理归档 | **⚠ 用户确认后**：删除分支、清理、更新 memory | 环境干净 |

---

## 文档目录规范

```
docs/
├── product/
│   ├── context/      # 用户输入、背景（仅供参考）
│   ├── deliverable/  # 确认进入开发的文档
│   ├── raw/          # 中间产物、实验文档
│   └── tools/        # 可复用工具、流程
├── development/
│   ├── todo/ doing/ done/
└── debug/
    ├── todo/ doing/ done/
```

- **命名**：`YYYY-MM-DD-<topic>.md`
- **流转**：状态变更时实际移动文件（todo→doing→done）
- **产品流转**：`raw/`（用户审查确认）→ `deliverable/`。`context/` 仅供参考，不可直接进入 `deliverable/`

---

## PyInstaller 打包规则详解

3. **数据文件清单** — Python 包的数据文件（模板、XML、配置）不会自动打入 .app，须在 `doc-assistant.spec` 的 `datas` 中显式声明。新增依赖后检查其是否携带数据文件。

4. **路径必须走 `resolve_path`** — 配置文件、数据库、日志等运行时路径必须通过 `app.paths.resolve_path()` 解析。`AppConfig` 须传 `_yaml_file=resolve_path("config.yaml")`，确保 .app 从 `~/Library/Application Support/doc-assistant/` 加载。

5. **绝对路径调用外部命令** — .app 环境的 PATH 仅含 `/usr/bin:/bin:/usr/sbin:/sbin`，调用系统命令（如 textutil）须用 `shutil.which()` 回退绝对路径。

6. **构建后验证** — `pyinstaller` 构建后须检查：关键数据文件是否在 bundle 中（`find dist/公文助手.app -name "..."`）、配置路径是否一致。

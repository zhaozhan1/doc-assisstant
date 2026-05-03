# 阶段四分项技术方案 — Web UI

**版本**: v1.0
**日期**: 2026-05-02
**状态**: 已确认
**关联文档**: [功能点拆分](2026-04-30-feature-04-web-ui.md) | [技术选型方案](2026-04-30-tech-overview.md) | [阶段三技术方案](2026-05-01-tech-design-phase-3.md)

---

## 一、核心设计决策

| # | 决策点 | 方案 | 理由 |
|---|--------|------|------|
| 1 | 视觉基调 | 简洁现代（Notion/Linear 风格） | 降低公文写作心理门槛，同时保持专业感 |
| 2 | 导航方式 | 固定展开侧边栏（200px） | 4 个页面项不复杂，侧栏视觉层次清晰 |
| 3 | 配色方案 | Ant Design 默认（冷灰蓝系） | 零定制成本，专业稳重，适合办公场景 |
| 4 | 写作页面布局 | 左右分栏（左输入 + 右预览） | 生成过程中可边看边等，空间利用最高效 |
| 5 | 分步检索流程 | 写作方向 → 关键词（可选）→ 检索 → 勾选 → 补充要求 → 生成 | 用户先明确意图，再精细化检索 |
| 6 | Word→PPT 输入源 | 三种：上传本地 / 知识库选择 / 本次生成文档 | 覆盖所有 Word 来源场景 |
| 7 | 开发策略 | 后端先行 | 补全 API 缺口后前端无阻碍开发 |
| 8 | 进度推送 | WebSocket（双向，支持 cancel） | 导入进度需要双向通信 |
| 9 | 流式生成 | 复用已有 SSE 端点 | `/api/generation/generate/stream` 已实现 |
| 10 | Word 模板 | 支持 .dotx 模板路径配置 | 用户可自定义输出样式，与国标结合 |

---

## 二、整体架构

### 布局骨架

```
┌──────────┬──────────────────────────────────────┐
│ 公文助手  │                                      │
│          │                                      │
│ 📚 知识库 │          页面内容区                    │
│ ✏️ 写作   │                                      │
│ 📋 模板   │                                      │
│ ⚙️ 设置   │                                      │
│          │                                      │
│──────────│                                      │
│ v0.1.0   │                                      │
└──────────┴──────────────────────────────────────┘
```

### 路由结构

```
/               → 重定向到 /knowledge-base
/knowledge-base → 知识库页面
/writing        → 写作页面
/templates      → 模板管理页面
/settings       → 设置页面
```

### 技术栈

| 层面 | 技术 |
|------|------|
| 框架 | React 18 + TypeScript + Vite |
| UI 库 | Ant Design 5（默认主题） |
| 状态管理 | Zustand |
| HTTP 客户端 | Axios |
| 路由 | React Router v6 |
| WebSocket | 原生 WebSocket API |
| SSE | EventSource / fetch stream |
| Markdown 渲染 | react-markdown |
| 包管理 | pnpm |

### 前端目录结构

```
frontend/src/
├── api/                     # Axios 实例 + 各模块 API
│   ├── client.ts            # Axios 实例 + 拦截器（统一错误处理）
│   ├── files.ts             # 文件管理 API
│   ├── search.ts            # 检索 API
│   ├── generation.ts        # 生成 API（含 SSE 封装）
│   ├── templates.ts         # 模板 API
│   └── settings.ts          # 设置 API
├── hooks/                   # 自定义 Hooks
│   ├── useWebSocket.ts      # WebSocket 连接管理
│   └── useSSE.ts            # SSE 流式读取
├── stores/                  # Zustand 状态管理
│   ├── useFileStore.ts      # 文件列表 + 分页
│   ├── useTaskStore.ts      # 导入任务状态
│   ├── useWritingStore.ts   # 写作页面状态
│   └── useSettingsStore.ts  # 设置表单状态
├── pages/                   # 页面组件
│   ├── KnowledgeBase/
│   │   └── index.tsx
│   ├── Writing/
│   │   ├── index.tsx
│   │   ├── OneStepMode.tsx
│   │   ├── StepByStepMode.tsx
│   │   └── WordToPptMode.tsx
│   ├── TemplateManager/
│   │   ├── index.tsx
│   │   └── TemplateEditor.tsx
│   └── Settings/
│       └── index.tsx
├── components/              # 通用组件
│   ├── Layout/
│   │   └── index.tsx        # 侧边栏 + 内容区布局
│   ├── ImportProgress.tsx   # 导入进度条/结果摘要
│   └── SourceList.tsx       # 素材来源清单
├── types/                   # TypeScript 类型定义
│   └── api.ts               # 后端接口类型映射
├── App.tsx                  # 路由配置
└── main.tsx                 # 入口
```

### Vite 代理配置

```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
});
```

---

## 三、F4.1 后端 API 缺口

### 已有端点（无需修改）

| 模块 | 端点 |
|------|------|
| 文件管理 | `GET /api/files`, `DELETE /api/files/{path}`, `POST .../reindex`, `PUT .../classification` |
| 检索 | `POST /api/search`, `POST /api/search/local` |
| 生成 | `POST /api/generation/generate`, `POST .../generate/stream` |
| 模板 | `GET/POST/PUT/DELETE /api/templates` |
| 设置 | `GET/PUT /api/settings/online-search`, `POST .../test-connection` |
| 健康检查 | `GET /health` |

### 新增端点

| 方法 | 路径 | 功能 |
|------|------|------|
| `POST` | `/api/files/upload` | 文件上传（multipart/form-data）→ 返回 task_id |
| `GET` | `/api/files/download/{path}` | 文件下载（FileResponse） |
| `WebSocket` | `/ws/tasks/{task_id}` | 任务进度实时推送 + cancel 指令 |
| `GET` | `/api/settings/knowledge-base` | 知识库配置读取 |
| `PUT` | `/api/settings/knowledge-base` | 知识库配置更新 |
| `GET` | `/api/settings/llm` | LLM 配置读取 |
| `PUT` | `/api/settings/llm` | LLM 配置更新 |
| `GET` | `/api/settings/generation` | 输出配置读取 |
| `PUT` | `/api/settings/generation` | 输出配置更新 |
| `GET` | `/api/settings/files/browse` | 目录浏览（路径选择器用） |
| `GET` | `/api/stats` | 知识库统计（文件总数/类型分布/最后更新） |

### 新增中间件

| 中间件 | 功能 |
|--------|------|
| `ExceptionMiddleware` | 统一异常 → `{error, detail}` JSON 响应 |
| `CORSMiddleware` | 仅开发环境，允许 localhost:5173 |

### 后端文件变更

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `api/routes/files.py` | 修改 | +upload, +download |
| `api/routes/settings.py` | 修改 | +KB/LLM/Generation 配置端点, +目录浏览 |
| `api/routes/stats.py` | 新增 | 知识库统计 API |
| `api/routes/ws.py` | 新增 | WebSocket 任务进度 |
| `api/middleware.py` | 新增 | 统一错误处理中间件 |
| `api/deps.py` | 修改 | 新增 get_task_manager、get_ingester 依赖 |
| `models/search.py` | 修改 | 新增 KBStats、KBStatsResponse |
| `settings_service.py` | 修改 | 扩展支持全部配置节 |
| `main.py` | 修改 | 注册中间件 + WS 路由 + CORS |
| `config.py` | 修改 | GenerationConfig 新增 word_template_path |

### WebSocket 协议

服务端 → 客户端：
```json
{"type": "progress", "data": {"task_id":"...", "status":"running", "total":100, "processed":45, "success":42, "failed":2, "skipped":1, "current_file":"..."}}
{"type": "completed", "data": {"task_id":"...", "status":"completed", "total":100, "success":95, "failed":3, "skipped":2}}
```

客户端 → 服务端：
```json
{"type": "cancel"}
```

### 统一错误响应

```json
{"error": "NOT_FOUND", "detail": "模板 custom_xxx 不存在"}
```

| HTTP 状态码 | error 值 | 场景 |
|-------------|----------|------|
| 400 | `BAD_REQUEST` | 参数校验失败 |
| 404 | `NOT_FOUND` | 资源不存在 |
| 409 | `CONFLICT` | 内置模板不可删除/修改 |
| 422 | `VALIDATION_ERROR` | Pydantic 校验失败 |
| 500 | `INTERNAL_ERROR` | 未预期异常 |

---

## 四、F4.3 知识库页面

### 页面布局（从上到下）

```
┌─────────────────────────────────────────────────┐
│ 统计卡片：[文件总数] [类型分布] [最后更新时间]     │
├─────────────────────────────────────────────────┤
│ 上传区域：拖拽 / 选择文件 / 选择文件夹            │
├─────────────────────────────────────────────────┤
│ 导入进度条（导入中显示，完成后变为结果摘要卡片）   │
├─────────────────────────────────────────────────┤
│ 筛选：[类型▼] [时间范围]     排序：[时间/名称▼]   │
├─────────────────────────────────────────────────┤
│ 文件列表表格（分页）                              │
│ 文件名 | 类型标签 | 日期 | 分块数 | 操作          │
└─────────────────────────────────────────────────┘
```

### 关键交互

| 功能 | 实现方式 |
|------|----------|
| 上传 | Ant Design Upload Dragger，支持文件 + 文件夹 |
| 导入进度 | WebSocket `/ws/tasks/{task_id}` 实时推送 |
| 导入完成 | 进度条位置变为结果摘要卡片（绿色左边框），显示成功/失败/跳过计数 |
| 失败详情 | 摘要卡片内折叠展开，显示文件名 + 失败原因 + 重新索引操作 |
| 关闭摘要 | 手动关闭，不自动消失 |
| 文件列表 | Ant Design Table，分页/筛选/排序 |
| 分类修正 | 操作列点击「修正」→ 行内 Select 下拉 |
| 删除/重新索引 | Popconfirm 二次确认 |

### 组件映射

| 组件 | Ant Design |
|------|------------|
| 统计卡片 | `Statistic` + `Card`（3 张横排） |
| 上传区域 | `Upload.Dragger` |
| 进度条 | `Progress` |
| 结果摘要 | 自定义卡片组件 `ImportProgress` |
| 文件表格 | `Table` |
| 筛选 | `Select` + `DatePicker.RangePicker` |
| 操作确认 | `Popconfirm` |
| 分类修正 | `Select`（行内编辑） |

### 数据流

```
Upload → POST /api/files/upload → task_id
  → WebSocket /ws/tasks/{task_id} → 进度更新
  → completed → 结果摘要卡片展示
  → 手动关闭 → 刷新文件列表 GET /api/files + 统计 GET /api/stats
```

---

## 五、F4.4 写作页面

### 整体布局

左右分栏：左侧输入控制区（flex: 1），右侧预览输出区（flex: 1.2）。

上方 3 个模式切换按钮（SegmentedControl 风格）：一步生成 / 分步检索 / Word→PPT。

### 模式 A — 一步生成

**左侧**：
- 写作需求输入框（TextArea，自然语言描述）
- 模板选择（可选，Select 下拉，默认"自动选择"）
- 生成按钮

**右侧**：
- 生成前：占位提示
- 生成中：流式 Markdown 渲染 + 打字光标 + "正在生成..." 状态
- 生成后：完整预览 + 下载 .docx 按钮 + 素材来源计数

**数据流**：
```
描述 → POST /api/generation/generate/stream (SSE)
  → 逐 token 渲染到预览区
  → [DONE] → 显示下载按钮 + 来源清单
```

### 模式 B — 分步检索

**左侧（从上到下）**：
1. **写作方向**（必填）：TextArea，描述公文主题和重点
2. **检索关键词**（可选）：Tag 输入模式，留空则后端从写作方向自动提取
3. **检索按钮**：POST /api/search → 展示结果列表
4. **检索结果列表**：Checkbox 勾选，每条显示文件名 + 片段预览 + 来源标签（本地/在线）+ 相关度
5. **已选素材计数**
6. **补充写作要求**（可选）：TextArea
7. **生成按钮**

**右侧**：同模式 A（等待 → 流式预览 → 下载）

**数据流**：
```
写作方向 + 关键词 → POST /api/search → 展示结果
勾选素材 + 补充要求 → POST /api/generation/generate/stream (selected_refs)
  → 流式预览 + 下载
```

### 模式 C — Word→PPT

**左侧**：三种输入源（Tab 切换）
- **上传文件**（默认）：拖拽/点击上传本地 .docx 文件
- **知识库选择**：搜索/浏览已导入的 .docx 文件列表
- **本次生成**：展示当前会话中由模式 A/B 生成的文档列表

生成按钮灰色禁用 + "后续版本支持"提示（阶段五实现）。

### 生成完成后状态（所有模式通用）

**左侧**：
- 原始输入（可修改后点击"重新生成"）
- 素材来源清单：本地文件（文件名 + 日期）、在线资料（标题 + URL）

**右侧**：
- 完整预览内容
- 下载 .docx 按钮（蓝色激活）

### 关键组件

| 组件 | 说明 |
|------|------|
| 模式切换 | Ant Design `Segmented` 或 3 个 Button |
| 输入框 | `Input.TextArea` |
| 关键词输入 | `Select` mode="tags" |
| 模板选择 | `Select` |
| 检索结果 | `List` + `Checkbox` |
| 流式预览 | `react-markdown` 实时渲染 |
| 来源清单 | 自定义 `SourceList` 组件 |
| 下载按钮 | `Button` + 文件下载逻辑 |

---

## 六、F4.5 模板管理页面

### 页面布局

```
┌─────────────────────────────────────────────────┐
│ 筛选：[全部] [内置] [自定义]      [+ 新建模板]    │
├─────────────────────────────────────────────────┤
│ 内置模板（12）                                   │
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐            │
│ │ 通知  │ │ 公告  │ │ 请示  │ │ 报告  │  ...     │
│ │ [内置]│ │ [内置]│ │ [内置]│ │ [内置]│          │
│ │ 查看→ │ │ 查看→ │ │ 查看→ │ │ 查看→ │          │
│ └──────┘ └──────┘ └──────┘ └──────┘            │
│                                                 │
│ 自定义模板（2）                                   │
│ ┌- - - - ┐ ┌- - - - ┐                          │
│ │ 表彰通报│ │ 专项方案│                          │
│ │[自定义] │ │[自定义] │                          │
│ │查看 编辑│ │查看 编辑│                          │
│ │删除     │ │删除     │                          │
│ └- - - - ┘ └- - - - ┘                          │
└─────────────────────────────────────────────────┘
```

内置模板：实线边框卡片，仅"查看详情"。
自定义模板：虚线边框卡片，支持查看/编辑/删除。

### 模板编辑器（Modal 弹窗）

| 字段 | 组件 | 说明 |
|------|------|------|
| 模板名称 | `Input` | |
| 公文类型 | `Select` | 下拉选择 |
| 结构大纲 | 动态表单 | 可增删段落 |

段落编辑结构：
- 段落标题（Input）
- 写作要点（Tag 模式，可增删）
- 格式规范（Tag 模式，可增删）
- 删除段落按钮

底部：+ 添加段落 → 取消 / 保存

---

## 七、F4.6 设置页面

### 页面布局

4 个 Tab：知识库 / LLM / 在线检索 / 输出。每个 Tab 独立保存。

### 知识库配置

| 字段 | 组件 | 默认值 |
|------|------|--------|
| 源文件夹路径 | `Input` + 浏览按钮（目录浏览 Modal） | 空 |
| 数据库路径 | `Input` | `./data/chroma_db` |
| 分块大小 | `InputNumber` | 500 |
| 分块重叠 | `InputNumber` | 50 |

### LLM 配置

| 字段 | 组件 | 说明 |
|------|------|------|
| Provider | `Radio`（Ollama / Claude） | 切换后显示对应字段 |
| Base URL | `Input` | 根据 Provider 填默认值 |
| Chat 模型 | `Input` | 手动输入模型名 |
| Embed 模型 | `Input` | 仅 Ollama 显示 |
| API Key | `Input.Password` | 仅 Claude 显示 |

### 在线检索配置

| 字段 | 组件 | 默认值 |
|------|------|--------|
| 启用开关 | `Switch` | 关 |
| Provider | `Select`（Tavily） | Tavily |
| API Key | `Input.Password` | 空 |
| 优先域名 | `Select` mode="tags" | gov.cn, npc.gov.cn, moj.gov.cn |
| 最大结果数 | `InputNumber` | 3 |

### 输出配置

| 字段 | 组件 | 默认值 |
|------|------|--------|
| 默认格式 | `Radio`（docx / md） | docx |
| 保存路径 | `Input` + 浏览按钮 | `./output` |
| Word 模板路径 | `Input` + 浏览按钮（.dotx 文件） | 空（可选） |
| 附带素材来源 | `Switch` | 开 |

**Word 模板说明**：配置 .dotx 文件路径后，生成 Word 文档时优先使用该模板样式，无模板时回退到内置 GB/T 9704-2012 排版。

### 保存逻辑

- 每个 Tab 独立保存（`PUT /api/settings/{section}`）
- 保存成功 → `message.success`
- API Key 等敏感字段：读取时脱敏，空值表示不变更

### 后端配置变更

`config.py` 中 `GenerationConfig` 新增：

```python
class GenerationConfig(BaseModel):
    output_format: str = "docx"
    save_path: str = "./output"
    include_sources: bool = True
    max_prompt_tokens: int = 4096
    word_template_path: str = ""  # 新增：.dotx 模板路径
```

`config.yaml` 新增：

```yaml
generation:
  word_template_path: ""  # 可选，.dotx Word 模板文件路径
```

---

## 八、测试策略

### 后端新增测试

| 测试文件 | 覆盖范围 |
|----------|----------|
| `test_file_upload.py` | 文件上传（multipart）、大小限制、格式过滤 |
| `test_file_download.py` | 文件下载、路径安全校验 |
| `test_ws_tasks.py` | WebSocket 连接、进度推送、cancel 指令 |
| `test_settings_kb.py` | 知识库配置读写 |
| `test_settings_llm.py` | LLM 配置读写 |
| `test_settings_gen.py` | 输出配置读写（含 word_template_path） |
| `test_stats.py` | 统计 API |
| `test_middleware.py` | 统一错误处理 |

### 前端测试

| 类型 | 工具 | 范围 |
|------|------|------|
| 单元测试 | Vitest | stores、hooks、API 层 |
| 组件测试 | Vitest + Testing Library | 页面组件渲染、交互 |

---

## 九、开发顺序

```
Sprint 1：F4.1 后端缺口补全（~2 天）
  ├── 文件上传/下载端点
  ├── WebSocket 任务进度
  ├── 完整 Settings API（KB/LLM/Generation + 目录浏览）
  ├── 统计 API
  ├── 统一错误处理中间件 + CORS
  └── GenerationConfig 新增 word_template_path

Sprint 2：F4.2 前端项目搭建（~1 天）
  ├── Vite + React + TS 初始化 + 依赖安装
  ├── Ant Design 配置 + 全局样式
  ├── 侧边栏布局组件 + React Router 路由
  ├── Axios 实例 + API 层骨架
  ├── 4 个空页面占位
  └── Zustand stores 骨架

Sprint 3：F4.3 知识库页面（~2 天）
  ├── 统计卡片
  ├── 上传 + 进度（WebSocket）
  ├── 导入结果摘要 + 失败详情折叠
  ├── 文件列表 + 筛选/排序/分页
  └── 操作：重新索引/删除/分类修正

Sprint 4：F4.4 写作页面（~2.5 天）
  ├── 模式 A：一步生成（流式预览 + 下载 + 来源清单）
  ├── 模式 B：分步检索（写作方向 + 关键词 + 检索 + 勾选 + 要求）
  ├── 模式 C：Word→PPT 占位（3 种输入源）
  └── 生成完成后状态（重新生成 + 来源清单）

Sprint 5：F4.5 模板管理（~1.5 天）
  ├── 模板列表（内置/自定义筛选 + 卡片网格）
  └── 模板编辑器 Modal（结构大纲动态表单）

Sprint 6：F4.6 设置页面（~1.5 天）
  └── 4 组配置表单（含 Word 模板路径配置）
```

总计约 **10.5 个工作日**。

---

## 十、现有文件变更汇总

### 后端

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `api/routes/files.py` | 修改 | +upload, +download |
| `api/routes/settings.py` | 修改 | +KB/LLM/Generation 配置端点, +目录浏览 |
| `api/routes/stats.py` | 新增 | 知识库统计 API |
| `api/routes/ws.py` | 新增 | WebSocket 任务进度 |
| `api/middleware.py` | 新增 | 统一错误处理中间件 |
| `api/deps.py` | 修改 | 新增依赖注入 |
| `models/search.py` | 修改 | 新增统计相关模型 |
| `settings_service.py` | 修改 | 扩展全部配置节支持 |
| `main.py` | 修改 | 注册中间件 + WS 路由 + CORS |
| `config.py` | 修改 | GenerationConfig 新增 word_template_path |
| `generation/docx_formatter.py` | 修改 | 支持 .dotx 模板样式引用 |

### 前端

全新创建，按第二节目录结构。

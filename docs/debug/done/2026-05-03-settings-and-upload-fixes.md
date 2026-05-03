# 设置页面与上传功能修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复三个用户测试中发现的 bug：知识库文件夹上传不可见、LLM 设置缺少 OpenAI 选项且平铺显示、在线检索缺少百度搜索。

**Architecture:** 前后端分层修复。后端修改配置模型和设置服务的序列化逻辑；前端修改类型定义和 UI 组件（条件渲染）。每个 bug 独立修复，按复杂度递增排序。

**Tech Stack:** Python/FastAPI/Pydantic（后端），React/TypeScript/Ant Design（前端），Vitest（前端测试），Pytest（后端测试）

---

## 文件结构

| 文件 | 职责 | 改动类型 |
|------|------|----------|
| `backend/app/config.py` | 配置模型定义 | 修改：`OnlineSearchConfig.provider` 默认值 |
| `backend/app/models/search.py` | API 层更新模型 | 修改：`LLMSettingsUpdate` 添加 `openai_*` 字段 |
| `backend/app/settings_service.py` | 配置读写服务 | 修改：`get_llm_config()` 展平逻辑、`update_llm_config()` 添加 openai 映射 |
| `frontend/src/types/api.ts` | TypeScript 类型定义 | 修改：`LLMSettings` / `LLMSettingsUpdate` 添加 `openai_*` 字段 |
| `frontend/src/pages/Settings/index.tsx` | 设置页面 UI | 修改：LLM 条件渲染 + OpenAI 选项、搜索下拉改 Baidu |
| `frontend/src/pages/KnowledgeBase/index.tsx` | 知识库页面 | 修改：文件夹上传按钮 UI |
| `backend/tests/test_settings_extended.py` | 后端设置路由测试 | 修改：适配新的 LLM 配置格式 |
| `backend/tests/test_settings_service.py` | 后端设置服务测试 | 修改：适配 `baidu` 默认值 |
| `backend/tests/test_api/test_settings_routes.py` | 在线检索路由测试 | 修改：适配 `baidu` 默认值 |
| `frontend/src/pages/Settings/__tests__/Settings.test.tsx` | 设置页面测试 | 修改：适配新的 mock 数据和 UI 结构 |
| `frontend/src/pages/KnowledgeBase/__tests__/KnowledgeBase.test.tsx` | 知识库测试 | 修改：验证文件夹按钮可见性 |

---

## Task 1: 在线检索默认改为百度

**Files:**
- Modify: `backend/app/config.py:74`
- Modify: `backend/tests/test_settings_service.py:19,41`
- Modify: `backend/tests/test_api/test_settings_routes.py:25-26,32-33`
- Modify: `frontend/src/pages/Settings/index.tsx:268-271`
- Modify: `frontend/src/pages/Settings/__tests__/Settings.test.tsx:39`

- [ ] **Step 1: 修改后端配置默认值**

`backend/app/config.py` 第 74 行：
```python
    provider: str = "baidu"
```

- [ ] **Step 2: 修改后端测试中的 provider 默认值**

`backend/tests/test_settings_service.py` 第 19 行和第 41 行：
```python
"provider": "baidu",
```

`backend/tests/test_api/test_settings_routes.py` 第 25 行和第 32 行，mock 返回值中：
```python
provider="baidu",
```

- [ ] **Step 3: 修改前端搜索提供商下拉选项**

`frontend/src/pages/Settings/index.tsx` 第 268-271 行：
```tsx
<Select
  options={[
    { label: "百度", value: "baidu" },
  ]}
/>
```

- [ ] **Step 4: 修改前端测试 mock 数据**

`frontend/src/pages/Settings/__tests__/Settings.test.tsx` 第 39 行：
```typescript
provider: "baidu",
```

- [ ] **Step 5: 运行测试验证**

Run: `cd backend && python -m pytest tests/test_settings_service.py tests/test_settings_extended.py tests/test_api/test_settings_routes.py -v`
Expected: 全部 PASS

Run: `cd frontend && pnpm test -- --run`
Expected: 全部 PASS

Run: `cd frontend && pnpm lint`
Expected: 无错误

- [ ] **Step 6: 提交**

```bash
git add backend/app/config.py backend/tests/ frontend/src/pages/Settings/ frontend/src/pages/Settings/__tests__/
git commit -m "fix: 在线检索默认供应商改为百度"
```

---

## Task 2: 知识库文件夹上传按钮 UI 优化

**Files:**
- Modify: `frontend/src/pages/KnowledgeBase/index.tsx:252-284`
- Modify: `frontend/src/pages/KnowledgeBase/__tests__/KnowledgeBase.test.tsx`

- [ ] **Step 1: 修改上传区域 UI**

将 `frontend/src/pages/KnowledgeBase/index.tsx` 第 252-284 行的拖拽区域和文件夹按钮替换为：

```tsx
<Space direction="vertical" style={{ width: "100%", marginBottom: 24 }}>
  <Upload.Dragger
    multiple
    showUploadList={false}
    beforeUpload={() => false}
    onChange={(info) => {
      const fileList = info.fileList
        .map((f) => f.originFileObj)
        .filter((f): f is NonNullable<typeof f> => f != null);
      if (fileList.length > 0) handleUpload(fileList as File[]);
    }}
  >
    <p className="ant-upload-drag-icon">
      <InboxOutlined />
    </p>
    <p className="ant-upload-text">
      拖拽文件到此处，或点击选择文件
    </p>
  </Upload.Dragger>
  <Upload
    directory
    showUploadList={false}
    beforeUpload={() => false}
    onChange={(info) => {
      const fileList = info.fileList
        .map((f) => f.originFileObj)
        .filter((f): f is NonNullable<typeof f> => f != null);
      if (fileList.length > 0) handleUpload(fileList as File[]);
    }}
  >
    <Button icon={<FolderOpenOutlined />} block>
      选择文件夹
    </Button>
  </Upload>
</Space>
```

注意：需要在文件顶部 import 中添加 `Space`（已有 `FolderOpenOutlined` 和 `Button` 的 import）。

- [ ] **Step 2: 更新前端测试验证文件夹按钮可见**

`frontend/src/pages/KnowledgeBase/__tests__/KnowledgeBase.test.tsx` 中添加测试：

```typescript
it("renders folder upload button", () => {
  render(<KnowledgeBase />);
  expect(screen.getByText("选择文件夹")).toBeInTheDocument();
});
```

- [ ] **Step 3: 运行测试**

Run: `cd frontend && pnpm test -- --run`
Expected: 全部 PASS

Run: `cd frontend && pnpm lint`
Expected: 无错误

- [ ] **Step 4: 提交**

```bash
git add frontend/src/pages/KnowledgeBase/
git commit -m "fix: 知识库文件夹上传按钮 UI 优化，提升可见性"
```

---

## Task 3: 后端 LLM 设置支持 OpenAI 提供商

**Files:**
- Modify: `backend/app/models/search.py:86-93`
- Modify: `backend/app/settings_service.py:70-113`

- [ ] **Step 1: 修改 `LLMSettingsUpdate` 添加 `openai_*` 和 `embed_provider` 字段**

`backend/app/models/search.py` 第 86-93 行替换为：

```python
class LLMSettingsUpdate(BaseModel):
    default_provider: str | None = None
    embed_provider: str | None = None
    ollama_base_url: str | None = None
    ollama_chat_model: str | None = None
    ollama_embed_model: str | None = None
    claude_base_url: str | None = None
    claude_api_key: str | None = None
    claude_chat_model: str | None = None
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    openai_chat_model: str | None = None
    openai_embed_model: str | None = None
```

- [ ] **Step 2: 修改 `get_llm_config()` 将嵌套 providers 展平为前端可用的字段**

`backend/app/settings_service.py` 第 70-83 行替换为：

```python
def get_llm_config(self) -> dict:
    """Return LLM config dict with api_key masked, providers flattened."""
    llm = self._config.llm
    result: dict = {
        "default_provider": llm.default_provider,
        "embed_provider": llm.embed_provider,
    }
    for name, prov in llm.providers.items():
        prov_data = prov.model_dump()
        if prov_data.get("api_key"):
            prov_data["api_key"] = "********"
        for field, value in prov_data.items():
            result[f"{name}_{field}"] = value
    return result
```

- [ ] **Step 3: 修改 `update_llm_config()` 添加 `openai_` 前缀映射和 `embed_provider` 处理**

`backend/app/settings_service.py` 第 85-113 行替换为：

```python
def update_llm_config(self, update: LLMSettingsUpdate) -> dict:
    """Update LLM config, mapping flat field names to nested provider configs."""
    update_data = update.model_dump(exclude_none=True)
    llm = self._config.llm

    if "default_provider" in update_data:
        llm.default_provider = update_data.pop("default_provider")
    if "embed_provider" in update_data:
        llm.embed_provider = update_data.pop("embed_provider")

    # Map flattened provider fields to nested config
    provider_fields: dict[str, dict[str, str]] = {}
    for flat_key, value in update_data.items():
        for prefix in ("ollama", "claude", "openai"):
            if flat_key.startswith(f"{prefix}_"):
                provider_fields.setdefault(prefix, {})[flat_key.removeprefix(f"{prefix}_")] = value
                break

    from app.config import ClaudeConfig, OllamaConfig, OpenAICompatibleConfig

    provider_defaults = {
        "ollama": OllamaConfig,
        "claude": ClaudeConfig,
        "openai": OpenAICompatibleConfig,
    }
    for provider_name, fields in provider_fields.items():
        if provider_name not in llm.providers:
            llm.providers[provider_name] = provider_defaults[provider_name]()
        llm.providers[provider_name] = llm.providers[provider_name].model_copy(update=fields)

    self._write_config()
    return self.get_llm_config()
```

- [ ] **Step 4: 运行后端测试**

Run: `cd backend && python -m pytest tests/test_settings_extended.py -v`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/models/search.py backend/app/settings_service.py
git commit -m "feat: 后端 LLM 设置支持 OpenAI 提供商和 embed_provider 配置"
```

---

## Task 4: 前端 LLM 设置添加 OpenAI 选项和条件渲染

**Files:**
- Modify: `frontend/src/types/api.ts:104-122`
- Modify: `frontend/src/pages/Settings/index.tsx:219-252`
- Modify: `frontend/src/pages/Settings/__tests__/Settings.test.tsx`

- [ ] **Step 1: 修改 TypeScript 类型定义**

`frontend/src/types/api.ts` 第 104-122 行替换为：

```typescript
export interface LLMSettings {
  default_provider: string;
  embed_provider: string;
  ollama_base_url: string;
  ollama_chat_model: string;
  ollama_embed_model: string;
  claude_base_url: string;
  claude_api_key: string;
  claude_chat_model: string;
  openai_base_url: string;
  openai_api_key: string;
  openai_chat_model: string;
  openai_embed_model: string;
}

export interface LLMSettingsUpdate {
  default_provider?: string | null;
  embed_provider?: string | null;
  ollama_base_url?: string | null;
  ollama_chat_model?: string | null;
  ollama_embed_model?: string | null;
  claude_base_url?: string | null;
  claude_api_key?: string | null;
  claude_chat_model?: string | null;
  openai_base_url?: string | null;
  openai_api_key?: string | null;
  openai_chat_model?: string | null;
  openai_embed_model?: string | null;
}
```

- [ ] **Step 2: 重写 LLM 选项卡为条件渲染**

`frontend/src/pages/Settings/index.tsx` 第 215-252 行（`key: "llm"` 的 children）替换为：

```tsx
children: (
  <Form form={llmForm} layout="vertical" disabled={loading}>
    <Form.Item label="聊天提供商" name="default_provider">
      <Select
        options={[
          { label: "OpenAI 兼容", value: "openai" },
          { label: "Ollama", value: "ollama" },
          { label: "Claude", value: "claude" },
        ]}
      />
    </Form.Item>
    <Form.Item noStyle shouldUpdate>
      {() => {
        const provider = llmForm.getFieldValue("default_provider");
        if (provider === "openai") {
          return (
            <>
              <Form.Item label="Base URL" name="openai_base_url">
                <Input />
              </Form.Item>
              <Form.Item label="API Key" name="openai_api_key">
                <Input.Password />
              </Form.Item>
              <Form.Item label="Chat Model" name="openai_chat_model">
                <Input />
              </Form.Item>
            </>
          );
        }
        if (provider === "ollama") {
          return (
            <>
              <Form.Item label="Base URL" name="ollama_base_url">
                <Input />
              </Form.Item>
              <Form.Item label="Chat Model" name="ollama_chat_model">
                <Input />
              </Form.Item>
            </>
          );
        }
        if (provider === "claude") {
          return (
            <>
              <Form.Item label="Base URL" name="claude_base_url">
                <Input />
              </Form.Item>
              <Form.Item label="API Key" name="claude_api_key">
                <Input.Password />
              </Form.Item>
              <Form.Item label="Chat Model" name="claude_chat_model">
                <Input />
              </Form.Item>
            </>
          );
        }
        return null;
      }}
    </Form.Item>
    <Form.Item label="Embedding 提供商" name="embed_provider">
      <Select
        options={[
          { label: "OpenAI 兼容", value: "openai" },
          { label: "Ollama", value: "ollama" },
        ]}
      />
    </Form.Item>
    <Form.Item noStyle shouldUpdate>
      {() => {
        const embedProv = llmForm.getFieldValue("embed_provider");
        if (embedProv === "openai") {
          return (
            <Form.Item label="Embed Model (OpenAI)" name="openai_embed_model">
              <Input />
            </Form.Item>
          );
        }
        if (embedProv === "ollama") {
          return (
            <Form.Item label="Embed Model (Ollama)" name="ollama_embed_model">
              <Input />
            </Form.Item>
          );
        }
        return null;
      }}
    </Form.Item>
    <Form.Item>
      <Button type="primary" onClick={handleSaveLLM}>
        保存
      </Button>
    </Form.Item>
  </Form>
),
```

- [ ] **Step 3: 更新前端测试 mock 数据和断言**

`frontend/src/pages/Settings/__tests__/Settings.test.tsx` 中 `mockLLM` 替换为：

```typescript
const mockLLM: LLMSettings = {
  default_provider: "openai",
  embed_provider: "openai",
  ollama_base_url: "http://localhost:11434",
  ollama_chat_model: "qwen2.5",
  ollama_embed_model: "bge-large-zh-v1.5",
  claude_base_url: "https://api.anthropic.com",
  claude_api_key: "sk-test-secret-key",
  claude_chat_model: "claude-sonnet-4-20250514",
  openai_base_url: "http://127.0.0.1:18008/v1",
  openai_api_key: "test-key",
  openai_chat_model: "Qwen3.6-35B-A3B-MLX-8bit",
  openai_embed_model: "bge-m3-mlx-fp16",
};
```

LLM 表单字段断言（原 "renders LLM config form fields with masked API key" 测试）替换为：

```typescript
it("renders LLM config form with conditional fields for selected provider", async () => {
  const user = userEvent.setup();
  render(<Settings />);

  // Switch to LLM tab
  await user.click(screen.getByText("LLM"));

  expect(screen.getByText("聊天提供商")).toBeInTheDocument();
  expect(screen.getByText("Embedding 提供商")).toBeInTheDocument();

  // Default provider is "openai", so OpenAI fields should be visible
  expect(screen.getByText("Chat Model")).toBeInTheDocument();
  expect(screen.getByText("Base URL")).toBeInTheDocument();
  expect(screen.getByText("API Key")).toBeInTheDocument();
},
);
```

- [ ] **Step 4: 运行前端测试和 lint**

Run: `cd frontend && pnpm test -- --run`
Expected: 全部 PASS

Run: `cd frontend && pnpm lint`
Expected: 无错误

- [ ] **Step 5: 提交**

```bash
git add frontend/src/types/api.ts frontend/src/pages/Settings/
git commit -m "feat: LLM 设置添加 OpenAI 选项，条件渲染提供商配置字段"
```

---

## Task 5: 更新后端测试适配新的 LLM 配置格式

**Files:**
- Modify: `backend/tests/test_settings_extended.py:54-70`

- [ ] **Step 1: 更新 LLM GET/PUT 测试**

`backend/tests/test_settings_extended.py` 中 `test_llm_config_get_masks_api_key` 和 `test_llm_config_update` 替换为：

```python
def test_llm_config_get_masks_api_key(client: TestClient) -> None:
    resp = client.get("/api/settings/llm")
    assert resp.status_code == 200
    data = resp.json()
    assert "default_provider" in data
    assert "embed_provider" in data
    # Flattened fields
    assert data["claude_api_key"] == "********"
    assert "claude_base_url" in data


def test_llm_config_update(client: TestClient) -> None:
    resp = client.put(
        "/api/settings/llm",
        json={"openai_chat_model": "test-model"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["openai_chat_model"] == "test-model"
```

- [ ] **Step 2: 运行全部后端测试**

Run: `cd backend && python -m pytest tests/test_settings_extended.py tests/test_settings_service.py tests/test_api/test_settings_routes.py -v`
Expected: 全部 PASS

- [ ] **Step 3: 提交**

```bash
git add backend/tests/
git commit -m "test: 更新后端测试适配 LLM 配置展平格式"
```

---

## Task 6: 全量测试验证 + 最终提交

- [ ] **Step 1: 运行全部后端测试**

Run: `cd backend && python -m pytest -x -q`
Expected: 全部 PASS

- [ ] **Step 2: 运行前端测试和 lint**

Run: `cd frontend && pnpm test -- --run && pnpm lint`
Expected: 全部 PASS

- [ ] **Step 3: 运行后端 ruff 检查**

Run: `cd backend && ruff check app/ tests/ && ruff format --check app/ tests/`
Expected: 无错误

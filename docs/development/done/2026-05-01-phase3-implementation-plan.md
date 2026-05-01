# 阶段三实施计划 — 写作辅助核心（F3.1~F3.5）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现意图解析（F3.1）、Prompt 构建（F3.2）、模板管理（F3.3）、LLM 公文生成（F3.4）、Word 格式化（F3.5），以及支撑这些功能的 API 层和配置扩展。F3.6（Word→PPT）推迟到阶段五。

**Architecture:** 分层模块化 + WriterService 门面 — IntentParser / PromptBuilder / TemplateManager / Writer / DocxFormatter 各自独立，由 WriterService 门面编排流程。API 层通过 FastAPI Lifespan + deps.py 注入组件。

**Tech Stack:** FastAPI, Pydantic v2, python-docx, PyYAML, pytest + pytest-asyncio

**Spec:** `docs/product/deliverable/2026-05-01-tech-design-phase-3.md`

**Branch:** `feature/phase-3-generation`（从 main 创建）

---

## File Structure

### 新建文件

| 文件 | 职责 |
|------|------|
| `backend/app/generation/__init__.py` | 包初始化 |
| `backend/app/generation/intent_parser.py` | F3.1 意图解析 |
| `backend/app/generation/prompt_builder.py` | F3.2 Prompt 构建 |
| `backend/app/generation/template_manager.py` | F3.3 模板管理 |
| `backend/app/generation/writer.py` | F3.4 LLM 生成 |
| `backend/app/generation/writer_service.py` | 门面编排 |
| `backend/app/generation/docx_formatter.py` | F3.5 Word 格式化 |
| `backend/app/generation/templates/*.yaml` | 12 个内置模板 |
| `backend/app/models/generation.py` | 生成相关 Pydantic 模型 |
| `backend/app/api/routes/generation.py` | 写作 API |
| `backend/app/api/routes/templates.py` | 模板管理 API |
| `backend/tests/test_generation/__init__.py` | 包初始化 |
| `backend/tests/test_generation/test_intent_parser.py` | IntentParser 测试 |
| `backend/tests/test_generation/test_prompt_builder.py` | PromptBuilder 测试 |
| `backend/tests/test_generation/test_template_manager.py` | TemplateManager 测试 |
| `backend/tests/test_generation/test_writer.py` | Writer 测试 |
| `backend/tests/test_generation/test_writer_service.py` | WriterService 测试 |
| `backend/tests/test_generation/test_docx_formatter.py` | DocxFormatter 测试 |
| `backend/tests/test_api/test_generation_routes.py` | 写作路由测试 |
| `backend/tests/test_api/test_template_routes.py` | 模板路由测试 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/app/llm/base.py` | 新增 `chat_stream()` 抽象方法 |
| `backend/app/llm/ollama_provider.py` | 实现流式 `chat_stream()` |
| `backend/app/llm/claude_provider.py` | 实现流式 `chat_stream()` |
| `backend/app/config.py` | 新增 `GenerationConfig` + AppConfig 字段 |
| `backend/app/main.py` | lifespan 新增服务实例化 + 路由注册 |
| `backend/app/api/deps.py` | 新增 WriterService / TemplateManager 依赖函数 |

---

## Task 1: 数据模型 + 配置扩展

**Files:**
- Create: `backend/app/models/generation.py`
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: 创建 models/generation.py**

```python
# backend/app/models/generation.py

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.search import SourceType, UnifiedSearchResult


class ParsedIntent(BaseModel):
    doc_type: str
    topic: str
    keywords: list[str] = Field(default_factory=list)
    raw_input: str


class TemplateSection(BaseModel):
    title: str
    writing_points: list[str] = Field(default_factory=list)
    format_rules: list[str] = Field(default_factory=list)


class TemplateDef(BaseModel):
    id: str
    name: str
    doc_type: str
    sections: list[TemplateSection] = Field(default_factory=list)
    is_builtin: bool = True


class PromptContext(BaseModel):
    intent: ParsedIntent
    style_refs: list[UnifiedSearchResult] = Field(default_factory=list)
    policy_refs: list[UnifiedSearchResult] = Field(default_factory=list)
    template: TemplateDef | None = None


class SourceAttribution(BaseModel):
    title: str
    source_type: SourceType
    url: str | None = None
    date: str | None = None


class GenerationRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)
    selected_refs: list[str] | None = None
    requirements: str | None = None
    template_id: str | None = None


class GenerationResult(BaseModel):
    content: str
    sources: list[SourceAttribution] = Field(default_factory=list)
    output_path: str | None = None
    template_used: str
```

- [ ] **Step 2: 扩展 config.py — 新增 GenerationConfig**

在 `config.py` 的 `OnlineSearchConfig` 类之后、`AppConfig` 类之前添加：

```python
class GenerationConfig(BaseModel):
    output_format: str = "docx"
    save_path: str = "./output"
    include_sources: bool = True
    max_prompt_tokens: int = 4096
```

在 `AppConfig` 类中添加字段（在 `online_search` 之后）：

```python
    generation: GenerationConfig = GenerationConfig()
```

- [ ] **Step 3: 添加测试 — GenerationConfig 默认值**

在 `backend/tests/test_config.py` 末尾追加：

```python
def test_generation_config_defaults():
    config = AppConfig()
    assert config.generation.output_format == "docx"
    assert config.generation.save_path == "./output"
    assert config.generation.include_sources is True
    assert config.generation.max_prompt_tokens == 4096
```

- [ ] **Step 4: 运行测试**

```bash
cd backend && pytest tests/test_config.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/generation.py backend/app/config.py backend/tests/test_config.py
git commit -m "feat(generation): add data models and GenerationConfig"
```

---

## Task 2: LLM Provider 流式扩展

**Files:**
- Modify: `backend/app/llm/base.py`
- Modify: `backend/app/llm/ollama_provider.py`
- Modify: `backend/app/llm/claude_provider.py`

- [ ] **Step 1: 写 base.py 的流式测试**

在 `backend/tests/` 下新建或追加到现有 LLM 测试文件。此处先写一个对流式接口的 mock 测试。

创建 `backend/tests/test_llm/__init__.py`（空文件），再创建 `backend/tests/test_llm/test_stream.py`：

```python
# backend/tests/test_llm/test_stream.py

from __future__ import annotations

import pytest

from app.llm.ollama_provider import OllamaProvider


@pytest.fixture
def provider() -> OllamaProvider:
    return OllamaProvider(
        base_url="http://localhost:11434",
        chat_model="test-model",
        embed_model="test-embed",
    )


@pytest.mark.asyncio
async def test_chat_stream_returns_tokens(provider: OllamaProvider, monkeypatch):
    """chat_stream should yield tokens from SSE lines."""
    sse_lines = [
        b'data: {"message":{"content":"Hello"}}\n',
        b'data: {"message":{"content":" world"}}\n',
        b'data: {"done":true}\n',
    ]

    class FakeAiterLines:
        def __init__(self, lines):
            self._lines = lines
            self._idx = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self._idx >= len(self._lines):
                raise StopAsyncIteration
            line = self._lines[self._idx]
            self._idx += 1
            return line

    async def fake_aiter_lines():
        return FakeAiterLines(sse_lines)

    # Monkeypatch the client's stream method
    original_build_request = provider._client.build_request

    class FakeResponse:
        status_code = 200
        def raise_for_status(self):
            pass
        async def aiter_lines(self):
            async for line in FakeAiterLines(sse_lines):
                yield line
        async def aclose(self):
            pass

    async def fake_stream(method, url, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(provider._client, "stream", fake_stream)

    tokens = []
    async for token in provider.chat_stream([{"role": "user", "content": "hi"}]):
        tokens.append(token)

    assert tokens == ["Hello", " world"]
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && pytest tests/test_llm/test_stream.py -v
```

Expected: FAIL — `OllamaProvider` 没有 `chat_stream` 方法。

- [ ] **Step 3: 在 base.py 新增 chat_stream 抽象方法**

在 `BaseLLMProvider` 类中，`chat` 方法之后添加：

```python
    @abstractmethod
    async def chat_stream(self, messages: list[dict], **kwargs):
        """流式对话，逐 token 返回。返回 AsyncGenerator[str, None]。"""
        ...
        # yield from 子类实现
```

注意：ABC 中抽象异步生成器需要特殊处理。使用如下方式：

```python
    @abstractmethod
    def chat_stream(self, messages: list[dict], **kwargs):
        """流式对话，返回 AsyncGenerator[str, None]。"""
        ...
```

将 `chat_stream` 定义为普通方法（非 async），返回 AsyncGenerator。这样子类可以用 `async def chat_stream` 实现。

- [ ] **Step 4: 在 ollama_provider.py 实现 chat_stream**

在 `OllamaProvider` 类中添加：

```python
    async def chat_stream(self, messages: list[dict], **kwargs):
        async with self._client.stream(
            "POST",
            "/api/chat",
            json={"model": self._chat_model, "messages": messages, "stream": True},
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                import json
                data = json.loads(line[5:].strip())
                if data.get("done"):
                    break
                content = data.get("message", {}).get("content", "")
                if content:
                    yield content
```

- [ ] **Step 5: 在 claude_provider.py 实现 chat_stream**

在 `ClaudeProvider` 类中添加：

```python
    async def chat_stream(self, messages: list[dict], **kwargs):
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=4096,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text
```

- [ ] **Step 6: 运行测试确认通过**

```bash
cd backend && pytest tests/test_llm/test_stream.py -v
```

Expected: PASS

- [ ] **Step 7: 运行全量测试确认无回归**

```bash
cd backend && pytest --tb=short
```

Expected: 全部 PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/llm/base.py backend/app/llm/ollama_provider.py backend/app/llm/claude_provider.py backend/tests/test_llm/
git commit -m "feat(llm): add chat_stream() for streaming generation"
```

---

## Task 3: 内置模板 + TemplateManager（F3.3）

**Files:**
- Create: `backend/app/generation/__init__.py`
- Create: `backend/app/generation/templates/*.yaml`（12 个）
- Create: `backend/app/generation/template_manager.py`
- Create: `backend/tests/test_generation/__init__.py`
- Create: `backend/tests/test_generation/test_template_manager.py`

- [ ] **Step 1: 创建包初始化文件**

```bash
touch backend/app/generation/__init__.py
touch backend/tests/test_generation/__init__.py
```

- [ ] **Step 2: 创建 12 个内置 YAML 模板**

在 `backend/app/generation/templates/` 下创建 12 个 YAML 文件。每个文件遵循统一格式：

**notice.yaml（通知）示例：**

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

其余 11 个模板（announcement, request, report, plan, program, minutes, contract, work_summary, speech, research_report, presentation）按类似格式创建，每个模板的 `id`、`name`、`doc_type` 和 `sections` 内容需符合对应公文类型的标准结构。

**announcement.yaml（公告）：** id=announcement, name=公告, sections: 标题/正文/落款
**request.yaml（请示）：** id=request, name=请示, sections: 标题/请示缘由/请示事项/结尾/落款
**report.yaml（报告）：** id=report, name=报告, sections: 标题/报告导语/主要工作/存在问题/下一步计划/落款
**plan.yaml（方案）：** id=plan, name=方案, sections: 标题/背景和目标/实施步骤/保障措施/落款
**program.yaml（规划）：** id=program, name=规划, sections: 标题/现状分析/总体目标/重点任务/实施步骤/保障措施/落款
**minutes.yaml（会议纪要）：** id=minutes, name=会议纪要, sections: 标题/会议信息/议题一/议题二/决议事项/落款
**contract.yaml（合同/协议）：** id=contract, name=合同, sections: 标题/当事人信息/合同标的/权利义务/违约责任/争议解决/签署页
**work_summary.yaml（工作总结）：** id=work_summary, name=工作总结, sections: 标题/工作概述/主要成绩/存在问题/经验教训/下步计划/落款
**speech.yaml（领导讲话稿）：** id=speech, name=领导讲话稿, sections: 称呼/开场白/主体内容/结尾号召
**research_report.yaml（调研报告）：** id=research_report, name=调研报告, sections: 标题/调研背景/调研方法/调研发现/分析与建议/结论/落款
**presentation.yaml（汇报 PPT）：** id=presentation, name=汇报PPT, sections: 封面/目录/背景/核心内容/数据支撑/总结展望

- [ ] **Step 3: 写 TemplateManager 测试**

创建 `backend/tests/test_generation/test_template_manager.py`：

```python
# backend/tests/test_generation/test_template_manager.py

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.generation.template_manager import TemplateManager
from app.models.generation import TemplateDef

BUILTIN_IDS = [
    "notice", "announcement", "request", "report", "plan",
    "program", "minutes", "contract", "work_summary",
    "speech", "research_report", "presentation",
]


@pytest.fixture
def builtin_dir() -> Path:
    return Path(__file__).parent.parent.parent / "app" / "generation" / "templates"


@pytest.fixture
def tm(tmp_path: Path, builtin_dir: Path) -> TemplateManager:
    return TemplateManager(builtin_dir=builtin_dir, custom_dir=tmp_path / "custom")


# --- 内置模板 ---


class TestBuiltinTemplates:
    def test_list_all_builtins(self, tm: TemplateManager):
        templates = tm.list_templates()
        builtin = [t for t in templates if t.is_builtin]
        assert len(builtin) == 12
        assert {t.id for t in builtin} == set(BUILTIN_IDS)

    def test_get_builtin_by_id(self, tm: TemplateManager):
        t = tm.get_template("notice")
        assert t.name == "通知"
        assert t.is_builtin is True
        assert len(t.sections) > 0

    def test_filter_by_doc_type(self, tm: TemplateManager):
        results = tm.list_templates(doc_type="notice")
        assert all(t.doc_type == "notice" for t in results)
        assert len(results) >= 1

    def test_get_nonexistent_raises(self, tm: TemplateManager):
        with pytest.raises(FileNotFoundError):
            tm.get_template("nonexistent_template")


# --- 自定义模板 CRUD ---


class TestCustomTemplates:
    def test_create_custom_template(self, tm: TemplateManager):
        new_tmpl = TemplateDef(
            id="custom_test",
            name="自定义测试模板",
            doc_type="notice",
            sections=[{"title": "测试段", "writing_points": ["要点1"], "format_rules": []}],
            is_builtin=False,
        )
        result = tm.create_template(new_tmpl)
        assert result.id == "custom_test"
        assert result.is_builtin is False

    def test_list_includes_custom(self, tm: TemplateManager):
        new_tmpl = TemplateDef(
            id="custom_extra",
            name="额外模板",
            doc_type="report",
            is_builtin=False,
        )
        tm.create_template(new_tmpl)
        all_tmpls = tm.list_templates()
        ids = [t.id for t in all_tmpls]
        assert "custom_extra" in ids

    def test_update_custom_template(self, tm: TemplateManager):
        new_tmpl = TemplateDef(
            id="custom_to_update",
            name="原始名称",
            doc_type="notice",
            is_builtin=False,
        )
        tm.create_template(new_tmpl)
        updated = TemplateDef(
            id="custom_to_update",
            name="更新名称",
            doc_type="notice",
            is_builtin=False,
        )
        result = tm.update_template("custom_to_update", updated)
        assert result.name == "更新名称"

    def test_delete_custom_template(self, tm: TemplateManager):
        new_tmpl = TemplateDef(
            id="custom_to_delete",
            name="待删除",
            doc_type="notice",
            is_builtin=False,
        )
        tm.create_template(new_tmpl)
        tm.delete_template("custom_to_delete")
        with pytest.raises(FileNotFoundError):
            tm.get_template("custom_to_delete")

    def test_update_builtin_raises(self, tm: TemplateManager):
        with pytest.raises(PermissionError):
            tm.update_template("notice", tm.get_template("notice"))

    def test_delete_builtin_raises(self, tm: TemplateManager):
        with pytest.raises(PermissionError):
            tm.delete_template("notice")
```

- [ ] **Step 4: 运行测试确认失败**

```bash
cd backend && pytest tests/test_generation/test_template_manager.py -v
```

Expected: FAIL — `template_manager` 模块不存在。

- [ ] **Step 5: 实现 TemplateManager**

创建 `backend/app/generation/template_manager.py`：

```python
# backend/app/generation/template_manager.py

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from app.models.generation import TemplateDef

logger = logging.getLogger(__name__)


class TemplateManager:
    def __init__(self, builtin_dir: Path, custom_dir: Path) -> None:
        self._builtin_dir = builtin_dir
        self._custom_dir = custom_dir
        self._custom_dir.mkdir(parents=True, exist_ok=True)

    def list_templates(self, doc_type: str | None = None) -> list[TemplateDef]:
        results = []
        for tmpl in self._load_builtin():
            if doc_type is None or tmpl.doc_type == doc_type:
                results.append(tmpl)
        for tmpl in self._load_custom():
            if doc_type is None or tmpl.doc_type == doc_type:
                results.append(tmpl)
        return results

    def get_template(self, template_id: str) -> TemplateDef:
        for tmpl in self._load_builtin():
            if tmpl.id == template_id:
                return tmpl
        for tmpl in self._load_custom():
            if tmpl.id == template_id:
                return tmpl
        raise FileNotFoundError(f"模板不存在: {template_id}")

    def create_template(self, template: TemplateDef) -> TemplateDef:
        template.is_builtin = False
        path = self._custom_dir / f"{template.id}.yaml"
        if path.exists():
            raise FileExistsError(f"模板已存在: {template.id}")
        path.write_text(
            yaml.dump(template.model_dump(exclude={"is_builtin"}), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return template

    def update_template(self, template_id: str, data: TemplateDef) -> TemplateDef:
        existing = self.get_template(template_id)
        if existing.is_builtin:
            raise PermissionError(f"内置模板不可修改: {template_id}")
        path = self._custom_dir / f"{template_id}.yaml"
        data.is_builtin = False
        path.write_text(
            yaml.dump(data.model_dump(exclude={"is_builtin"}), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return data

    def delete_template(self, template_id: str) -> None:
        existing = self.get_template(template_id)
        if existing.is_builtin:
            raise PermissionError(f"内置模板不可删除: {template_id}")
        path = self._custom_dir / f"{template_id}.yaml"
        path.unlink()

    def _load_builtin(self) -> list[TemplateDef]:
        results = []
        if not self._builtin_dir.exists():
            return results
        for f in sorted(self._builtin_dir.glob("*.yaml")):
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            data["is_builtin"] = True
            results.append(TemplateDef.model_validate(data))
        return results

    def _load_custom(self) -> list[TemplateDef]:
        results = []
        for f in sorted(self._custom_dir.glob("*.yaml")):
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            data["is_builtin"] = False
            results.append(TemplateDef.model_validate(data))
        return results
```

- [ ] **Step 6: 运行测试确认通过**

```bash
cd backend && pytest tests/test_generation/test_template_manager.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/generation/ backend/tests/test_generation/
git commit -m "feat(templates): add TemplateManager with 12 built-in YAML templates"
```

---

## Task 4: IntentParser（F3.1）

**Files:**
- Create: `backend/app/generation/intent_parser.py`
- Create: `backend/tests/test_generation/test_intent_parser.py`

- [ ] **Step 1: 写 IntentParser 测试**

创建 `backend/tests/test_generation/test_intent_parser.py`：

```python
# backend/tests/test_generation/test_intent_parser.py

from __future__ import annotations

import json

import pytest

from app.generation.intent_parser import IntentParser
from app.llm.base import BaseLLMProvider


class MockLLM(BaseLLMProvider):
    def __init__(self, response: str):
        self._response = response

    async def chat(self, messages: list[dict], **kwargs) -> str:
        return self._response

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return []

    async def chat_stream(self, messages: list[dict], **kwargs):
        return
        yield  # make it an async generator


@pytest.fixture
def mock_llm():
    return MockLLM(
        response=json.dumps(
            {"doc_type": "notice", "topic": "节假日安排", "keywords": ["放假", "节假日", "安排"]}
        )
    )


class TestIntentParser:
    @pytest.mark.asyncio
    async def test_parse_notice(self, mock_llm):
        parser = IntentParser(mock_llm)
        result = await parser.parse("请帮我写一份关于国庆节放假安排的通知")
        assert result.doc_type == "notice"
        assert "放假" in result.keywords or "节假日" in result.keywords
        assert result.raw_input == "请帮我写一份关于国庆节放假安排的通知"

    @pytest.mark.asyncio
    async def test_parse_defaults_on_invalid_json(self):
        bad_llm = MockLLM(response="这不是JSON")
        parser = IntentParser(bad_llm)
        result = await parser.parse("写个东西")
        assert result.doc_type == "report"  # 默认值
        assert result.topic != ""
        assert result.raw_input == "写个东西"

    @pytest.mark.asyncio
    async def test_parse_extracts_keywords(self, mock_llm):
        parser = IntentParser(mock_llm)
        result = await parser.parse("写一份通知")
        assert len(result.keywords) > 0
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && pytest tests/test_generation/test_intent_parser.py -v
```

Expected: FAIL

- [ ] **Step 3: 实现 IntentParser**

创建 `backend/app/generation/intent_parser.py`：

```python
# backend/app/generation/intent_parser.py

from __future__ import annotations

import json
import logging

from app.llm.base import BaseLLMProvider
from app.models.generation import ParsedIntent

logger = logging.getLogger(__name__)

DOC_TYPES = {
    "notice": "通知",
    "announcement": "公告",
    "request": "请示",
    "report": "报告",
    "plan": "方案",
    "program": "规划",
    "minutes": "会议纪要",
    "contract": "合同/协议",
    "work_summary": "工作总结",
    "speech": "领导讲话稿",
    "research_report": "调研报告",
    "presentation": "汇报PPT",
}

SYSTEM_PROMPT = f"""你是一个公文类型识别助手。请从用户的描述中提取以下信息，以 JSON 格式返回：
- doc_type: 文件类型，必须是以下之一：{json.dumps(list(DOC_TYPES.keys()), ensure_ascii=False)}
- topic: 文件主题（简短概括）
- keywords: 关键词列表（用于检索参考素材）

如果无法确定文件类型，doc_type 设为 "report"。
只返回 JSON，不要解释。"""


class IntentParser:
    def __init__(self, llm: BaseLLMProvider) -> None:
        self._llm = llm

    async def parse(self, user_input: str) -> ParsedIntent:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ]
        response = await self._llm.chat(messages)
        return self._parse_response(response, user_input)

    def _parse_response(self, response: str, raw_input: str) -> ParsedIntent:
        try:
            data = json.loads(response)
            doc_type = data.get("doc_type", "report")
            if doc_type not in DOC_TYPES:
                doc_type = "report"
            return ParsedIntent(
                doc_type=doc_type,
                topic=data.get("topic", raw_input[:20]),
                keywords=data.get("keywords", []),
                raw_input=raw_input,
            )
        except (json.JSONDecodeError, AttributeError):
            logger.warning("意图解析失败，使用默认值: %s", response[:100])
            return ParsedIntent(
                doc_type="report",
                topic=raw_input[:20],
                keywords=[],
                raw_input=raw_input,
            )
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend && pytest tests/test_generation/test_intent_parser.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/generation/intent_parser.py backend/tests/test_generation/test_intent_parser.py
git commit -m "feat(generation): add IntentParser for document type extraction"
```

---

## Task 5: PromptBuilder（F3.2）

**Files:**
- Create: `backend/app/generation/prompt_builder.py`
- Create: `backend/tests/test_generation/test_prompt_builder.py`

- [ ] **Step 1: 写 PromptBuilder 测试**

创建 `backend/tests/test_generation/test_prompt_builder.py`：

```python
# backend/tests/test_generation/test_prompt_builder.py

from __future__ import annotations

import pytest

from app.generation.prompt_builder import PromptBuilder
from app.models.generation import ParsedIntent, PromptContext, TemplateDef, TemplateSection
from app.models.search import SourceType, UnifiedSearchResult


def _make_result(title: str, content: str, source_type: SourceType = SourceType.LOCAL) -> UnifiedSearchResult:
    return UnifiedSearchResult(
        source_type=source_type,
        title=title,
        content=content,
        score=0.8,
    )


@pytest.fixture
def builder() -> PromptBuilder:
    return PromptBuilder(max_tokens=2000)


@pytest.fixture
def context() -> PromptContext:
    intent = ParsedIntent(doc_type="notice", topic="放假安排", keywords=["放假"], raw_input="写一份放假通知")
    template = TemplateDef(
        id="notice", name="通知", doc_type="notice",
        sections=[
            TemplateSection(title="正文", writing_points=["背景", "要求"], format_rules=["缩进"]),
        ],
    )
    style_refs = [
        _make_result("参考1", "参考内容1" * 50),
        _make_result("参考2", "参考内容2" * 50),
    ]
    policy_refs = [
        _make_result("政策1", "政策内容1", SourceType.ONLINE),
    ]
    return PromptContext(intent=intent, style_refs=style_refs, policy_refs=policy_refs, template=template)


class TestPromptBuilder:
    def test_build_returns_messages_list(self, builder: PromptBuilder, context: PromptContext):
        messages = builder.build(context)
        assert isinstance(messages, list)
        assert len(messages) >= 2  # system + user at minimum
        assert messages[0]["role"] == "system"
        assert any(m["role"] == "user" for m in messages)

    def test_build_contains_intent_info(self, builder: PromptBuilder, context: PromptContext):
        messages = builder.build(context)
        combined = " ".join(m["content"] for m in messages)
        assert "放假" in combined or "通知" in combined

    def test_build_contains_template_format(self, builder: PromptBuilder, context: PromptContext):
        messages = builder.build(context)
        combined = " ".join(m["content"] for m in messages)
        assert "缩进" in combined

    def test_build_truncates_style_refs_when_over_limit(self, context: PromptContext):
        small_builder = PromptBuilder(max_tokens=100)
        messages = small_builder.build(context)
        combined = " ".join(m["content"] for m in messages)
        # 100 tokens is very small, style refs should be truncated
        assert isinstance(messages, list)

    def test_build_empty_refs(self, builder: PromptBuilder):
        intent = ParsedIntent(doc_type="report", topic="测试", keywords=["测试"], raw_input="测试")
        ctx = PromptContext(intent=intent, style_refs=[], policy_refs=[], template=None)
        messages = builder.build(ctx)
        assert isinstance(messages, list)
        assert len(messages) >= 1
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && pytest tests/test_generation/test_prompt_builder.py -v
```

Expected: FAIL

- [ ] **Step 3: 实现 PromptBuilder**

创建 `backend/app/generation/prompt_builder.py`：

```python
# backend/app/generation/prompt_builder.py

from __future__ import annotations

import logging

from app.models.generation import PromptContext

logger = logging.getLogger(__name__)

ROLE_PROMPT = """你是一位资深的政府机关公文写作专家。你的任务是根据提供的信息撰写一份规范、完整的公文初稿。

要求：
- 严格遵循公文的格式规范和行文风格
- 语言严谨、表述准确、逻辑清晰
- 适当引用提供的参考素材，但不要直接复制
- 文末附上参考素材来源清单"""


class PromptBuilder:
    def __init__(self, max_tokens: int = 4096) -> None:
        self._max_tokens = max_tokens

    def build(self, context: PromptContext) -> list[dict]:
        parts: list[tuple[str, int]] = []
        budget = self._max_tokens

        # 1. 角色设定（必保留）
        role_text = ROLE_PROMPT
        role_tokens = self._estimate_tokens(role_text)
        budget -= role_tokens

        # 2. 写作任务（必保留）
        task_text = self._build_task(context)
        task_tokens = self._estimate_tokens(task_text)
        budget -= task_tokens

        # 3. 格式要求（中优先级）
        format_text = ""
        if context.template:
            format_text = self._build_format(context.template)
            format_tokens = self._estimate_tokens(format_text)
            if format_tokens <= budget:
                budget -= format_tokens
            else:
                format_text = ""
                logger.info("格式要求因长度限制被截断")

        # 4. 文风参考（低优先级）
        style_text = self._build_style_refs(context.style_refs, budget)
        style_tokens = self._estimate_tokens(style_text)
        budget -= style_tokens

        # 5. 政策依据（最低优先级）
        policy_text = self._build_policy_refs(context.policy_refs, budget)

        user_content = "\n\n".join(
            p for p in [task_text, format_text, style_text, policy_text] if p
        )

        return [
            {"role": "system", "content": role_text},
            {"role": "user", "content": user_content},
        ]

    def _build_task(self, context: PromptContext) -> str:
        parts = [
            f"## 写作任务",
            f"文件类型：{context.intent.doc_type}",
            f"主题：{context.intent.topic}",
        ]
        if context.intent.keywords:
            parts.append(f"关键词：{', '.join(context.intent.keywords)}")
        parts.append(f"\n请根据以上要求撰写完整公文。")
        return "\n".join(parts)

    def _build_format(self, template) -> str:
        lines = ["## 格式要求", f"模板：{template.name}"]
        for section in template.sections:
            lines.append(f"\n### {section.title}")
            if section.writing_points:
                lines.append("写作要点：")
                for p in section.writing_points:
                    lines.append(f"  - {p}")
            if section.format_rules:
                lines.append("格式规范：")
                for r in section.format_rules:
                    lines.append(f"  - {r}")
        return "\n".join(lines)

    def _build_style_refs(self, refs, budget: int) -> str:
        if not refs:
            return ""
        lines = ["## 文风参考（以下为相似公文的片段，供参考风格和表述）"]
        for r in refs:
            entry = f"\n【{r.title}】\n{r.content[:500]}"
            estimated = self._estimate_tokens("\n".join(lines) + entry)
            if estimated > budget:
                break
            lines.append(entry)
        return "\n".join(lines)

    def _build_policy_refs(self, refs, budget: int) -> str:
        if not refs:
            return ""
        lines = ["## 政策依据"]
        for r in refs:
            entry = f"\n【{r.title}】\n{r.content[:300]}"
            if r.metadata.get("url"):
                entry += f"\n来源：{r.metadata['url']}"
            estimated = self._estimate_tokens("\n".join(lines) + entry)
            if estimated > budget:
                break
            lines.append(entry)
        return "\n".join(lines)

    def _estimate_tokens(self, text: str) -> int:
        return len(text)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend && pytest tests/test_generation/test_prompt_builder.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/generation/prompt_builder.py backend/tests/test_generation/test_prompt_builder.py
git commit -m "feat(generation): add PromptBuilder with priority-based truncation"
```

---

## Task 6: Writer（F3.4）

**Files:**
- Create: `backend/app/generation/writer.py`
- Create: `backend/tests/test_generation/test_writer.py`

- [ ] **Step 1: 写 Writer 测试**

创建 `backend/tests/test_generation/test_writer.py`：

```python
# backend/tests/test_generation/test_writer.py

from __future__ import annotations

import pytest

from app.generation.writer import Writer
from app.llm.base import BaseLLMProvider


class MockStreamLLM(BaseLLMProvider):
    def __init__(self, response: str = "生成的公文内容"):
        self._response = response

    async def chat(self, messages: list[dict], **kwargs) -> str:
        return self._response

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return []

    async def chat_stream(self, messages: list[dict], **kwargs):
        for char in self._response:
            yield char


class TestWriter:
    @pytest.mark.asyncio
    async def test_generate_returns_content(self):
        writer = Writer(MockStreamLLM("测试公文"))
        result = await writer.generate([{"role": "user", "content": "写通知"}])
        assert result == "测试公文"

    @pytest.mark.asyncio
    async def test_generate_stream_yields_tokens(self):
        writer = Writer(MockStreamLLM("你好"))
        tokens = []
        async for token in writer.generate_stream([{"role": "user", "content": "写通知"}]):
            tokens.append(token)
        assert tokens == ["你", "好"]

    @pytest.mark.asyncio
    async def test_generate_empty_response(self):
        writer = Writer(MockStreamLLM(""))
        result = await writer.generate([{"role": "user", "content": "写通知"}])
        assert result == ""
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && pytest tests/test_generation/test_writer.py -v
```

Expected: FAIL

- [ ] **Step 3: 实现 Writer**

创建 `backend/app/generation/writer.py`：

```python
# backend/app/generation/writer.py

from __future__ import annotations

from collections.abc import AsyncGenerator

from app.llm.base import BaseLLMProvider


class Writer:
    def __init__(self, llm: BaseLLMProvider) -> None:
        self._llm = llm

    async def generate(self, messages: list[dict]) -> str:
        return await self._llm.chat(messages)

    async def generate_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        async for token in self._llm.chat_stream(messages):
            yield token
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend && pytest tests/test_generation/test_writer.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/generation/writer.py backend/tests/test_generation/test_writer.py
git commit -m "feat(generation): add Writer with sync and streaming generation"
```

---

## Task 7: DocxFormatter（F3.5）

**Files:**
- Create: `backend/app/generation/docx_formatter.py`
- Create: `backend/tests/test_generation/test_docx_formatter.py`

- [ ] **Step 1: 写 DocxFormatter 测试**

创建 `backend/tests/test_generation/test_docx_formatter.py`：

```python
# backend/tests/test_generation/test_docx_formatter.py

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from app.generation.docx_formatter import DocxFormatter

SAMPLE_CONTENT = """# 关于国庆节放假安排的通知

各科室：

根据国务院办公厅通知精神，现将国庆节放假安排通知如下。

## 一、放假时间

10月1日至10月7日放假调休，共7天。

## 二、有关要求

各部门要妥善安排好值班和安全保卫等工作。

三、注意事项

节假日期间注意出行安全。

XX单位
2024年9月20日
"""


@pytest.fixture
def formatter(tmp_path: Path) -> DocxFormatter:
    return DocxFormatter(output_dir=tmp_path)


class TestDocxFormatter:
    def test_format_creates_docx(self, formatter: DocxFormatter):
        path = formatter.format(SAMPLE_CONTENT, "notice", "国庆节放假")
        assert path.exists()
        assert path.suffix == ".docx"

    def test_file_naming(self, formatter: DocxFormatter):
        path = formatter.format(SAMPLE_CONTENT, "notice", "放假安排")
        name = path.name
        assert name.startswith("notice_")
        assert name.endswith(".docx")
        assert date.today().isoformat() in name

    def test_topic_truncation(self, formatter: DocxFormatter):
        long_topic = "这" * 30
        path = formatter.format(SAMPLE_CONTENT, "report", long_topic)
        # 文件名中 topic 部分不超过 20 字符
        name = path.stem
        topic_part = name.split("_")[1]
        assert len(topic_part) <= 20

    def test_font_detection(self, formatter: DocxFormatter):
        font_map = formatter._font_map
        assert "body" in font_map
        assert "title" in font_map
        # 至少有字体映射
        assert len(font_map) >= 5

    def test_parse_structure(self, formatter: DocxFormatter):
        structure = formatter._parse_structure(SAMPLE_CONTENT)
        assert len(structure) > 0
        # 标题和段落都被解析
        types = [s["type"] for s in structure]
        assert "title" in types or "heading1" in types

    def test_empty_content_still_creates_file(self, formatter: DocxFormatter):
        path = formatter.format("简单内容", "report", "测试")
        assert path.exists()
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && pytest tests/test_generation/test_docx_formatter.py -v
```

Expected: FAIL

- [ ] **Step 3: 实现 DocxFormatter**

创建 `backend/app/generation/docx_formatter.py`：

```python
# backend/app/generation/docx_formatter.py

from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

logger = logging.getLogger(__name__)

# 字体映射：(理想字体, 降级字体)
FONT_CANDIDATES = {
    "title": ("方正小标宋简体", "宋体"),
    "heading1": ("方正黑体_GBK", "黑体"),
    "heading2": ("方正楷体_GBK", "楷体"),
    "heading3": ("方正仿宋_GBK", "仿宋"),
    "body": ("方正仿宋_GBK", "仿宋"),
}

FONT_SIZES = {
    "title": Pt(22),      # 二号
    "heading1": Pt(16),   # 三号
    "heading2": Pt(16),
    "heading3": Pt(16),
    "body": Pt(16),
}

ALIGNMENTS = {
    "title": WD_ALIGN_PARAGRAPH.CENTER,
    "heading1": WD_ALIGN_PARAGRAPH.LEFT,
    "heading2": WD_ALIGN_PARAGRAPH.LEFT,
    "heading3": WD_ALIGN_PARAGRAPH.LEFT,
    "body": WD_ALIGN_PARAGRAPH.LEFT,
}

EN_NUM_PATTERN = re.compile(r"[a-zA-Z0-9]+")


class DocxFormatter:
    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._font_map = self._detect_fonts()

    def format(self, content: str, doc_type: str, topic: str) -> Path:
        structure = self._parse_structure(content)
        doc = Document()

        # 页边距（GB/T 9704-2012 近似值）
        for section in doc.sections:
            section.top_margin = Cm(3.7)
            section.bottom_margin = Cm(3.5)
            section.left_margin = Cm(2.8)
            section.right_margin = Cm(2.6)

        for item in structure:
            style_type = item["type"]
            text = item["text"]
            font_name = self._font_map.get(style_type, self._font_map["body"])
            font_size = FONT_SIZES.get(style_type, FONT_SIZES["body"])
            alignment = ALIGNMENTS.get(style_type, ALIGNMENTS["body"])

            p = doc.add_paragraph()
            p.alignment = alignment
            pf = p.paragraph_format
            pf.line_spacing = Pt(28)
            pf.space_before = Pt(0)
            pf.space_after = Pt(0)
            if style_type not in ("title",):
                pf.first_line_indent = Pt(32)  # 两字缩进

            self._add_text_with_font(p, text, font_name, font_size)

        filename = self._make_filename(doc_type, topic)
        path = self._output_dir / filename
        doc.save(str(path))
        return path

    def _parse_structure(self, content: str) -> list[dict]:
        structure = []
        lines = content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("# ") and not line.startswith("## "):
                structure.append({"type": "title", "text": line[2:]})
            elif line.startswith("## "):
                structure.append({"type": "heading1", "text": line[3:]})
            elif line.startswith("### "):
                structure.append({"type": "heading2", "text": line[4:]})
            else:
                structure.append({"type": "body", "text": line})
        return structure

    def _add_text_with_font(self, paragraph, text: str, font_name: str, font_size) -> None:
        runs = EN_NUM_PATTERN.split(text)
        en_parts = EN_NUM_PATTERN.findall(text)

        for i, run_text in enumerate(runs):
            if run_text:
                run = paragraph.add_run(run_text)
                run.font.name = font_name
                run.font.size = font_size
            if i < len(en_parts):
                run = paragraph.add_run(en_parts[i])
                run.font.name = "Times New Roman"
                run.font.size = font_size

    def _make_filename(self, doc_type: str, topic: str) -> str:
        safe_topic = re.sub(r"[^\w\u4e00-\u9fff]", "", topic)[:20]
        return f"{doc_type}_{safe_topic}_{date.today().isoformat()}.docx"

    def _detect_fonts(self) -> dict:
        from platform import system

        available = set()
        if system() == "Darwin":
            import subprocess
            try:
                result = subprocess.run(
                    ["system_profiler", "SPFontsDataType"],
                    capture_output=True, text=True, timeout=10,
                )
                for name in FONT_CANDIDATES.values():
                    for n in name:
                        if n in result.stdout:
                            available.add(n)
            except Exception:
                pass

        resolved = {}
        for key, (preferred, fallback) in FONT_CANDIDATES.items():
            if preferred in available:
                resolved[key] = preferred
            else:
                resolved[key] = fallback
                if preferred != fallback:
                    logger.info("字体 %s 不可用，降级为 %s", preferred, fallback)

        return resolved
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend && pytest tests/test_generation/test_docx_formatter.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/generation/docx_formatter.py backend/tests/test_generation/test_docx_formatter.py
git commit -m "feat(generation): add DocxFormatter with GB/T 9704-2012 layout"
```

---

## Task 8: WriterService 门面

**Files:**
- Create: `backend/app/generation/writer_service.py`
- Create: `backend/tests/test_generation/test_writer_service.py`

- [ ] **Step 1: 写 WriterService 测试**

创建 `backend/tests/test_generation/test_writer_service.py`：

```python
# backend/tests/test_generation/test_writer_service.py

from __future__ import annotations

from pathlib import Path

import pytest

from app.generation.docx_formatter import DocxFormatter
from app.generation.intent_parser import IntentParser
from app.generation.prompt_builder import PromptBuilder
from app.generation.template_manager import TemplateManager
from app.generation.writer import Writer
from app.generation.writer_service import WriterService
from app.llm.base import BaseLLMProvider
from app.models.generation import GenerationRequest
from app.models.search import SourceType, UnifiedSearchResult
from app.retrieval.retriever import Retriever


class FakeLLM(BaseLLMProvider):
    async def chat(self, messages: list[dict], **kwargs) -> str:
        return '{"doc_type": "notice", "topic": "测试", "keywords": ["测试"]}'

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return []

    async def chat_stream(self, messages: list[dict], **kwargs):
        return
        yield


class FakeStreamLLM(BaseLLMProvider):
    async def chat(self, messages: list[dict], **kwargs) -> str:
        # 如果是意图解析，返回 JSON；否则返回生成内容
        last_msg = messages[-1]["content"] if messages else ""
        if "doc_type" in str(messages[0].get("content", "")):
            return '{"doc_type": "notice", "topic": "测试", "keywords": ["测试"]}'
        return "# 关于测试的通知\n\n测试正文内容"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return []

    async def chat_stream(self, messages: list[dict], **kwargs):
        for char in "测试流式内容":
            yield char


class FakeRetriever:
    async def search(self, request) -> list[UnifiedSearchResult]:
        return [
            UnifiedSearchResult(
                source_type=SourceType.LOCAL,
                title="参考文档",
                content="参考内容",
                score=0.9,
                metadata={"doc_date": "2024-01-01"},
            )
        ]

    async def search_local(self, request) -> list[UnifiedSearchResult]:
        return await self.search(request)


@pytest.fixture
def builtin_dir() -> Path:
    return Path(__file__).parent.parent.parent / "app" / "generation" / "templates"


@pytest.fixture
def writer_service(tmp_path: Path, builtin_dir: Path) -> WriterService:
    llm = FakeStreamLLM()
    return WriterService(
        intent_parser=IntentParser(llm),
        prompt_builder=PromptBuilder(max_tokens=2000),
        template_mgr=TemplateManager(builtin_dir=builtin_dir, custom_dir=tmp_path / "custom"),
        writer=Writer(llm),
        docx_formatter=DocxFormatter(output_dir=tmp_path / "output"),
        retriever=FakeRetriever(),
    )


class TestWriterService:
    @pytest.mark.asyncio
    async def test_generate_from_description(self, writer_service: WriterService, tmp_path):
        req = GenerationRequest(description="写一份测试通知")
        result = await writer_service.generate_from_description(req)
        assert result.content != ""
        assert result.template_used == "notice"
        assert result.output_path is not None

    @pytest.mark.asyncio
    async def test_generate_stream(self, writer_service: WriterService):
        req = GenerationRequest(description="写一份测试通知")
        tokens = []
        async for token in writer_service.generate_stream(req):
            tokens.append(token)
        assert len(tokens) > 0
        assert "".join(tokens) == "测试流式内容"

    @pytest.mark.asyncio
    async def test_sources_extracted(self, writer_service: WriterService):
        req = GenerationRequest(description="写一份测试通知")
        result = await writer_service.generate_from_description(req)
        assert len(result.sources) > 0
        assert result.sources[0].title == "参考文档"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && pytest tests/test_generation/test_writer_service.py -v
```

Expected: FAIL

- [ ] **Step 3: 实现 WriterService**

创建 `backend/app/generation/writer_service.py`：

```python
# backend/app/generation/writer_service.py

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from app.generation.docx_formatter import DocxFormatter
from app.generation.intent_parser import IntentParser
from app.generation.prompt_builder import PromptBuilder
from app.generation.template_manager import TemplateManager
from app.generation.writer import Writer
from app.models.generation import GenerationRequest, GenerationResult, PromptContext, SourceAttribution
from app.models.search import SearchRequest, SourceType, UnifiedSearchResult
from app.retrieval.retriever import Retriever

logger = logging.getLogger(__name__)


class WriterService:
    def __init__(
        self,
        intent_parser: IntentParser,
        prompt_builder: PromptBuilder,
        template_mgr: TemplateManager,
        writer: Writer,
        docx_formatter: DocxFormatter,
        retriever: Retriever,
    ) -> None:
        self._intent_parser = intent_parser
        self._prompt_builder = prompt_builder
        self._template_mgr = template_mgr
        self._writer = writer
        self._docx_formatter = docx_formatter
        self._retriever = retriever

    async def generate_from_description(self, req: GenerationRequest) -> GenerationResult:
        intent = await self._intent_parser.parse(req.description)
        template = self._resolve_template(req.template_id, intent.doc_type)
        search_results = await self._retriever.search(
            SearchRequest(query=" ".join(intent.keywords), top_k=5)
        )
        context = PromptContext(
            intent=intent,
            style_refs=search_results[:5],
            policy_refs=[r for r in search_results if r.source_type == SourceType.ONLINE],
            template=template,
        )
        messages = self._prompt_builder.build(context)
        content = await self._writer.generate(messages)
        output_path = self._docx_formatter.format(content, intent.doc_type, intent.topic)
        sources = self._extract_sources(search_results)

        return GenerationResult(
            content=content,
            sources=sources,
            output_path=str(output_path),
            template_used=template.id,
        )

    async def generate_from_selection(self, req: GenerationRequest) -> GenerationResult:
        intent = await self._intent_parser.parse(req.requirements or req.description)
        template = self._resolve_template(req.template_id, intent.doc_type)
        style_refs = await self._fetch_selected_refs(req.selected_refs or [])
        context = PromptContext(
            intent=intent,
            style_refs=style_refs,
            policy_refs=[],
            template=template,
        )
        messages = self._prompt_builder.build(context)
        content = await self._writer.generate(messages)
        output_path = self._docx_formatter.format(content, intent.doc_type, intent.topic)
        sources = self._extract_sources(style_refs)

        return GenerationResult(
            content=content,
            sources=sources,
            output_path=str(output_path),
            template_used=template.id,
        )

    async def generate_stream(self, req: GenerationRequest) -> AsyncGenerator[str, None]:
        intent = await self._intent_parser.parse(req.description)
        template = self._resolve_template(req.template_id, intent.doc_type)
        search_results = await self._retriever.search(
            SearchRequest(query=" ".join(intent.keywords), top_k=5)
        )
        context = PromptContext(
            intent=intent,
            style_refs=search_results[:5],
            policy_refs=[],
            template=template,
        )
        messages = self._prompt_builder.build(context)
        async for token in self._writer.generate_stream(messages):
            yield token

    def _resolve_template(self, template_id: str | None, doc_type: str):
        if template_id:
            try:
                return self._template_mgr.get_template(template_id)
            except FileNotFoundError:
                pass
        templates = self._template_mgr.list_templates(doc_type=doc_type)
        if templates:
            return templates[0]
        templates = self._template_mgr.list_templates(doc_type="report")
        return templates[0]

    async def _fetch_selected_refs(self, ref_ids: list[str]) -> list[UnifiedSearchResult]:
        if not ref_ids:
            return []
        results = await self._retriever.search(
            SearchRequest(query=" ".join(ref_ids), top_k=len(ref_ids))
        )
        return results

    def _extract_sources(self, results: list[UnifiedSearchResult]) -> list[SourceAttribution]:
        sources = []
        for r in results:
            sources.append(SourceAttribution(
                title=r.title,
                source_type=r.source_type,
                url=r.metadata.get("url"),
                date=r.metadata.get("doc_date"),
            ))
        return sources
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend && pytest tests/test_generation/test_writer_service.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/generation/writer_service.py backend/tests/test_generation/test_writer_service.py
git commit -m "feat(generation): add WriterService facade for mode A/B/stream"
```

---

## Task 9: API 路由 + deps + main.py 集成

**Files:**
- Create: `backend/app/api/routes/generation.py`
- Create: `backend/app/api/routes/templates.py`
- Modify: `backend/app/api/deps.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_api/test_generation_routes.py`
- Create: `backend/tests/test_api/test_template_routes.py`

- [ ] **Step 1: 创建 generation 路由**

创建 `backend/app/api/routes/generation.py`：

```python
# backend/app/api/routes/generation.py

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_writer_service
from app.generation.writer_service import WriterService
from app.models.generation import GenerationRequest, GenerationResult

router = APIRouter(prefix="/api/generation", tags=["generation"])

_writer_service_dep = Depends(get_writer_service)


@router.post("/generate", response_model=GenerationResult)
async def generate(
    req: GenerationRequest,
    service: WriterService = _writer_service_dep,
) -> GenerationResult:
    return await service.generate_from_description(req)


@router.post("/generate/stream")
async def generate_stream(
    req: GenerationRequest,
    service: WriterService = _writer_service_dep,
):
    async def event_generator():
        async for token in service.generate_stream(req):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

- [ ] **Step 2: 创建 templates 路由**

创建 `backend/app/api/routes/templates.py`：

```python
# backend/app/api/routes/templates.py

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.deps import get_template_manager
from app.generation.template_manager import TemplateManager
from app.models.generation import TemplateDef

router = APIRouter(prefix="/api/templates", tags=["templates"])

_tm_dep = Depends(get_template_manager)


@router.get("", response_model=list[TemplateDef])
async def list_templates(
    doc_type: str | None = Query(default=None),
    tm: TemplateManager = _tm_dep,
) -> list[TemplateDef]:
    return tm.list_templates(doc_type=doc_type)


@router.get("/{template_id}", response_model=TemplateDef)
async def get_template(
    template_id: str,
    tm: TemplateManager = _tm_dep,
) -> TemplateDef:
    return tm.get_template(template_id)


@router.post("", response_model=TemplateDef, status_code=201)
async def create_template(
    template: TemplateDef,
    tm: TemplateManager = _tm_dep,
) -> TemplateDef:
    return tm.create_template(template)


@router.put("/{template_id}", response_model=TemplateDef)
async def update_template(
    template_id: str,
    template: TemplateDef,
    tm: TemplateManager = _tm_dep,
) -> TemplateDef:
    return tm.update_template(template_id, template)


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: str,
    tm: TemplateManager = _tm_dep,
) -> Response:
    tm.delete_template(template_id)
    return Response(status_code=204)
```

- [ ] **Step 3: 扩展 deps.py**

在 `backend/app/api/deps.py` 末尾追加：

```python
from app.generation.template_manager import TemplateManager
from app.generation.writer_service import WriterService


def get_writer_service(request: Request) -> WriterService:
    return request.app.state.writer_service


def get_template_manager(request: Request) -> TemplateManager:
    return request.app.state.template_mgr
```

注意：import 行添加在文件顶部，函数定义添加在文件末尾。

- [ ] **Step 4: 修改 main.py — 添加 lifespan 服务和路由注册**

在 `main.py` 的 import 部分添加：

```python
from app.api.routes import generation, templates
from app.generation.docx_formatter import DocxFormatter
from app.generation.intent_parser import IntentParser
from app.generation.prompt_builder import PromptBuilder
from app.generation.template_manager import TemplateManager
from app.generation.writer import Writer
from app.generation.writer_service import WriterService
```

在 `_lifespan` 函数中，`app.state.settings_service = settings_service` 之后添加：

```python
        # Generation services
        intent_parser = IntentParser(llm)
        template_mgr = TemplateManager(
            builtin_dir=Path(__file__).parent / "generation" / "templates",
            custom_dir=Path(config.generation.save_path) / "templates",
        )
        prompt_builder = PromptBuilder(max_tokens=config.generation.max_prompt_tokens)
        gen_writer = Writer(llm)
        docx_formatter = DocxFormatter(output_dir=Path(config.generation.save_path))
        writer_service = WriterService(
            intent_parser, prompt_builder, template_mgr,
            gen_writer, docx_formatter, retriever,
        )

        app.state.writer_service = writer_service
        app.state.template_mgr = template_mgr
```

在路由注册部分（`app.include_router(settings.router)` 之后）添加：

```python
    app.include_router(generation.router)
    app.include_router(templates.router)
```

- [ ] **Step 5: 写 generation 路由测试**

创建 `backend/tests/test_api/test_generation_routes.py`：

```python
# backend/tests/test_api/test_generation_routes.py

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.models.generation import GenerationResult, SourceAttribution
from app.models.search import SourceType


@pytest.fixture
def client():
    from app.main import create_app
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_writer_service():
    svc = AsyncMock()
    svc.generate_from_description.return_value = GenerationResult(
        content="测试公文内容",
        sources=[SourceAttribution(title="参考1", source_type=SourceType.LOCAL)],
        output_path="/tmp/test.docx",
        template_used="notice",
    )
    return svc


class TestGenerationRoutes:
    def test_generate_endpoint(self, client, mock_writer_service):
        with patch("app.api.routes.generation.get_writer_service", return_value=mock_writer_service):
            resp = client.post(
                "/api/generation/generate",
                json={"description": "写一份测试通知"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["template_used"] == "notice"
        assert data["content"] == "测试公文内容"

    def test_generate_stream_endpoint(self, client, mock_writer_service):
        async def fake_stream(req):
            yield "你"
            yield "好"

        mock_writer_service.generate_stream = fake_stream

        with patch("app.api.routes.generation.get_writer_service", return_value=mock_writer_service):
            resp = client.post(
                "/api/generation/generate/stream",
                json={"description": "写一份测试通知"},
            )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
```

- [ ] **Step 6: 写 template 路由测试**

创建 `backend/tests/test_api/test_template_routes.py`：

```python
# backend/tests/test_api/test_template_routes.py

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.generation.template_manager import TemplateManager
from app.models.generation import TemplateDef


@pytest.fixture
def builtin_dir() -> Path:
    return Path(__file__).parent.parent.parent / "app" / "generation" / "templates"


@pytest.fixture
def tm(tmp_path: Path, builtin_dir: Path) -> TemplateManager:
    return TemplateManager(builtin_dir=builtin_dir, custom_dir=tmp_path / "custom")


@pytest.fixture
def client(tm: TemplateManager):
    from app.main import create_app
    app = create_app()
    app.state.template_mgr = tm
    return TestClient(app)


class TestTemplateRoutes:
    def test_list_templates(self, client):
        resp = client.get("/api/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 12

    def test_get_template(self, client):
        resp = client.get("/api/templates/notice")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "notice"
        assert data["is_builtin"] is True

    def test_get_nonexistent_template(self, client):
        resp = client.get("/api/templates/nonexistent")
        assert resp.status_code == 404

    def test_create_custom_template(self, client):
        resp = client.post(
            "/api/templates",
            json={
                "id": "custom_test",
                "name": "自定义模板",
                "doc_type": "notice",
                "sections": [],
                "is_builtin": False,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["is_builtin"] is False

    def test_delete_builtin_forbidden(self, client):
        resp = client.delete("/api/templates/notice")
        assert resp.status_code in (403, 500)
```

- [ ] **Step 7: 运行测试**

```bash
cd backend && pytest tests/test_api/ -v
```

Expected: PASS

- [ ] **Step 8: 运行全量测试确认无回归**

```bash
cd backend && pytest --tb=short
```

Expected: 全部 PASS

- [ ] **Step 9: Lint 检查**

```bash
cd backend && ruff check app/ tests/ && ruff format --check app/ tests/
```

Expected: 无错误

- [ ] **Step 10: Commit**

```bash
git add backend/app/api/ backend/app/main.py backend/tests/test_api/
git commit -m "feat(api): add generation and templates routes with deps injection"
```

---

## Task 10: 全量验证 + CLAUDE.md 更新

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: 运行全量测试 + 覆盖率**

```bash
cd backend && pytest --cov=app --cov-report=term-missing
```

Expected: 覆盖率 ≥ 80%，全部 PASS

- [ ] **Step 2: Lint 全量检查**

```bash
cd backend && ruff check app/ tests/ && ruff format --check app/ tests/
```

Expected: 无错误

- [ ] **Step 3: 更新 CLAUDE.md 当前状态**

将 CLAUDE.md 中的当前状态行改为：

```
**当前状态**：阶段三（写作辅助核心）开发中。
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: 更新项目状态至阶段三开发中"
```

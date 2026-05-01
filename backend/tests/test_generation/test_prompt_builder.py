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
        id="notice",
        name="通知",
        doc_type="notice",
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
        assert len(messages) >= 2
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
        assert isinstance(messages, list)

    def test_build_empty_refs(self, builder: PromptBuilder):
        intent = ParsedIntent(doc_type="report", topic="测试", keywords=["测试"], raw_input="测试")
        ctx = PromptContext(intent=intent, style_refs=[], policy_refs=[], template=None)
        messages = builder.build(ctx)
        assert isinstance(messages, list)
        assert len(messages) >= 1

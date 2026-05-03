from __future__ import annotations

import logging

from app.models.generation import PromptContext

logger = logging.getLogger(__name__)

ROLE_PROMPT = (
    "你是一位资深的政府机关公文写作专家。你的任务是根据提供的信息撰写一份规范、完整的公文初稿。\n\n"
    "要求：\n"
    "- 严格遵循 GB/T 9704-2012 公文格式规范和行文风格\n"
    "- 语言严谨、表述准确、逻辑清晰\n"
    "- 适当引用提供的参考素材，但不要直接复制\n"
    "- 文末附上参考素材来源清单\n"
    "- 直接输出纯文本，禁止使用任何 Markdown 格式符号（如 **、*、##、###、` 等）\n"
    '- 标题层级使用中文公文格式：一级用"一、二、三、"，二级用"（一）（二）（三）"，三级用"1. 2. 3."'
)


class PromptBuilder:
    def __init__(self, max_tokens: int = 4096) -> None:
        self._max_tokens = max_tokens

    def build(self, context: PromptContext) -> list[dict]:
        budget = self._max_tokens

        role_text = ROLE_PROMPT
        budget -= self._estimate_tokens(role_text)

        task_text = self._build_task(context)
        budget -= self._estimate_tokens(task_text)

        format_text = ""
        if context.template:
            format_text = self._build_format(context.template)
            format_tokens = self._estimate_tokens(format_text)
            if format_tokens <= budget:
                budget -= format_tokens
            else:
                format_text = ""
                logger.info("格式要求因长度限制被截断")

        style_text = self._build_style_refs(context.style_refs, budget)
        budget -= self._estimate_tokens(style_text)

        policy_text = self._build_policy_refs(context.policy_refs, budget)

        user_content = "\n\n".join(p for p in [task_text, format_text, style_text, policy_text] if p)

        return [
            {"role": "system", "content": role_text},
            {"role": "user", "content": user_content},
        ]

    def _build_task(self, context: PromptContext) -> str:
        parts = [
            "## 写作任务",
            f"文件类型：{context.intent.doc_type}",
            f"主题：{context.intent.topic}",
        ]
        if context.intent.keywords:
            parts.append(f"关键词：{', '.join(context.intent.keywords)}")
        parts.append("\n请根据以上要求撰写完整公文。")
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

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

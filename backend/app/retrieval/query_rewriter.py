from __future__ import annotations

import logging

from app.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class QueryRewriter:
    def __init__(self, llm: BaseLLMProvider) -> None:
        self._llm = llm

    async def rewrite(self, query: str) -> str:
        try:
            prompt = (
                "你是一个搜索查询优化助手。请改写以下查询，扩展同义词、纠正错别字，"
                "使其更适合文档检索。\n\n"
                f"原始查询：{query}\n\n"
                "要求：只输出改写后的查询文本，不要其他内容。"
            )
            result = await self._llm.chat([{"role": "user", "content": prompt}])
            rewritten = result.strip()
            return rewritten if rewritten else query
        except Exception:
            logger.warning("查询改写失败，使用原始查询", exc_info=True)
            return query

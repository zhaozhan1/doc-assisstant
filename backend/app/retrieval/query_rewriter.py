from __future__ import annotations

from app.llm.base import BaseLLMProvider


class QueryRewriter:
    def __init__(self, llm: BaseLLMProvider) -> None:
        self._llm = llm

    async def rewrite(self, query: str) -> str:
        prompt = f"""你是一个搜索查询优化助手。请改写以下查询，扩展同义词、纠正错别字，使其更适合文档检索。

原始查询：{query}

要求：只输出改写后的查询文本，不要其他内容。改写后的查询应包含原始关键词和可能的同义词。"""
        return await self._llm.chat([{"role": "user", "content": prompt}])

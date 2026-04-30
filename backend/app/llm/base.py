from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> str: ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    async def classify(self, text: str, labels: list[str]) -> str:
        prompt = (
            f"请从以下类别中选择最匹配的一个：{', '.join(labels)}\n\n"
            f"文本内容：\n{text[:500]}\n\n"
            "只返回类别名称，不要解释。"
        )
        response = await self.chat([{"role": "user", "content": prompt}])
        return self._match_label(response.strip(), labels)

    @staticmethod
    def _match_label(response: str, labels: list[str]) -> str:
        response = response.strip()
        for label in labels:
            if label in response:
                return label
        return labels[-1]

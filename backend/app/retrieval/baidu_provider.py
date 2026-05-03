from __future__ import annotations

import logging

import httpx

from app.models.search import OnlineSearchItem
from app.retrieval.online_search import BaseOnlineSearchProvider

logger = logging.getLogger(__name__)

_BAIDU_SEARCH_API = "https://qianfan.baidubce.com/v2/ai_search/web_search"


class BaiduSearchProvider(BaseOnlineSearchProvider):
    """Online search provider using Baidu Qianfan Search API."""

    def __init__(self, api_key: str = "", base_url: str = "") -> None:
        self._api_key = api_key
        self._api_url = base_url or _BAIDU_SEARCH_API
        self._client = httpx.AsyncClient(timeout=15)

    async def search(
        self,
        query: str,
        max_results: int = 3,
        domains: list[str] | None = None,
    ) -> list[OnlineSearchItem]:
        if not self._api_key:
            logger.warning("百度搜索 API Key 未配置")
            return []

        body: dict = {
            "messages": [{"content": query[:72], "role": "user"}],
            "search_source": "baidu_search_v2",
            "resource_type_filter": [{"type": "web", "top_k": max_results}],
        }
        if domains:
            body.setdefault("search_filter", {}).setdefault("match", {})["site"] = domains

        headers = {
            "X-Appbuilder-Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = await self._client.post(self._api_url, json=body, headers=headers)
            resp.raise_for_status()
        except Exception:
            logger.warning("百度搜索 API 请求失败", exc_info=True)
            return []

        data = resp.json()
        if "code" in data:
            logger.warning("百度搜索 API 错误: code=%s message=%s", data.get("code"), data.get("message"))
            return []

        references = data.get("references") or []
        results: list[OnlineSearchItem] = []
        for ref in references[:max_results]:
            results.append(OnlineSearchItem(
                title=ref.get("title", ""),
                snippet=ref.get("snippet") or ref.get("content", ""),
                url=ref.get("url", ""),
            ))
        return results

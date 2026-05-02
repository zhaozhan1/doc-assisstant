from __future__ import annotations

import logging

import httpx
from selectolax.parser import HTMLParser

from app.models.search import OnlineSearchItem
from app.retrieval.online_search import BaseOnlineSearchProvider

logger = logging.getLogger(__name__)

_BAIDU_SEARCH_URL = "https://www.baidu.com/s"


class BaiduSearchProvider(BaseOnlineSearchProvider):
    """Online search provider using Baidu search engine."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=10,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9",
            },
        )

    async def _fetch_html(self, query: str) -> str:
        response = await self._client.get(_BAIDU_SEARCH_URL, params={"wd": query, "rn": "10"})
        response.raise_for_status()
        return response.text

    async def search(
        self,
        query: str,
        max_results: int = 3,
        domains: list[str] | None = None,
    ) -> list[OnlineSearchItem]:
        search_query = query
        if domains:
            site_filter = " OR ".join(f"site:{d}" for d in domains)
            search_query = f"{query} {site_filter}"

        try:
            html = await self._fetch_html(search_query)
        except Exception:
            logger.warning("百度搜索请求失败", exc_info=True)
            return []

        return _parse_baidu_html(html)[:max_results]


def _parse_baidu_html(html: str) -> list[OnlineSearchItem]:
    tree = HTMLParser(html)
    results: list[OnlineSearchItem] = []

    for container in tree.css("div.result.c-container"):
        link = container.css_first("h3 a")
        if not link:
            continue
        title = link.text(strip=True)
        href = link.attributes.get("href", "")

        snippet = ""
        snippet_el = container.css_first("span.content-right_8Zs40")
        if snippet_el:
            snippet = snippet_el.text(strip=True)
        if not snippet:
            snippet_el = container.css_first("div.c-abstract")
            if snippet_el:
                snippet = snippet_el.text(strip=True)

        if title and href:
            results.append(OnlineSearchItem(title=title, snippet=snippet, url=href))

    return results

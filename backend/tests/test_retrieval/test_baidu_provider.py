from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.config import OnlineSearchConfig
from app.retrieval.online_search import OnlineSearchFactory


class TestBaiduSearchProvider:
    async def test_search_returns_parsed_results(self) -> None:
        """Baidu provider should parse HTML response into OnlineSearchItem list."""
        from app.retrieval.baidu_provider import BaiduSearchProvider

        provider = BaiduSearchProvider()

        html = """
        <html><body>
        <div class="result c-container">
            <h3 class="t"><a href="http://www.example.com/page1">测试标题一</a></h3>
            <span class="content-right_8Zs40">测试摘要内容一</span>
        </div>
        <div class="result c-container">
            <h3 class="t"><a href="http://www.example.com/page2">测试标题二</a></h3>
            <span class="content-right_8Zs40">测试摘要内容二</span>
        </div>
        </body></html>
        """

        with patch.object(provider, "_fetch_html", new_callable=AsyncMock, return_value=html):
            results = await provider.search("测试查询", max_results=3)

        assert len(results) == 2
        assert results[0].title == "测试标题一"
        assert results[0].url == "http://www.example.com/page1"
        assert results[0].snippet == "测试摘要内容一"
        assert results[1].title == "测试标题二"

    async def test_search_respects_max_results(self) -> None:
        """Should limit results to max_results."""
        from app.retrieval.baidu_provider import BaiduSearchProvider

        provider = BaiduSearchProvider()

        html = """
        <html><body>
        <div class="result c-container">
            <h3 class="t"><a href="http://example.com/1">标题1</a></h3>
            <span class="content-right_8Zs40">摘要1</span>
        </div>
        <div class="result c-container">
            <h3 class="t"><a href="http://example.com/2">标题2</a></h3>
            <span class="content-right_8Zs40">摘要2</span>
        </div>
        <div class="result c-container">
            <h3 class="t"><a href="http://example.com/3">标题3</a></h3>
            <span class="content-right_8Zs40">摘要3</span>
        </div>
        </body></html>
        """

        with patch.object(provider, "_fetch_html", new_callable=AsyncMock, return_value=html):
            results = await provider.search("测试", max_results=2)

        assert len(results) == 2

    async def test_search_with_domain_filter(self) -> None:
        """Should append site: prefix when domains specified."""
        from app.retrieval.baidu_provider import BaiduSearchProvider

        provider = BaiduSearchProvider()
        captured_query: list[str] = []

        async def mock_fetch(query: str) -> str:
            captured_query.append(query)
            return "<html><body></body></html>"

        with patch.object(provider, "_fetch_html", side_effect=mock_fetch):
            await provider.search("测试", domains=["gov.cn", "org.cn"])

        assert "site:gov.cn OR site:org.cn" in captured_query[0]

    async def test_search_empty_html_returns_empty(self) -> None:
        """Empty HTML should return empty results."""
        from app.retrieval.baidu_provider import BaiduSearchProvider

        provider = BaiduSearchProvider()

        with patch.object(provider, "_fetch_html", new_callable=AsyncMock, return_value="<html><body></body></html>"):
            results = await provider.search("测试")

        assert results == []

    async def test_search_network_error_returns_empty(self) -> None:
        """Network error should return empty list, not raise."""
        from app.retrieval.baidu_provider import BaiduSearchProvider

        provider = BaiduSearchProvider()

        with patch.object(provider, "_fetch_html", new_callable=AsyncMock, side_effect=Exception("network error")):
            results = await provider.search("测试")

        assert results == []


class TestBaiduFactoryIntegration:
    def test_factory_creates_baidu_provider(self) -> None:
        """Factory should create BaiduSearchProvider when provider='baidu'."""
        config = OnlineSearchConfig(enabled=True, provider="baidu")
        provider = OnlineSearchFactory.create(config)
        assert provider is not None
        from app.retrieval.baidu_provider import BaiduSearchProvider

        assert isinstance(provider, BaiduSearchProvider)

    async def test_end_to_end_service_with_baidu(self) -> None:
        """OnlineSearchService with BaiduSearchProvider should return unified results."""
        from app.retrieval.online_search import OnlineSearchService

        config = OnlineSearchConfig(enabled=True, provider="baidu", max_results=2)
        service = OnlineSearchService.from_config(config)

        html = """
        <html><body>
        <div class="result c-container">
            <h3 class="t"><a href="http://gov.cn/policy">政策文件</a></h3>
            <span class="content-right_8Zs40">政策摘要内容</span>
        </div>
        </body></html>
        """

        from app.retrieval.baidu_provider import BaiduSearchProvider

        with patch.object(BaiduSearchProvider, "_fetch_html", new_callable=AsyncMock, return_value=html):
            results = await service.search("政策")

        assert len(results) == 1
        assert results[0].title == "政策文件"

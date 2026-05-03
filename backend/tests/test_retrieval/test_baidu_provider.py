from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx

from app.config import OnlineSearchConfig
from app.retrieval.online_search import OnlineSearchFactory


def _make_response(json_data: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("POST", "https://example.com"),
    )


class TestBaiduSearchProvider:
    async def test_search_returns_parsed_results(self) -> None:
        from app.retrieval.baidu_provider import BaiduSearchProvider

        provider = BaiduSearchProvider(api_key="test-key")

        api_response = _make_response({
            "references": [
                {"title": "测试标题一", "snippet": "测试摘要一", "url": "http://example.com/1"},
                {"title": "测试标题二", "snippet": "测试摘要二", "url": "http://example.com/2"},
            ],
        })

        with patch.object(provider._client, "post", new_callable=AsyncMock, return_value=api_response):
            results = await provider.search("测试查询", max_results=3)

        assert len(results) == 2
        assert results[0].title == "测试标题一"
        assert results[0].url == "http://example.com/1"
        assert results[0].snippet == "测试摘要一"
        assert results[1].title == "测试标题二"

    async def test_search_respects_max_results(self) -> None:
        from app.retrieval.baidu_provider import BaiduSearchProvider

        provider = BaiduSearchProvider(api_key="test-key")

        api_response = _make_response({
            "references": [
                {"title": "标题1", "snippet": "摘要1", "url": "http://example.com/1"},
                {"title": "标题2", "snippet": "摘要2", "url": "http://example.com/2"},
                {"title": "标题3", "snippet": "摘要3", "url": "http://example.com/3"},
            ],
        })

        with patch.object(provider._client, "post", new_callable=AsyncMock, return_value=api_response):
            results = await provider.search("测试", max_results=2)

        assert len(results) == 2

    async def test_search_with_domain_filter(self) -> None:
        from app.retrieval.baidu_provider import BaiduSearchProvider

        provider = BaiduSearchProvider(api_key="test-key")

        api_response = _make_response({"references": []})
        captured_body: list[dict] = []

        async def mock_post(url, **kwargs):
            captured_body.append(kwargs.get("json", {}))
            return api_response

        with patch.object(provider._client, "post", side_effect=mock_post):
            await provider.search("测试", domains=["gov.cn", "org.cn"])

        assert captured_body[0]["search_filter"]["match"]["site"] == ["gov.cn", "org.cn"]

    async def test_search_empty_response_returns_empty(self) -> None:
        from app.retrieval.baidu_provider import BaiduSearchProvider

        provider = BaiduSearchProvider(api_key="test-key")

        api_response = _make_response({"references": []})

        with patch.object(provider._client, "post", new_callable=AsyncMock, return_value=api_response):
            results = await provider.search("测试")

        assert results == []

    async def test_search_api_error_returns_empty(self) -> None:
        from app.retrieval.baidu_provider import BaiduSearchProvider

        provider = BaiduSearchProvider(api_key="test-key")

        api_response = _make_response({"code": "error", "message": "rate limited"})

        with patch.object(provider._client, "post", new_callable=AsyncMock, return_value=api_response):
            results = await provider.search("测试")

        assert results == []

    async def test_search_no_api_key_returns_empty(self) -> None:
        from app.retrieval.baidu_provider import BaiduSearchProvider

        provider = BaiduSearchProvider(api_key="")
        results = await provider.search("测试")

        assert results == []

    async def test_search_network_error_returns_empty(self) -> None:
        from app.retrieval.baidu_provider import BaiduSearchProvider

        provider = BaiduSearchProvider(api_key="test-key")

        with patch.object(provider._client, "post", new_callable=AsyncMock, side_effect=httpx.HTTPError("timeout")):
            results = await provider.search("测试")

        assert results == []


class TestBaiduFactoryIntegration:
    def test_factory_creates_baidu_provider(self) -> None:
        config = OnlineSearchConfig(enabled=True, provider="baidu", api_key="test-key")
        provider = OnlineSearchFactory.create(config)
        assert provider is not None
        from app.retrieval.baidu_provider import BaiduSearchProvider

        assert isinstance(provider, BaiduSearchProvider)

    async def test_end_to_end_service_with_baidu(self) -> None:
        from app.retrieval.online_search import OnlineSearchService

        config = OnlineSearchConfig(enabled=True, provider="baidu", api_key="test-key", max_results=2)
        service = OnlineSearchService.from_config(config)

        api_response = _make_response({
            "references": [
                {"title": "政策文件", "snippet": "政策摘要", "url": "http://gov.cn/policy"},
            ],
        })

        from app.retrieval.baidu_provider import BaiduSearchProvider

        with patch.object(BaiduSearchProvider, "_client", create=True):
            provider = service._provider
            with patch.object(provider._client, "post", new_callable=AsyncMock, return_value=api_response):
                results = await service.search("政策")

        assert len(results) == 1
        assert results[0].title == "政策文件"

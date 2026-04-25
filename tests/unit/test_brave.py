"""Unit tests for Brave Search provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from search.providers.brave import BraveProvider
from search.providers.base import ProviderConfig, ProviderStatus


@pytest.fixture
def config():
    return ProviderConfig(api_key="test-brave-key")


@pytest.fixture
def provider(config):
    return BraveProvider(config)


class TestBraveProvider:
    """Tests for BraveProvider."""

    def test_name(self, provider):
        assert provider.name == "brave"

    def test_supports_realtime(self, provider):
        assert provider.supports_realtime is True

    def test_is_available_with_key(self, provider):
        assert provider.is_available is True

    def test_is_available_without_key(self):
        p = BraveProvider(ProviderConfig(api_key=""))
        # Base class is_available checks enabled + circuit breaker, not api_key.
        # The provider returns [] from search() if api_key is empty.
        assert p.is_available is True  # available but search returns []

    @pytest.mark.asyncio
    async def test_search_no_api_key(self):
        p = BraveProvider(ProviderConfig(api_key=""))
        results = await p.search("test query")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_success(self, provider):
        mock_response_data = {
            "web": {
                "results": [
                    {
                        "title": "Test Result 1",
                        "url": "https://example.com/1",
                        "description": "First test result",
                    },
                    {
                        "title": "Test Result 2",
                        "url": "https://example.com/2",
                        "description": "Second test result",
                    },
                ]
            }
        }

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = AsyncMock(return_value=mock_response_data)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.closed = False
        provider._session = mock_session

        results = await provider.search("test query", num_results=5)

        assert len(results) == 2
        assert results[0].title == "Test Result 1"
        assert results[0].url == "https://example.com/1"
        assert results[0].source == "brave"
        assert results[1].title == "Test Result 2"

    @pytest.mark.asyncio
    async def test_search_with_realtime_filter(self, provider):
        mock_response_data = {"web": {"results": []}}
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = AsyncMock(return_value=mock_response_data)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.closed = False
        provider._session = mock_session

        await provider.search("test query", include_realtime=True)

        call_args = mock_session.get.call_args
        params = call_args[1].get("params", {})
        assert "freshness" in params

    @pytest.mark.asyncio
    async def test_search_handles_rate_limit(self, provider):
        import aiohttp

        mock_resp = AsyncMock()
        mock_resp.status = 429
        mock_resp.raise_for_status = MagicMock(
            side_effect=aiohttp.ClientResponseError(
                request_info=MagicMock(), history=(), status=429
            )
        )
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.closed = False
        provider._session = mock_session

        results = await provider.search("test query")
        assert results == []
        health = provider.get_health()
        assert health.status == ProviderStatus.RATE_LIMITED

    @pytest.mark.asyncio
    async def test_parse_empty_response(self, provider):
        results = provider._parse_response({}, "test", 10)
        assert results == []

    @pytest.mark.asyncio
    async def test_parse_mixed_response(self, provider):
        """Test parsing mixed (blended) results format."""
        data = {
            "mixed": {
                "main": [
                    {
                        "result": {
                            "title": "Mixed Result",
                            "url": "https://example.com/mixed",
                            "description": "From mixed results",
                        }
                    }
                ]
            }
        }
        results = provider._parse_response(data, "test", 10)
        assert len(results) == 1
        assert results[0].title == "Mixed Result"

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, provider):
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.closed = False
        provider._session = mock_session

        status = await provider.health_check()
        assert status == ProviderStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_no_key(self):
        p = BraveProvider(ProviderConfig(api_key=""))
        status = await p.health_check()
        assert status == ProviderStatus.DOWN

    @pytest.mark.asyncio
    async def test_context_manager(self, provider):
        async with provider as p:
            assert p.name == "brave"

    @pytest.mark.asyncio
    async def test_search_skips_incomplete_results(self, provider):
        """Results missing title or URL should be skipped."""
        data = {
            "web": {
                "results": [
                    {"title": "Good", "url": "https://example.com", "description": "ok"},
                    {"title": "No URL", "description": "missing url"},
                    {"url": "https://example.com/2", "description": "missing title"},
                ]
            }
        }
        results = provider._parse_response(data, "test", 10)
        assert len(results) == 1
        assert results[0].title == "Good"

    @pytest.mark.asyncio
    async def test_num_results_capped_at_20(self, provider):
        """Search should not request more than 20 results from API."""
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = AsyncMock(return_value={"web": {"results": []}})
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.closed = False
        provider._session = mock_session

        await provider.search("test", num_results=100)

        call_args = mock_session.get.call_args
        params = call_args[1].get("params", {})
        assert params["count"] == 20

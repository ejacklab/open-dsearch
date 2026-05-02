"""Unit tests for search providers."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from src.search.providers.base import (
    SearchProvider,
    ProviderConfig,
    SearchResult,
    ProviderStatus,
    ProviderHealth
)
from src.search.providers.gemini import GeminiProvider
from src.search.providers.minimax import MiniMaxProvider
from src.search.providers.kimi import KimiProvider
from src.search.providers.registry import ProviderRegistry


class TestSearchResult:
    """Tests for SearchResult dataclass."""
    
    def test_create_search_result(self):
        """Test creating a search result."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
            source="test"
        )
        
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"
        assert result.source == "test"
        assert result.score == 0.0
        assert result.timestamp is not None
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Snippet",
            source="test",
            score=0.5
        )
        
        data = result.to_dict()
        assert data["title"] == "Test"
        assert data["url"] == "https://example.com"
        assert data["score"] == 0.5
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "title": "Test",
            "url": "https://example.com",
            "snippet": "Snippet",
            "source": "test",
            "score": 0.5,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        result = SearchResult.from_dict(data)
        assert result.title == "Test"
        assert result.url == "https://example.com"
        assert result.score == 0.5


class TestProviderConfig:
    """Tests for ProviderConfig."""
    
    def test_create_config(self):
        """Test creating provider config."""
        config = ProviderConfig(
            api_key="test-key",
            timeout_seconds=60.0,
            max_retries=5
        )
        
        assert config.api_key == "test-key"
        assert config.timeout_seconds == 60.0
        assert config.max_retries == 5
        assert config.enabled is True
    
    def test_config_extra_headers(self):
        """Test config with extra headers."""
        config = ProviderConfig(
            api_key="key",
            extra_headers={"X-Custom": "value"}
        )
        
        assert config.extra_headers["X-Custom"] == "value"


class TestProviderHealth:
    """Tests for ProviderHealth."""
    
    def test_initial_health(self):
        """Test initial health state."""
        health = ProviderHealth()
        
        assert health.status == ProviderStatus.HEALTHY
        assert health.consecutive_failures == 0
        assert health.total_requests == 0
    
    def test_record_success(self):
        """Test recording successful request."""
        health = ProviderHealth()
        
        # Simulate some failures first
        health.consecutive_failures = 2
        health.status = ProviderStatus.DEGRADED
        
        # Record success
        health.last_success = datetime.now(timezone.utc)
        health.consecutive_failures = 0
        health.successful_requests = 1
        health.total_requests = 1
        
        assert health.consecutive_failures == 0
        assert health.successful_requests == 1
    
    def test_record_failure(self):
        """Test recording failed request."""
        health = ProviderHealth()
        
        health.consecutive_failures = 4
        health.total_requests = 4
        health.last_failure = datetime.now(timezone.utc)
        
        # After 5 failures, status should be DOWN
        health.consecutive_failures = 5
        health.status = ProviderStatus.DOWN
        
        assert health.status == ProviderStatus.DOWN
        assert health.consecutive_failures == 5


class TestProviderRegistry:
    """Tests for ProviderRegistry."""
    
    def test_list_providers(self):
        """Test listing registered providers."""
        providers = ProviderRegistry.list_providers()
        
        assert "gemini" in providers
        assert "minimax" in providers
        assert "kimi" in providers
    
    def test_get_provider_class(self):
        """Test getting provider class."""
        cls = ProviderRegistry.get_provider_class("gemini")
        assert cls == GeminiProvider
        
        cls = ProviderRegistry.get_provider_class("unknown")
        assert cls is None
    
    def test_create_provider(self):
        """Test creating provider instance."""
        config = ProviderConfig(api_key="test-key")
        provider = ProviderRegistry.create_provider("gemini", config)
        
        assert isinstance(provider, GeminiProvider)
        assert provider.config.api_key == "test-key"
    
    def test_register_provider(self):
        """Test registering a new provider."""
        
        class MockProvider(SearchProvider):
            @property
            def name(self):
                return "mock"
            
            @property
            def supports_realtime(self):
                return False
            
            async def search(self, query, num_results=10, include_realtime=False):
                return []
            
            async def health_check(self):
                return ProviderStatus.HEALTHY
        
        ProviderRegistry.register("mock", MockProvider)
        
        assert "mock" in ProviderRegistry.list_providers()
        
        # Cleanup
        ProviderRegistry.unregister("mock")


class TestGeminiProvider:
    """Tests for GeminiProvider."""
    
    def test_provider_properties(self):
        """Test provider properties."""
        config = ProviderConfig(api_key="test-key")
        provider = GeminiProvider(config)
        
        assert provider.name == "gemini"
        assert provider.supports_realtime is True
    
    def test_is_available_with_key(self):
        """Test availability with API key."""
        config = ProviderConfig(api_key="test-key")
        provider = GeminiProvider(config)
        
        assert provider.is_available is True
    
    def test_is_available_without_key(self):
        """Test availability without API key."""
        config = ProviderConfig(api_key="")
        provider = GeminiProvider(config)
        
        assert provider.is_available is False
    
    def test_is_available_disabled(self):
        """Test availability when disabled."""
        config = ProviderConfig(api_key="test-key", enabled=False)
        provider = GeminiProvider(config)
        
        assert provider.is_available is False
    
    def test_parse_response(self):
        """Test parsing Gemini API response."""
        config = ProviderConfig(api_key="test-key")
        provider = GeminiProvider(config)
        
        data = {
            "candidates": [{
                "groundingMetadata": {
                    "groundingChunks": [
                        {"web": {"title": "Result 1", "uri": "https://example.com/1"}},
                        {"web": {"title": "Result 2", "uri": "https://example.com/2"}}
                    ]
                }
            }]
        }
        
        
        results = provider._parse_response(data, "test query", 10)
        
        assert len(results) == 2
        assert results[0].title == "Result 1"
        assert results[0].url == "https://example.com/1"
        assert results[0].source == "gemini"
    
    def test_parse_empty_response(self):
        """Test parsing empty response."""
        config = ProviderConfig(api_key="test-key")
        provider = GeminiProvider(config)
        
        results = provider._parse_response({}, "query", 10)
        assert len(results) == 0
        
        results = provider._parse_response({"candidates": []}, "query", 10)
        assert len(results) == 0
    
    def test_record_success(self):
        """Test recording successful request."""
        config = ProviderConfig(api_key="test-key")
        provider = GeminiProvider(config)
        
        provider.record_success(100.0)
        
        health = provider.get_health()
        assert health.total_requests == 1
        assert health.successful_requests == 1
        assert health.consecutive_failures == 0
    
    def test_record_failure(self):
        """Test recording failed request."""
        config = ProviderConfig(api_key="test-key")
        provider = GeminiProvider(config)
        
        provider.record_failure(Exception("Test error"))
        
        health = provider.get_health()
        assert health.total_requests == 1
        assert health.consecutive_failures == 1


class TestMiniMaxProvider:
    """Tests for MiniMaxProvider."""
    
    def test_provider_properties(self):
        """Test provider properties."""
        config = ProviderConfig(api_key="test-key")
        provider = MiniMaxProvider(config)
        
        assert provider.name == "minimax"
        assert provider.supports_realtime is False
    
    def test_parse_response_with_results(self):
        """Test parsing response with results field."""
        config = ProviderConfig(api_key="test-key")
        provider = MiniMaxProvider(config)
        
        data = {
            "results": [
                {"title": "Result 1", "url": "https://example.com/1", "snippet": "Snippet 1"},
                {"title": "Result 2", "url": "https://example.com/2", "snippet": "Snippet 2"}
            ]
        }
        
        results = provider._parse_response(data, "query")
        
        assert len(results) == 2
        assert results[0].title == "Result 1"
        assert results[0].source == "minimax"
    
    def test_parse_response_with_organic(self):
        """Test parsing response with organic field."""
        config = ProviderConfig(api_key="test-key")
        provider = MiniMaxProvider(config)
        
        data = {
            "organic": [
                {"title": "Result 1", "link": "https://example.com/1", "description": "Desc 1"}
            ]
        }
        
        results = provider._parse_response(data, "query")
        
        assert len(results) == 1
        assert results[0].url == "https://example.com/1"


class TestKimiProvider:
    """Tests for KimiProvider."""
    
    def test_provider_properties(self):
        """Test provider properties."""
        config = ProviderConfig(api_key="test-key")
        provider = KimiProvider(config)
        
        assert provider.name == "kimi"
        assert provider.supports_realtime is True
    
    def test_parse_markdown_links(self):
        """Test parsing markdown links from content."""
        config = ProviderConfig(api_key="test-key")
        provider = KimiProvider(config)
        
        data = {
            "choices": [{
                "message": {
                    "content": "Here are some results:\n[Result 1](https://example.com/1)\n[Result 2](https://example.com/2)"
                }
            }]
        }
        
        results = provider._parse_response(data, "query", 10)
        
        assert len(results) == 2
        assert results[0].title == "Result 1"
        assert results[0].url == "https://example.com/1"
    
    def test_parse_plain_urls(self):
        """Test parsing plain URLs when no markdown links."""
        config = ProviderConfig(api_key="test-key")
        provider = KimiProvider(config)
        
        data = {
            "choices": [{
                "message": {
                    "content": "Check out https://example.com/page for more info."
                }
            }]
        }
        
        results = provider._parse_response(data, "query", 10)
        
        assert len(results) == 1
        assert results[0].url == "https://example.com/page"

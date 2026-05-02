"""Unit tests for search providers (no pytest dependency)."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from search.providers.base import (
    SearchProvider,
    ProviderConfig,
    SearchResult,
    ProviderStatus,
    ProviderHealth
)
from search.providers.gemini import GeminiProvider
from search.providers.minimax import MiniMaxProvider
from search.providers.kimi import KimiProvider
from search.providers.registry import ProviderRegistry


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
        print("  ✓ test_create_search_result")
    
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
        print("  ✓ test_to_dict")
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        from datetime import datetime, timezone
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
        print("  ✓ test_from_dict")


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
        print("  ✓ test_create_config")
    
    def test_config_extra_headers(self):
        """Test config with extra headers."""
        config = ProviderConfig(
            api_key="key",
            extra_headers={"X-Custom": "value"}
        )
        
        assert config.extra_headers["X-Custom"] == "value"
        print("  ✓ test_config_extra_headers")


class TestProviderHealth:
    """Tests for ProviderHealth."""
    
    def test_initial_health(self):
        """Test initial health state."""
        health = ProviderHealth()
        
        assert health.status == ProviderStatus.HEALTHY
        assert health.consecutive_failures == 0
        assert health.total_requests == 0
        print("  ✓ test_initial_health")


class TestProviderRegistry:
    """Tests for ProviderRegistry."""
    
    def test_list_providers(self):
        """Test listing registered providers."""
        providers = ProviderRegistry.list_providers()
        
        assert "gemini" in providers
        assert "minimax" in providers
        assert "kimi" in providers
        print("  ✓ test_list_providers")
    
    def test_get_provider_class(self):
        """Test getting provider class."""
        cls = ProviderRegistry.get_provider_class("gemini")
        assert cls == GeminiProvider
        
        cls = ProviderRegistry.get_provider_class("unknown")
        assert cls is None
        print("  ✓ test_get_provider_class")
    
    def test_create_provider(self):
        """Test creating provider instance."""
        config = ProviderConfig(api_key="test-key")
        provider = ProviderRegistry.create_provider("gemini", config)
        
        assert isinstance(provider, GeminiProvider)
        assert provider.config.api_key == "test-key"
        print("  ✓ test_create_provider")


class TestGeminiProvider:
    """Tests for GeminiProvider."""
    
    def test_provider_properties(self):
        """Test provider properties."""
        config = ProviderConfig(api_key="test-key")
        provider = GeminiProvider(config)
        
        assert provider.name == "gemini"
        assert provider.supports_realtime is True
        print("  ✓ test_provider_properties")
    
    def test_is_available_with_key(self):
        """Test availability with API key."""
        config = ProviderConfig(api_key="test-key")
        provider = GeminiProvider(config)
        
        assert provider.is_available is True
        print("  ✓ test_is_available_with_key")
    
    def test_is_available_without_key(self):
        """Test availability without API key."""
        config = ProviderConfig(api_key="")
        provider = GeminiProvider(config)
        
        assert provider.is_available is False
        print("  ✓ test_is_available_without_key")
    
    def test_is_available_disabled(self):
        """Test availability when disabled."""
        config = ProviderConfig(api_key="test-key", enabled=False)
        provider = GeminiProvider(config)
        
        assert provider.is_available is False
        print("  ✓ test_is_available_disabled")
    
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
        print("  ✓ test_parse_response")
    
    def test_parse_empty_response(self):
        """Test parsing empty response."""
        config = ProviderConfig(api_key="test-key")
        provider = GeminiProvider(config)
        
        results = provider._parse_response({}, "query", 10)
        assert len(results) == 0
        
        results = provider._parse_response({"candidates": []}, "query", 10)
        assert len(results) == 0
        print("  ✓ test_parse_empty_response")
    
    def test_record_success(self):
        """Test recording successful request."""
        config = ProviderConfig(api_key="test-key")
        provider = GeminiProvider(config)
        
        provider.record_success(100.0)
        
        health = provider.get_health()
        assert health.total_requests == 1
        assert health.successful_requests == 1
        assert health.consecutive_failures == 0
        print("  ✓ test_record_success")
    
    def test_record_failure(self):
        """Test recording failed request."""
        config = ProviderConfig(api_key="test-key")
        provider = GeminiProvider(config)
        
        provider.record_failure(Exception("Test error"))
        
        health = provider.get_health()
        assert health.total_requests == 1
        assert health.consecutive_failures == 1
        print("  ✓ test_record_failure")


class TestMiniMaxProvider:
    """Tests for MiniMaxProvider."""
    
    def test_provider_properties(self):
        """Test provider properties."""
        config = ProviderConfig(api_key="test-key")
        provider = MiniMaxProvider(config)
        
        assert provider.name == "minimax"
        assert provider.supports_realtime is False
        print("  ✓ test_provider_properties")
    
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
        print("  ✓ test_parse_response_with_results")
    
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
        print("  ✓ test_parse_response_with_organic")


class TestKimiProvider:
    """Tests for KimiProvider."""
    
    def test_provider_properties(self):
        """Test provider properties."""
        config = ProviderConfig(api_key="test-key")
        provider = KimiProvider(config)
        
        assert provider.name == "kimi"
        assert provider.supports_realtime is True
        print("  ✓ test_provider_properties")
    
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
        print("  ✓ test_parse_markdown_links")
    
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
        print("  ✓ test_parse_plain_urls")


def run_all_tests():
    """Run all tests."""
    test_classes = [
        TestSearchResult,
        TestProviderConfig,
        TestProviderHealth,
        TestProviderRegistry,
        TestGeminiProvider,
        TestMiniMaxProvider,
        TestKimiProvider,
    ]
    
    passed = 0
    failed = 0
    
    print("=" * 70)
    print("Provider Tests")
    print("=" * 70)
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        methods = [m for m in dir(test_class) if m.startswith("test_")]
        
        for method_name in methods:
            try:
                instance = test_class()
                getattr(instance, method_name)()
                passed += 1
            except Exception as e:
                print(f"  ✗ {method_name}: {e}")
                failed += 1
    
    print()
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)

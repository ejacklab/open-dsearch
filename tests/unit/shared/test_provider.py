"""Unit tests for provider abstraction module."""

import pytest
from datetime import datetime
from unittest.mock import Mock

from src.shared.provider import (
    SearchProvider,
    ProviderConfig,
    ProviderStatus,
    ProviderCapabilities,
    SearchResult,
    ProviderHealth,
    ProviderRegistry,
    get_registry,
    reset_registry,
)


class MockProvider(SearchProvider):
    """Mock provider for testing."""
    
    @property
    def name(self) -> str:
        return "mock"
    
    def _get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            web_search=True,
            realtime_search=False,
            max_results_per_query=10
        )
    
    async def search(self, query: str, num_results: int = 10, **kwargs):
        return [SearchResult(
            title=f"Result for {query}",
            url="https://example.com",
            snippet="Test snippet",
            source=self.name
        )]
    
    async def health_check(self) -> ProviderStatus:
        return ProviderStatus.HEALTHY


class TestSearchResult:
    """Tests for SearchResult dataclass."""
    
    def test_create_basic(self):
        """Test creating a basic search result."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet"
        )
        
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"
        assert result.source == "unknown"
        assert result.score == 0.0
        assert result.timestamp is not None
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Snippet",
            source="test_provider",
            score=0.95
        )
        
        data = result.to_dict()
        assert data["title"] == "Test"
        assert data["url"] == "https://example.com"
        assert data["source"] == "test_provider"
        assert data["score"] == 0.95
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "title": "Test",
            "url": "https://example.com",
            "snippet": "Snippet",
            "source": "provider",
            "score": 0.8,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        result = SearchResult.from_dict(data)
        assert result.title == "Test"
        assert result.score == 0.8
        assert result.timestamp is not None
    
    def test_from_dict_no_timestamp(self):
        """Test creating from dict without timestamp."""
        data = {
            "title": "Test",
            "url": "https://example.com",
            "snippet": "Snippet"
        }
        
        result = SearchResult.from_dict(data)
        assert result.title == "Test"
        assert result.timestamp is None


class TestProviderConfig:
    """Tests for ProviderConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = ProviderConfig(api_key="test-key")
        
        assert config.api_key == "test-key"
        assert config.timeout_seconds == 30.0
        assert config.max_retries == 3
        assert config.rate_limit_per_minute == 60
        assert config.enabled is True
        assert config.priority == 1
    
    def test_to_dict_excludes_api_key(self):
        """Test that to_dict excludes sensitive API key."""
        config = ProviderConfig(api_key="secret-key")
        data = config.to_dict()
        
        assert "api_key" not in data
        assert data["timeout_seconds"] == 30.0


class TestProviderCapabilities:
    """Tests for ProviderCapabilities."""
    
    def test_default_capabilities(self):
        """Test default capability values."""
        caps = ProviderCapabilities()
        
        assert caps.web_search is True
        assert caps.realtime_search is False
        assert caps.citations is False
        assert caps.max_results_per_query == 10
        assert caps.supported_languages == ["en"]
    
    def test_to_dict(self):
        """Test converting capabilities to dict."""
        caps = ProviderCapabilities(
            web_search=True,
            realtime_search=True,
            max_results_per_query=20
        )
        
        data = caps.to_dict()
        assert data["web_search"] is True
        assert data["realtime_search"] is True
        assert data["max_results_per_query"] == 20


class TestProviderHealth:
    """Tests for ProviderHealth."""
    
    def test_default_health(self):
        """Test default health values."""
        health = ProviderHealth()
        
        assert health.status == ProviderStatus.UNKNOWN
        assert health.consecutive_failures == 0
        assert health.success_rate_24h == 1.0
    
    def test_to_dict(self):
        """Test converting health to dict."""
        health = ProviderHealth(
            status=ProviderStatus.HEALTHY,
            consecutive_failures=0,
            average_latency_ms=150.0
        )
        
        data = health.to_dict()
        assert data["status"] == "healthy"
        assert data["average_latency_ms"] == 150.0


class TestProviderRegistry:
    """Tests for ProviderRegistry."""
    
    def setup_method(self):
        """Reset registry before each test."""
        reset_registry()
    
    def teardown_method(self):
        """Reset registry after each test."""
        reset_registry()
    
    def test_register_provider(self):
        """Test registering a provider class."""
        registry = get_registry()
        registry.register("mock", MockProvider)
        
        assert "mock" in registry.list_providers()
    
    def test_register_non_provider(self):
        """Test that non-provider classes cannot be registered."""
        registry = get_registry()
        
        with pytest.raises(ValueError, match="must inherit from SearchProvider"):
            registry.register("invalid", str)
    
    def test_create_provider(self):
        """Test creating a provider instance."""
        registry = get_registry()
        registry.register("mock", MockProvider)
        
        config = ProviderConfig(api_key="test")
        provider = registry.create("mock", config)
        
        assert isinstance(provider, MockProvider)
        assert provider.config == config
    
    def test_create_unregistered(self):
        """Test creating unregistered provider raises error."""
        registry = get_registry()
        config = ProviderConfig(api_key="test")
        
        with pytest.raises(KeyError, match="not registered"):
            registry.create("unknown", config)
    
    def test_get_enabled_providers(self):
        """Test getting enabled providers."""
        registry = get_registry()
        registry.register("mock", MockProvider)
        
        # Create enabled provider
        enabled_config = ProviderConfig(api_key="test", enabled=True)
        registry.create("mock", enabled_config)
        
        enabled = registry.get_enabled_providers()
        assert len(enabled) == 1
    

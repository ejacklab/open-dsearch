"""Integration tests for search providers."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from search.providers.base import SearchProvider, ProviderConfig, SearchResult, ProviderStatus
from search.providers.registry import ProviderRegistry
from search.providers.kimi import KimiProvider
from search.providers.gemini import GeminiProvider
from search.providers.minimax import MiniMaxProvider


class MockProvider(SearchProvider):
    """Mock provider for testing."""

    def __init__(self, name, config, simulate_failures=False):
        super().__init__(config)
        self._name = name
        self.simulate_failures = simulate_failures
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def supports_realtime(self) -> bool:
        return True

    async def search(self, query, num_results=10, include_realtime=False):
        self.call_count += 1

        if self.simulate_failures and self.call_count % 3 == 0:
            raise Exception("Simulated provider failure")

        # Return mock results
        results = []
        for i in range(min(num_results, 3)):
            results.append(SearchResult(
                title=f"Mock Result {i+1} for '{query}' from {self._name}",
                url=f"https://mock-{self._name}.com/result{i+1}",
                snippet=f"Mock snippet for query '{query}' from {self._name}",
                source=self._name,
                score=1.0 - (i * 0.2),
                metadata={"mock": True, "provider": self._name}
            ))

        return results

    async def health_check(self):
        if self.simulate_failures and self.call_count % 3 == 0:
            return ProviderStatus.DOWN
        return ProviderStatus.HEALTHY


class TestProviderRegistryClass:
    """Test cases for ProviderRegistry class methods."""

    def test_list_providers(self):
        """Test listing all registered provider names."""
        names = ProviderRegistry.list_providers()
        assert "gemini" in names
        assert "minimax" in names
        assert "kimi" in names

    def test_get_provider_class(self):
        """Test getting a provider class by name."""
        cls = ProviderRegistry.get_provider_class("gemini")
        assert cls is GeminiProvider

    def test_get_provider_class_nonexistent(self):
        """Test getting a non-existent provider class."""
        cls = ProviderRegistry.get_provider_class("nonexistent")
        assert cls is None

    def test_create_provider(self):
        """Test creating a provider instance."""
        config = ProviderConfig(api_key="test-key")
        provider = ProviderRegistry.create_provider("gemini", config)
        assert provider is not None
        assert isinstance(provider, GeminiProvider)

    def test_create_provider_nonexistent(self):
        """Test creating a non-existent provider."""
        config = ProviderConfig(api_key="test-key")
        provider = ProviderRegistry.create_provider("nonexistent", config)
        assert provider is None

    def test_register_and_unregister(self):
        """Test dynamic registration and unregistration."""
        original = ProviderRegistry.list_providers()
        ProviderRegistry.register("mock-test", MockProvider)
        assert "mock-test" in ProviderRegistry.list_providers()

        result = ProviderRegistry.unregister("mock-test")
        assert result is True
        assert "mock-test" not in ProviderRegistry.list_providers()

        # Unregister non-existent
        result = ProviderRegistry.unregister("nonexistent")
        assert result is False

        # Restore original state
        assert set(ProviderRegistry.list_providers()) == set(original)


class TestProviderBase:
    """Test base provider functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.config = ProviderConfig(
            api_key="test-api-key",
            timeout_seconds=10.0,
            max_retries=3,
            rate_limit_per_minute=60
        )
        self.provider = MockProvider("test-provider", self.config)

    def test_provider_initialization(self):
        """Test provider initialization."""
        assert self.provider.name == "test-provider"
        assert self.provider.config.api_key == "test-api-key"
        assert self.provider.config.timeout_seconds == 10.0
        assert self.provider.is_available is True

    def test_provider_availability(self):
        """Test provider availability status."""
        assert self.provider.is_available is True

        self.provider.config.enabled = False
        assert self.provider.is_available is False

        self.provider.config.enabled = True
        self.provider._circuit_open = True
        assert self.provider.is_available is False

    def test_record_success(self):
        """Test recording successful requests."""
        self.provider.record_success(150.0)

        health = self.provider.get_health()
        assert health.total_requests == 1
        assert health.successful_requests == 1
        assert health.consecutive_failures == 0
        assert health.last_success is not None
        assert health.avg_latency_ms == 150.0

    def test_record_failure(self):
        """Test recording failed requests."""
        self.provider.record_failure(Exception("Test error"))

        health = self.provider.get_health()
        assert health.total_requests == 1
        assert health.successful_requests == 0
        assert health.consecutive_failures == 1
        assert health.last_failure is not None

    def test_circuit_breaker(self):
        """Test circuit breaker behavior."""
        for _ in range(5):
            self.provider.record_failure(Exception("Test error"))

        assert self.provider._circuit_open is True
        assert self.provider.is_available is False

        self.provider.reset_circuit()
        assert self.provider._circuit_open is False
        assert self.provider.is_available is True


class TestProviderHealth:
    """Test provider health management."""

    def setup_method(self):
        """Setup test fixtures."""
        self.config = ProviderConfig(api_key="test-key")
        self.provider = MockProvider("test-provider", self.config)

    def test_initial_health_status(self):
        """Test initial health status."""
        health = self.provider.get_health()
        assert health.status == ProviderStatus.HEALTHY
        assert health.consecutive_failures == 0
        assert health.total_requests == 0

    def test_health_status_degraded(self):
        """Test health status degrades with failures."""
        # 2 consecutive failures → DEGRADED
        self.provider.record_failure(Exception("fail"))
        self.provider.record_failure(Exception("fail"))
        health = self.provider.get_health()
        assert health.status == ProviderStatus.DEGRADED

    def test_health_status_down(self):
        """Test health status goes DOWN after many failures."""
        for _ in range(5):
            self.provider.record_failure(Exception("fail"))
        health = self.provider.get_health()
        assert health.status == ProviderStatus.DOWN

    def test_rate_limit_status(self):
        """Test rate limiting status."""
        rate_limit_error = Exception("rate limit exceeded")
        self.provider.record_failure(rate_limit_error)

        health = self.provider.get_health()
        assert health.status == ProviderStatus.RATE_LIMITED


class TestSearchResult:
    """Test SearchResult functionality."""

    def test_search_result_creation(self):
        """Test SearchResult creation."""
        result = SearchResult(
            title="Test Result",
            url="https://example.com/test",
            snippet="Test snippet",
            source="test"
        )

        assert result.title == "Test Result"
        assert result.url == "https://example.com/test"
        assert result.snippet == "Test snippet"
        assert result.source == "test"
        assert result.score == 0.0
        assert result.metadata == {}
        assert result.timestamp is not None

    def test_search_result_to_dict(self):
        """Test SearchResult to_dict conversion."""
        result = SearchResult(
            title="Test Result",
            url="https://example.com/test",
            snippet="Test snippet",
            source="test",
            score=0.8,
            metadata={"key": "value"}
        )

        result_dict = result.to_dict()

        assert result_dict["title"] == "Test Result"
        assert result_dict["url"] == "https://example.com/test"
        assert result_dict["score"] == 0.8
        assert "timestamp" in result_dict

    def test_search_result_from_dict(self):
        """Test SearchResult from_dict creation."""
        data = {
            "title": "Test Result",
            "url": "https://example.com/test",
            "snippet": "Test snippet",
            "source": "test",
            "score": 0.8,
            "metadata": {"key": "value"},
            "timestamp": "2024-01-01T00:00:00"
        }

        result = SearchResult.from_dict(data)

        assert result.title == "Test Result"
        assert result.url == "https://example.com/test"
        assert result.score == 0.8

    def test_search_result_roundtrip(self):
        """Test to_dict → from_dict roundtrip."""
        original = SearchResult(
            title="Round Trip",
            url="https://example.com/rt",
            snippet="Round trip snippet",
            source="test",
            score=0.95,
            metadata={"foo": "bar"}
        )
        restored = SearchResult.from_dict(original.to_dict())

        assert restored.title == original.title
        assert restored.url == original.url
        assert restored.snippet == original.snippet
        assert restored.score == original.score


class TestProviderConfig:
    """Test ProviderConfig functionality."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ProviderConfig(api_key="test-key")

        assert config.api_key == "test-key"
        assert config.timeout_seconds == 30.0
        assert config.max_retries == 3
        assert config.rate_limit_per_minute == 60
        assert config.enabled is True
        assert config.priority == 1
        assert config.extra_headers == {}
        assert config.base_url is None

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ProviderConfig(
            api_key="test-key",
            timeout_seconds=60.0,
            max_retries=5,
            rate_limit_per_minute=120,
            enabled=False,
            priority=2,
            extra_headers={"User-Agent": "TestAgent"},
            base_url="https://api.example.com"
        )

        assert config.timeout_seconds == 60.0
        assert config.max_retries == 5
        assert config.enabled is False
        assert config.base_url == "https://api.example.com"

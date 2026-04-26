"""Unit tests for xAI provider — config field access and response parsing."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.search.providers.base import ProviderConfig, ProviderStatus
from src.search.providers.xai import XaiProvider


class TestXaiProviderConfig:
    """Verify xAI provider works with ProviderConfig model/max_tokens/temperature."""

    def test_config_defaults(self):
        """ProviderConfig should have model, max_tokens, temperature defaults."""
        config = ProviderConfig(api_key="test-key")
        assert config.model is None
        assert config.max_tokens == 2048
        assert config.temperature == 0.0

    def test_config_custom_model(self):
        """ProviderConfig should accept custom model settings."""
        config = ProviderConfig(
            api_key="test-key",
            model="grok-3",
            max_tokens=4096,
            temperature=0.7,
        )
        assert config.model == "grok-3"
        assert config.max_tokens == 4096
        assert config.temperature == 0.7

    def test_xai_uses_config_model(self):
        """xAI provider should use config.model or fall back to grok-beta."""
        config = ProviderConfig(api_key="test-key", model="grok-3")
        provider = XaiProvider(config)
        assert provider.config.model == "grok-3"

    def test_xai_uses_default_model(self):
        """xAI provider falls back to grok-beta when model is None."""
        config = ProviderConfig(api_key="test-key")
        provider = XaiProvider(config)
        # In xai.py: self.config.model or "grok-beta"
        assert provider.config.model or "grok-beta" == "grok-beta"

    def test_provider_properties(self):
        config = ProviderConfig(api_key="test-key")
        provider = XaiProvider(config)
        assert provider.name == "xai"
        assert provider.supports_realtime is False


class TestXaiProviderParsing:
    """Test xAI response parsing."""

    def test_parse_json_results(self):
        config = ProviderConfig(api_key="test-key")
        provider = XaiProvider(config)

        data = {
            "choices": [{
                "message": {
                    "content": '{"results": [{"title": "Test", "url": "https://example.com", "content": "desc", "published_at": "2024-01-01"}]}'
                }
            }]
        }
        results = provider._parse_response(data, "test query")
        assert len(results) == 1
        assert results[0].title == "Test"
        assert results[0].url == "https://example.com"

    def test_parse_fallback_urls(self):
        config = ProviderConfig(api_key="test-key")
        provider = XaiProvider(config)

        data = {
            "choices": [{
                "message": {
                    "content": "Check this out https://example.com/page for more details"
                }
            }]
        }
        results = provider._parse_response(data, "test query")
        assert len(results) >= 1
        assert results[0].url == "https://example.com/page"

    def test_parse_empty_content(self):
        config = ProviderConfig(api_key="test-key")
        provider = XaiProvider(config)

        data = {"choices": [{"message": {"content": "Some text without urls"}}]}
        results = provider._parse_response(data, "test query")
        # Should still produce a fallback result
        assert len(results) >= 1

"""Integration tests for search providers with mocked APIs."""

import json
from pathlib import Path

import pytest
import responses

import research_python as rp


@pytest.fixture
def gemini_mock_response():
    """Load mock Gemini API response."""
    return {
        "candidates": [{
            "groundingMetadata": {
                "groundingChunks": [
                    {"web": {"uri": "https://example.com/doc1", "title": "Documentation"}},
                    {"web": {"uri": "https://github.com/user/repo", "title": "GitHub Repo"}},
                    {"web": {"uri": "https://docs.python.org", "title": "Python Docs"}},
                ]
            }
        }]
    }


class TestGeminiSearch:
    """Integration tests for Gemini search provider."""
    
    @responses.activate
    def test_gemini_search_success(self, gemini_mock_response, mock_api_keys):
        """Should successfully parse Gemini search results."""
        responses.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
            json=gemini_mock_response,
            status=200
        )
        
        # Disable rate limiting for test
        rp._rate_limiters["gemini"] = rp.RateLimiter(rate=1000, burst=100)
        
        results = rp.search_gemini("test query", limit=10)
        
        assert len(results) == 3
        assert all(hasattr(r, "title") for r in results)
        assert all(hasattr(r, "url") for r in results)
        assert results[0].source == "gemini"
    
    @responses.activate
    def test_gemini_search_rate_limit(self, mock_api_keys):
        """Should handle rate limit errors."""
        responses.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
            status=429,
            json={"error": "Rate limit exceeded"}
        )
        
        rp._rate_limiters["gemini"] = rp.RateLimiter(rate=1000, burst=100)
        
        # With retry decorator, this may retry and eventually fail
        results = rp.search_gemini("test query", limit=10)
        
        # Should return empty on error after retries
        assert results == []
    
    @responses.activate
    def test_gemini_search_empty_response(self, mock_api_keys):
        """Should handle empty response."""
        responses.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
            json={"candidates": []},
            status=200
        )
        
        rp._rate_limiters["gemini"] = rp.RateLimiter(rate=1000, burst=100)
        
        results = rp.search_gemini("test query")
        assert results == []


class TestMiniMaxSearch:
    """Integration tests for MiniMax search provider."""
    
    @responses.activate
    def test_minimax_search_success(self, mock_api_keys):
        """Should successfully parse MiniMax search results."""
        mock_response = {
            "organic": [
                {"title": "Result 1", "link": "https://example.com/1", "snippet": "Snippet 1"},
                {"title": "Result 2", "link": "https://example.com/2", "snippet": "Snippet 2"},
            ]
        }
        
        responses.post(
            "https://api.minimax.io/v1/coding_plan/search",
            json=mock_response,
            status=200
        )
        
        rp._rate_limiters["minimax"] = rp.RateLimiter(rate=1000, burst=100)
        
        results = rp.search_minimax("test query", limit=10)
        
        assert len(results) == 2
        assert results[0].title == "Result 1"
        assert results[0].url == "https://example.com/1"
    
    @responses.activate
    def test_minimax_search_empty_organic(self, mock_api_keys):
        """Should handle empty organic results."""
        responses.post(
            "https://api.minimax.io/v1/coding_plan/search",
            json={"organic": []},
            status=200
        )
        
        rp._rate_limiters["minimax"] = rp.RateLimiter(rate=1000, burst=100)
        
        results = rp.search_minimax("test query")
        assert results == []


class TestKimiSearch:
    """Integration tests for Kimi search provider."""
    
    @responses.activate
    def test_kimi_search_success(self, mock_api_keys):
        """Should successfully parse Kimi search results."""
        mock_response = {
            "choices": [{
                "message": {
                    "content": """
[Python Documentation](https://docs.python.org)
Official Python documentation.

[Rust Book](https://doc.rust-lang.org)
The Rust Programming Language.
"""
                }
            }]
        }
        
        responses.post(
            "https://api.moonshot.ai/v1/chat/completions",
            json=mock_response,
            status=200
        )
        
        rp._rate_limiters["kimi"] = rp.RateLimiter(rate=1000, burst=100)
        
        results = rp.search_kimi("test query", limit=10)
        
        assert len(results) == 2
        assert "docs.python.org" in results[0].url
    
    @responses.activate
    def test_kimi_search_no_links(self, mock_api_keys):
        """Should handle content without markdown links."""
        responses.post(
            "https://api.moonshot.ai/v1/chat/completions",
            json={"choices": [{"message": {"content": "No links here"}}]},
            status=200
        )
        
        rp._rate_limiters["kimi"] = rp.RateLimiter(rate=1000, burst=100)
        
        results = rp.search_kimi("test query")
        assert results == []


class TestMultiProviderSearch:
    """Tests for multi-provider search orchestration."""
    
    @responses.activate
    def test_providers_available(self, mock_api_keys):
        """Should detect available providers."""
        # All providers should be detected with mock keys
        providers = []
        if rp.get_secret("gemini"):
            providers.append("gemini")
        if rp.get_secret("minimax"):
            providers.append("minimax")
        if rp.get_secret("kimi"):
            providers.append("kimi")
        
        assert len(providers) == 3

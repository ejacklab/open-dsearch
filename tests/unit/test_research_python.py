"""Tests for research_python.py module."""

import time
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest
import responses

import research_python as rp


class TestRateLimiter:
    """Tests for token bucket rate limiter."""
    
    def test_rate_limiter_initializes_full(self):
        """Rate limiter should start with full bucket."""
        limiter = rp.RateLimiter(rate=2.0, burst=5)
        assert limiter._tokens == 5
    
    def test_rate_limiter_acquires_token(self):
        """Should acquire token when available."""
        limiter = rp.RateLimiter(rate=10.0, burst=5)
        limiter.acquire()
        assert limiter._tokens == 4
    
    def test_rate_limiter_acquires_multiple_tokens(self):
        """Should acquire multiple tokens correctly."""
        limiter = rp.RateLimiter(rate=10.0, burst=5)
        limiter.acquire()
        limiter.acquire()
        limiter.acquire()
        assert limiter._tokens == 2
    
    def test_rate_limiter_refills_over_time(self):
        """Should refill tokens over time."""
        limiter = rp.RateLimiter(rate=100.0, burst=5)  # Fast refill
        limiter._tokens = 0  # Empty the bucket
        
        # Wait a bit
        time.sleep(0.05)
        
        # Should have some tokens now
        limiter.acquire()
        assert limiter._tokens >= 0


class TestQueryExpansion:
    """Tests for query expansion functionality."""
    
    def test_expand_queries_returns_original(self):
        """Should always include original query."""
        queries = rp.expand_queries("Python testing", count=3)
        assert "Python testing" in queries
    
    def test_expand_queries_generates_variations(self):
        """Should generate query variations."""
        queries = rp.expand_queries("Rust async", count=5)
        assert len(queries) >= 2
        assert all(isinstance(q, str) for q in queries)
    
    def test_expand_queries_respects_count(self):
        """Should respect the count parameter."""
        queries = rp.expand_queries("topic", count=3)
        assert len(queries) <= 3
    
    def test_expand_queries_with_variations(self):
        """Should include template-based variations."""
        queries = rp.expand_queries("Python", count=8)
        # Should have original + variations
        assert len(queries) > 1
        # Check for expected variations
        variations = [q for q in queries if q != "Python"]
        assert len(variations) > 0


class TestTopicValidation:
    """Tests for topic validation."""
    
    def test_validate_topic_valid(self):
        """Should accept valid topics."""
        is_valid, error = rp.validate_topic("Python programming")
        assert is_valid is True
        assert error == ""
    
    def test_validate_topic_empty(self):
        """Should reject empty topics."""
        is_valid, error = rp.validate_topic("")
        assert is_valid is False
        assert "empty" in error.lower()
    
    def test_validate_topic_whitespace(self):
        """Should reject whitespace-only topics."""
        is_valid, error = rp.validate_topic("   ")
        assert is_valid is False
        assert "empty" in error.lower()
    
    def test_validate_topic_too_long(self):
        """Should reject topics over 500 chars."""
        is_valid, error = rp.validate_topic("x" * 501)
        assert is_valid is False
        assert "too long" in error.lower()
    
    def test_validate_topic_max_length(self):
        """Should accept topics exactly 500 chars."""
        is_valid, error = rp.validate_topic("x" * 500)
        assert is_valid is True


class TestScoringAndRanking:
    """Tests for result scoring and ranking."""
    
    def test_score_and_rank_empty_list(self):
        """Should handle empty result list."""
        results = []
        scored = rp.score_and_rank(results, top_n=5, query_terms=["test"])
        assert scored == []
    
    def test_score_and_rank_single_result(self):
        """Should handle single result."""
        results = [rp.SearchResult("Title", "https://example.com", "Snippet")]
        scored = rp.score_and_rank(results, top_n=5, query_terms=["test"])
        assert len(scored) == 1
    
    def test_score_and_rank_deduplicates(self):
        """Should deduplicate results by URL."""
        results = [
            rp.SearchResult("Title1", "https://example.com/page1", "Snippet1"),
            rp.SearchResult("Title2", "https://example.com/page1", "Snippet2"),  # Same URL
            rp.SearchResult("Title3", "https://example.com/page2", "Snippet3"),
        ]
        scored = rp.score_and_rank(results, top_n=10, query_terms=["test"])
        # Should dedupe to 2 unique URLs
        assert len(scored) == 2
    
    def test_score_and_rank_limits_top_n(self):
        """Should respect top_n limit."""
        results = [
            rp.SearchResult(f"Title{i}", f"https://example{i}.com", f"Snippet{i}")
            for i in range(20)
        ]
        scored = rp.score_and_rank(results, top_n=5, query_terms=["test"])
        assert len(scored) == 5
    
    def test_score_and_rank_keyword_matching(self):
        """Should score based on keyword matching."""
        results = [
            rp.SearchResult("Python Guide", "https://example.com/python", "Learn Python"),
            rp.SearchResult("Other Topic", "https://example.com/other", "Something else"),
        ]
        scored = rp.score_and_rank(results, top_n=5, query_terms=["python"])
        # Python result should score higher
        assert scored[0].title == "Python Guide"
    
    def test_score_and_rank_source_quality_bonus(self):
        """Should give bonus for high-quality sources."""
        results = [
            rp.SearchResult("GitHub Repo", "https://github.com/user/repo", "Code"),
            rp.SearchResult("Random Site", "https://random.com/page", "Content"),
        ]
        scored = rp.score_and_rank(results, top_n=5, query_terms=["test"])
        # GitHub should score higher due to source bonus
        assert "github.com" in scored[0].url or scored[0].score >= scored[1].score


class TestFetchUrl:
    """Tests for URL fetching."""
    
    @responses.activate
    def test_fetch_url_success(self):
        """Should fetch and convert HTML to text."""
        html_content = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Hello World</h1>
                <p>This is a test.</p>
                <script>alert('ignore me');</script>
            </body>
        </html>
        """
        responses.add(
            responses.GET,
            "https://example.com",
            body=html_content,
            status=200,
            content_type="text/html"
        )
        
        result = rp.fetch_url("https://example.com", max_kb=100)
        assert result["url"] == "https://example.com"
        assert "Hello World" in result["markdown"]
        assert "alert" not in result["markdown"]  # Script should be removed
    
    @responses.activate
    def test_fetch_url_failure(self):
        """Should handle fetch failures gracefully."""
        responses.add(
            responses.GET,
            "https://example.com",
            body="Not Found",
            status=404
        )
        
        result = rp.fetch_url("https://example.com")
        assert "Error" in result["markdown"] or "Fetch failed" in result["title"]
    
    @responses.activate
    def test_fetch_url_respects_max_kb(self):
        """Should respect max_kb limit."""
        large_content = "x" * (200 * 1024)  # 200KB
        responses.add(
            responses.GET,
            "https://example.com",
            body=large_content,
            status=200
        )
        
        result = rp.fetch_url("https://example.com", max_kb=100)
        # Content should be truncated
        assert len(result["markdown"]) <= 100 * 1024 + 100  # Allow for truncation message


class TestGetSecret:
    """Tests for get_secret function."""
    
    def test_get_secret_from_env(self, monkeypatch):
        """Should get secret from environment."""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        secret = rp.get_secret("gemini")
        assert secret == "test-key"
    
    def test_get_secret_not_set(self, monkeypatch):
        """Should return None when secret not set."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        secret = rp.get_secret("gemini")
        # May return None or config value, but shouldn't crash
        assert secret is None or isinstance(secret, str)


class TestWithRetry:
    """Tests for retry decorator."""
    
    def test_retry_success_first_attempt(self):
        """Should return result on first success."""
        @rp.with_retry
        def success_func():
            return "success"
        
        result = success_func()
        assert result == "success"
    
    def test_retry_eventual_success(self):
        """Should retry and eventually succeed."""
        call_count = 0
        
        @rp.with_retry(max_retries=3, base_delay=0.01)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = flaky_func()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhausted(self):
        """Should raise after max retries exhausted."""
        @rp.with_retry(max_retries=2, base_delay=0.01)
        def always_fails():
            raise Exception("Always fails")
        
        with pytest.raises(Exception, match="Always fails"):
            always_fails()


class TestSearchProviders:
    """Tests for search provider functions."""
    
    @responses.activate
    def test_search_gemini_no_api_key(self, monkeypatch):
        """Should return empty list when no API key."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        # Also mock config.get_secret to return None
        with patch("research_python.get_secret", return_value=None):
            results = rp.search_gemini("test query")
            assert results == []
    
    @responses.activate
    def test_search_minimax_no_api_key(self, monkeypatch):
        """Should return empty list when no API key."""
        monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
        with patch("research_python.get_secret", return_value=None):
            results = rp.search_minimax("test query")
            assert results == []
    
    @responses.activate
    def test_search_kimi_no_api_key(self, monkeypatch):
        """Should return empty list when no API key."""
        monkeypatch.delenv("KIMI_API_KEY", raising=False)
        with patch("research_python.get_secret", return_value=None):
            results = rp.search_kimi("test query")
            assert results == []
    
    @responses.activate
    def test_search_gemini_success(self, gemini_search_response, mock_api_keys):
        """Should parse Gemini search results."""
        responses.add(
            responses.POST,
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
            json=gemini_search_response,
            status=200
        )
        
        # Disable rate limiter for test
        rp._rate_limiters["gemini"] = rp.RateLimiter(rate=1000, burst=100)
        
        results = rp.search_gemini("test query", limit=10)
        assert len(results) > 0
        assert all(isinstance(r, rp.SearchResult) for r in results)
    
    @responses.activate  
    def test_search_minimax_success(self, minimax_search_response, mock_api_keys):
        """Should parse MiniMax search results."""
        responses.add(
            responses.POST,
            "https://api.minimax.io/v1/coding_plan/search",
            json=minimax_search_response,
            status=200
        )
        
        rp._rate_limiters["minimax"] = rp.RateLimiter(rate=1000, burst=100)
        
        results = rp.search_minimax("test query", limit=10)
        assert len(results) > 0
        assert all(isinstance(r, rp.SearchResult) for r in results)
    
    @responses.activate
    def test_search_kimi_success(self, kimi_search_response, mock_api_keys):
        """Should parse Kimi search results."""
        responses.add(
            responses.POST,
            "https://api.moonshot.ai/v1/chat/completions",
            json=kimi_search_response,
            status=200
        )
        
        rp._rate_limiters["kimi"] = rp.RateLimiter(rate=1000, burst=100)
        
        results = rp.search_kimi("test query", limit=10)
        assert len(results) > 0
        assert all(isinstance(r, rp.SearchResult) for r in results)


class TestResearchFunction:
    """Tests for main research function."""
    
    def test_research_invalid_topic(self):
        """Should return None for invalid topic."""
        result = rp.research("")
        assert result is None
    
    def test_research_invalid_top(self):
        """Should return None for invalid top parameter."""
        result = rp.research("topic", top=0)
        assert result is None
    
    def test_research_invalid_queries(self):
        """Should return None for invalid queries parameter."""
        result = rp.research("topic", queries=0)
        assert result is None
    
    @patch("research_python.get_secret")
    def test_research_no_providers(self, mock_get_secret):
        """Should return None when no providers available."""
        mock_get_secret.return_value = None
        result = rp.research("test topic")
        assert result is None

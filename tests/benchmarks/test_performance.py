"""Performance benchmark tests."""

import pytest

import research_python as rp


class TestQueryExpansionBenchmark:
    """Benchmark query expansion performance."""
    
    def test_expand_queries_performance(self, benchmark):
        """Benchmark query expansion."""
        result = benchmark(rp.expand_queries, "Rust async programming", count=10)
        assert len(result) > 0
        # Target: <10ms
        assert benchmark.stats["mean"] < 0.01


class TestScoringBenchmark:
    """Benchmark result scoring performance."""
    
    def test_score_and_rank_small_dataset(self, benchmark):
        """Benchmark scoring with 10 results."""
        results = [
            rp.SearchResult(f"Title {i}", f"https://example{i}.com", f"Snippet {i}")
            for i in range(10)
        ]
        
        result = benchmark(rp.score_and_rank, results, 5, ["test", "query"])
        assert len(result) <= 5
    
    def test_score_and_rank_medium_dataset(self, benchmark):
        """Benchmark scoring with 100 results."""
        results = [
            rp.SearchResult(f"Title {i}", f"https://example{i}.com", f"Snippet {i}")
            for i in range(100)
        ]
        
        result = benchmark(rp.score_and_rank, results, 50, ["test", "query"])
        assert len(result) <= 50
        # Target: <100ms for 100 results
        assert benchmark.stats["mean"] < 0.1
    
    def test_score_and_rank_large_dataset(self, benchmark):
        """Benchmark scoring with 1000 results."""
        results = [
            rp.SearchResult(f"Title {i}", f"https://example{i}.com", f"Snippet {i}")
            for i in range(1000)
        ]
        
        result = benchmark(rp.score_and_rank, results, 50, ["test", "query"])
        assert len(result) <= 50


class TestRateLimiterBenchmark:
    """Benchmark rate limiter performance."""
    
    def test_rate_limiter_acquire(self, benchmark):
        """Benchmark rate limiter acquire."""
        limiter = rp.RateLimiter(rate=1000.0, burst=100)
        
        def acquire_token():
            limiter.acquire()
        
        benchmark(acquire_token)


class TestTopicValidationBenchmark:
    """Benchmark topic validation performance."""
    
    def test_validate_topic_short(self, benchmark):
        """Benchmark validation of short topic."""
        benchmark(rp.validate_topic, "Python")
    
    def test_validate_topic_long(self, benchmark):
        """Benchmark validation of long topic."""
        long_topic = "Python " * 50
        benchmark(rp.validate_topic, long_topic)


class TestFetchUrlBenchmark:
    """Benchmark URL fetching (mocked)."""
    
    @pytest.mark.slow
    def test_fetch_url_mock(self, benchmark, mocker):
        """Benchmark URL fetch with mocked response."""
        mock_response = mocker.MagicMock()
        mock_response.text = "<html><body><h1>Test</h1></body></html>"
        
        mocker.patch("requests.get", return_value=mock_response)
        
        # This will test the HTML parsing logic
        result = benchmark(rp.fetch_url, "https://example.com")
        assert result is not None

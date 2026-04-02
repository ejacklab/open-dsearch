"""Unit tests for ranking and deduplication."""

import pytest
from datetime import datetime, timezone

from src.search.ranking.scorer import ResultScorer, ScoringWeights
from src.search.ranking.dedup import Deduplicator, DedupConfig
from src.search.providers.base import SearchResult


class TestResultScorer:
    """Tests for ResultScorer."""
    
    def test_score_results(self):
        """Test scoring results."""
        scorer = ResultScorer()
        
        results = [
            SearchResult("Python Tutorial", "https://example.com", "Learn Python", "gemini"),
            SearchResult("Python Guide", "https://docs.python.org", "Official docs", "kimi"),
        ]
        
        scored = scorer.score_results(results, "python tutorial")
        
        assert len(scored) == 2
        assert all(r.score > 0 for r in scored)
        # Results should be sorted by score
        assert scored[0].score >= scored[1].score
    
    def test_score_with_github_bonus(self):
        """Test scoring with GitHub URL bonus."""
        scorer = ResultScorer()
        
        results = [
            SearchResult("Some Tutorial", "https://example.com/python", "Tutorial", "gemini"),
            SearchResult("Python Repo", "https://github.com/user/python", "Code", "kimi"),
        ]
        
        scored = scorer.score_results(results, "python")
        
        # GitHub result should score higher
        github_result = next(r for r in scored if "github.com" in r.url)
        other_result = next(r for r in scored if "example.com" in r.url)
        assert github_result.score > other_result.score
    
    def test_score_with_docs_bonus(self):
        """Test scoring with docs URL bonus."""
        scorer = ResultScorer()
        
        results = [
            SearchResult("Tutorial", "https://example.com/python", "Tutorial", "gemini"),
            SearchResult("Docs", "https://docs.python.org", "Documentation", "kimi"),
        ]
        
        scored = scorer.score_results(results, "python")
        
        # Docs result should score higher
        docs_result = next(r for r in scored if "docs." in r.url)
        other_result = next(r for r in scored if "example.com" in r.url)
        assert docs_result.score > other_result.score
    
    def test_score_empty_results(self):
        """Test scoring empty results."""
        scorer = ResultScorer()
        
        scored = scorer.score_results([], "query")
        
        assert scored == []
    
    def test_get_top_results(self):
        """Test getting top N results."""
        scorer = ResultScorer()
        
        results = [
            SearchResult(f"Result {i}", f"https://{i}.com", "Snippet", "gemini", score=float(10-i))
            for i in range(10)
        ]
        
        top = scorer.get_top_results(results, n=5)
        
        assert len(top) == 5
        assert top[0].score == 10.0
        assert top[4].score == 6.0
    
    def test_filter_by_domain(self):
        """Test filtering by domain."""
        scorer = ResultScorer()
        
        results = [
            SearchResult("R1", "https://github.com/user/repo", "Code", "gemini"),
            SearchResult("R2", "https://example.com/page", "Page", "kimi"),
            SearchResult("R3", "https://github.com/other/repo", "Other", "minimax"),
        ]
        
        filtered = scorer.filter_by_domain(results, allowed_domains=["github.com"])
        
        assert len(filtered) == 2
        assert all("github.com" in r.url for r in filtered)
    
    def test_filter_blocked_domains(self):
        """Test filtering blocked domains."""
        scorer = ResultScorer()
        
        results = [
            SearchResult("R1", "https://github.com/user/repo", "Code", "gemini"),
            SearchResult("R2", "https://spam.com/page", "Spam", "kimi"),
            SearchResult("R3", "https://example.com/page", "Page", "minimax"),
        ]
        
        filtered = scorer.filter_by_domain(results, blocked_domains=["spam.com"])
        
        assert len(filtered) == 2
        assert all("spam.com" not in r.url for r in filtered)


class TestDeduplicator:
    """Tests for Deduplicator."""
    
    def test_deduplicate_by_url(self):
        """Test deduplicating by URL."""
        dedup = Deduplicator()
        
        results = [
            SearchResult("Result 1", "https://example.com/page", "Snippet 1", "gemini"),
            SearchResult("Result 2", "https://example.com/page", "Snippet 2", "kimi"),  # Same URL
            SearchResult("Result 3", "https://other.com/page", "Snippet 3", "minimax"),
        ]
        
        deduped = dedup.deduplicate(results)
        
        assert len(deduped) == 2
    
    def test_normalize_urls(self):
        """Test URL normalization."""
        dedup = Deduplicator(DedupConfig(normalize_urls=True))
        
        results = [
            SearchResult("R1", "https://www.example.com/page", "S1", "gemini"),
            SearchResult("R2", "https://example.com/page", "S2", "kimi"),  # Same without www
        ]
        
        deduped = dedup.deduplicate(results)
        
        assert len(deduped) == 1
    
    def test_limit_by_domain(self):
        """Test limiting results per domain."""
        dedup = Deduplicator(DedupConfig(max_per_domain=2))
        
        results = [
            SearchResult(f"R{i}", f"https://example.com/page{i}", f"S{i}", "gemini")
            for i in range(5)
        ]
        
        deduped = dedup.deduplicate(results)
        
        assert len(deduped) == 2
    
    def test_deduplicate_by_content(self):
        """Test deduplicating by content similarity."""
        dedup = Deduplicator(DedupConfig(content_similarity_threshold=0.9))
        
        results = [
            SearchResult("Python Tutorial", "https://example.com", "Learn Python basics", "gemini"),
            SearchResult("Python Tutorial", "https://other.com", "Learn Python basics", "kimi"),  # Similar content
            SearchResult("Different Topic", "https://another.com", "Something else entirely", "minimax"),
        ]
        
        deduped = dedup.deduplicate(results)
        
        # Should have at most 2 results (first and third)
        assert len(deduped) <= 2
    
    def test_empty_results(self):
        """Test deduplicating empty results."""
        dedup = Deduplicator()
        
        deduped = dedup.deduplicate([])
        
        assert deduped == []
    
    def test_get_duplicate_groups(self):
        """Test getting duplicate groups."""
        dedup = Deduplicator(DedupConfig(content_similarity_threshold=0.9))
        
        results = [
            SearchResult("Python Tutorial", "https://example.com", "Learn Python", "gemini"),
            SearchResult("Python Guide", "https://other.com", "Learn Python", "kimi"),  # Similar
            SearchResult("Rust Tutorial", "https://rust.com", "Learn Rust", "minimax"),  # Different
        ]
        
        groups = dedup.get_duplicate_groups(results)
        
        assert len(groups) == 2  # Two groups: [Python results] and [Rust result]

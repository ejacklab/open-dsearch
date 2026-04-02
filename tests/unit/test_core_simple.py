"""Simple unit tests for core search functionality (no external deps)."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import importlib.util

# Load modules directly to avoid __init__.py imports
spec = importlib.util.spec_from_file_location("base", "src/search/providers/base.py")
base_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base_module)
ProviderConfig = base_module.ProviderConfig
SearchResult = base_module.SearchResult
ProviderStatus = base_module.ProviderStatus
ProviderHealth = base_module.ProviderHealth

spec = importlib.util.spec_from_file_location("caching_base", "src/search/caching/base.py")
caching_base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(caching_base)
CacheKey = caching_base.CacheKey

spec = importlib.util.spec_from_file_location("scorer", "src/search/ranking/scorer.py")
scorer_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scorer_module)
ResultScorer = scorer_module.ResultScorer

spec = importlib.util.spec_from_file_location("dedup", "src/search/ranking/dedup.py")
dedup_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dedup_module)
Deduplicator = dedup_module.Deduplicator
DedupConfig = dedup_module.DedupConfig

spec = importlib.util.spec_from_file_location("expansion", "src/search/expansion.py")
expansion_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(expansion_module)
QueryExpander = expansion_module.QueryExpander


class TestSearchResult:
    """Tests for SearchResult."""
    
    def test_create(self):
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
            source="test"
        )
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.score == 0.0
        print("  ✓ SearchResult creation")
    
    def test_to_dict(self):
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Snippet",
            source="test",
            score=0.5
        )
        data = result.to_dict()
        assert data["title"] == "Test"
        assert data["score"] == 0.5
        print("  ✓ SearchResult.to_dict")
    
    def test_from_dict(self):
        from datetime import datetime
        data = {
            "title": "Test",
            "url": "https://example.com",
            "snippet": "Snippet",
            "source": "test",
            "score": 0.5,
            "timestamp": datetime.now().isoformat()
        }
        result = SearchResult.from_dict(data)
        assert result.title == "Test"
        assert result.score == 0.5
        print("  ✓ SearchResult.from_dict")


class TestProviderConfig:
    """Tests for ProviderConfig."""
    
    def test_create(self):
        config = ProviderConfig(
            api_key="test-key",
            timeout_seconds=60.0,
            max_retries=5
        )
        assert config.api_key == "test-key"
        assert config.timeout_seconds == 60.0
        assert config.max_retries == 5
        assert config.enabled is True
        print("  ✓ ProviderConfig creation")


class TestProviderHealth:
    """Tests for ProviderHealth."""
    
    def test_initial(self):
        health = ProviderHealth()
        assert health.status == ProviderStatus.HEALTHY
        assert health.consecutive_failures == 0
        print("  ✓ ProviderHealth initial state")


class TestCacheKey:
    """Tests for CacheKey."""
    
    def test_create(self):
        key = CacheKey(
            query="python tutorial",
            providers=("gemini", "kimi"),
            num_results=10,
            include_realtime=False
        )
        assert key.query == "python tutorial"
        assert key.providers == ("gemini", "kimi")
        print("  ✓ CacheKey creation")
    
    def test_to_string(self):
        key = CacheKey(
            query="python tutorial",
            providers=("gemini", "kimi"),
            num_results=10,
            include_realtime=False
        )
        key_str = key.to_string()
        assert isinstance(key_str, str)
        assert len(key_str) == 32
        print("  ✓ CacheKey.to_string")
    
    def test_consistency(self):
        key1 = CacheKey.from_params(
            query="Python Tutorial",
            providers=["gemini", "kimi"],
            num_results=10
        )
        key2 = CacheKey.from_params(
            query="python tutorial",
            providers=["kimi", "gemini"],
            num_results=10
        )
        assert key1.to_string() == key2.to_string()
        print("  ✓ CacheKey consistency")


class TestResultScorer:
    """Tests for ResultScorer."""
    
    def test_score_results(self):
        scorer = ResultScorer()
        results = [
            SearchResult("Python Tutorial", "https://example.com", "Learn Python", "gemini"),
            SearchResult("Python Guide", "https://docs.python.org", "Official docs", "kimi"),
        ]
        scored = scorer.score_results(results, "python tutorial")
        assert len(scored) == 2
        assert all(r.score > 0 for r in scored)
        print("  ✓ ResultScorer scoring")
    
    def test_github_bonus(self):
        scorer = ResultScorer()
        results = [
            SearchResult("Tutorial", "https://example.com/python", "Tutorial", "gemini"),
            SearchResult("Repo", "https://github.com/user/python", "Code", "kimi"),
        ]
        scored = scorer.score_results(results, "python")
        github_result = next(r for r in scored if "github.com" in r.url)
        other_result = next(r for r in scored if "example.com" in r.url)
        assert github_result.score > other_result.score
        print("  ✓ ResultScorer GitHub bonus")
    
    def test_empty_results(self):
        scorer = ResultScorer()
        scored = scorer.score_results([], "query")
        assert scored == []
        print("  ✓ ResultScorer empty results")


class TestDeduplicator:
    """Tests for Deduplicator."""
    
    def test_deduplicate_by_url(self):
        dedup = Deduplicator()
        results = [
            SearchResult("Result 1", "https://example.com/page", "Snippet 1", "gemini"),
            SearchResult("Result 2", "https://example.com/page", "Snippet 2", "kimi"),
            SearchResult("Result 3", "https://other.com/page", "Snippet 3", "minimax"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 2
        print("  ✓ Deduplicator URL dedup")
    
    def test_normalize_urls(self):
        dedup = Deduplicator(DedupConfig(normalize_urls=True))
        results = [
            SearchResult("R1", "https://www.example.com/page", "S1", "gemini"),
            SearchResult("R2", "https://example.com/page", "S2", "kimi"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1
        print("  ✓ Deduplicator URL normalization")
    
    def test_limit_by_domain(self):
        dedup = Deduplicator(DedupConfig(max_per_domain=2))
        results = [
            SearchResult(f"R{i}", f"https://example.com/page{i}", f"S{i}", "gemini")
            for i in range(5)
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 2
        print("  ✓ Deduplicator domain limit")
    
    def test_empty_results(self):
        dedup = Deduplicator()
        deduped = dedup.deduplicate([])
        assert deduped == []
        print("  ✓ Deduplicator empty results")


class TestQueryExpander:
    """Tests for QueryExpander."""
    
    def test_includes_original(self):
        expander = QueryExpander()
        expansions = expander.expand("python tutorial", count=5)
        assert "python tutorial" in expansions
        print("  ✓ QueryExpander includes original")
    
    def test_count(self):
        expander = QueryExpander()
        expansions = expander.expand("python", count=3)
        assert len(expansions) <= 3
        print("  ✓ QueryExpander respects count")
    
    def test_extract_keywords(self):
        expander = QueryExpander()
        keywords = expander.extract_keywords("how to learn python programming")
        assert "python" in keywords
        assert "programming" in keywords
        assert "how" not in keywords
        print("  ✓ QueryExpander keyword extraction")


def run_all_tests():
    """Run all tests."""
    test_classes = [
        TestSearchResult,
        TestProviderConfig,
        TestProviderHealth,
        TestCacheKey,
        TestResultScorer,
        TestDeduplicator,
        TestQueryExpander,
    ]
    
    passed = 0
    failed = 0
    
    print("=" * 70)
    print("Open Dsearch Core Tests")
    print("=" * 70)
    print()
    
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

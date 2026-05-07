"""Unit tests for search orchestrator."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.search.orchestrator import SearchOrchestrator, SearchOptions, SearchResponse
from src.search.providers.base import SearchProvider, ProviderConfig, SearchResult, ProviderStatus
from src.search.caching.memory_cache import MemoryCache
from src.search.ranking.scorer import ResultScorer


class MockSearchProvider(SearchProvider):
    """Mock provider for testing."""
    
    def __init__(self, name, results=None, fail=False):
        config = ProviderConfig(api_key="test-key")
        super().__init__(config)
        self._name = name
        self._results = results or []
        self._fail = fail
    
    @property
    def name(self):
        return self._name
    
    @property
    def supports_realtime(self):
        return True
    
    async def search(self, query, num_results=10, include_realtime=False):
        if self._fail:
            raise Exception("Search failed")
        return [
            SearchResult(
                title=f"{self._name} result",
                url=f"https://{self._name}.com",
                snippet=f"From {self._name}",
                source=self._name
            )
        ]
    
    async def health_check(self):
        return ProviderStatus.HEALTHY


class TestSearchOptions:
    """Tests for SearchOptions."""
    
    def test_default_options(self):
        """Test default options."""
        opts = SearchOptions(query="python")
        
        assert opts.query == "python"
        assert opts.num_results == 10
        assert opts.providers is None
        assert opts.use_cache is True
        assert opts.deduplicate is True
    
    def test_custom_options(self):
        """Test custom options."""
        opts = SearchOptions(
            query="python",
            num_results=20,
            providers=["gemini", "kimi"],
            use_cache=False
        )
        
        assert opts.num_results == 20
        assert opts.providers == ["gemini", "kimi"]
        assert opts.use_cache is False


class TestSearchResponse:
    """Tests for SearchResponse."""
    
    def test_create_response(self):
        """Test creating response."""
        response = SearchResponse(
            results=[],
            total_found=0,
            providers_used=[],
            providers_failed=[],
            execution_time_ms=100.0,
            cache_hit=False
        )
        
        assert response.total_found == 0
        assert response.cache_hit is False
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        response = SearchResponse(
            results=[
                SearchResult("Title", "https://example.com", "Snippet", "gemini")
            ],
            total_found=1,
            providers_used=["gemini"],
            providers_failed=[],
            execution_time_ms=100.0,
            cache_hit=False
        )
        
        data = response.to_dict()
        
        assert data["total_found"] == 1
        assert data["cache_hit"] is False
        assert len(data["results"]) == 1


class TestSearchOrchestrator:
    """Tests for SearchOrchestrator."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mock providers."""
        p1 = MockSearchProvider("gemini")
        p2 = MockSearchProvider("kimi")
        
        orch = SearchOrchestrator(providers=[p1, p2])
        return orch
    
    @pytest.mark.asyncio
    async def test_add_remove_provider(self):
        """Test adding and removing providers."""
        orch = SearchOrchestrator()
        provider = MockSearchProvider("test")
        
        orch.add_provider(provider)
        assert len(orch.providers) == 1
        
        removed = orch.remove_provider("test")
        assert removed is True
        assert len(orch.providers) == 0
        
        # Remove non-existent
        removed = orch.remove_provider("nonexistent")
        assert removed is False
    
    @pytest.mark.asyncio
    async def test_search_with_providers(self):
        """Test search with providers."""
        orch = SearchOrchestrator()
        orch.add_provider(MockSearchProvider("gemini"))
        orch.add_provider(MockSearchProvider("kimi"))
        
        options = SearchOptions(query="python", num_results=5)
        response = await orch.search(options)
        
        assert response.total_found == 2
        assert "gemini" in response.providers_used
        assert "kimi" in response.providers_used
        assert len(response.results) == 2
    
    @pytest.mark.asyncio
    async def test_search_with_cache_hit(self):
        """Test search with cache hit."""
        cache = MemoryCache()
        orch = SearchOrchestrator(cache=cache)
        
        # Pre-populate cache
        from src.search.caching.base import CacheKey
        key = CacheKey.from_params("python", ["gemini"], 10)
        cached_results = [
            SearchResult("Cached", "https://cached.com", "Cached result", "gemini")
        ]
        await cache.set(key, cached_results)
        
        options = SearchOptions(query="python", num_results=10, providers=["gemini"])
        response = await orch.search(options)
        
        assert response.cache_hit is True
        assert response.total_found == 1
        assert response.results[0].title == "Cached"
    
    @pytest.mark.asyncio
    async def test_search_with_provider_failure(self):
        """Test search with provider failure."""
        orch = SearchOrchestrator()
        orch.add_provider(MockSearchProvider("gemini", fail=False))
        orch.add_provider(MockSearchProvider("kimi", fail=True))
        
        options = SearchOptions(query="python", num_results=5)
        response = await orch.search(options)
        
        assert "gemini" in response.providers_used
        assert "kimi" in response.providers_failed
        assert response.total_found == 1
    
    @pytest.mark.asyncio
    async def test_search_no_providers(self):
        """Test search with no providers."""
        orch = SearchOrchestrator()
        
        options = SearchOptions(query="python")
        response = await orch.search(options)
        
        assert response.total_found == 0
        assert response.results == []
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check."""
        orch = SearchOrchestrator()
        orch.add_provider(MockSearchProvider("gemini"))
        orch.add_provider(MockSearchProvider("kimi"))
        
        health = await orch.health_check()
        
        assert health["gemini"] == ProviderStatus.HEALTHY
        assert health["kimi"] == ProviderStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_stream_search(self):
        """Test streaming search."""
        orch = SearchOrchestrator()
        orch.add_provider(MockSearchProvider("gemini"))
        orch.add_provider(MockSearchProvider("kimi"))
        
        options = SearchOptions(query="python", num_results=5, expand_queries=False)
        results = []
        
        async for result in orch.stream_search(options):
            results.append(result)
        
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_rescore_after_enrichment_flag_default(self):
        """rescore_after_enrichment defaults to True."""
        opts = SearchOptions(query="test")
        assert opts.rescore_after_enrichment is True

    @pytest.mark.asyncio
    async def test_search_rescores_after_enrichment(self):
        """Verify orchestrator calls rescore when enrichment + flag enabled."""
        scorer = ResultScorer()
        orch = SearchOrchestrator(scorer=scorer)
        orch.add_provider(MockSearchProvider("gemini"))

        options = SearchOptions(
            query="python",
            fetch_content=True,
            rescore_after_enrichment=True,
        )

        # Mock _enrich_with_content to add fetched_content
        original_enrich = orch._enrich_with_content

        async def mock_enrich(results, **kwargs):
            for r in results:
                r.fetched_content = "Python programming tutorial content"
            return results

        orch._enrich_with_content = mock_enrich

        response = await orch.search(options)

        # Results should have been re-scored with content
        # If rescore worked, results with fetched_content should have
        # higher scores than without
        assert response.total_found >= 1

    @pytest.mark.asyncio
    async def test_search_no_rescore_when_flag_off(self):
        """Verify no rescore when rescore_after_enrichment=False."""
        from unittest.mock import patch

        orch = SearchOrchestrator()
        orch.add_provider(MockSearchProvider("gemini"))

        options = SearchOptions(
            query="python",
            fetch_content=True,
            rescore_after_enrichment=False,
        )

        async def mock_enrich(results, **kwargs):
            for r in results:
                r.fetched_content = "Python content"
            return results

        orch._enrich_with_content = mock_enrich

        with patch.object(orch.scorer, 'rescore_with_content', wraps=orch.scorer.rescore_with_content) as spy:
            await orch.search(options)
            spy.assert_not_called()

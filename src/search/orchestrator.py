"""Search orchestrator for multi-provider coordination."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, AsyncIterator

from .providers.base import SearchProvider, SearchResult, ProviderStatus
from .providers.registry import ProviderRegistry
from .caching.base import CacheBackend, CacheKey
from .caching.memory_cache import MemoryCache
from .ranking.scorer import ResultScorer
from .ranking.dedup import Deduplicator, DedupConfig
from .expansion import QueryExpander


@dataclass
class SearchOptions:
    """Search options."""
    query: str
    num_results: int = 10
    providers: Optional[List[str]] = None
    include_realtime: bool = False
    fetch_content: bool = False
    use_cache: bool = True
    timeout_seconds: float = 30.0
    deduplicate: bool = True
    expand_queries: bool = True
    num_query_variations: int = 3


@dataclass
class SearchResponse:
    """Search response."""
    results: List[SearchResult]
    total_found: int
    providers_used: List[str]
    providers_failed: List[str]
    execution_time_ms: float
    cache_hit: bool
    query_expansions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "results": [r.to_dict() for r in self.results],
            "total_found": self.total_found,
            "providers_used": self.providers_used,
            "providers_failed": self.providers_failed,
            "execution_time_ms": self.execution_time_ms,
            "cache_hit": self.cache_hit,
            "query_expansions": self.query_expansions,
        }


class SearchOrchestrator:
    """Orchestrate multi-provider search."""
    
    def __init__(
        self,
        providers: Optional[List[SearchProvider]] = None,
        cache: Optional[CacheBackend] = None,
        scorer: Optional[ResultScorer] = None,
        deduplicator: Optional[Deduplicator] = None,
        expander: Optional[QueryExpander] = None
    ):
        """
        Initialize orchestrator.
        
        Args:
            providers: List of search providers
            cache: Cache backend
            scorer: Result scorer
            deduplicator: Deduplicator
            expander: Query expander
        """
        self.providers = providers or []
        self.cache = cache or MemoryCache()
        self.scorer = scorer or ResultScorer()
        self.deduplicator = deduplicator or Deduplicator(DedupConfig())
        self.expander = expander or QueryExpander()
    
    def add_provider(self, provider: SearchProvider) -> None:
        """Add a search provider."""
        self.providers.append(provider)
    
    def remove_provider(self, name: str) -> bool:
        """Remove a provider by name."""
        for i, p in enumerate(self.providers):
            if p.name == name:
                self.providers.pop(i)
                return True
        return False
    
    async def search(self, options: SearchOptions) -> SearchResponse:
        """
        Execute search.
        
        Args:
            options: Search options
            
        Returns:
            Search response
        """
        start_time = time.time()
        
        # Check cache
        if options.use_cache and self.cache:
            cache_key = CacheKey.from_params(
                query=options.query,
                providers=options.providers or [p.name for p in self.providers],
                num_results=options.num_results,
                include_realtime=options.include_realtime
            )
            
            cached = await self.cache.get(cache_key)
            if cached:
                return SearchResponse(
                    results=cached[:options.num_results],
                    total_found=len(cached),
                    providers_used=[],
                    providers_failed=[],
                    execution_time_ms=(time.time() - start_time) * 1000,
                    cache_hit=True
                )
        
        # Expand queries if enabled
        queries = [options.query]
        if options.expand_queries:
            queries = self.expander.expand(
                options.query,
                count=options.num_query_variations
            )
        
        # Get providers to use
        providers_to_use = self._get_providers(options.providers)
        
        if not providers_to_use:
            return SearchResponse(
                results=[],
                total_found=0,
                providers_used=[],
                providers_failed=[],
                execution_time_ms=(time.time() - start_time) * 1000,
                cache_hit=False,
                query_expansions=queries
            )
        
        # Execute searches
        all_results = []
        providers_used = []
        providers_failed = []
        
        # Create tasks for each provider-query combination
        tasks = []
        for provider in providers_to_use:
            for query in queries:
                task = self._search_with_provider(
                    provider,
                    query,
                    options.num_results,
                    options.include_realtime
                )
                tasks.append((provider.name, query, task))
        
        # Execute with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*[t[2] for t in tasks], return_exceptions=True),
                timeout=options.timeout_seconds
            )
            
            # Process results
            for i, (name, query, _) in enumerate(tasks):
                result = results[i]
                
                if isinstance(result, Exception):
                    providers_failed.append(name)
                else:
                    if name not in providers_used:
                        providers_used.append(name)
                    all_results.extend(result)
                    
        except asyncio.TimeoutError:
            providers_failed.extend([t[0] for t in tasks])
        
        # Deduplicate
        if options.deduplicate:
            all_results = self.deduplicator.deduplicate(all_results)
        
        # Score and rank
        all_results = self.scorer.score_results(all_results, options.query)
        
        # Cache results
        if options.use_cache and self.cache and all_results:
            await self.cache.set(cache_key, all_results)
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        return SearchResponse(
            results=all_results[:options.num_results],
            total_found=len(all_results),
            providers_used=providers_used,
            providers_failed=providers_failed,
            execution_time_ms=execution_time_ms,
            cache_hit=False,
            query_expansions=queries
        )
    
    async def stream_search(
        self,
        options: SearchOptions
    ) -> AsyncIterator[SearchResult]:
        """
        Stream search results as they arrive.
        
        Args:
            options: Search options
            
        Yields:
            Search results
        """
        # Expand queries if enabled
        queries = [options.query]
        if options.expand_queries:
            queries = self.expander.expand(
                options.query,
                count=options.num_query_variations
            )
        
        # Get providers
        providers_to_use = self._get_providers(options.providers)
        
        if not providers_to_use:
            return
        
        # Create tasks
        tasks = []
        for provider in providers_to_use:
            for query in queries:
                task = self._search_with_provider(
                    provider,
                    query,
                    options.num_results,
                    options.include_realtime
                )
                tasks.append(asyncio.create_task(task))
        
        # Yield results as they complete
        seen_urls = set()
        
        for coro in asyncio.as_completed(tasks, timeout=options.timeout_seconds):
            try:
                results = await coro
                for result in results:
                    if result.url not in seen_urls:
                        seen_urls.add(result.url)
                        yield result
            except Exception:
                pass  # Skip failed results in stream
    
    async def _search_with_provider(
        self,
        provider: SearchProvider,
        query: str,
        num_results: int,
        include_realtime: bool
    ) -> List[SearchResult]:
        """Search with a single provider."""
        if not provider.is_available:
            return []

        # Do NOT swallow exceptions — let asyncio.gather handle them so
        # orchestrator can record which providers failed
        return await provider.search(
            query,
            num_results=num_results,
            include_realtime=include_realtime
        )
    
    def _get_providers(self, names: Optional[List[str]]) -> List[SearchProvider]:
        """Get providers by name or all available."""
        if not names:
            return [p for p in self.providers if p.is_available]
        
        name_set = set(names)
        return [
            p for p in self.providers
            if p.name in name_set and p.is_available
        ]
    
    async def health_check(self) -> Dict[str, ProviderStatus]:
        """
        Check health of all providers.
        
        Returns:
            Dictionary of provider names to status
        """
        results = {}
        
        for provider in self.providers:
            try:
                status = await provider.health_check()
                results[provider.name] = status
            except Exception:
                results[provider.name] = ProviderStatus.DOWN
        
        return results
    
    async def close(self):
        """Close all providers."""
        for provider in self.providers:
            if hasattr(provider, 'close'):
                await provider.close()
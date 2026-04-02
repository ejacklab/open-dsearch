"""
Open Dsearch - Core Search Module

Multi-provider autonomous research pipeline with caching, ranking,
and provider abstraction.
"""
from typing import TYPE_CHECKING

__version__ = "0.2.0"

# Type-only imports to avoid circular dependencies at import time
if TYPE_CHECKING:
    from .orchestrator import SearchOrchestrator, SearchOptions, SearchResponse
    from .providers.base import SearchProvider, ProviderConfig, SearchResult, ProviderStatus
    from .caching.base import CacheBackend, CacheKey
    from .ranking.scorer import ResultScorer

__all__ = [
    "SearchOrchestrator",
    "SearchOptions",
    "SearchResponse",
    "SearchProvider",
    "ProviderConfig",
    "SearchResult",
    "ProviderStatus",
    "CacheBackend",
    "CacheKey",
    "ResultScorer",
]


def __getattr__(name: str):
    """Lazy import to avoid heavy dependencies during test collection."""
    if name == "SearchOrchestrator":
        from .orchestrator import SearchOrchestrator
        return SearchOrchestrator
    if name == "SearchOptions":
        from .orchestrator import SearchOptions
        return SearchOptions
    if name == "SearchResponse":
        from .orchestrator import SearchResponse
        return SearchResponse
    if name == "SearchProvider":
        from .providers.base import SearchProvider
        return SearchProvider
    if name == "ProviderConfig":
        from .providers.base import ProviderConfig
        return ProviderConfig
    if name == "SearchResult":
        from .providers.base import SearchResult
        return SearchResult
    if name == "ProviderStatus":
        from .providers.base import ProviderStatus
        return ProviderStatus
    if name == "CacheBackend":
        from .caching.base import CacheBackend
        return CacheBackend
    if name == "CacheKey":
        from .caching.base import CacheKey
        return CacheKey
    if name == "ResultScorer":
        from .ranking.scorer import ResultScorer
        return ResultScorer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

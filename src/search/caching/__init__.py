"""Caching layer for search results."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import CacheBackend, CacheKey
    from .memory_cache import MemoryCache
    from .sqlite_cache import SQLiteCache

__all__ = [
    "CacheBackend",
    "CacheKey",
    "MemoryCache",
    "SQLiteCache",
]


def __getattr__(name: str):
    """Lazy import to avoid heavy dependencies during test collection."""
    if name == "CacheBackend":
        from .base import CacheBackend
        return CacheBackend
    if name == "CacheKey":
        from .base import CacheKey
        return CacheKey
    if name == "MemoryCache":
        from .memory_cache import MemoryCache
        return MemoryCache
    if name == "SQLiteCache":
        from .sqlite_cache import SQLiteCache
        return SQLiteCache
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

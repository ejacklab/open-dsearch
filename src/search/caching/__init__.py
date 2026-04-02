"""Caching layer for search results."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import CacheBackend, CacheKey
    from .sqlite_cache import SQLiteCache
    from .memory_cache import MemoryCache

__all__ = [
    "CacheBackend",
    "CacheKey",
    "SQLiteCache",
    "MemoryCache",
]


def __getattr__(name: str):
    """Lazy import to avoid heavy dependencies during test collection."""
    if name == "CacheBackend":
        from .base import CacheBackend
        return CacheBackend
    if name == "CacheKey":
        from .base import CacheKey
        return CacheKey
    if name == "SQLiteCache":
        from .sqlite_cache import SQLiteCache
        return SQLiteCache
    if name == "MemoryCache":
        from .memory_cache import MemoryCache
        return MemoryCache
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

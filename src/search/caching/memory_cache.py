"""In-memory cache implementation."""

import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from .base import CacheBackend, CacheKey
from ..providers.base import SearchResult


@dataclass
class CacheEntry:
    """Cache entry with TTL."""
    results: List[SearchResult]
    expires_at: float
    access_count: int = 0
    created_at: float = field(default_factory=time.time)


class MemoryCache(CacheBackend):
    """In-memory LRU cache with TTL."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize memory cache.
        
        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0
    
    async def get(self, key: CacheKey) -> Optional[List[SearchResult]]:
        """
        Get cached results.
        
        Args:
            key: Cache key
            
        Returns:
            Cached results or None
        """
        key_str = key.to_string()
        
        if key_str not in self._cache:
            self._misses += 1
            return None
        
        entry = self._cache[key_str]
        
        # Check if expired
        if time.time() > entry.expires_at:
            del self._cache[key_str]
            self._misses += 1
            return None
        
        # Update access stats and move to end (LRU)
        entry.access_count += 1
        self._cache.move_to_end(key_str)
        self._hits += 1
        
        return entry.results
    
    async def set(
        self,
        key: CacheKey,
        results: List[SearchResult],
        ttl_seconds: int = 3600
    ) -> None:
        """
        Cache results.
        
        Args:
            key: Cache key
            results: Results to cache
            ttl_seconds: Time to live in seconds
        """
        key_str = key.to_string()
        
        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size and key_str not in self._cache:
            self._cache.popitem(last=False)
        
        ttl = ttl_seconds if ttl_seconds > 0 else self.default_ttl
        entry = CacheEntry(
            results=results,
            expires_at=time.time() + ttl if ttl_seconds != 0 else time.time()  # ttl=0 = immediate expiry
        )
        
        self._cache[key_str] = entry
        self._cache.move_to_end(key_str)
    
    async def invalidate(self, pattern: Optional[str] = None) -> int:
        """
        Invalidate cached entries.
        
        Args:
            pattern: Optional pattern to match (None = all)
            
        Returns:
            Number of entries invalidated
        """
        if pattern is None:
            count = len(self._cache)
            self._cache.clear()
            return count
        
        # For memory cache, pattern matching is limited
        # We match against the key string
        to_remove = []
        for key_str in self._cache.keys():
            if pattern.lower() in key_str.lower():
                to_remove.append(key_str)
        
        for key_str in to_remove:
            del self._cache[key_str]
        
        return len(to_remove)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with stats
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        
        # Count expired entries
        now = time.time()
        expired = sum(
            1 for entry in self._cache.values()
            if now > entry.expires_at
        )
        
        return {
            "type": "memory",
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
            "expired_entries": expired,
            "default_ttl": self.default_ttl,
        }
    
    async def clear_expired(self) -> int:
        """
        Clear expired entries.
        
        Returns:
            Number of entries cleared
        """
        now = time.time()
        to_remove = [
            key for key, entry in self._cache.items()
            if now > entry.expires_at
        ]
        
        for key in to_remove:
            del self._cache[key]
        
        return len(to_remove)

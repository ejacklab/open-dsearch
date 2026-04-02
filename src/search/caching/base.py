"""Cache interface definitions."""

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple

from ..providers.base import SearchResult


@dataclass(frozen=True)
class CacheKey:
    """Immutable cache key for search queries."""
    query: str
    providers: Tuple[str, ...]
    num_results: int
    include_realtime: bool = False
    
    def to_string(self) -> str:
        """Convert to string hash."""
        data = {
            "q": self.query.lower().strip(),
            "p": sorted(self.providers),
            "n": self.num_results,
            "r": self.include_realtime,
        }
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()[:32]
    
    @classmethod
    def from_params(
        cls,
        query: str,
        providers: List[str],
        num_results: int,
        include_realtime: bool = False
    ) -> "CacheKey":
        """Create cache key from parameters."""
        return cls(
            query=query,
            providers=tuple(sorted(providers)),
            num_results=num_results,
            include_realtime=include_realtime
        )


class CacheBackend(ABC):
    """Abstract cache backend."""
    
    @abstractmethod
    async def get(self, key: CacheKey) -> Optional[List[SearchResult]]:
        """
        Get cached results.
        
        Args:
            key: Cache key
            
        Returns:
            Cached results or None
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def invalidate(self, pattern: Optional[str] = None) -> int:
        """
        Invalidate cached entries.
        
        Args:
            pattern: Optional pattern to match (None = all)
            
        Returns:
            Number of entries invalidated
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with stats
        """
        pass
    
    def _serialize_results(self, results: List[SearchResult]) -> str:
        """Serialize results to JSON string."""
        return json.dumps([r.to_dict() for r in results])
    
    def _deserialize_results(self, data: str) -> List[SearchResult]:
        """Deserialize results from JSON string."""
        try:
            items = json.loads(data)
            return [SearchResult.from_dict(item) for item in items]
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

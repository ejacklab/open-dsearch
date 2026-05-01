"""Unit tests for caching."""

import sqlite3
import time
import pytest
import asyncio
from datetime import datetime

from src.search.caching.base import CacheKey
from src.search.caching.memory_cache import MemoryCache
from src.search.caching.sqlite_cache import SQLiteCache
from src.search.providers.base import SearchResult


class TestCacheKey:
    """Tests for CacheKey."""
    
    def test_create_key(self):
        """Test creating cache key."""
        key = CacheKey(
            query="python tutorial",
            providers=("gemini", "kimi"),
            num_results=10,
            include_realtime=False
        )
        
        assert key.query == "python tutorial"
        assert key.providers == ("gemini", "kimi")
        assert key.num_results == 10
    
    def test_to_string(self):
        """Test converting to string."""
        key = CacheKey(
            query="python tutorial",
            providers=("gemini", "kimi"),
            num_results=10,
            include_realtime=False
        )
        
        key_str = key.to_string()
        assert isinstance(key_str, str)
        assert len(key_str) == 32  # SHA256 hex digest length
    
    def test_from_params(self):
        """Test creating from parameters."""
        key = CacheKey.from_params(
            query="python tutorial",
            providers=["kimi", "gemini"],  # Unsorted
            num_results=10
        )
        
        assert key.providers == ("gemini", "kimi")  # Sorted
    
    def test_key_consistency(self):
        """Test that same params produce same key."""
        key1 = CacheKey.from_params(
            query="Python Tutorial",
            providers=["gemini", "kimi"],
            num_results=10
        )
        
        key2 = CacheKey.from_params(
            query="python tutorial",  # Lowercase
            providers=["kimi", "gemini"],  # Different order
            num_results=10
        )
        
        assert key1.to_string() == key2.to_string()


class TestMemoryCache:
    """Tests for MemoryCache."""
    
    @pytest.fixture
    async def cache(self):
        """Create cache instance."""
        cache = MemoryCache(max_size=100, default_ttl=3600)
        yield cache
    
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test setting and getting cache entry."""
        cache = MemoryCache()
        key = CacheKey.from_params("query", ["gemini"], 10)
        results = [
            SearchResult("Title", "https://example.com", "Snippet", "gemini")
        ]
        
        await cache.set(key, results)
        cached = await cache.get(key)
        
        assert cached is not None
        assert len(cached) == 1
        assert cached[0].title == "Title"
    
    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss."""
        cache = MemoryCache()
        key = CacheKey.from_params("query", ["gemini"], 10)
        
        cached = await cache.get(key)
        
        assert cached is None
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test cache entry expiration."""
        cache = MemoryCache()
        key = CacheKey.from_params("query", ["gemini"], 10)
        results = [SearchResult("Title", "https://example.com", "Snippet", "gemini")]
        
        # Set with 0 TTL (expired immediately)
        await cache.set(key, results, ttl_seconds=0)
        
        # Wait a tiny bit
        await asyncio.sleep(0.1)
        
        cached = await cache.get(key)
        assert cached is None
    
    @pytest.mark.asyncio
    async def test_invalidate_all(self):
        """Test invalidating all entries."""
        cache = MemoryCache()
        key1 = CacheKey.from_params("query1", ["gemini"], 10)
        key2 = CacheKey.from_params("query2", ["kimi"], 10)
        
        await cache.set(key1, [SearchResult("T1", "https://1.com", "S1", "gemini")])
        await cache.set(key2, [SearchResult("T2", "https://2.com", "S2", "kimi")])
        
        count = await cache.invalidate()
        
        assert count == 2
        assert await cache.get(key1) is None
        assert await cache.get(key2) is None
    
    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting cache stats."""
        cache = MemoryCache()
        key = CacheKey.from_params("query", ["gemini"], 10)
        
        # Initial stats
        stats = await cache.get_stats()
        assert stats["type"] == "memory"
        assert stats["size"] == 0
        
        # Add entry
        await cache.set(key, [SearchResult("T", "https://example.com", "S", "gemini")])
        
        # Get to record hit
        await cache.get(key)
        
        stats = await cache.get_stats()
        assert stats["size"] == 1
        assert stats["hits"] == 1
        assert stats["hit_rate"] == 1.0
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU eviction."""
        cache = MemoryCache(max_size=2)
        
        key1 = CacheKey.from_params("query1", ["gemini"], 10)
        key2 = CacheKey.from_params("query2", ["gemini"], 10)
        key3 = CacheKey.from_params("query3", ["gemini"], 10)
        
        await cache.set(key1, [SearchResult("T1", "https://1.com", "S", "gemini")])
        await cache.set(key2, [SearchResult("T2", "https://2.com", "S", "gemini")])
        
        # Access key1 to make it more recent
        await cache.get(key1)
        
        # Add third entry - should evict key2
        await cache.set(key3, [SearchResult("T3", "https://3.com", "S", "gemini")])
        
        assert await cache.get(key1) is not None
        assert await cache.get(key2) is None  # Evicted
        assert await cache.get(key3) is not None


class TestSQLiteCache:
    """Tests for SQLiteCache."""
    
    @pytest.fixture
    async def cache(self, tmp_path):
        """Create cache instance."""
        db_path = tmp_path / "test_cache.db"
        cache = SQLiteCache(db_path=db_path)
        yield cache
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, tmp_path):
        """Test setting and getting cache entry."""
        db_path = tmp_path / "test_cache.db"
        cache = SQLiteCache(db_path=db_path)
        
        key = CacheKey.from_params("query", ["gemini"], 10)
        results = [
            SearchResult("Title", "https://example.com", "Snippet", "gemini")
        ]
        
        await cache.set(key, results)
        cached = await cache.get(key)
        
        assert cached is not None
        assert len(cached) == 1
        assert cached[0].title == "Title"
    
    @pytest.mark.asyncio
    async def test_persistence(self, tmp_path):
        """Test that cache persists across instances."""
        db_path = tmp_path / "test_cache.db"
        key = CacheKey.from_params("query", ["gemini"], 10)
        results = [SearchResult("Title", "https://example.com", "Snippet", "gemini")]
        
        # Create first cache instance and store
        cache1 = SQLiteCache(db_path=db_path)
        await cache1.set(key, results)
        
        # Create second cache instance
        cache2 = SQLiteCache(db_path=db_path)
        cached = await cache2.get(key)
        
        assert cached is not None
        assert cached[0].title == "Title"
    
    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, tmp_path):
        """Test invalidating by pattern."""
        db_path = tmp_path / "test_cache.db"
        cache = SQLiteCache(db_path=db_path)
        
        # Add entries
        for i in range(3):
            key = CacheKey.from_params(f"query{i}", ["gemini"], 10)
            await cache.set(key, [SearchResult(f"T{i}", f"https://{i}.com", "S", "gemini")])
        
        # Invalidate with pattern
        count = await cache.invalidate(pattern="query")
        
        assert count == 3
    
    @pytest.mark.asyncio
    async def test_get_stats(self, tmp_path):
        """Test getting cache stats."""
        db_path = tmp_path / "test_cache.db"
        cache = SQLiteCache(db_path=db_path)
        
        stats = await cache.get_stats()
        
        assert stats["type"] == "sqlite"
        assert "db_path" in stats
        assert "size" in stats

    @pytest.mark.asyncio
    async def test_expiration(self, tmp_path):
        """Test that expired entries return None."""
        db_path = tmp_path / "test_cache.db"
        cache = SQLiteCache(db_path=db_path)
        
        key = CacheKey.from_params("query", ["gemini"], 10)
        results = [SearchResult("Title", "https://example.com", "Snippet", "gemini")]
        
        await cache.set(key, results, ttl_seconds=1)
        await asyncio.sleep(1.1)
        
        cached = await cache.get(key)
        assert cached is None

    @pytest.mark.asyncio
    async def test_clear_expired(self, tmp_path):
        """Test clearing expired entries."""
        db_path = tmp_path / "test_cache.db"
        cache = SQLiteCache(db_path=db_path)
        
        key = CacheKey.from_params("query", ["gemini"], 10)
        results = [SearchResult("T", "https://example.com", "S", "gemini")]
        
        await cache.set(key, results, ttl_seconds=1)
        await asyncio.sleep(2.0)
        
        cleared = await cache.clear_expired()
        assert cleared >= 1
        
        stats = await cache.get_stats()
        assert stats["size"] == 0

    @pytest.mark.asyncio
    async def test_upsert_overwrite(self, tmp_path):
        """Test that set overwrites existing entry."""
        db_path = tmp_path / "test_cache.db"
        cache = SQLiteCache(db_path=db_path)
        
        key = CacheKey.from_params("query", ["gemini"], 10)
        r1 = [SearchResult("Title1", "https://1.com", "S1", "gemini")]
        r2 = [SearchResult("Title2", "https://2.com", "S2", "gemini")]
        
        await cache.set(key, r1)
        await cache.set(key, r2)
        
        cached = await cache.get(key)
        assert cached is not None
        assert cached[0].title == "Title2"

    @pytest.mark.asyncio
    async def test_invalidate_all(self, tmp_path):
        """Test invalidating all entries."""
        db_path = tmp_path / "test_cache.db"
        cache = SQLiteCache(db_path=db_path)
        
        for i in range(3):
            key = CacheKey.from_params(f"query{i}", ["gemini"], 10)
            await cache.set(key, [SearchResult(f"T{i}", f"https://{i}.com", "S", "gemini")])
        
        count = await cache.invalidate()
        assert count == 3
        assert (await cache.get_stats())["size"] == 0

    @pytest.mark.asyncio
    async def test_corrupt_data_handling(self, tmp_path):
        """Test that corrupt JSON data returns empty list gracefully."""
        db_path = tmp_path / "test_cache.db"
        cache = SQLiteCache(db_path=db_path)
        
        # Inject corrupt data directly
        key_str = CacheKey.from_params("query", ["gemini"], 10).to_string()
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO search_cache (key, query_text, data, expires_at, created_at) VALUES (?, ?, ?, ?, ?)",
            (key_str, "query", "NOT_JSON!!!", time.time() + 3600, time.time())
        )
        conn.commit()
        conn.close()
        
        cached = await cache.get(CacheKey.from_params("query", ["gemini"], 10))
        assert cached == []

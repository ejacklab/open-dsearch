"""SQLite cache implementation."""

import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from .base import CacheBackend, CacheKey
from ..providers.base import SearchResult


class SQLiteCache(CacheBackend):
    """SQLite-based persistent cache."""
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        default_ttl: int = 3600
    ):
        """
        Initialize SQLite cache.
        
        Args:
            db_path: Path to SQLite database (None = ~/.cache/dsearch/cache.db)
            default_ttl: Default TTL in seconds
        """
        if db_path is None:
            db_path = Path.home() / ".cache" / "dsearch" / "cache.db"
        
        self.db_path = db_path
        self.default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
        
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    access_count INTEGER DEFAULT 0
                )
            """)
            
            # Create index for expiration queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires 
                ON cache(expires_at)
            """)
            
            conn.commit()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    async def get(self, key: CacheKey) -> Optional[List[SearchResult]]:
        """
        Get cached results.
        
        Args:
            key: Cache key
            
        Returns:
            Cached results or None
        """
        key_str = key.to_string()
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT data, expires_at, access_count FROM cache WHERE key = ?",
                    (key_str,)
                )
                row = cursor.fetchone()
                
                if not row:
                    self._misses += 1
                    return None
                
                # Check if expired
                if time.time() > row["expires_at"]:
                    conn.execute("DELETE FROM cache WHERE key = ?", (key_str,))
                    conn.commit()
                    self._misses += 1
                    return None
                
                # Update access count
                conn.execute(
                    "UPDATE cache SET access_count = ? WHERE key = ?",
                    (row["access_count"] + 1, key_str)
                )
                conn.commit()
                
                self._hits += 1
                return self._deserialize_results(row["data"])
                
        except sqlite3.Error:
            self._misses += 1
            return None
    
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
        ttl = ttl_seconds if ttl_seconds > 0 else self.default_ttl
        
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cache (key, data, created_at, expires_at, access_count)
                    VALUES (?, ?, ?, ?, 0)
                    """,
                    (
                        key_str,
                        self._serialize_results(results),
                        time.time(),
                        time.time() + ttl
                    )
                )
                conn.commit()
        except sqlite3.Error:
            pass  # Fail silently for cache
    
    async def invalidate(self, pattern: Optional[str] = None) -> int:
        """
        Invalidate cached entries.
        
        Args:
            pattern: Optional pattern to match (None = all)
            
        Returns:
            Number of entries invalidated
        """
        try:
            with self._get_connection() as conn:
                if pattern is None:
                    cursor = conn.execute("DELETE FROM cache")
                else:
                    cursor = conn.execute(
                        "DELETE FROM cache WHERE key LIKE ?",
                        (f"%{pattern}%",)
                    )
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error:
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with stats
        """
        try:
            with self._get_connection() as conn:
                # Total entries
                cursor = conn.execute("SELECT COUNT(*) FROM cache")
                total = cursor.fetchone()[0]
                
                # Expired entries
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM cache WHERE expires_at < ?",
                    (time.time(),)
                )
                expired = cursor.fetchone()[0]
                
                # Average access count
                cursor = conn.execute(
                    "SELECT AVG(access_count) FROM cache"
                )
                avg_access = cursor.fetchone()[0] or 0
                
                total_requests = self._hits + self._misses
                hit_rate = self._hits / total_requests if total_requests > 0 else 0
                
                return {
                    "type": "sqlite",
                    "db_path": str(self.db_path),
                    "size": total,
                    "expired_entries": expired,
                    "hits": self._hits,
                    "misses": self._misses,
                    "hit_rate": round(hit_rate, 4),
                    "avg_access_count": round(avg_access, 2),
                    "default_ttl": self.default_ttl,
                }
        except sqlite3.Error as e:
            return {
                "type": "sqlite",
                "error": str(e),
                "hits": self._hits,
                "misses": self._misses,
            }
    
    async def clear_expired(self) -> int:
        """
        Clear expired entries.
        
        Returns:
            Number of entries cleared
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM cache WHERE expires_at < ?",
                    (time.time(),)
                )
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error:
            return 0
    
    async def vacuum(self) -> None:
        """Optimize database."""
        try:
            with self._get_connection() as conn:
                conn.execute("VACUUM")
                conn.commit()
        except sqlite3.Error:
            pass
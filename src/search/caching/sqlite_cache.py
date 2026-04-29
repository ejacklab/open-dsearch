"""SQLite-based persistent cache implementation."""

import asyncio
import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from .base import CacheBackend, CacheKey
from ..providers.base import SearchResult


class SQLiteCache(CacheBackend):
    """Persistent cache backed by SQLite.

    Suitable for environments where search results should survive process
    restarts. Uses a single ``search_cache`` table with a text primary key
    (the hashed cache-key string).

    All public methods are ``async`` so they fit seamlessly alongside
    :class:`MemoryCache`.  SQLite access is wrapped in
    ``asyncio.to_thread`` to avoid blocking the event loop.
    """

    def __init__(
        self,
        db_path: str | Path = "cache/search_cache.db",
        default_ttl: int = 3600,
        pragmas: Optional[Dict[str, Any]] = None,
    ):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self._pragmas = pragmas or {
            "journal_mode": "WAL",
            "synchronous": "NORMAL",
        }
        self._local = asyncio.get_event_loop()
        self._init_db()

    # ------------------------------------------------------------------
    # DB helpers (synchronous — called via to_thread)
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        for pragma, value in self._pragmas.items():
            conn.execute(f"PRAGMA {pragma} = {json.dumps(value)}")
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS search_cache (
                    key         TEXT PRIMARY KEY,
                    query_text  TEXT NOT NULL DEFAULT '',
                    data        TEXT NOT NULL,
                    expires_at  REAL NOT NULL,
                    created_at  REAL NOT NULL,
                    access_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # CacheBackend interface
    # ------------------------------------------------------------------

    async def get(self, key: CacheKey) -> Optional[List[SearchResult]]:
        """Retrieve cached results (or ``None`` on miss / expiry)."""
        key_str = key.to_string()
        row = await asyncio.to_thread(self._get_row, key_str)

        if row is None:
            return None

        # Check expiry
        if time.time() > row["expires_at"]:
            await asyncio.to_thread(self._delete, key_str)
            return None

        # Bump access count (fire-and-forget)
        await asyncio.to_thread(self._bump_access, key_str)

        return self._deserialize_results(row["data"])

    async def set(
        self,
        key: CacheKey,
        results: List[SearchResult],
        ttl_seconds: int = 3600,
    ) -> None:
        """Store results with an optional TTL."""
        key_str = key.to_string()
        query_text = key.query.lower().strip()
        data = self._serialize_results(results)
        ttl = ttl_seconds if ttl_seconds > 0 else self.default_ttl
        expires_at = time.time() + ttl
        created_at = time.time()

        await asyncio.to_thread(
            self._upsert, key_str, query_text, data, expires_at, created_at
        )

    async def invalidate(self, pattern: Optional[str] = None) -> int:
        """Remove entries.  ``None`` clears everything; a string pattern
        matches (case-insensitive) against the raw key hash."""
        if pattern is None:
            return await asyncio.to_thread(self._delete_all)
        return await asyncio.to_thread(self._delete_by_pattern, pattern)

    async def get_stats(self) -> Dict[str, Any]:
        """Return basic cache statistics."""
        row = await asyncio.to_thread(self._stats_row)
        now = time.time()
        expired = await asyncio.to_thread(self._count_expired, now)
        return {
            "type": "sqlite",
            "db_path": str(self.db_path),
            "size": row["cnt"] if row else 0,
            "expired_entries": expired,
            "default_ttl": self.default_ttl,
        }

    # ------------------------------------------------------------------
    # Low-level sync helpers
    # ------------------------------------------------------------------

    def _get_row(self, key_str: str) -> Optional[sqlite3.Row]:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM search_cache WHERE key = ?", (key_str,)
            )
            return cur.fetchone()
        finally:
            conn.close()

    def _upsert(
        self, key_str: str, query_text: str, data: str, expires_at: float, created_at: float
    ) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO search_cache (key, query_text, data, expires_at, created_at, access_count)
                VALUES (?, ?, ?, ?, ?, 0)
                ON CONFLICT(key) DO UPDATE SET
                    query_text = excluded.query_text,
                    data = excluded.data,
                    expires_at = excluded.expires_at,
                    created_at = excluded.created_at,
                    access_count = 0
                """,
                (key_str, query_text, data, expires_at, created_at),
            )
            conn.commit()
        finally:
            conn.close()

    def _delete(self, key_str: str) -> None:
        conn = self._connect()
        try:
            conn.execute("DELETE FROM search_cache WHERE key = ?", (key_str,))
            conn.commit()
        finally:
            conn.close()

    def _delete_all(self) -> int:
        conn = self._connect()
        try:
            cur = conn.execute("SELECT COUNT(*) AS cnt FROM search_cache")
            count = cur.fetchone()["cnt"]
            conn.execute("DELETE FROM search_cache")
            conn.commit()
            return count
        finally:
            conn.close()

    def _delete_by_pattern(self, pattern: str) -> int:
        # Match against both the raw key hash and the stored query text
        conn = self._connect()
        try:
            cur = conn.execute(
                "DELETE FROM search_cache WHERE key LIKE ? OR query_text LIKE ?",
                (f"%{pattern}%", f"%{pattern}%"),
            )
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()

    def _bump_access(self, key_str: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE search_cache SET access_count = access_count + 1 WHERE key = ?",
                (key_str,),
            )
            conn.commit()
        finally:
            conn.close()

    def _stats_row(self) -> Optional[sqlite3.Row]:
        conn = self._connect()
        try:
            cur = conn.execute("SELECT COUNT(*) AS cnt FROM search_cache")
            return cur.fetchone()
        finally:
            conn.close()

    def _count_expired(self, now: float) -> int:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT COUNT(*) AS cnt FROM search_cache WHERE expires_at < ?",
                (now,),
            )
            return cur.fetchone()["cnt"]
        finally:
            conn.close()

    def _serialize_results(self, results: List[SearchResult]) -> str:
        return json.dumps([r.to_dict() for r in results])

    def _deserialize_results(self, data: str) -> List[SearchResult]:
        try:
            items = json.loads(data)
            return [SearchResult.from_dict(item) for item in items]
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

    async def clear_expired(self) -> int:
        """Remove expired entries."""
        now = time.time()
        return await asyncio.to_thread(self._clear_expired_sync, now)

    def _clear_expired_sync(self, now: float) -> int:
        conn = self._connect()
        try:
            cur = conn.execute(
                "DELETE FROM search_cache WHERE expires_at < ?", (now,)
            )
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()

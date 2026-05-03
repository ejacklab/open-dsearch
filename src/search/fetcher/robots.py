"""Robots.txt compliance checker for the URL fetcher.

Caches parsed robots.txt per domain to avoid repeated fetches.
Follows RFC 9309 (Robots Exclusion Protocol) basics.
"""

import asyncio
import time
from typing import Dict, Optional, Set
from urllib.parse import urlparse

import aiohttp


class RobotsChecker:
    """Check URLs against robots.txt rules.

    Usage::

        checker = RobotsChecker(user_agent="OpenDsearch/0.2.0")
        allowed = await checker.is_allowed("https://example.com/page")
    """

    # Cache robots.txt for this many seconds
    CACHE_TTL = 3600  # 1 hour

    def __init__(
        self,
        user_agent: str = "OpenDsearch",
        session: Optional[aiohttp.ClientSession] = None,
    ):
        self.user_agent = user_agent.lower()
        self._session = session
        self._cache: Dict[str, tuple[float, Set[str], Set[str]]] = {}
        # domain -> (fetched_at, disallowed_paths, allowed_paths)
        self._lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"User-Agent": self.user_agent}
            )
        return self._session

    async def is_allowed(self, url: str) -> bool:
        """Check whether *url* is allowed by the site's robots.txt.

        Returns ``True`` when no robots.txt is found or when the path is
        not disallowed for our user-agent.
        """
        parsed = urlparse(url)
        domain_key = f"{parsed.scheme}://{parsed.netloc}"

        rules = await self._get_rules(domain_key)
        if rules is None:
            # No robots.txt → allow
            return True

        fetched_at, disallowed, allowed = rules

        # Expired?
        if time.time() - fetched_at > self.CACHE_TTL:
            async with self._lock:
                self._cache.pop(domain_key, None)
            rules = await self._get_rules(domain_key)
            if rules is None:
                return True
            _, disallowed, allowed = rules

        path = parsed.path or "/"

        # Check allowed first (more specific)
        for prefix in allowed:
            if path.startswith(prefix):
                return True

        # Check disallowed
        for prefix in disallowed:
            if path.startswith(prefix):
                return False

        return True

    async def _get_rules(
        self, domain_key: str
    ) -> Optional[tuple[float, Set[str], Set[str]]]:
        """Fetch and parse robots.txt for *domain_key*."""
        if domain_key in self._cache:
            return self._cache[domain_key]

        robots_url = f"{domain_key}/robots.txt"
        try:
            session = await self._get_session()
            async with session.get(robots_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    self._cache[domain_key] = (time.time(), set(), set())
                    return self._cache[domain_key]
                text = await resp.text(max_length=500_000)
        except Exception:
            # Network error → assume allowed (fail open)
            self._cache[domain_key] = (time.time(), set(), set())
            return self._cache[domain_key]

        disallowed, allowed = self._parse_robots(text)
        entry = (time.time(), disallowed, allowed)
        self._cache[domain_key] = entry
        return entry

    def _parse_robots(self, text: str) -> tuple[Set[str], Set[str]]:
        """Parse robots.txt into disallowed and allowed path sets.

        Respects the most specific matching group for our user-agent.
        """
        disallowed: Set[str] = set()
        allowed: Set[str] = set()

        # Track which groups apply to us
        applies_to_us = False

        for line in text.splitlines():
            line = line.strip()
            # Strip comments
            if "#" in line:
                line = line[: line.index("#")].strip()
            if not line:
                continue

            parts = line.split(":", 1)
            if len(parts) != 2:
                continue
            directive = parts[0].strip().lower()
            value = parts[1].strip()

            if directive == "user-agent":
                applies_to_us = value == "*" or value.lower() == self.user_agent
            elif directive == "disallow" and applies_to_us and value:
                disallowed.add(value)
            elif directive == "allow" and applies_to_us and value:
                allowed.add(value)

        return disallowed, allowed

    async def close(self) -> None:
        """Close the internal session (only if we created it)."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

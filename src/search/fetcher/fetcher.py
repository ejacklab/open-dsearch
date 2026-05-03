"""URL fetcher with connection pooling."""

import asyncio
from dataclasses import dataclass
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import aiohttp


@dataclass
class FetchResult:
    """Result of URL fetch."""
    url: str
    status: int
    content: Optional[str] = None
    content_type: Optional[str] = None
    title: Optional[str] = None
    error: Optional[str] = None
    fetch_time_ms: float = 0.0
    byte_size: int = 0
    
    def is_success(self) -> bool:
        """Check if fetch was successful."""
        return self.status == 200 and self.content is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "status": self.status,
            "content": self.content,
            "content_type": self.content_type,
            "title": self.title,
            "error": self.error,
            "fetch_time_ms": self.fetch_time_ms,
            "byte_size": self.byte_size,
        }


class URLFetcher:
    """Async URL fetcher with connection pooling."""
    
    DEFAULT_TIMEOUT = 30
    DEFAULT_MAX_SIZE = 1024 * 1024  # 1MB
    
    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        max_size: int = DEFAULT_MAX_SIZE,
        max_connections: int = 100,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize fetcher.
        
        Args:
            timeout: Request timeout in seconds
            max_size: Maximum content size in bytes
            max_connections: Maximum concurrent connections
            headers: Default headers
        """
        self.timeout = timeout
        self.max_size = max_size
        self.max_connections = max_connections
        self.headers = headers or {
            "User-Agent": "OpenDsearch/0.2.0 (Research Bot)"
        }
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._robots_checker: Optional["RobotsChecker"] = None
        self._respect_robots: bool = True
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._connector = aiohttp.TCPConnector(
                limit=self.max_connections,
                limit_per_host=10,
                enable_cleanup_closed=True,
                force_close=True,
            )

            timeout = aiohttp.ClientTimeout(total=self.timeout)

            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout,
                headers=self.headers
            )

        return self._session
    
    async def fetch(self, url: str) -> FetchResult:
        """
        Fetch URL content.

        Args:
            url: URL to fetch

        Returns:
            Fetch result
        """
        import time

        start_time = time.time()

        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return FetchResult(
                url=url,
                status=0,
                error="Invalid URL"
            )

        # Check robots.txt before fetching
        if self._respect_robots:
            try:
                from .robots import RobotsChecker
                if self._robots_checker is None:
                    self._robots_checker = RobotsChecker(
                        user_agent=self.headers.get("User-Agent", "OpenDsearch")
                    )
                if not await self._robots_checker.is_allowed(url):
                    return FetchResult(
                        url=url,
                        status=403,
                        error="Blocked by robots.txt"
                    )
            except Exception:
                # Fail open — don't block fetches if robots check fails
                pass

        try:
            session = await self._get_session()

            async with session.get(url) as response:
                fetch_time_ms = (time.time() - start_time) * 1000
                status = response.status
                content_type = response.headers.get("Content-Type", "")

                if status != 200:
                    return FetchResult(
                        url=url,
                        status=status,
                        content_type=content_type,
                        error=f"HTTP {status}",
                        fetch_time_ms=fetch_time_ms
                    )

                # Read content with size limit
                content_bytes = await response.read()

                if len(content_bytes) > self.max_size:
                    return FetchResult(
                        url=url,
                        status=status,
                        content_type=content_type,
                        error=f"Content too large ({len(content_bytes)} bytes)",
                        fetch_time_ms=fetch_time_ms,
                        byte_size=len(content_bytes)
                    )

                # Decode content
                try:
                    content = content_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    content = content_bytes.decode('utf-8', errors='ignore')

                # Extract title
                title = self._extract_title(content)
                fetch_time_ms = (time.time() - start_time) * 1000

                return FetchResult(
                    url=url,
                    status=status,
                    content=content,
                    content_type=content_type,
                    title=title,
                    fetch_time_ms=fetch_time_ms,
                    byte_size=len(content_bytes)
                )

        except asyncio.TimeoutError:
            return FetchResult(
                url=url,
                status=0,
                error=f"Timeout after {self.timeout}s",
                fetch_time_ms=(time.time() - start_time) * 1000
            )
        except aiohttp.ClientError as e:
            return FetchResult(
                url=url,
                status=0,
                error=f"Client error: {str(e)}",
                fetch_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return FetchResult(
                url=url,
                status=0,
                error=f"Error: {str(e)}",
                fetch_time_ms=(time.time() - start_time) * 1000
            )
    
    async def fetch_many(
        self,
        urls: list,
        max_concurrent: int = 10
    ) -> list:
        """
        Fetch multiple URLs concurrently.

        Args:
            urls: URLs to fetch
            max_concurrent: Maximum concurrent fetches

        Returns:
            List of fetch results
        """
        if self._semaphore is None or self._semaphore._value != max_concurrent:
            self._semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_limit(url):
            async with self._semaphore:
                return await self.fetch(url)

        tasks = [fetch_with_limit(url) for url in urls]
        return await asyncio.gather(*tasks)
    
    def _extract_title(self, html: str) -> Optional[str]:
        """Extract title from HTML."""
        import re
        
        # Simple regex for title tag
        match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Try h1
        match = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return None
    
    async def close(self):
        """Close fetcher and release resources."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

        if self._connector:
            await self._connector.close()
            self._connector = None

        if self._robots_checker:
            await self._robots_checker.close()
            self._robots_checker = None

        self._semaphore = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

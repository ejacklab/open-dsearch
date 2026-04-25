"""Brave Search provider — real web search via Brave Search API.

Brave offers a free tier (2,000 queries/month) with structured results,
making it ideal for agent-driven research. Unlike LLM-based providers,
this returns actual search engine results with titles, URLs, and snippets.
"""

import time
from typing import Dict, List, Optional
import aiohttp

from .base import SearchProvider, ProviderConfig, SearchResult, ProviderStatus


class BraveProvider(SearchProvider):
    """Brave Search API provider with structured web results."""

    API_BASE = "https://api.search.brave.com/res/v1"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "brave"

    @property
    def supports_realtime(self) -> bool:
        return True

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            )
        return self._session

    async def search(
        self,
        query: str,
        num_results: int = 10,
        include_realtime: bool = False,
    ) -> List[SearchResult]:
        """
        Search using Brave Search API.

        Args:
            query: Search query
            num_results: Max results to return (capped at 20)
            include_realtime: If True, use news freshness filter

        Returns:
            List of SearchResult objects
        """
        if not self.config.api_key:
            return []

        start_time = time.time()

        try:
            session = await self._get_session()
            url = f"{self.API_BASE}/web/search"

            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.config.api_key,
            }
            if self.config.extra_headers:
                headers.update(self.config.extra_headers)

            params: Dict[str, str | int] = {
                "q": query,
                "count": min(num_results, 20),
            }

            if include_realtime:
                params["freshness"] = "pw"  # past week
                params["search_filter"] = "news"

            async with session.get(
                url,
                headers=headers,
                params=params,
            ) as response:
                response.raise_for_status()
                data = await response.json()

                results = self._parse_response(data, query, num_results)

                latency_ms = (time.time() - start_time) * 1000
                self.record_success(latency_ms)

                return results

        except aiohttp.ClientResponseError as e:
            if e.status == 429:
                self.record_failure(Exception("Rate limit exceeded"))
            else:
                self.record_failure(e)
            return []
        except Exception as e:
            self.record_failure(e)
            return []

    def _parse_response(
        self,
        data: dict,
        query: str,
        limit: int,
    ) -> List[SearchResult]:
        """Parse Brave Search API response into SearchResults."""
        results = []

        # Brave returns web results under mixed > main or web > results
        web_data = data.get("web", {})
        items = web_data.get("results", [])

        # Also include mixed results if available (blended web + news)
        if not items:
            mixed = data.get("mixed", {})
            items = mixed.get("main", [])
            # Mixed items have a nested "result" field
            items = [
                item.get("result", item) if isinstance(item, dict) else item
                for item in items
            ]

        for item in items[:limit]:
            title = item.get("title", "").strip()
            url = item.get("url", "").strip()
            snippet = item.get("description", "").strip()

            if not title or not url:
                continue

            metadata: Dict = {
                "provider": "brave",
                "query": query,
            }

            # Enrich with available metadata
            if item.get("age"):
                metadata["age"] = item["age"]
            if item.get("language"):
                metadata["language"] = item["language"]
            if item.get("family_friendly"):
                metadata["family_friendly"] = item["family_friendly"]

            # Page rank / position (Brave provides this)
            if item.get("page_rank") is not None:
                metadata["page_rank"] = item["page_rank"]

            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet or f"Brave result for: {query}",
                    source=self.name,
                    score=float(item.get("page_rank", 0) or 0),
                    metadata=metadata,
                )
            )

        return results

    async def health_check(self) -> ProviderStatus:
        """Check Brave Search API health with a lightweight query."""
        if not self.config.api_key:
            return ProviderStatus.DOWN

        try:
            session = await self._get_session()
            url = f"{self.API_BASE}/web/search"
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": self.config.api_key,
            }
            params = {"q": "health check", "count": 1}

            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    return ProviderStatus.HEALTHY
                elif response.status == 429:
                    return ProviderStatus.RATE_LIMITED
                else:
                    return ProviderStatus.DEGRADED
        except Exception:
            return ProviderStatus.DOWN

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

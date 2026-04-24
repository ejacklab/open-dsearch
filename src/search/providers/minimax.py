"""MiniMax search provider."""

import time
from typing import List, Optional
import aiohttp

from .base import SearchProvider, ProviderConfig, SearchResult, ProviderStatus


class MiniMaxProvider(SearchProvider):
    """MiniMax search provider."""
    
    DEFAULT_HOST = "https://api.minimax.chat"
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        self._base_url = config.base_url or self.DEFAULT_HOST
    
    @property
    def name(self) -> str:
        return "minimax"
    
    @property
    def supports_realtime(self) -> bool:
        return False
    
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
        include_realtime: bool = False
    ) -> List[SearchResult]:
        """
        Search using MiniMax API.
        
        Args:
            query: Search query
            num_results: Max results to return
            include_realtime: Ignored (MiniMax doesn't support real-time)
            
        Returns:
            List of SearchResult objects
        """
        if not self.config.api_key:
            return []
        
        start_time = time.time()
        
        try:
            session = await self._get_session()
            url = f"{self._base_url}/v1/text/search"
            
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            }
            if self.config.extra_headers:
                headers.update(self.config.extra_headers)
            
            body = {
                "query": query,
                "num_results": num_results
            }
            
            async with session.post(
                url,
                headers=headers,
                json=body
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                results = self._parse_response(data, query)
                
                # Record success
                latency_ms = (time.time() - start_time) * 1000
                self.record_success(latency_ms)
                
                return results[:num_results]
                
        except aiohttp.ClientResponseError as e:
            if e.status == 429:
                self.record_failure(Exception("Rate limit exceeded"))
            else:
                self.record_failure(e)
            return []
        except Exception as e:
            self.record_failure(e)
            return []
    
    def _parse_response(self, data: dict, query: str) -> List[SearchResult]:
        """Parse MiniMax API response into SearchResults."""
        results = []
        
        # Handle different response formats
        if "results" in data:
            items = data["results"]
        elif "organic" in data:
            items = data["organic"]
        elif "data" in data:
            items = data["data"]
        else:
            items = []
        
        for item in items:
            title = item.get("title", "").strip()
            url = item.get("url", item.get("link", "")).strip()
            snippet = item.get("snippet", item.get("description", "")).strip()
            
            if title and url:
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet or f"MiniMax result for: {query}",
                    source=self.name,
                    metadata={
                        "provider": "minimax",
                        "query": query,
                    }
                ))
        
        return results
    
    async def health_check(self) -> ProviderStatus:
        """Check MiniMax API health."""
        if not self.config.api_key:
            return ProviderStatus.DOWN
        
        try:
            session = await self._get_session()
            url = f"{self._base_url}/v1/models"
            headers = {"Authorization": f"Bearer {self.config.api_key}"}
            
            async with session.get(url, headers=headers) as response:
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

"""Moonshot Kimi search provider."""

import re
import time
from typing import List, Optional
import aiohttp

from .base import SearchProvider, ProviderConfig, SearchResult, ProviderStatus


class KimiProvider(SearchProvider):
    """Moonshot Kimi search provider."""
    
    DEFAULT_MODEL = "kimi-k2-turbo-preview"
    DEFAULT_HOST = "https://api.moonshot.ai"
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        self._base_url = config.base_url or self.DEFAULT_HOST
    
    @property
    def name(self) -> str:
        return "kimi"
    
    @property
    def supports_realtime(self) -> bool:
        return True
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()
    
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
        Search using Kimi API with web search tool.
        
        Args:
            query: Search query
            num_results: Max results to return
            include_realtime: Use real-time web search
            
        Returns:
            List of SearchResult objects
        """
        if not self.config.api_key:
            return []
        
        # Circuit breaker guard — skip if provider is unavailable
        if not self.is_available:
            return []
        
        start_time = time.time()
        
        try:
            session = await self._get_session()
            url = f"{self._base_url}/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            }
            if self.config.extra_headers:
                headers.update(self.config.extra_headers)
            
            tools = []
            if include_realtime:
                tools.append({
                    "type": "builtin_function",
                    "function": {"name": "$web_search"}
                })
            
            body = {
                "model": self.DEFAULT_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful search assistant."
                    },
                    {
                        "role": "user",
                        "content": f"Search the web for: {query}. List the top {num_results} most relevant sources with their titles, URLs, and brief descriptions."
                    }
                ],
                "temperature": 0.6,
                "tools": tools if tools else None
            }
            
            # Remove None values
            body = {k: v for k, v in body.items() if v is not None}
            
            # Shallow copy messages to avoid mutating original body
            messages = list(body["messages"])
            
            async with session.post(
                url,
                headers=headers,
                json=body
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                # Check for tool_calls response - need 2-step flow
                first_msg = data["choices"][0].get("message", {}) if data.get("choices") else {}
                if first_msg.get("tool_calls"):
                    # Append assistant message and tool result
                    messages.append(first_msg)
                    tool_call = first_msg["tool_calls"][0]
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": tool_call["function"].get("arguments", "")
                    })
                    
                    # Second request without tools to get actual content
                    body2 = {
                        "model": self.DEFAULT_MODEL,
                        "messages": messages,
                        "temperature": 0.3,
                    }
                    
                    async with session.post(
                        url,
                        headers=headers,
                        json=body2
                    ) as response2:
                        response2.raise_for_status()
                        data = await response2.json()
                
                results = self._parse_response(data, query, num_results)
                
                # Record success
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
        limit: int
    ) -> List[SearchResult]:
        """Parse Kimi API response into SearchResults."""
        results = []
        
        choices = data.get("choices", [])
        if not choices:
            return results
        
        content = choices[0].get("message", {}).get("content", "")
        if not content:
            return results
        
        # Extract markdown links [title](url)
        link_pattern = r'\[([^\]]+)\]\((https?://[^\)]+)\)'
        for match in re.finditer(link_pattern, content):
            title = match.group(1).strip()
            url = match.group(2).strip()
            
            if title and url:
                # Extract snippet from text after the markdown link
                after = content[match.end():match.end() + 200]
                snippet = after.strip().lstrip("-–—").strip()[:150]
                snippet = snippet or f"Kimi result for: {query}"
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source=self.name,
                    metadata={
                        "provider": "kimi",
                        "query": query,
                    }
                ))
        
        # Also try to extract plain URLs if no markdown links found
        if not results:
            url_pattern = r'(https?://[^\s\)]+)'
            urls = re.findall(url_pattern, content)
            for url in urls[:limit]:
                # Try to extract title from nearby text
                url_pos = content.find(url)
                context = content[max(0, url_pos-100):min(len(content), url_pos+100)]
                
                # Look for a title pattern
                title = url
                title_match = re.search(r'(?:^|\n)\s*([^\n]{10,100})\s*(?:\n|$)', context)
                if title_match:
                    title = title_match.group(1).strip()
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=f"Kimi result for: {query}",
                    source=self.name,
                    metadata={
                        "provider": "kimi",
                        "query": query,
                    }
                ))
        
        return results[:limit]
    
    async def health_check(self) -> ProviderStatus:
        """Check Kimi API health."""
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
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

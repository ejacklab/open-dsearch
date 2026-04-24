"""xAI search provider."""

import time
from typing import List, Optional
import aiohttp

from .base import SearchProvider, ProviderConfig, SearchResult, ProviderStatus


class XaiProvider(SearchProvider):
    """xAI search provider."""
    
    DEFAULT_HOST = "https://api.x.ai"
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        self._base_url = config.base_url or self.DEFAULT_HOST
    
    @property
    def name(self) -> str:
        return "xai"
    
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
        Search using xAI API.
        
        Args:
            query: Search query
            num_results: Max results to return
            include_realtime: Ignored (xAI doesn't support real-time)
            
        Returns:
            List of SearchResult objects
        """
        if not self.config.api_key:
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
            
            # Create a search-specific prompt
            prompt = f"""
You are a research assistant. Search the internet for information about '{query}' and provide a comprehensive response.

Format your response as a JSON object with the following structure:
{{
    "results": [
        {{
            "title": "Title of the result",
            "content": "Brief summary or key information (2-3 sentences)",
            "url": "https://example.com",
            "published_at": "2024-01-01",
            "metadata": {{}}
        }}
    ]
}}

Focus on accuracy, relevance, and provide specific information about the topic. If you cannot find specific information, acknowledge this limitation and provide what relevant information you can.

Context: The user is asking about: {query}
"""

            body = {
                "model": self.config.model or "grok-beta",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
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
        """Parse xAI API response into SearchResults."""
        results = []
        
        try:
            # Extract the response content
            content = ""
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    content = choice["message"]["content"]
            
            # Try to parse JSON response first
            if content.strip().startswith("{"):
                try:
                    import json
                    parsed = json.loads(content)
                    if "results" in parsed:
                        for item in parsed["results"]:
                            title = item.get("title", "").strip()
                            url = item.get("url", "").strip()
                            content_text = item.get("content", "").strip()
                            
                            if title and url:
                                results.append(SearchResult(
                                    title=title,
                                    url=url,
                                    snippet=content_text,
                                    source=self.name,
                                    metadata={
                                        "provider": "xai",
                                        "query": query,
                                        "published_at": item.get("published_at"),
                                    }
                                ))
                except (json.JSONDecodeError, KeyError):
                    pass
            
            # Fallback: treat as general research content
            if not results and content:
                # Extract potential URLs and titles from content
                import re
                url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
                urls = re.findall(url_pattern, content)
                
                if urls:
                    # Use first URL found
                    url = urls[0]
                    title = f"Research on {query}"
                    snippet = content[:300] + "..." if len(content) > 300 else content
                    
                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        source=self.name,
                        metadata={
                            "provider": "xai",
                            "query": query,
                        }
                    ))
                else:
                    # No URLs found, create a general result
                    results.append(SearchResult(
                        title=f"Research on {query}",
                        url=None,
                        snippet=content[:500] + "..." if len(content) > 500 else content,
                        source=self.name,
                        metadata={
                            "provider": "xai",
                            "query": query,
                        }
                    ))
        
        except Exception:
            # If parsing fails, create a basic result
            results.append(SearchResult(
                title=f"Research on {query}",
                url=None,
                snippet=f"xAI search results for: {query}",
                source=self.name,
                metadata={
                    "provider": "xai",
                    "query": query,
                }
            ))
        
        return results
    
    async def health_check(self) -> ProviderStatus:
        """Check xAI API health."""
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
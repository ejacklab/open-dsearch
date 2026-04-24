"""Google Gemini search provider."""

import time
from typing import Dict, List, Optional
import aiohttp

from .base import SearchProvider, ProviderConfig, SearchResult, ProviderStatus


class GeminiProvider(SearchProvider):
    """Google Gemini search provider with Google Search tool."""
    
    DEFAULT_MODEL = "gemini-1.5-flash"
    API_BASE = "https://generativelanguage.googleapis.com/v1beta"
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
    
    @property
    def name(self) -> str:
        return "gemini"
    
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
        include_realtime: bool = False
    ) -> List[SearchResult]:
        """
        Search using Gemini API with Google Search tool.
        
        Args:
            query: Search query
            num_results: Max results to return
            include_realtime: Ignored (Gemini always uses real-time search)
            
        Returns:
            List of SearchResult objects
        """
        if not self.config.api_key:
            return []
        
        start_time = time.time()
        
        try:
            session = await self._get_session()
            url = f"{self.API_BASE}/models/{self.DEFAULT_MODEL}:generateContent"
            
            params = {"key": self.config.api_key}
            body = {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": f"Search for: {query}"}]
                }],
                "tools": [{"googleSearch": {}}],
                "generationConfig": {
                    "temperature": 0.0,
                    "maxOutputTokens": 1024
                }
            }
            
            async with session.post(
                url,
                params=params,
                json=body,
                headers=self.config.extra_headers
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
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
        """Parse Gemini API response into SearchResults."""
        results = []
        
        candidates = data.get("candidates", [])
        if not candidates:
            return results
        
        grounding = candidates[0].get("groundingMetadata", {})
        chunks = grounding.get("groundingChunks", [])
        
        # Build snippet lookup from groundingSupports
        # Each support maps a text segment to the chunks it references
        chunk_snippets: Dict[int, str] = {}
        for support in grounding.get("groundingSupports", []):
            segment_text = support.get("segment", {}).get("text", "").strip()
            for chunk_idx in support.get("groundingChunkIndices", []):
                existing = chunk_snippets.get(chunk_idx, "")
                if segment_text and len(segment_text) > len(existing):
                    chunk_snippets[chunk_idx] = segment_text
        
        # Also extract the model's text response for fallback snippets
        model_text = ""
        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            if "text" in part:
                model_text += part["text"]
        
        for idx, chunk in enumerate(chunks[:limit]):
            web = chunk.get("web", {})
            title = web.get("title", "").strip()
            uri = web.get("uri", "").strip()
            
            if title and uri:
                # Use extracted snippet, or fallback
                snippet = chunk_snippets.get(idx, "")
                if not snippet:
                    snippet = f"Source for: {query}"
                
                results.append(SearchResult(
                    title=title,
                    url=uri,
                    snippet=snippet,
                    source=self.name,
                    metadata={
                        "provider": "gemini",
                        "query": query,
                    }
                ))
        
        return results
    
    async def health_check(self) -> ProviderStatus:
        """Check Gemini API health."""
        if not self.config.api_key:
            return ProviderStatus.DOWN
        
        try:
            session = await self._get_session()
            url = f"{self.API_BASE}/models"
            params = {"key": self.config.api_key}
            
            async with session.get(url, params=params) as response:
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

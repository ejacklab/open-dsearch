"""Test data factories using factory_boy pattern."""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class SearchResultFactory:
    """Factory for creating test SearchResult objects."""
    
    @staticmethod
    def create(
        title: str = None,
        url: str = None,
        snippet: str = None,
        source: str = "gemini",
        score: float = None
    ) -> Dict[str, Any]:
        """Create a single search result."""
        return {
            "title": title or f"Test Result {random.randint(1, 1000)}",
            "url": url or f"https://example{random.randint(1, 100)}.com/page",
            "snippet": snippet or "This is a test search result snippet.",
            "source": source,
            "score": score if score is not None else round(random.uniform(0.5, 1.0), 2)
        }
    
    @staticmethod
    def create_batch(count: int, **kwargs) -> List[Dict[str, Any]]:
        """Create multiple search results."""
        return [SearchResultFactory.create(**kwargs) for _ in range(count)]


@dataclass
class APIResponseFactory:
    """Factory for creating mock API responses."""
    
    @staticmethod
    def gemini_search(results_count: int = 3) -> Dict[str, Any]:
        """Create mock Gemini API response."""
        chunks = []
        for i in range(results_count):
            chunks.append({
                "web": {
                    "uri": f"https://example{i+1}.com/page",
                    "title": f"Result {i+1}"
                }
            })
        
        return {
            "candidates": [{
                "content": {"role": "model", "parts": [{"text": "Search results"}]},
                "groundingMetadata": {
                    "groundingChunks": chunks
                }
            }]
        }
    
    @staticmethod
    def minimax_search(results_count: int = 3) -> Dict[str, Any]:
        """Create mock MiniMax API response."""
        organic = []
        for i in range(results_count):
            organic.append({
                "title": f"MiniMax Result {i+1}",
                "link": f"https://minimax{i+1}.com",
                "snippet": f"Snippet for result {i+1}"
            })
        
        return {"organic": organic}
    
    @staticmethod
    def kimi_search(results_count: int = 3) -> Dict[str, Any]:
        """Create mock Kimi API response."""
        links = "\n\n".join([
            f"[Result {i+1}](https://kimi{i+1}.com)\nDescription {i+1}"
            for i in range(results_count)
        ])
        
        return {
            "choices": [{
                "message": {
                    "content": f"Here are the results:\n\n{links}"
                }
            }]
        }
    
    @staticmethod
    def xai_search(results_count: int = 3) -> Dict[str, Any]:
        """Create mock xAI API response."""
        citations = [
            {"url": f"https://xai{i+1}.com", "title": f"xAI Result {i+1}"}
            for i in range(results_count)
        ]
        
        return {
            "choices": [{
                "message": {
                    "content": "Search results with citations",
                    "citations": citations
                }
            }]
        }
    
    @staticmethod
    def error_response(error_message: str = "An error occurred", status: int = 500) -> Dict[str, Any]:
        """Create mock error response."""
        return {
            "error": error_message,
            "status": status
        }
    
    @staticmethod
    def rate_limit_response() -> Dict[str, Any]:
        """Create mock rate limit response."""
        return {
            "error": "Rate limit exceeded",
            "retry_after": 60
        }


@dataclass
class ResearchOutputFactory:
    """Factory for creating research output data."""
    
    @staticmethod
    def create_json_output(sources_count: int = 5) -> Dict[str, Any]:
        """Create JSON format research output."""
        return {
            "query": "Test research query",
            "sources": SearchResultFactory.create_batch(sources_count),
            "metadata": {
                "duration_ms": 2500,
                "sources_count": sources_count,
                "providers_used": ["gemini", "minimax"]
            }
        }
    
    @staticmethod
    def create_vectors_output(sources_count: int = 5) -> List[Dict[str, str]]:
        """Create vectors format research output."""
        return [
            {"title": f"Source {i+1}", "url": f"https://example{i+1}.com"}
            for i in range(sources_count)
        ]
    
    @staticmethod
    def create_markdown_output(sources_count: int = 5) -> str:
        """Create markdown format research output."""
        lines = ["# Research: Test Query", ""]
        
        for i in range(sources_count):
            lines.extend([
                f"## Source {i+1}",
                f"**URL:** https://example{i+1}.com",
                "",
                f"Content for source {i+1}...",
                "",
                "---",
                ""
            ])
        
        return "\n".join(lines)


def create_mock_results(count: int = 10, **kwargs) -> List[Dict[str, Any]]:
    """Convenience function to create mock search results."""
    return SearchResultFactory.create_batch(count, **kwargs)


def create_mock_response(provider: str, result_count: int = 5) -> Dict[str, Any]:
    """Convenience function to create mock API response for a provider."""
    factory = APIResponseFactory()
    
    providers = {
        "gemini": factory.gemini_search,
        "minimax": factory.minimax_search,
        "kimi": factory.kimi_search,
        "xai": factory.xai_search,
    }
    
    if provider in providers:
        return providers[provider](result_count)
    
    return factory.error_response(f"Unknown provider: {provider}")

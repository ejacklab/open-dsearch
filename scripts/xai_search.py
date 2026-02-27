#!/usr/bin/env python3
"""
xAI (Grok) Search - Python Bridge

Provides web search and X (Twitter) search using xAI's Grok models.
Supports both synchronous and asynchronous execution for better concurrency.

Usage:
    python xai_search.py "query" --limit 10
    python xai_search.py "query" --limit 10 --x-search
    python xai_search.py "query" --limit 10 --async
    python xai_search.py "query" --allowed-domains github.com,stackoverflow.com
"""

import os
import sys
import json
import argparse
import asyncio
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from datetime import datetime

try:
    from xai_sdk import Client, AsyncClient
    from xai_sdk.chat import user
    from xai_sdk.tools import web_search, x_search

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    Client = None
    AsyncClient = None
    user = None
    web_search = None
    x_search = None


@dataclass
class SearchResult:
    """Standardized search result"""

    title: str
    url: str
    snippet: str


class XAISearchError(Exception):
    """Base exception for xAI search errors"""

    def __init__(self, message: str, code: Optional[str] = None):
        super().__init__(message)
        self.code = code


class XAISearch:
    """
    xAI Search wrapper with best practices:
    - Sync/Async support
    - Proper error handling
    - Tool parameter support
    - Retry logic
    """

    DEFAULT_MODEL = "grok-4-1-fast-reasoning"
    DEFAULT_TIMEOUT = 300  # 5 minutes

    # gRPC error codes from xAI SDK
    ERROR_CODES = {
        "UNKNOWN": "Unknown error occurred",
        "INVALID_ARGUMENT": "Invalid argument provided",
        "DEADLINE_EXCEEDED": "Request timeout",
        "NOT_FOUND": "Resource not found",
        "PERMISSION_DENIED": "Permission denied - check API key",
        "UNAUTHENTICATED": "Invalid or missing API key",
        "RESOURCE_EXHAUSTED": "Rate limit exceeded",
        "INTERNAL": "Internal server error",
        "UNAVAILABLE": "Service temporarily unavailable",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        timeout: int = DEFAULT_TIMEOUT,
        enable_retries: bool = True,
        max_retries: int = 3,
    ):
        """
        Initialize xAI search client.

        Args:
            api_key: xAI API key (reads from XAI_API_KEY if not provided)
            model: Grok model to use
            timeout: Request timeout in seconds
            enable_retries: Enable automatic retries for transient errors
            max_retries: Maximum retry attempts
        """
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        if not self.api_key:
            raise XAISearchError("XAI_API_KEY not set", "UNAUTHENTICATED")

        self.model = model
        self.timeout = timeout
        self.enable_retries = enable_retries
        self.max_retries = max_retries
        self._client = None
        self._async_client = None

    @property
    def client(self):
        """Lazy initialization of sync client"""
        if self._client is None:
            self._client = Client(api_key=self.api_key, timeout=self.timeout)  # type: ignore[union-attr]
        return self._client  # type: ignore[return-value]

    @property
    def async_client(self):
        """Lazy initialization of async client"""
        if self._async_client is None:
            self._async_client = AsyncClient(api_key=self.api_key, timeout=self.timeout)  # type: ignore[union-attr]
        return self._async_client  # type: ignore[return-value]

    def _parse_citations(self, response_obj, limit: int) -> List[SearchResult]:
        """Extract search results from citations"""
        results = []

        if not hasattr(response_obj, "citations") or not response_obj.citations:
            return results

        for c in response_obj.citations:
            # Handle different citation object structures
            title = getattr(c, "title", None) or getattr(c, "name", "Unknown Title")
            url = (
                getattr(c, "url", None)
                or getattr(c, "uri", None)
                or getattr(c, "link", "")
            )
            snippet = (
                getattr(c, "snippet", None)
                or getattr(c, "text", None)
                or getattr(c, "description", "")
            )

            if url:
                results.append(
                    SearchResult(
                        title=title or "Unknown", url=url, snippet=snippet or ""
                    )
                )

            if len(results) >= limit:
                break

        return results

    def _handle_error(self, error: Exception) -> XAISearchError:
        """Convert exceptions to XAISearchError with proper codes"""
        error_str = str(error)

        # Check for gRPC status codes
        for code, description in self.ERROR_CODES.items():
            if code in error_str or description.lower() in error_str.lower():
                return XAISearchError(error_str, code)

        # Default to internal error
        return XAISearchError(error_str, "INTERNAL")

    def search(
        self,
        query: str,
        limit: int = 10,
        use_x_search: bool = False,
        # Web search specific params
        allowed_domains: Optional[List[str]] = None,
        excluded_domains: Optional[List[str]] = None,
        enable_image_understanding: bool = False,
        # X search specific params
        allowed_x_handles: Optional[List[str]] = None,
        excluded_x_handles: Optional[List[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        enable_video_understanding: bool = False,
    ) -> List[SearchResult]:
        """
        Synchronous search using xAI Grok.

        Args:
            query: Search query
            limit: Maximum number of results
            use_x_search: Use X search instead of web search

            # web_search parameters
            allowed_domains: Only search in these domains (max 5)
            excluded_domains: Exclude these domains (max 5)
            enable_image_understanding: Analyze images in results

            # x_search parameters
            allowed_x_handles: Only from these handles (max 10)
            excluded_x_handles: Exclude these handles (max 10)
            from_date: Start date (ISO8601)
            to_date: End date (ISO8601)
            enable_video_understanding: Analyze videos in X posts

        Returns:
            List of SearchResult objects
        """
        if not SDK_AVAILABLE:
            raise XAISearchError(
                "xai-sdk not installed. Run: pip install xai-sdk", "INTERNAL"
            )

        attempt = 0
        last_error = None

        while attempt < self.max_retries:
            try:
                # Build tool with parameters
                if use_x_search:
                    tool = x_search(  # type: ignore
                        allowed_x_handles=allowed_x_handles,
                        excluded_x_handles=excluded_x_handles,
                        from_date=datetime.fromisoformat(from_date)
                        if from_date
                        else None,
                        to_date=datetime.fromisoformat(to_date) if to_date else None,
                        enable_image_understanding=enable_image_understanding,
                        enable_video_understanding=enable_video_understanding,
                    )
                else:
                    tool = web_search(  # type: ignore
                        allowed_domains=allowed_domains,
                        excluded_domains=excluded_domains,
                        enable_image_understanding=enable_image_understanding,
                    )

                chat = self.client.chat.create(  # type: ignore
                    model=self.model,
                    tools=[tool],
                    include=["verbose_streaming"],
                )

                search_type = "on X" if use_x_search else "the web"
                chat.append(user(f"Search {search_type} for: {query}"))  # type: ignore

                response_obj = None
                for response, chunk in chat.stream():
                    response_obj = response

                return self._parse_citations(response_obj, limit)

            except Exception as e:
                last_error = self._handle_error(e)
                attempt += 1

                # Only retry on transient errors
                if last_error.code in [
                    "UNAVAILABLE",
                    "RESOURCE_EXHAUSTED",
                    "DEADLINE_EXCEEDED",
                ]:
                    if attempt < self.max_retries:
                        wait_time = 0.5 * (2**attempt)  # Exponential backoff
                        print(
                            f"Retry {attempt}/{self.max_retries} after {wait_time}s...",
                            file=sys.stderr,
                        )
                        import time

                        time.sleep(wait_time)
                        continue

                # Non-retryable error
                break

        raise last_error or XAISearchError("Unknown error", "UNKNOWN")

    async def search_async(
        self, query: str, limit: int = 10, use_x_search: bool = False, **kwargs
    ) -> List[SearchResult]:
        """
        Asynchronous search using xAI Grok.
        Better for concurrent execution in Rust tokio runtime.
        """
        if not SDK_AVAILABLE:
            raise XAISearchError(
                "xai-sdk not installed. Run: pip install xai-sdk", "INTERNAL"
            )

        attempt = 0
        last_error = None

        while attempt < self.max_retries:
            try:
                # Build tool with parameters
                if use_x_search:
                    tool = x_search(  # type: ignore[call-arg]
                        allowed_x_handles=kwargs.get("allowed_x_handles"),
                        excluded_x_handles=kwargs.get("excluded_x_handles"),
                        from_date=kwargs.get("from_date"),
                        to_date=kwargs.get("to_date"),
                        enable_image_understanding=kwargs.get(
                            "enable_image_understanding", False
                        ),
                        enable_video_understanding=kwargs.get(
                            "enable_video_understanding", False
                        ),
                    )
                else:
                    tool = web_search(  # type: ignore[call-arg]
                        allowed_domains=kwargs.get("allowed_domains"),
                        excluded_domains=kwargs.get("excluded_domains"),
                        enable_image_understanding=kwargs.get(
                            "enable_image_understanding", False
                        ),
                    )

                chat = self.async_client.chat.create(  # type: ignore
                    model=self.model,
                    tools=[tool],
                    include=["verbose_streaming"],
                )

                search_type = "on X" if use_x_search else "the web"
                chat.append(user(f"Search {search_type} for: {query}"))  # type: ignore

                response_obj = None
                async for response, chunk in chat.stream():
                    response_obj = response

                return self._parse_citations(response_obj, limit)

            except Exception as e:
                last_error = self._handle_error(e)
                attempt += 1

                if last_error.code in [
                    "UNAVAILABLE",
                    "RESOURCE_EXHAUSTED",
                    "DEADLINE_EXCEEDED",
                ]:
                    if attempt < self.max_retries:
                        wait_time = 0.5 * (2**attempt)
                        print(
                            f"Retry {attempt}/{self.max_retries} after {wait_time}s...",
                            file=sys.stderr,
                        )
                        await asyncio.sleep(wait_time)
                        continue
                break

        raise last_error or XAISearchError("Unknown error", "UNKNOWN")


def search_xai(
    query: str, limit: int = 10, use_x_search: bool = False, **kwargs
) -> str:
    """
    Main entry point for Rust bridge.
    Returns JSON string of results.
    """
    try:
        searcher = XAISearch()
        results = searcher.search(
            query=query, limit=limit, use_x_search=use_x_search, **kwargs
        )

        output = [
            {"title": r.title, "url": r.url, "snippet": r.snippet} for r in results
        ]

        return json.dumps(output)

    except XAISearchError as e:
        return json.dumps({"error": str(e), "code": e.code, "success": False})
    except Exception as e:
        return json.dumps({"error": str(e), "success": False})


async def search_xai_async(
    query: str, limit: int = 10, use_x_search: bool = False, **kwargs
) -> str:
    """Async entry point for concurrent execution"""
    try:
        searcher = XAISearch()
        results = await searcher.search_async(
            query=query, limit=limit, use_x_search=use_x_search, **kwargs
        )

        output = [
            {"title": r.title, "url": r.url, "snippet": r.snippet} for r in results
        ]

        return json.dumps(output)

    except XAISearchError as e:
        return json.dumps({"error": str(e), "code": e.code, "success": False})
    except Exception as e:
        return json.dumps({"error": str(e), "success": False})


def main():
    parser = argparse.ArgumentParser(
        description="Web/X search using xAI (Grok)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Rust async" --limit 10
  %(prog)s "Rust async" --limit 10 --x-search
  %(prog)s "Rust async" --allowed-domains github.com,stackoverflow.com
  %(prog)s "AI news" --from-date 2025-01-01 --to-date 2025-02-01
        """,
    )
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Number of results")
    parser.add_argument(
        "--x-search", action="store_true", help="Use X search instead of web search"
    )
    parser.add_argument(
        "--async", dest="use_async", action="store_true", help="Use async client"
    )

    # Web search options
    parser.add_argument(
        "--allowed-domains", help="Comma-separated list of allowed domains"
    )
    parser.add_argument(
        "--excluded-domains", help="Comma-separated list of excluded domains"
    )
    parser.add_argument(
        "--enable-image-understanding",
        action="store_true",
        help="Enable image analysis",
    )

    # X search options
    parser.add_argument("--allowed-handles", help="Comma-separated list of X handles")
    parser.add_argument(
        "--excluded-handles", help="Comma-separated list of excluded X handles"
    )
    parser.add_argument("--from-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to-date", help="End date (YYYY-MM-DD)")
    parser.add_argument(
        "--enable-video-understanding",
        action="store_true",
        help="Enable video analysis (X only)",
    )

    # Client options
    parser.add_argument(
        "--model", default="grok-4-1-fast-reasoning", help="Model to use"
    )
    parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds")

    args = parser.parse_args()

    # Parse list arguments
    allowed_domains = args.allowed_domains.split(",") if args.allowed_domains else None
    excluded_domains = (
        args.excluded_domains.split(",") if args.excluded_domains else None
    )
    allowed_handles = args.allowed_handles.split(",") if args.allowed_handles else None
    excluded_handles = (
        args.excluded_handles.split(",") if args.excluded_handles else None
    )

    try:
        searcher = XAISearch(model=args.model, timeout=args.timeout)

        if args.use_async:
            results = asyncio.run(
                searcher.search_async(
                    query=args.query,
                    limit=args.limit,
                    use_x_search=args.x_search,
                    allowed_domains=allowed_domains,
                    excluded_domains=excluded_domains,
                    enable_image_understanding=args.enable_image_understanding,
                    allowed_x_handles=allowed_handles,
                    excluded_x_handles=excluded_handles,
                    from_date=args.from_date,
                    to_date=args.to_date,
                    enable_video_understanding=args.enable_video_understanding,
                )
            )
        else:
            results = searcher.search(
                query=args.query,
                limit=args.limit,
                use_x_search=args.x_search,
                allowed_domains=allowed_domains,
                excluded_domains=excluded_domains,
                enable_image_understanding=args.enable_image_understanding,
                allowed_x_handles=allowed_handles,
                excluded_x_handles=excluded_handles,
                from_date=args.from_date,
                to_date=args.to_date,
                enable_video_understanding=args.enable_video_understanding,
            )
            results = json.dumps(
                [
                    {"title": r.title, "url": r.url, "snippet": r.snippet}
                    for r in results
                ]
            )

        print(results)

    except XAISearchError as e:
        print(json.dumps({"error": str(e), "code": e.code, "success": False}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e), "success": False}))
        sys.exit(1)


if __name__ == "__main__":
    main()

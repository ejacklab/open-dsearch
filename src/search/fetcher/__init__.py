"""URL fetching and content extraction."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .fetcher import URLFetcher, FetchResult
    from .parser import HTMLParser

__all__ = [
    "URLFetcher",
    "FetchResult",
    "HTMLParser",
]


def __getattr__(name: str):
    """Lazy import to avoid heavy dependencies during test collection."""
    if name == "URLFetcher":
        from .fetcher import URLFetcher
        return URLFetcher
    if name == "FetchResult":
        from .fetcher import FetchResult
        return FetchResult
    if name == "HTMLParser":
        from .parser import HTMLParser
        return HTMLParser
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

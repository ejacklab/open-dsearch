"""URL fetching and content extraction."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .fetcher import URLFetcher, FetchResult
    from .parser import HTMLParser
    from .robots import RobotsChecker

__all__ = [
    "URLFetcher",
    "FetchResult",
    "HTMLParser",
    "RobotsChecker",
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
    if name == "RobotsChecker":
        from .robots import RobotsChecker
        return RobotsChecker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

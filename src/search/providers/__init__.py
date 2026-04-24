"""Search provider implementations."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import SearchProvider, ProviderConfig, SearchResult, ProviderStatus
    from .gemini import GeminiProvider
    from .minimax import MiniMaxProvider
    from .kimi import KimiProvider
    from .xai import XaiProvider
    from .registry import ProviderRegistry

__all__ = [
    "SearchProvider",
    "ProviderConfig",
    "SearchResult",
    "ProviderStatus",
    "GeminiProvider",
    "MiniMaxProvider",
    "KimiProvider",
    "XaiProvider",
    "ProviderRegistry",
]


def __getattr__(name: str):
    """Lazy import to avoid heavy dependencies during test collection."""
    if name == "SearchProvider":
        from .base import SearchProvider
        return SearchProvider
    if name == "ProviderConfig":
        from .base import ProviderConfig
        return ProviderConfig
    if name == "SearchResult":
        from .base import SearchResult
        return SearchResult
    if name == "ProviderStatus":
        from .base import ProviderStatus
        return ProviderStatus
    if name == "GeminiProvider":
        from .gemini import GeminiProvider
        return GeminiProvider
    if name == "MiniMaxProvider":
        from .minimax import MiniMaxProvider
        return MiniMaxProvider
    if name == "KimiProvider":
        from .kimi import KimiProvider
        return KimiProvider
    if name == "XaiProvider":
        from .xai import XaiProvider
        return XaiProvider
    if name == "ProviderRegistry":
        from .registry import ProviderRegistry
        return ProviderRegistry
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

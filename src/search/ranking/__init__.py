"""Result ranking and deduplication."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .scorer import ResultScorer
    from .dedup import Deduplicator

__all__ = [
    "ResultScorer",
    "Deduplicator",
]


def __getattr__(name: str):
    """Lazy import to avoid heavy dependencies during test collection."""
    if name == "ResultScorer":
        from .scorer import ResultScorer
        return ResultScorer
    if name == "Deduplicator":
        from .dedup import Deduplicator
        return Deduplicator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

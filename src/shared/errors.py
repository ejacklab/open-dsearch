"""
Error handling utilities for Open Dsearch.

Provides a hierarchy of custom exceptions with rich context,
error codes, and retry suggestions.
"""

from typing import Any, Dict, List, Optional
from enum import Enum


class ErrorCode(Enum):
    """Error codes for categorizing failures."""
    # General errors
    UNKNOWN = "E000"
    VALIDATION = "E001"
    CONFIGURATION = "E002"
    TIMEOUT = "E003"

    # Provider errors
    PROVIDER_ERROR = "E100"
    PROVIDER_UNAVAILABLE = "E101"
    PROVIDER_RATE_LIMITED = "E102"
    PROVIDER_AUTH_ERROR = "E103"
    PROVIDER_QUOTA_EXCEEDED = "E104"

    # Search errors
    SEARCH_ERROR = "E200"
    SEARCH_NO_RESULTS = "E201"
    SEARCH_TIMEOUT = "E202"

    # Network errors
    NETWORK_ERROR = "E300"
    NETWORK_TIMEOUT = "E301"
    NETWORK_DNS_ERROR = "E302"

    # Cache errors
    CACHE_ERROR = "E400"
    CACHE_MISS = "E401"


class DsearchError(Exception):
    """
    Base exception for Open Dsearch.

    Attributes:
        message: Error message
        code: Error code
        context: Additional context
        retryable: Whether the operation can be retried
        retry_after: Suggested seconds to wait before retry
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN,
        context: Optional[Dict[str, Any]] = None,
        retryable: bool = False,
        retry_after: Optional[float] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.context = context or {}
        self.retryable = retryable
        self.retry_after = retry_after
        self.cause = cause

    def __str__(self) -> str:
        parts = [f"[{self.code.value}] {self.message}"]
        if self.context:
            parts.append(f"Context: {self.context}")
        if self.retryable:
            parts.append(f"Retryable: yes (after {self.retry_after}s)" if self.retry_after else "Retryable: yes")
        if self.cause:
            parts.append(f"Caused by: {self.cause}")
        return " | ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            "error": True,
            "code": self.code.value,
            "message": self.message,
            "context": self.context,
            "retryable": self.retryable,
            "retry_after": self.retry_after,
        }


class ValidationError(DsearchError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        **kwargs
    ):
        context = kwargs.get("context", {})
        context.update({
            "field": field,
            "value": str(value) if value is not None else None
        })
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION,
            context=context,
            retryable=False,
            **kwargs
        )
        self.field = field
        self.value = value


class ConfigError(DsearchError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        context = kwargs.get("context", {})
        if config_key:
            context["config_key"] = config_key
        super().__init__(
            message=message,
            code=ErrorCode.CONFIGURATION,
            context=context,
            retryable=False,
            **kwargs
        )
        self.config_key = config_key


class TimeoutError(DsearchError):
    """Raised when an operation times out."""

    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        **kwargs
    ):
        context = kwargs.get("context", {})
        if timeout_seconds:
            context["timeout_seconds"] = timeout_seconds
        super().__init__(
            message=message,
            code=ErrorCode.TIMEOUT,
            context=context,
            retryable=True,
            **kwargs
        )
        self.timeout_seconds = timeout_seconds


class ProviderError(DsearchError):
    """Base exception for provider-related errors."""

    def __init__(
        self,
        message: str,
        provider: str,
        code: ErrorCode = ErrorCode.PROVIDER_ERROR,
        **kwargs
    ):
        context = kwargs.get("context", {})
        context["provider"] = provider
        super().__init__(
            message=message,
            code=code,
            context=context,
            **kwargs
        )
        self.provider = provider


class ProviderUnavailableError(ProviderError):
    """Raised when a provider is unavailable."""

    def __init__(self, provider: str, **kwargs):
        super().__init__(
            message=f"Provider '{provider}' is unavailable",
            provider=provider,
            code=ErrorCode.PROVIDER_UNAVAILABLE,
            retryable=True,
            retry_after=30.0,
            **kwargs
        )


class ProviderRateLimitError(ProviderError):
    """Raised when a provider rate limits the request."""

    def __init__(
        self,
        provider: str,
        retry_after: Optional[float] = None,
        **kwargs
    ):
        message = f"Rate limited by provider '{provider}'"
        if retry_after:
            message += f" (retry after {retry_after}s)"

        super().__init__(
            message=message,
            provider=provider,
            code=ErrorCode.PROVIDER_RATE_LIMITED,
            retryable=True,
            retry_after=retry_after,
            **kwargs
        )


class ProviderAuthError(ProviderError):
    """Raised when provider authentication fails."""

    def __init__(self, provider: str, **kwargs):
        super().__init__(
            message=f"Authentication failed for provider '{provider}'",
            provider=provider,
            code=ErrorCode.PROVIDER_AUTH_ERROR,
            retryable=False,
            **kwargs
        )


class ProviderQuotaError(ProviderError):
    """Raised when provider quota is exceeded."""

    def __init__(self, provider: str, **kwargs):
        super().__init__(
            message=f"Quota exceeded for provider '{provider}'",
            provider=provider,
            code=ErrorCode.PROVIDER_QUOTA_EXCEEDED,
            retryable=False,
            **kwargs
        )


class SearchError(DsearchError):
    """Raised when search operation fails."""

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        code: ErrorCode = ErrorCode.SEARCH_ERROR,
        **kwargs
    ):
        context = kwargs.get("context", {})
        if query:
            context["query"] = query[:100]  # Truncate long queries
        super().__init__(
            message=message,
            code=code,
            context=context,
            **kwargs
        )
        self.query = query


class NoResultsError(SearchError):
    """Raised when search returns no results."""

    def __init__(self, query: str, **kwargs):
        super().__init__(
            message=f"No results found for query: {query[:50]}...",
            query=query,
            code=ErrorCode.SEARCH_NO_RESULTS,
            retryable=False,
            **kwargs
        )


class NetworkError(DsearchError):
    """Raised when network operation fails."""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        code: ErrorCode = ErrorCode.NETWORK_ERROR,
        **kwargs
    ):
        context = kwargs.get("context", {})
        if url:
            context["url"] = url
        super().__init__(
            message=message,
            code=code,
            context=context,
            retryable=True,
            **kwargs
        )
        self.url = url


class NetworkTimeoutError(NetworkError):
    """Raised when network request times out."""

    def __init__(self, url: str, timeout: Optional[float] = None, **kwargs):
        message = f"Network timeout for {url}"
        if timeout:
            message += f" (timeout: {timeout}s)"
        super().__init__(
            message=message,
            url=url,
            code=ErrorCode.NETWORK_TIMEOUT,
            retry_after=5.0,
            **kwargs
        )
        self.timeout = timeout


class CacheError(DsearchError):
    """Raised when cache operation fails."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.CACHE_ERROR,
            **kwargs
        )


class CacheMissError(CacheError):
    """Raised when cache key is not found."""

    def __init__(self, key: str, **kwargs):
        super().__init__(
            message=f"Cache miss for key: {key}",
            code=ErrorCode.CACHE_MISS,
            retryable=False,
            **kwargs
        )
        self.key = key


def wrap_exception(
    exc: Exception,
    message: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> DsearchError:
    """
    Wrap a standard exception in a DsearchError.

    Args:
        exc: Original exception
        message: Optional override message
        context: Additional context

    Returns:
        DsearchError with appropriate code
    """
    if isinstance(exc, DsearchError):
        return exc

    msg = message or str(exc)
    ctx = context or {}

    # Map common exceptions
    import requests
    if isinstance(exc, requests.exceptions.Timeout):
        return TimeoutError(
            message=msg,
            context=ctx,
            cause=exc
        )
    elif isinstance(exc, requests.exceptions.ConnectionError):
        return NetworkError(
            message=msg,
            context=ctx,
            cause=exc
        )
    elif isinstance(exc, requests.exceptions.HTTPError):
        status_code = exc.response.status_code if hasattr(exc, 'response') else None
        if status_code == 429:
            return ProviderRateLimitError(
                provider=ctx.get("provider", "unknown"),
                context=ctx,
                cause=exc
            )
        elif status_code in (401, 403):
            return ProviderAuthError(
                provider=ctx.get("provider", "unknown"),
                context=ctx,
                cause=exc
            )

    return DsearchError(
        message=msg,
        context=ctx,
        cause=exc
    )


def is_retryable(exc: Exception) -> bool:
    """
    Check if an exception indicates a retryable error.

    Args:
        exc: Exception to check

    Returns:
        True if error is retryable
    """
    if isinstance(exc, DsearchError):
        return exc.retryable

    # Common retryable exceptions (built-in)
    retryable_exceptions = (
        ConnectionError,  # network-level errors
        TimeoutError,     # socket-level timeouts
        OSError,          # IO errors including network
    )

    # requests library exceptions
    try:
        import requests
        retryable_exceptions += (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
        )
    except ImportError:
        pass

    return isinstance(exc, retryable_exceptions)

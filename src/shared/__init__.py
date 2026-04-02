"""
Open Dsearch - Shared Core Modules

This package contains core modules that other components depend on:
- Provider abstraction for search providers
- Rate limiting with token bucket and retry logic
- Configuration management (env + file)
- Error handling utilities
- Logging and metrics infrastructure
"""

from .provider import (
    SearchProvider,
    ProviderConfig,
    ProviderStatus,
    ProviderCapabilities,
    SearchResult,
    ProviderRegistry,
)
from .rate_limiter import (
    RateLimiter,
    TokenBucket,
    LeakyBucket,
    AdaptiveRateLimiter,
    RateLimitError,
)
from .config import Config, ConfigError, ConfigSource
from .errors import (
    DsearchError,
    ProviderError,
    ProviderRateLimitError,
    ValidationError,
    ConfigError as ConfigErrorClass,
    TimeoutError,
)
from .logging import get_logger, configure_logging, MetricsCollector
from .retry import (
    with_retry,
    retry_call,
    RetryConfig,
    RetryExhaustedError,
    RetryContext,
)

__version__ = "0.1.0"

__all__ = [
    # Provider
    "SearchProvider",
    "ProviderConfig",
    "ProviderStatus",
    "ProviderCapabilities",
    "SearchResult",
    "ProviderRegistry",
    # Rate Limiter
    "RateLimiter",
    "TokenBucket",
    "LeakyBucket",
    "AdaptiveRateLimiter",
    "RateLimitError",
    # Config
    "Config",
    "ConfigError",
    "ConfigSource",
    # Errors
    "DsearchError",
    "ProviderError",
    "ProviderRateLimitError",
    "ValidationError",
    "TimeoutError",
    # Logging
    "get_logger",
    "configure_logging",
    "MetricsCollector",
    # Retry
    "with_retry",
    "retry_call",
    "RetryConfig",
    "RetryExhaustedError",
    "RetryContext",
]

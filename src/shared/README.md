# Open Dsearch - Shared Core Modules

This package contains the core shared modules that other components of Open Dsearch depend on. These modules provide foundational functionality for the entire system.

## Modules Overview

### 1. Provider (`provider.py`)

Abstract base class and data structures for search providers.

**Key Components:**
- `SearchProvider` - Abstract base class for all search providers
- `ProviderConfig` - Configuration dataclass for providers
- `ProviderCapabilities` - Capability flags for providers
- `SearchResult` - Standardized search result structure
- `ProviderRegistry` - Registry for managing provider instances
- `ProviderStatus` - Health status enumeration

**Usage:**
```python
from src.shared import SearchProvider, ProviderConfig, SearchResult

class MyProvider(SearchProvider):
    @property
    def name(self) -> str:
        return "my_provider"
    
    async def search(self, query: str, num_results: int = 10, **kwargs):
        # Implementation
        return [SearchResult(title="...", url="...", snippet="...")]
    
    async def health_check(self):
        return ProviderStatus.HEALTHY

# Register provider
from src.shared import get_registry
registry = get_registry()
registry.register("my_provider", MyProvider)
```

### 2. Rate Limiter (`rate_limiter.py`)

Multiple rate limiting strategies for API request management.

**Key Components:**
- `TokenBucket` - Classic bursty rate limiter
- `LeakyBucket` - Smooth output rate limiter
- `AdaptiveRateLimiter` - Self-tuning rate limiter with AIMD
- `RateLimiterManager` - Central manager for multiple limiters

**Usage:**
```python
from src.shared import TokenBucket, get_rate_limiter_manager

# Per-provider rate limiting
limiter = TokenBucket(rate=2.0, capacity=5)
if limiter.acquire():
    # Make API call
    pass

# Or use the global manager
manager = get_rate_limiter_manager()
manager.register("gemini", TokenBucket(rate=2.0, capacity=5))
if manager.acquire("gemini"):
    # Make API call
    pass
```

### 3. Config (`config.py`)

Configuration management with multiple source support.

**Key Components:**
- `Config` - Main configuration class
- `ConfigSource` - Enumeration of config sources
- `ConfigValue` - Value with source metadata

**Priority Order:**
1. Environment variables (`DSEARCH_*`)
2. Configuration files (`~/.config/dsearch/config.yaml`)
3. Default values

**Usage:**
```python
from src.shared import get_config, Config

config = get_config()
timeout = config.get("api_timeout", 30.0)
api_key = config.get_secret("gemini")

# Provider-specific config
provider_config = config.get_provider_config("gemini")
```

### 4. Errors (`errors.py`)

Rich error hierarchy with context and retry information.

**Key Components:**
- `DsearchError` - Base exception class
- `ProviderError` - Provider-related errors
- `ValidationError` - Input validation errors
- `TimeoutError` - Timeout errors
- `RateLimitError` - Rate limiting errors
- `wrap_exception()` - Convert standard exceptions
- `is_retryable()` - Check if error is retryable

**Usage:**
```python
from src.shared import DsearchError, ValidationError, wrap_exception

try:
    result = await provider.search(query)
except Exception as e:
    error = wrap_exception(e, context={"provider": "gemini"})
    if error.retryable:
        # Retry logic
        pass
```

### 5. Logging (`logging.py`)

Structured logging with JSON support and metrics collection.

**Key Components:**
- `get_logger()` - Get logger with context support
- `configure_logging()` - Configure logging output
- `MetricsCollector` - Collect and export metrics
- `Timer` - Context manager for timing operations
- `LogContext` - Context manager for request/trace IDs

**Usage:**
```python
from src.shared import get_logger, MetricsCollector, Timer

logger = get_logger(__name__)
logger.info("Processing request")

# Metrics
collector = MetricsCollector()
with collector.timer("search_operation"):
    # Do work
    pass

# Export metrics
print(collector.export_prometheus())
```

### 6. Retry (`retry.py`)

Retry logic with exponential backoff and jitter.

**Key Components:**
- `with_retry` - Decorator for retry logic
- `retry_call()` - Function wrapper for retries
- `RetryConfig` - Configuration for retry behavior
- `RetryContext` - Context manager for manual retry control

**Usage:**
```python
from src.shared import with_retry, RetryConfig

@with_retry(max_attempts=3, base_delay=1.0)
async def fetch_data():
    # This will be retried on failure
    return await api.call()

# Or use manually
config = RetryConfig(max_attempts=3)
result = retry_call(api.call, config)
```

## Testing

All modules have comprehensive unit tests in `tests/unit/shared/`:

```bash
# Run all shared module tests
pytest tests/unit/shared/ -v

# Run with coverage
pytest tests/unit/shared/ --cov=src/shared --cov-report=term-missing
```

## Design Principles

1. **Type Safety**: All modules use type hints throughout
2. **Thread Safety**: Rate limiters and registries use proper locking
3. **Async Support**: Provider interface supports async/await
4. **Testability**: Global state can be reset for isolated tests
5. **Observability**: Built-in metrics and structured logging
6. **Configuration**: Environment-aware with sensible defaults

## Integration

These modules are designed to be imported by other components:

```python
# In a provider implementation
from src.shared import SearchProvider, ProviderConfig, RateLimitError

# In the API server
from src.shared import get_config, get_logger, MetricsCollector

# In error handlers
from src.shared import wrap_exception, is_retryable
```
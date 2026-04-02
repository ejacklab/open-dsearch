"""
Retry logic with exponential backoff for Open Dsearch.

Provides decorators and context managers for retrying operations
with configurable backoff strategies.
"""

import random
import time
import functools
from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple, Type, Union
from typing import List

from .errors import DsearchError, is_retryable
from .logging import get_logger, get_metrics_collector


logger = get_logger(__name__)


class RetryExhaustedError(DsearchError):
    """Raised when all retry attempts are exhausted."""
    
    def __init__(self, attempts: int, last_error: Exception):
        super().__init__(
            message=f"Retry exhausted after {attempts} attempts",
            context={"attempts": attempts, "last_error": str(last_error)},
            retryable=False
        )
        self.attempts = attempts
        self.last_error = last_error


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_max: float = 0.1
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    on_retry: Optional[Callable[[Exception, int], None]] = None
    on_success: Optional[Callable[[int], None]] = None
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a retry attempt.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            jitter_amount = delay * self.jitter_max * random.random()
            delay += jitter_amount
        
        return delay


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None
):
    """
    Decorator to add retry logic to a function.
    
    Args:
        max_attempts: Maximum number of attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to delays
        retryable_exceptions: Exceptions to retry on
        
    Returns:
        Decorated function
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions or (Exception,)
    )
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return retry_call(func, config, *args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await retry_call_async(func, config, *args, **kwargs)
        
        # Return async wrapper if function is async
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


def retry_call(
    func: Callable,
    config: RetryConfig,
    *args,
    **kwargs
) -> Any:
    """
    Call function with retry logic.
    
    Args:
        func: Function to call
        config: Retry configuration
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
        
    Raises:
        RetryExhaustedError: If all attempts fail
    """
    last_error: Optional[Exception] = None
    metrics = get_metrics_collector()
    
    for attempt in range(config.max_attempts):
        try:
            result = func(*args, **kwargs)
            
            if attempt > 0 and config.on_success:
                config.on_success(attempt)
            
            # Record success metric
            metrics.increment("retry.success", tags={
                "function": func.__name__,
                "attempt": str(attempt)
            })
            
            return result
            
        except Exception as e:
            last_error = e
            
            # Check if we should retry
            if not isinstance(e, config.retryable_exceptions):
                raise
            
            if not is_retryable(e):
                raise
            
            if attempt >= config.max_attempts - 1:
                break
            
            # Calculate delay
            delay = config.calculate_delay(attempt)
            
            logger.warning(
                f"Retry {attempt + 1}/{config.max_attempts} for {func.__name__} "
                f"after error: {e}. Waiting {delay:.2f}s"
            )
            
            if config.on_retry:
                config.on_retry(e, attempt)
            
            # Record retry metric
            metrics.increment("retry.attempt", tags={
                "function": func.__name__,
                "attempt": str(attempt),
                "error_type": type(e).__name__
            })
            
            time.sleep(delay)
    
    # All attempts exhausted
    metrics.increment("retry.exhausted", tags={
        "function": func.__name__,
        "attempts": str(config.max_attempts)
    })
    
    raise RetryExhaustedError(config.max_attempts, last_error)


async def retry_call_async(
    func: Callable,
    config: RetryConfig,
    *args,
    **kwargs
) -> Any:
    """
    Async version of retry_call.
    
    Args:
        func: Async function to call
        config: Retry configuration
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
    """
    import asyncio
    
    last_error: Optional[Exception] = None
    metrics = get_metrics_collector()
    
    for attempt in range(config.max_attempts):
        try:
            result = await func(*args, **kwargs)
            
            if attempt > 0 and config.on_success:
                config.on_success(attempt)
            
            metrics.increment("retry.success", tags={
                "function": func.__name__,
                "attempt": str(attempt)
            })
            
            return result
            
        except Exception as e:
            last_error = e
            
            if not isinstance(e, config.retryable_exceptions):
                raise
            
            if not is_retryable(e):
                raise
            
            if attempt >= config.max_attempts - 1:
                break
            
            delay = config.calculate_delay(attempt)
            
            logger.warning(
                f"Retry {attempt + 1}/{config.max_attempts} for {func.__name__} "
                f"after error: {e}. Waiting {delay:.2f}s"
            )
            
            if config.on_retry:
                config.on_retry(e, attempt)
            
            metrics.increment("retry.attempt", tags={
                "function": func.__name__,
                "attempt": str(attempt),
                "error_type": type(e).__name__
            })
            
            await asyncio.sleep(delay)
    
    metrics.increment("retry.exhausted", tags={
        "function": func.__name__,
        "attempts": str(config.max_attempts)
    })
    
    raise RetryExhaustedError(config.max_attempts, last_error)


class RetryContext:
    """Context manager for retry operations."""
    
    def __init__(self, config: Optional[RetryConfig] = None, **kwargs):
        """Initialize with configuration."""
        self.config = config or RetryConfig(**kwargs)
        self.attempt = 0
        self.last_error: Optional[Exception] = None
    
    def __enter__(self):
        """Enter context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - handle retries."""
        if exc_val is None:
            return True
        
        self.last_error = exc_val
        
        # Check if we should retry
        if not isinstance(exc_val, self.config.retryable_exceptions):
            return False
        
        if not is_retryable(exc_val):
            return False
        
        if self.attempt >= self.config.max_attempts - 1:
            raise RetryExhaustedError(self.config.max_attempts, exc_val)
        
        # Calculate and apply delay
        delay = self.config.calculate_delay(self.attempt)
        logger.warning(
            f"Retry {self.attempt + 1}/{self.config.max_attempts} "
            f"after error: {exc_val}. Waiting {delay:.2f}s"
        )
        
        if self.config.on_retry:
            self.config.on_retry(exc_val, self.attempt)
        
        time.sleep(delay)
        self.attempt += 1
        
        # Suppress exception to allow retry
        return True
    
    def should_continue(self) -> bool:
        """Check if we should continue retrying."""
        return self.attempt < self.config.max_attempts

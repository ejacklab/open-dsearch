"""
Rate limiting implementations for Open Dsearch.

Provides multiple rate limiting strategies:
- Token Bucket: Classic bursty rate limiter
- Leaky Bucket: Smooth output rate limiter
- Adaptive Rate Limiter: Self-tuning based on feedback
"""

import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Callable
from enum import Enum


class RateLimitStrategy(Enum):
    """Available rate limiting strategies."""
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"
    ADAPTIVE = "adaptive"


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class RateLimiter(ABC):
    """Abstract base class for rate limiters."""
    
    @abstractmethod
    def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens from the rate limiter.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens acquired, False if rate limited
        """
        pass
    
    @abstractmethod
    def acquire_blocking(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens, blocking if necessary.
        
        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum time to wait (None = infinite)
            
        Returns:
            True if tokens acquired, False if timeout
        """
        pass
    
    @abstractmethod
    def get_state(self) -> dict:
        """Get current rate limiter state."""
        pass


@dataclass
class TokenBucket(RateLimiter):
    """
    Token bucket rate limiter.
    
    Allows bursts up to bucket capacity while maintaining
    an average rate over time.
    
    Attributes:
        rate: Tokens added per second
        capacity: Maximum bucket capacity
    """
    rate: float = 1.0
    capacity: int = 10
    _tokens: float = field(default=0.0, init=False)
    _last_update: float = field(default_factory=time.time, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    
    def __post_init__(self):
        """Initialize bucket with full capacity."""
        self._tokens = float(self.capacity)
    
    def _add_tokens(self) -> None:
        """Add tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_update
        self._tokens = min(
            self.capacity,
            self._tokens + elapsed * self.rate
        )
        self._last_update = now
    
    def acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without blocking.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if acquired, False if not enough tokens
        """
        with self._lock:
            self._add_tokens()
            
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False
    
    def acquire_blocking(
        self,
        tokens: int = 1,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Acquire tokens, blocking until available.
        
        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum wait time in seconds
            
        Returns:
            True if acquired, False if timeout
        """
        start_time = time.time()
        
        while True:
            with self._lock:
                self._add_tokens()
                
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
                
                # Calculate wait time
                tokens_needed = tokens - self._tokens
                wait_time = tokens_needed / self.rate
                
                if timeout is not None:
                    elapsed = time.time() - start_time
                    remaining = timeout - elapsed
                    if remaining <= 0:
                        return False
                    wait_time = min(wait_time, remaining)
            
            time.sleep(wait_time)
    
    def get_state(self) -> dict:
        """Get current bucket state."""
        with self._lock:
            self._add_tokens()
            return {
                "strategy": RateLimitStrategy.TOKEN_BUCKET.value,
                "rate": self.rate,
                "capacity": self.capacity,
                "tokens": self._tokens,
                "available": self._tokens,
            }
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """Get estimated wait time for tokens."""
        with self._lock:
            self._add_tokens()
            if self._tokens >= tokens:
                return 0.0
            return (tokens - self._tokens) / self.rate


@dataclass
class LeakyBucket(RateLimiter):
    """
    Leaky bucket rate limiter.
    
    Smooths out request rate by processing at a constant
    rate regardless of input burstiness.
    
    Attributes:
        leak_rate: Rate at which bucket leaks (requests/sec)
        capacity: Maximum bucket capacity
    """
    leak_rate: float = 1.0
    capacity: int = 10
    _volume: float = field(default=0.0, init=False)
    _last_leak: float = field(default_factory=time.time, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    
    def _leak(self) -> None:
        """Leak volume based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_leak
        self._volume = max(0.0, self._volume - elapsed * self.leak_rate)
        self._last_leak = now
    
    def acquire(self, tokens: int = 1) -> bool:
        """
        Try to add to bucket without blocking.
        
        Args:
            tokens: Volume to add (typically 1 per request)
            
        Returns:
            True if added, False if bucket full
        """
        with self._lock:
            self._leak()
            
            if self._volume + tokens <= self.capacity:
                self._volume += tokens
                return True
            return False
    
    def acquire_blocking(
        self,
        tokens: int = 1,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Add to bucket, blocking if full.
        
        Args:
            tokens: Volume to add
            timeout: Maximum wait time
            
        Returns:
            True if added, False if timeout
        """
        start_time = time.time()
        
        while True:
            with self._lock:
                self._leak()
                
                if self._volume + tokens <= self.capacity:
                    self._volume += tokens
                    return True
                
                # Calculate wait time for enough capacity
                space_needed = (self._volume + tokens) - self.capacity
                wait_time = space_needed / self.leak_rate
                
                if timeout is not None:
                    elapsed = time.time() - start_time
                    remaining = timeout - elapsed
                    if remaining <= 0:
                        return False
                    wait_time = min(wait_time, remaining)
            
            time.sleep(wait_time)
    
    def get_state(self) -> dict:
        """Get current bucket state."""
        with self._lock:
            self._leak()
            return {
                "strategy": RateLimitStrategy.LEAKY_BUCKET.value,
                "leak_rate": self.leak_rate,
                "capacity": self.capacity,
                "volume": self._volume,
                "available": self.capacity - self._volume,
            }


@dataclass
class AdaptiveRateLimiter(RateLimiter):
    """
    Adaptive rate limiter using AIMD (Additive Increase
    Multiplicative Decrease) algorithm.
    
    Automatically adjusts rate based on success/failure feedback.
    
    Attributes:
        initial_rate: Starting rate (requests/sec)
        min_rate: Minimum allowed rate
        max_rate: Maximum allowed rate
        add_increment: Amount to add on success
        multiply_decrease: Factor to multiply on failure
    """
    initial_rate: float = 10.0
    min_rate: float = 0.1
    max_rate: float = 1000.0
    add_increment: float = 1.0
    multiply_decrease: float = 0.5
    
    _current_rate: float = field(init=False)
    _success_count: int = field(default=0, init=False)
    _failure_count: int = field(default=0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _inner: TokenBucket = field(init=False)
    
    def __post_init__(self):
        """Initialize with token bucket."""
        self._current_rate = self.initial_rate
        self._inner = TokenBucket(
            rate=self._current_rate,
            capacity=max(1, int(self._current_rate))
        )
    
    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens."""
        return self._inner.acquire(tokens)
    
    def acquire_blocking(
        self,
        tokens: int = 1,
        timeout: Optional[float] = None
    ) -> bool:
        """Acquire tokens with blocking."""
        return self._inner.acquire_blocking(tokens, timeout)
    
    def report_success(self) -> None:
        """Report successful request - increases rate."""
        with self._lock:
            self._success_count += 1
            self._current_rate = min(
                self.max_rate,
                self._current_rate + self.add_increment
            )
            self._update_inner()
    
    def report_failure(self, is_rate_limit: bool = False) -> None:
        """
        Report failed request - decreases rate.
        
        Args:
            is_rate_limit: True if failure was due to rate limiting
        """
        with self._lock:
            self._failure_count += 1
            if is_rate_limit:
                self._current_rate = max(
                    self.min_rate,
                    self._current_rate * self.multiply_decrease
                )
                self._update_inner()
    
    def _update_inner(self) -> None:
        """Update inner token bucket with new rate."""
        self._inner.rate = self._current_rate
        self._inner.capacity = max(1, int(self._current_rate))
    
    def get_state(self) -> dict:
        """Get current adaptive state."""
        with self._lock:
            return {
                "strategy": RateLimitStrategy.ADAPTIVE.value,
                "current_rate": self._current_rate,
                "min_rate": self.min_rate,
                "max_rate": self.max_rate,
                "success_count": self._success_count,
                "failure_count": self._failure_count,
                "inner": self._inner.get_state(),
            }


def create_rate_limiter(
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET,
    **kwargs
) -> RateLimiter:
    """
    Factory function to create rate limiters.
    
    Args:
        strategy: Rate limiting strategy
        **kwargs: Strategy-specific parameters
        
    Returns:
        Configured rate limiter
    """
    if strategy == RateLimitStrategy.TOKEN_BUCKET:
        return TokenBucket(
            rate=kwargs.get("rate", 1.0),
            capacity=kwargs.get("capacity", 10)
        )
    elif strategy == RateLimitStrategy.LEAKY_BUCKET:
        return LeakyBucket(
            leak_rate=kwargs.get("leak_rate", 1.0),
            capacity=kwargs.get("capacity", 10)
        )
    elif strategy == RateLimitStrategy.ADAPTIVE:
        return AdaptiveRateLimiter(
            initial_rate=kwargs.get("initial_rate", 10.0),
            min_rate=kwargs.get("min_rate", 0.1),
            max_rate=kwargs.get("max_rate", 1000.0),
            add_increment=kwargs.get("add_increment", 1.0),
            multiply_decrease=kwargs.get("multiply_decrease", 0.5)
        )
    else:
        raise ValueError(f"Unknown strategy: {strategy}")


class RateLimiterManager:
    """Manages rate limiters for multiple providers."""
    
    def __init__(self):
        """Initialize empty manager."""
        self._limiters: dict[str, RateLimiter] = {}
    
    def register(
        self,
        name: str,
        limiter: RateLimiter
    ) -> None:
        """Register a rate limiter for a provider."""
        self._limiters[name] = limiter
    
    def get(self, name: str) -> Optional[RateLimiter]:
        """Get rate limiter for a provider."""
        return self._limiters.get(name)
    
    def acquire(self, name: str, tokens: int = 1) -> bool:
        """Acquire tokens from a provider's rate limiter."""
        limiter = self._limiters.get(name)
        if limiter is None:
            return True  # No limiter = no limit
        return limiter.acquire(tokens)
    
    def get_all_states(self) -> dict:
        """Get states of all rate limiters."""
        return {
            name: limiter.get_state()
            for name, limiter in self._limiters.items()
        }


# Global manager instance
_manager: Optional[RateLimiterManager] = None


def get_rate_limiter_manager() -> RateLimiterManager:
    """Get or create global rate limiter manager."""
    global _manager
    if _manager is None:
        _manager = RateLimiterManager()
    return _manager


def reset_rate_limiter_manager() -> None:
    """Reset global manager (useful for testing)."""
    global _manager
    _manager = None
"""Unit tests for rate limiter module."""

import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from src.shared.rate_limiter import (
    TokenBucket,
    LeakyBucket,
    AdaptiveRateLimiter,
    RateLimitStrategy,
    create_rate_limiter,
    RateLimiterManager,
    get_rate_limiter_manager,
    reset_rate_limiter_manager,
)


class TestTokenBucket:
    """Tests for TokenBucket rate limiter."""
    
    def test_initial_tokens(self):
        """Test bucket starts with full capacity."""
        bucket = TokenBucket(rate=1.0, capacity=5)
        state = bucket.get_state()
        assert state["tokens"] == 5.0
    
    def test_acquire_success(self):
        """Test successful token acquisition."""
        bucket = TokenBucket(rate=10.0, capacity=5)
        
        assert bucket.acquire() is True
        state = bucket.get_state()
        assert state["tokens"] == 4.0
    
    def test_acquire_multiple_tokens(self):
        """Test acquiring multiple tokens."""
        bucket = TokenBucket(rate=10.0, capacity=10)
        
        assert bucket.acquire(3) is True
        state = bucket.get_state()
        assert state["tokens"] == 7.0
    
    def test_acquire_failure(self):
        """Test acquisition failure when empty."""
        bucket = TokenBucket(rate=0.1, capacity=1)
        bucket.acquire()  # Empty the bucket
        
        assert bucket.acquire() is False
    
    def test_token_refill(self):
        """Test tokens refill over time."""
        bucket = TokenBucket(rate=10.0, capacity=5)
        bucket.acquire(5)  # Empty bucket
        
        time.sleep(0.15)  # Wait for refill
        
        state = bucket.get_state()
        assert state["tokens"] > 0
    
    def test_acquire_blocking(self):
        """Test blocking acquisition."""
        bucket = TokenBucket(rate=100.0, capacity=1)
        bucket.acquire()  # Empty bucket
        
        start = time.time()
        result = bucket.acquire_blocking(timeout=0.05)
        elapsed = time.time() - start
        
        assert result is True
        assert elapsed >= 0.01  # Should have waited
    
    def test_acquire_blocking_timeout(self):
        """Test blocking acquisition timeout."""
        bucket = TokenBucket(rate=0.1, capacity=1)
        bucket.acquire()  # Empty bucket
        
        result = bucket.acquire_blocking(timeout=0.01)
        assert result is False
    
    def test_get_wait_time(self):
        """Test calculating wait time."""
        bucket = TokenBucket(rate=1.0, capacity=5)
        bucket.acquire(5)  # Empty bucket
        
        wait_time = bucket.get_wait_time(1)
        assert wait_time > 0
    
    def test_thread_safety(self):
        """Test thread-safe operation."""
        bucket = TokenBucket(rate=1000.0, capacity=100)
        
        def acquire_tokens():
            for _ in range(10):
                bucket.acquire()
        
        threads = [threading.Thread(target=acquire_tokens) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        state = bucket.get_state()
        assert state["tokens"] == 50.0


class TestLeakyBucket:
    """Tests for LeakyBucket rate limiter."""
    
    def test_initial_volume(self):
        """Test bucket starts empty."""
        bucket = LeakyBucket(leak_rate=1.0, capacity=5)
        state = bucket.get_state()
        assert state["volume"] == 0.0
    
    def test_acquire_success(self):
        """Test successful acquisition."""
        bucket = LeakyBucket(leak_rate=1.0, capacity=5)
        
        assert bucket.acquire() is True
        state = bucket.get_state()
        assert state["volume"] == 1.0
    
    def test_acquire_failure_when_full(self):
        """Test failure when bucket is full."""
        bucket = LeakyBucket(leak_rate=0.1, capacity=1)
        bucket.acquire()  # Fill bucket
        
        assert bucket.acquire() is False
    
    def test_leak_over_time(self):
        """Test bucket leaks over time."""
        bucket = LeakyBucket(leak_rate=10.0, capacity=5)
        bucket.acquire(5)  # Fill bucket
        
        time.sleep(0.15)  # Wait for leak
        
        state = bucket.get_state()
        assert state["volume"] < 5.0
    
    def test_acquire_blocking(self):
        """Test blocking acquisition."""
        bucket = LeakyBucket(leak_rate=100.0, capacity=1)
        bucket.acquire()  # Fill bucket
        
        start = time.time()
        result = bucket.acquire_blocking(timeout=0.05)
        elapsed = time.time() - start
        
        assert result is True
        assert elapsed >= 0.01


class TestAdaptiveRateLimiter:
    """Tests for AdaptiveRateLimiter."""
    
    def test_initial_state(self):
        """Test initial state."""
        limiter = AdaptiveRateLimiter(initial_rate=10.0)
        state = limiter.get_state()
        
        assert state["current_rate"] == 10.0
        assert state["strategy"] == "adaptive"
    
    def test_report_success_increases_rate(self):
        """Test success increases rate."""
        limiter = AdaptiveRateLimiter(
            initial_rate=10.0,
            add_increment=5.0,
            max_rate=100.0
        )
        
        limiter.report_success()
        state = limiter.get_state()
        
        assert state["current_rate"] == 15.0
    
    def test_report_failure_decreases_rate(self):
        """Test failure decreases rate."""
        limiter = AdaptiveRateLimiter(
            initial_rate=10.0,
            multiply_decrease=0.5,
            min_rate=1.0
        )
        
        limiter.report_failure(is_rate_limit=True)
        state = limiter.get_state()
        
        assert state["current_rate"] == 5.0
    
    def test_rate_bounds(self):
        """Test rate respects min/max bounds."""
        limiter = AdaptiveRateLimiter(
            initial_rate=5.0,
            min_rate=2.0,
            max_rate=8.0,
            add_increment=10.0,
            multiply_decrease=0.1
        )
        
        # Try to exceed max
        limiter.report_success()
        state = limiter.get_state()
        assert state["current_rate"] == 8.0  # Capped at max
        
        # Try to go below min
        limiter.report_failure(is_rate_limit=True)
        limiter.report_failure(is_rate_limit=True)
        state = limiter.get_state()
        assert state["current_rate"] == 2.0  # Capped at min
    
    def test_acquire_delegates_to_inner(self):
        """Test acquire delegates to inner limiter."""
        limiter = AdaptiveRateLimiter(initial_rate=10.0)
        
        # Should succeed with initial tokens
        assert limiter.acquire() is True


class TestRateLimiterFactory:
    """Tests for rate limiter factory."""
    
    def test_create_token_bucket(self):
        """Test creating token bucket."""
        limiter = create_rate_limiter(
            strategy=RateLimitStrategy.TOKEN_BUCKET,
            rate=5.0,
            capacity=10
        )
        
        assert isinstance(limiter, TokenBucket)
        state = limiter.get_state()
        assert state["strategy"] == "token_bucket"
    
    def test_create_leaky_bucket(self):
        """Test creating leaky bucket."""
        limiter = create_rate_limiter(
            strategy=RateLimitStrategy.LEAKY_BUCKET,
            leak_rate=5.0,
            capacity=10
        )
        
        assert isinstance(limiter, LeakyBucket)
        state = limiter.get_state()
        assert state["strategy"] == "leaky_bucket"
    
    def test_create_adaptive(self):
        """Test creating adaptive limiter."""
        limiter = create_rate_limiter(
            strategy=RateLimitStrategy.ADAPTIVE,
            initial_rate=10.0
        )
        
        assert isinstance(limiter, AdaptiveRateLimiter)
        state = limiter.get_state()
        assert state["strategy"] == "adaptive"
    
    def test_invalid_strategy(self):
        """Test invalid strategy raises error."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            create_rate_limiter(strategy="invalid")


class TestRateLimiterManager:
    """Tests for RateLimiterManager."""
    
    def setup_method(self):
        """Reset manager before each test."""
        reset_rate_limiter_manager()
    
    def teardown_method(self):
        """Reset manager after each test."""
        reset_rate_limiter_manager()
    
    def test_register_and_get(self):
        """Test registering and retrieving limiters."""
        manager = get_rate_limiter_manager()
        limiter = TokenBucket(rate=1.0, capacity=5)
        
        manager.register("test", limiter)
        retrieved = manager.get("test")
        
        assert retrieved is limiter
    
    def test_get_nonexistent(self):
        """Test getting non-existent limiter returns None."""
        manager = get_rate_limiter_manager()
        assert manager.get("nonexistent") is None
    
    def test_acquire_from_registered(self):
        """Test acquire from registered limiter."""
        manager = get_rate_limiter_manager()
        limiter = TokenBucket(rate=100.0, capacity=5)
        
        manager.register("test", limiter)
        result = manager.acquire("test")
        
        assert result is True
    
    def test_acquire_no_limiter(self):
        """Test acquire with no limiter returns True."""
        manager = get_rate_limiter_manager()
        result = manager.acquire("nonexistent")
        
        assert result is True  # No limit = no blocking
    
    def test_get_all_states(self):
        """Test getting all limiter states."""
        manager = get_rate_limiter_manager()
        manager.register("a", TokenBucket(rate=1.0, capacity=5))
        manager.register("b", TokenBucket(rate=2.0, capacity=10))
        
        states = manager.get_all_states()
        
        assert "a" in states
        assert "b" in states
        assert states["a"]["rate"] == 1.0
        assert states["b"]["rate"] == 2.0

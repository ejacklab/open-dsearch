"""Comprehensive unit tests for rate limiting."""

import time
import threading
import pytest

from src.shared.rate_limiter import (
    TokenBucket,
    LeakyBucket,
    AdaptiveRateLimiter,
    RateLimiterManager,
    create_rate_limiter,
    RateLimitStrategy,
    RateLimitError,
)


# ─── Token Bucket Tests ──────────────────────────────────────────────

class TestTokenBucket:
    """Tests for TokenBucket rate limiter."""

    def test_init_full(self):
        """Bucket starts full."""
        bucket = TokenBucket(rate=1.0, capacity=10)
        assert bucket._tokens == 10.0

    def test_acquire_single(self):
        """Acquire one token succeeds when tokens available."""
        bucket = TokenBucket(rate=1.0, capacity=10)
        assert bucket.acquire(1) is True
        assert bucket._tokens == 9.0

    def test_acquire_multiple(self):
        """Acquire multiple tokens at once."""
        bucket = TokenBucket(rate=1.0, capacity=10)
        assert bucket.acquire(5) is True
        assert bucket._tokens == 5.0

    def test_acquire_exhausts(self):
        """Acquire fails when bucket empty."""
        bucket = TokenBucket(rate=0.001, capacity=5)  # Very slow refill
        bucket.acquire(5)  # Drain
        assert bucket.acquire(1) is False

    def test_refill_over_time(self):
        """Tokens refill based on elapsed time."""
        bucket = TokenBucket(rate=100.0, capacity=10)
        bucket.acquire(10)  # Empty it
        assert bucket.acquire(1) is False
        time.sleep(0.02)  # Wait ~2 tokens worth
        # After refill, should have some tokens
        state = bucket.get_state()
        assert state["tokens"] > 0

    def test_capacity_limit(self):
        """Tokens never exceed capacity."""
        bucket = TokenBucket(rate=1000.0, capacity=5)
        time.sleep(0.05)  # Let it "refill" way past capacity
        state = bucket.get_state()
        assert state["tokens"] <= 5.0

    def test_get_wait_time(self):
        """Wait time is zero when tokens available."""
        bucket = TokenBucket(rate=1.0, capacity=10)
        assert bucket.get_wait_time(1) == 0.0

    def test_get_wait_time_positive(self):
        """Wait time positive when insufficient tokens."""
        bucket = TokenBucket(rate=2.0, capacity=5)
        bucket.acquire(5)
        wait = bucket.get_wait_time(3)
        assert wait > 0  # Need to wait for refill

    def test_get_state_structure(self):
        """State dict has expected keys."""
        bucket = TokenBucket(rate=5.0, capacity=20)
        state = bucket.get_state()
        assert state["strategy"] == "token_bucket"
        assert state["rate"] == 5.0
        assert state["capacity"] == 20
        assert "tokens" in state

    def test_thread_safety_basic(self):
        """Concurrent acquires don't corrupt state."""
        bucket = TokenBucket(rate=10000.0, capacity=10000)
        errors = []

        def worker():
            try:
                for _ in range(50):
                    bucket.acquire(1)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(errors) == 0
        state = bucket.get_state()
        assert 0 <= state["tokens"] <= 10000


class TestLeakyBucket:
    """Tests for LeakyBucket rate limiter."""

    def test_acquire_when_space(self):
        """Acquire succeeds when bucket has space."""
        bucket = LeakyBucket(leak_rate=1.0, capacity=10)
        assert bucket.acquire(1) is True
        assert bucket._volume == 1.0

    def test_acquire_fills_to_capacity(self):
        """Can fill up to capacity."""
        bucket = LeakyBucket(leak_rate=1.0, capacity=5)
        assert bucket.acquire(5) is True
        assert bucket.acquire(1) is False  # Full

    def test_leak_over_time(self):
        """Volume decreases over time (leaking)."""
        bucket = LeakyBucket(leak_rate=100.0, capacity=50)
        bucket.acquire(50)  # Fill completely
        assert bucket.acquire(1) is False
        time.sleep(0.03)  # Let it leak
        state = bucket.get_state()
        assert state["available"] > 0  # Space opened up

    def test_get_state_structure(self):
        """State dict has expected keys."""
        bucket = LeakyBucket(leak_rate=3.0, capacity=15)
        state = bucket.get_state()
        assert state["strategy"] == "leaky_bucket"
        assert state["leak_rate"] == 3.0
        assert state["capacity"] == 15
        assert "volume" in state
        assert "available" in state

    def test_empty_bucket_has_full_availability(self):
        """Empty bucket shows full availability."""
        bucket = LeakyBucket(leak_rate=1.0, capacity=10)
        state = bucket.get_state()
        assert state["available"] == 10


class TestAdaptiveRateLimiter:
    """Tests for AdaptiveRateLimiter (AIMD)."""

    def test_init_rate(self):
        """Starts with initial_rate."""
        adap = AdaptiveRateLimiter(initial_rate=20.0)
        state = adap.get_state()
        assert state["current_rate"] == 20.0

    def test_success_increases_rate(self):
        """Success increases current rate."""
        adap = AdaptiveRateLimiter(
            initial_rate=10.0,
            max_rate=100.0,
            add_increment=5.0
        )
        adap.report_success()
        state = adap.get_state()
        assert state["current_rate"] == 15.0

    def test_success_clamps_at_max(self):
        """Rate doesn't exceed max_rate."""
        adap = AdaptiveRateLimiter(
            initial_rate=99.0,
            max_rate=100.0,
            add_increment=5.0
        )
        adap.report_success()
        state = adap.get_state()
        assert state["current_rate"] == 100.0

    def test_failure_decreases_rate(self):
        """Failure (rate limit) multiplies rate down."""
        adap = AdaptiveRateLimiter(
            initial_rate=100.0,
            min_rate=1.0,
            multiply_decrease=0.5
        )
        adap.report_failure(is_rate_limit=True)
        state = adap.get_state()
        assert state["current_rate"] == 50.0

    def test_failure_clamps_at_min(self):
        """Rate doesn't go below min_rate."""
        adap = AdaptiveRateLimiter(
            initial_rate=0.15,
            min_rate=0.1,
            multiply_decrease=0.5
        )
        adap.report_failure(is_rate_limit=True)
        state = adap.get_state()
        assert state["current_rate"] == 0.1

    def test_tracks_success_count(self):
        """Success counter increments."""
        adap = AdaptiveRateLimiter()
        adap.report_success()
        adap.report_success()
        state = adap.get_state()
        assert state["success_count"] == 2

    def test_tracks_failure_count(self):
        """Failure counter increments."""
        adap = AdaptiveRateLimiter()
        adap.report_failure(is_rate_limit=True)
        state = adap.get_state()
        assert state["failure_count"] == 1

    def test_acquire_delegates_to_inner(self):
        """Acquire works through inner token bucket."""
        adap = AdaptiveRateLimiter(initial_rate=10.0)
        assert adap.acquire(1) is True  # Should have tokens

    def test_inner_updates_on_rate_change(self):
        """Inner token bucket reflects new rate after adjustment."""
        adap = AdaptiveRateLimiter(initial_rate=10.0)
        old_inner_rate = adap._inner.rate
        adap.report_success()  # Increases rate
        assert adap._inner.rate > old_inner_rate


class TestCreateRateLimiterFactory:
    """Tests for the factory function."""

    def test_token_bucket_factory(self):
        """Creates token bucket by default."""
        limiter = create_rate_limiter(RateLimitStrategy.TOKEN_BUCKET, rate=5.0, capacity=20)
        assert isinstance(limiter, TokenBucket)
        assert limiter.rate == 5.0
        assert limiter.capacity == 20

    def test_leaky_bucket_factory(self):
        """Creates leaky bucket."""
        limiter = create_rate_limiter(RateLimitStrategy.LEAKY_BUCKET, leak_rate=3.0, capacity=7)
        assert isinstance(limiter, LeakyBucket)
        assert limiter.leak_rate == 3.0

    def test_adaptive_factory(self):
        """Creates adaptive rate limiter."""
        limiter = create_rate_limiter(RateLimitStrategy.ADAPTIVE, initial_rate=50.0)
        assert isinstance(limiter, AdaptiveRateLimiter)

    def test_unknown_strategy_raises(self):
        """Unknown strategy raises ValueError."""
        with pytest.raises(ValueError):
            create_rate_limiter("nonexistent_strategy")  # type: ignore


class TestRateLimiterManager:
    """Tests for RateLimiterManager."""

    def test_register_and_get(self):
        """Register and retrieve a limiter."""
        mgr = RateLimiterManager()
        tb = TokenBucket(rate=5.0, capacity=10)
        mgr.register("gemini", tb)
        assert mgr.get("gemini") is tb

    def test_get_missing_returns_none(self):
        """Missing key returns None."""
        mgr = RateLimiterManager()
        assert mgr.get("nonexistent") is None

    def test_acquire_missing_allows(self):
        """Acquire on unregistered provider returns True (no limit)."""
        mgr = RateLimiterManager()
        assert mgr.acquire("unknown") is True

    def test_acquire_registered(self):
        """Acquire delegates to registered limiter."""
        mgr = RateLimiterManager()
        tb = TokenBucket(rate=1.0, capacity=1)
        mgr.register("test", tb)
        assert mgr.acquire("test") is True
        assert mgr.acquire("test") is False  # Exhausted

    def test_get_all_states(self):
        """Get all states returns per-provider dict."""
        mgr = RateLimiterManager()
        mgr.register("a", TokenBucket(rate=1.0, capacity=5))
        mgr.register("b", LeakyBucket(leak_rate=2.0, capacity=10))
        states = mgr.get_all_states()
        assert "a" in states
        assert "b" in states
        assert states["a"]["strategy"] == "token_bucket"
        assert states["b"]["strategy"] == "leaky_bucket"


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_message_and_retry_after(self):
        """Stores message and optional retry_after."""
        err = RateLimitError("too fast", retry_after=2.5)
        assert str(err) == "too fast"
        assert err.retry_after == 2.5

    def test_no_retry_after(self):
        """retry_after defaults to None."""
        err = RateLimitError("too fast")
        assert err.retry_after is None

"""Comprehensive unit tests for retry logic."""

import time
import asyncio
from unittest.mock import patch, MagicMock

import pytest

from src.shared.retry import (
    RetryConfig,
    RetryExhaustedError,
    RetryContext,
    with_retry,
    retry_call,
    retry_call_async,
)


# ─── RetryConfig Tests ────────────────────────────────────────────────

class TestRetryConfig:
    """Tests for RetryConfig."""

    def test_defaults(self):
        """Default values are sensible."""
        cfg = RetryConfig()
        assert cfg.max_attempts == 3
        assert cfg.base_delay == 1.0
        assert cfg.max_delay == 60.0
        assert cfg.exponential_base == 2.0
        assert cfg.jitter is True

    def test_calculate_delay_no_jitter(self):
        """Exponential backoff without jitter."""
        cfg = RetryConfig(
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=False
        )
        assert cfg.calculate_delay(0) == 1.0   # 1 * 2^0
        assert cfg.calculate_delay(1) == 2.0   # 1 * 2^1
        assert cfg.calculate_delay(2) == 4.0   # 1 * 2^2

    def test_calculate_delay_clamps_to_max(self):
        """Delay never exceeds max_delay."""
        cfg = RetryConfig(
            base_delay=10.0,
            max_delay=30.0,
            exponential_base=10.0,
            jitter=False
        )
        # 10 * 10^2 = 1000 → clamped to 30
        assert cfg.calculate_delay(2) == 30.0

    def test_calculate_delay_with_jitter(self):
        """With jitter, delay is >= base and <= base + jitter%."""
        cfg = RetryConfig(
            base_delay=1.0,
            max_delay=100.0,
            jitter=True,
            jitter_max=0.5
        )
        for _ in range(20):
            delay = cfg.calculate_delay(0)
            assert 1.0 <= delay <= 1.5


class TestRetryExhaustedError:
    """Tests for RetryExhaustedError."""

    def test_message_format(self):
        """Message includes attempt count."""
        err = RetryExhaustedError(3, ValueError("boom"))
        assert "3 attempts" in str(err)
        assert err.attempts == 3
        assert isinstance(err.last_error, ValueError)

    def test_is_dsearch_error(self):
        """Is a DsearchError subclass (retryable=False)."""
        from src.shared.errors import DsearchError
        err = RetryExhaustedError(3, RuntimeError("x"))
        assert isinstance(err, DsearchError)
        assert err.retryable is False


# ─── retry_call Tests ─────────────────────────────────────────────────

class TestRetryCall:
    """Tests for synchronous retry_call."""

    def test_success_first_attempt(self):
        """Returns result on first try."""
        result = retry_call(lambda: 42, RetryConfig(max_attempts=3))
        assert result == 42

    def test_success_after_retries(self):
        """Succeeds after some failures."""
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return "ok"

        result = retry_call(flaky, RetryConfig(max_attempts=5, base_delay=0.01, jitter=False))
        assert result == "ok"
        assert call_count == 3

    def test_exhaustion_raises(self):
        """Raises RetryExhaustedError when all attempts fail."""
        def always_fail():
            raise ValueError("permanent")

        with pytest.raises(RetryExhaustedError) as exc_info:
            retry_call(always_fail, RetryConfig(max_attempts=3, base_delay=0.01, jitter=False))

        assert exc_info.value.attempts == 3
        assert isinstance(exc_info.value.last_error, ValueError)

    def test_non_retryable_bubbles_with_narrow_exceptions(self):
        """Non-retryable DsearchError bubbles when excluded from retryable_exceptions."""
        from src.shared.errors import ConfigError

        def raise_config_error():
            raise ConfigError("bad config")

        # Exclude DsearchError hierarchy — forces is_retryable() check
        with pytest.raises(ConfigError):
            retry_call(
                raise_config_error,
                RetryConfig(
                    max_attempts=5, base_delay=0.01, jitter=False,
                    retryable_exceptions=(ConnectionError, TimeoutError, OSError)
                )
            )

    def test_on_retry_callback(self):
        """on_retry callback fires on each failed attempt."""
        attempts_log = []

        cfg = RetryConfig(
            max_attempts=3,
            base_delay=0.01,
            jitter=False,
            on_retry=lambda err, attempt: attempts_log.append((type(err).__name__, attempt))
        )

        def fail_twice():
            if len(attempts_log) < 2:
                raise ConnectionError("fail")
            return "recovered"

        retry_call(fail_twice, cfg)
        assert len(attempts_log) == 2

    def test_on_success_callback(self):
        """on_success callback fires after recovery."""
        success_attempts = []

        cfg = RetryConfig(
            max_attempts=3,
            base_delay=0.01,
            jitter=False,
            on_success=lambda attempt: success_attempts.append(attempt)
        )

        call_count = 0
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("tmp")
            return "ok"

        retry_call(flaky, cfg)
        assert len(success_attempts) == 1
        assert success_attempts[0] == 1  # 0-indexed: succeeded on attempt 1

    def test_custom_retryable_exceptions(self):
        """Only retries on specified exception types."""
        def raise_type_error():
            raise TypeError("wrong type")

        # Only retry ConnectionError — TypeError should bubble immediately
        with pytest.raises(TypeError):
            retry_call(
                raise_type_error,
                RetryConfig(
                    max_attempts=5,
                    base_delay=0.01,
                    jitter=False,
                    retryable_exceptions=(ConnectionError,)
                )
            )


# ─── retry_call_async Tests ───────────────────────────────────────────

class TestRetryCallAsync:
    """Tests for async retry_call."""

    @pytest.mark.asyncio
    async def test_async_success_after_retries(self):
        """Async succeeds after failures."""
        call_count = 0

        async def async_flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("async transient")
            return "async ok"

        result = await retry_call_async(
            async_flaky,
            RetryConfig(max_attempts=5, base_delay=0.01, jitter=False)
        )
        assert result == "async ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_async_exhaustion(self):
        """Async raises after all attempts fail."""
        async def always_fail():
            raise RuntimeError("async boom")

        with pytest.raises(RetryExhaustedError):
            await retry_call_async(
                always_fail,
                RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)
            )


# ─── with_retry Decorator Tests ───────────────────────────────────────

class TestWithRetryDecorator:
    """Tests for the @with_retry decorator."""

    def test_decorator_sync_function(self):
        """Decorator works on sync functions."""
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01, jitter=False)
        def sync_fn():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("tmp")
            return "sync_ok"

        result = sync_fn()
        assert result == "sync_ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_decorator_async_function(self):
        """Decorator works on async functions."""
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01, jitter=False)
        async def async_fn():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("async tmp")
            return "async_ok"

        result = await async_fn()
        assert result == "async_ok"
        assert call_count == 2


# ─── RetryContext Tests ───────────────────────────────────────────────

class TestRetryContext:
    """Tests for RetryContext context manager."""

    def test_no_exception_is_clean_exit(self):
        """Clean exit returns True (no error)."""
        cfg = RetryConfig(max_attempts=3, base_delay=0.01, jitter=False)
        with RetryContext(cfg) as ctx:
            pass  # No exception
        # Context should be usable
        assert ctx.last_error is None

    def test_should_continue(self):
        """should_continue reflects remaining attempts."""
        cfg = RetryConfig(max_attempts=3)
        ctx = RetryContext(cfg)
        assert ctx.should_continue() is True  # 0 < 3
        ctx.attempt = 2
        assert ctx.should_continue() is True  # 2 < 3
        ctx.attempt = 3
        assert ctx.should_continue() is False  # 3 not < 3

"""Unit tests for retry module."""

import pytest
import time
from unittest.mock import Mock, patch

from src.shared.retry import (
    RetryConfig,
    RetryExhaustedError,
    with_retry,
    retry_call,
    RetryContext,
)
from src.shared.errors import is_retryable


class TestRetryConfig:
    """Tests for RetryConfig."""
    
    def test_default_values(self):
        """Test default configuration."""
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
    
    def test_calculate_delay_no_jitter(self):
        """Test delay calculation without jitter."""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            jitter=False
        )
        
        assert config.calculate_delay(0) == 1.0
        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(2) == 4.0
    
    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            jitter=True,
            jitter_max=0.1
        )
        
        delay = config.calculate_delay(0)
        assert delay >= 1.0
        assert delay <= 1.1  # 1.0 + 10% jitter
    
    def test_calculate_delay_respects_max(self):
        """Test delay respects max_delay."""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=10.0,
            max_delay=5.0,
            jitter=False
        )
        
        delay = config.calculate_delay(1)
        assert delay == 5.0  # Capped at max


class TestRetryExhaustedError:
    """Tests for RetryExhaustedError."""
    
    def test_error_creation(self):
        """Test creating exhausted error."""
        cause = ValueError("Original")
        error = RetryExhaustedError(attempts=3, last_error=cause)
        
        assert error.attempts == 3
        assert error.last_error is cause
        assert "3 attempts" in error.message


class TestWithRetryDecorator:
    """Tests for with_retry decorator."""
    
    def test_successful_call(self):
        """Test successful function call."""
        @with_retry(max_attempts=3)
        def success_func():
            return "success"
        
        result = success_func()
        assert result == "success"
    
    def test_retry_on_failure(self):
        """Test retry on failure."""
        call_count = 0
        
        @with_retry(max_attempts=3, base_delay=0.01)
        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Failed")
            return "success"
        
        result = fail_then_succeed()
        assert result == "success"
        assert call_count == 3
    
    def test_exhausted_retries(self):
        """Test exhausted retries raises error."""
        @with_retry(max_attempts=2, base_delay=0.01)
        def always_fail():
            raise ConnectionError("Always fails")
        
        with pytest.raises(RetryExhaustedError) as exc_info:
            always_fail()
        
        assert exc_info.value.attempts == 2
    
    def test_non_retryable_exception(self):
        """Test non-retryable exception is not retried."""
        call_count = 0
        
        @with_retry(max_attempts=3, base_delay=0.01)
        def raise_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")
        
        with pytest.raises(ValueError):
            raise_value_error()
        
        assert call_count == 1  # Not retried
    
    def test_custom_retryable_exceptions(self):
        """Test custom retryable exceptions."""
        call_count = 0
        
        @with_retry(
            max_attempts=2,
            base_delay=0.01,
            retryable_exceptions=(ValueError,)
        )
        def raise_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Retryable")
        
        with pytest.raises(RetryExhaustedError):
            raise_value_error()
        
        assert call_count == 2  # Retried


class TestRetryCall:
    """Tests for retry_call function."""
    
    def test_successful_call(self):
        """Test successful call."""
        def success():
            return "done"
        
        config = RetryConfig(max_attempts=3)
        result = retry_call(success, config)
        
        assert result == "done"
    
    def test_retry_then_success(self):
        """Test retry then success."""
        call_count = 0
        
        def sometimes_fail():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Fail")
            return "success"
        
        config = RetryConfig(max_attempts=3, base_delay=0.01)
        result = retry_call(sometimes_fail, config)
        
        assert result == "success"
        assert call_count == 2
    
    def test_all_attempts_fail(self):
        """Test when all attempts fail."""
        def always_fail():
            raise ConnectionError("Fail")
        
        config = RetryConfig(max_attempts=2, base_delay=0.01)
        
        with pytest.raises(RetryExhaustedError):
            retry_call(always_fail, config)
    
    def test_callback_on_retry(self):
        """Test on_retry callback."""
        retry_calls = []
        
        def on_retry(error, attempt):
            retry_calls.append((str(error), attempt))
        
        def fail_twice():
            raise ConnectionError("Fail")
        
        config = RetryConfig(
            max_attempts=2,
            base_delay=0.01,
            on_retry=on_retry
        )
        
        with pytest.raises(RetryExhaustedError):
            retry_call(fail_twice, config)
        
        assert len(retry_calls) == 1


class TestRetryContext:
    """Tests for RetryContext."""
    
    def test_successful_context(self):
        """Test successful context usage."""
        config = RetryConfig(max_attempts=3)
        
        with RetryContext(config) as ctx:
            pass  # Success
        
        assert ctx.attempt == 0
    
    def test_context_retries(self):
        """Test context with retries."""
        config = RetryConfig(max_attempts=3, base_delay=0.01)
        attempt = 0
        
        for _ in range(3):
            try:
                with RetryContext(config) as ctx:
                    attempt += 1
                    if attempt < 3:
                        raise ConnectionError("Fail")
                break
            except RetryExhaustedError:
                break
        
        assert attempt == 3
    
    def test_should_continue(self):
        """Test should_continue method."""
        config = RetryConfig(max_attempts=3)
        ctx = RetryContext(config)
        
        assert ctx.should_continue() is True
        ctx.attempt = 3
        assert ctx.should_continue() is False

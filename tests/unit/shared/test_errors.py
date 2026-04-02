"""Unit tests for error handling module."""

import pytest
from unittest.mock import Mock

from src.shared.errors import (
    ErrorCode,
    DsearchError,
    ValidationError,
    ConfigError,
    TimeoutError,
    ProviderError,
    ProviderUnavailableError,
    ProviderRateLimitError,
    ProviderAuthError,
    ProviderQuotaError,
    SearchError,
    NoResultsError,
    NetworkError,
    NetworkTimeoutError,
    wrap_exception,
    is_retryable,
)


class TestErrorCode:
    """Tests for ErrorCode enum."""
    
    def test_error_codes_exist(self):
        """Test that error codes are defined."""
        assert ErrorCode.UNKNOWN.value == "E000"
        assert ErrorCode.VALIDATION.value == "E001"
        assert ErrorCode.PROVIDER_ERROR.value == "E100"
        assert ErrorCode.SEARCH_ERROR.value == "E200"


class TestDsearchError:
    """Tests for base DsearchError."""
    
    def test_basic_error(self):
        """Test creating basic error."""
        error = DsearchError("Something went wrong")
        
        assert error.message == "Something went wrong"
        assert error.code == ErrorCode.UNKNOWN
        assert error.retryable is False
    
    def test_error_with_code(self):
        """Test error with specific code."""
        error = DsearchError(
            "Validation failed",
            code=ErrorCode.VALIDATION,
            retryable=False
        )
        
        assert error.code == ErrorCode.VALIDATION
    
    def test_error_with_context(self):
        """Test error with context."""
        error = DsearchError(
            "Failed",
            context={"key": "value", "num": 123}
        )
        
        assert error.context["key"] == "value"
    
    def test_error_with_cause(self):
        """Test error with cause."""
        cause = ValueError("Original error")
        error = DsearchError("Wrapped", cause=cause)
        
        assert error.cause is cause
    
    def test_error_str(self):
        """Test string representation."""
        error = DsearchError("Test error", code=ErrorCode.UNKNOWN)
        str_repr = str(error)
        
        assert "[E000]" in str_repr
        assert "Test error" in str_repr
    
    def test_error_str_with_context(self):
        """Test string with context."""
        error = DsearchError(
            "Test",
            context={"info": "extra"},
            retryable=True,
            retry_after=5.0
        )
        str_repr = str(error)
        
        assert "Context:" in str_repr
        assert "Retryable:" in str_repr
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        error = DsearchError(
            "Test",
            code=ErrorCode.VALIDATION,
            context={"field": "name"},
            retryable=False
        )
        
        data = error.to_dict()
        assert data["error"] is True
        assert data["code"] == "E001"
        assert data["message"] == "Test"
        assert data["context"]["field"] == "name"


class TestValidationError:
    """Tests for ValidationError."""
    
    def test_basic_validation(self):
        """Test basic validation error."""
        error = ValidationError("Invalid input")
        
        assert error.code == ErrorCode.VALIDATION
        assert error.retryable is False
    
    def test_validation_with_field(self):
        """Test validation with field info."""
        error = ValidationError(
            "Invalid",
            field="username",
            value="bad!@#"
        )
        
        assert error.field == "username"
        assert error.value == "bad!@#"
        assert error.context["field"] == "username"


class TestConfigError:
    """Tests for ConfigError."""
    
    def test_basic_config_error(self):
        """Test basic config error."""
        error = ConfigError("Missing config")
        
        assert error.code == ErrorCode.CONFIGURATION
        assert error.config_key is None
    
    def test_config_error_with_key(self):
        """Test config error with key."""
        error = ConfigError("Invalid", config_key="api.timeout")
        
        assert error.config_key == "api.timeout"
        assert error.context["config_key"] == "api.timeout"


class TestTimeoutError:
    """Tests for TimeoutError."""
    
    def test_timeout_error(self):
        """Test timeout error."""
        error = TimeoutError("Operation timed out", timeout_seconds=30.0)
        
        assert error.code == ErrorCode.TIMEOUT
        assert error.retryable is True
        assert error.timeout_seconds == 30.0


class TestProviderErrors:
    """Tests for provider error hierarchy."""
    
    def test_provider_error(self):
        """Test base provider error."""
        error = ProviderError("Failed", provider="gemini")
        
        assert error.provider == "gemini"
        assert error.context["provider"] == "gemini"
    
    def test_provider_unavailable(self):
        """Test unavailable error."""
        error = ProviderUnavailableError("gemini")
        
        assert error.code == ErrorCode.PROVIDER_UNAVAILABLE
        assert error.retryable is True
        assert error.retry_after == 30.0
    
    def test_provider_rate_limit(self):
        """Test rate limit error."""
        error = ProviderRateLimitError("gemini", retry_after=60.0)
        
        assert error.code == ErrorCode.PROVIDER_RATE_LIMITED
        assert error.retry_after == 60.0
        assert "retry after 60.0s" in error.message
    
    def test_provider_rate_limit_no_retry_after(self):
        """Test rate limit without retry_after."""
        error = ProviderRateLimitError("gemini")
        
        assert error.retry_after is None
        assert "retry after" not in error.message
    
    def test_provider_auth_error(self):
        """Test auth error."""
        error = ProviderAuthError("gemini")
        
        assert error.code == ErrorCode.PROVIDER_AUTH_ERROR
        assert error.retryable is False
    
    def test_provider_quota_error(self):
        """Test quota error."""
        error = ProviderQuotaError("gemini")
        
        assert error.code == ErrorCode.PROVIDER_QUOTA_EXCEEDED
        assert error.retryable is False


class TestSearchErrors:
    """Tests for search error hierarchy."""
    
    def test_search_error(self):
        """Test base search error."""
        error = SearchError("Search failed", query="test query")
        
        assert error.query == "test query"
        assert "test query" in error.context["query"]
    
    def test_no_results_error(self):
        """Test no results error."""
        error = NoResultsError("python programming")
        
        assert error.code == ErrorCode.SEARCH_NO_RESULTS
        assert "python programming" in error.message
        assert error.retryable is False


class TestNetworkErrors:
    """Tests for network error hierarchy."""
    
    def test_network_error(self):
        """Test base network error."""
        error = NetworkError("Connection failed", url="https://api.example.com")
        
        assert error.url == "https://api.example.com"
        assert error.retryable is True
    
    def test_network_timeout(self):
        """Test network timeout error."""
        error = NetworkTimeoutError("https://api.example.com", timeout=30.0)
        
        assert error.code == ErrorCode.NETWORK_TIMEOUT
        assert error.timeout == 30.0
        assert error.retry_after == 5.0


class TestWrapException:
    """Tests for wrap_exception function."""
    
    def test_wrap_dsearch_error(self):
        """Test wrapping already wrapped error returns same."""
        original = ValidationError("Test")
        wrapped = wrap_exception(original)
        
        assert wrapped is original
    
    def test_wrap_regular_exception(self):
        """Test wrapping regular exception."""
        original = ValueError("Something")
        wrapped = wrap_exception(original, message="Custom message")
        
        assert isinstance(wrapped, DsearchError)
        assert wrapped.message == "Custom message"
        assert wrapped.cause is original


class TestIsRetryable:
    """Tests for is_retryable function."""
    
    def test_retryable_dsearch_error(self):
        """Test retryable DsearchError."""
        error = TimeoutError("Timed out")
        assert is_retryable(error) is True
    
    def test_non_retryable_dsearch_error(self):
        """Test non-retryable DsearchError."""
        error = ValidationError("Invalid")
        assert is_retryable(error) is False
    
    def test_regular_exception(self):
        """Test regular exception."""
        error = ValueError("Something")
        # Regular exceptions are not retryable by default
        assert is_retryable(error) is False

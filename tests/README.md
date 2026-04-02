# Open Dsearch Test Suite

Comprehensive testing infrastructure for the Open Dsearch multi-provider research pipeline.

## Quick Start

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
make test

# Or using pytest directly
pytest tests/ -v
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                 # Shared fixtures and configuration
├── README.md                   # This file
├── unit/                       # Unit tests (fast, isolated)
│   ├── test_config.py          # Configuration tests
│   ├── test_research.py        # Research module tests
│   ├── test_research_python.py # Python fallback tests
│   ├── test_api_server.py      # API server tests
│   └── test_web_fetch.py       # Web fetcher tests
├── integration/                # Integration tests (with mocks)
│   ├── test_search_providers.py # Provider integration tests
│   └── test_end_to_end.py      # End-to-end tests
├── mocks/                      # Mock data and factories
│   ├── factories.py            # Test data factories
│   └── responses/              # Cached API responses
│       ├── gemini_search.json
│       ├── minimax_search.json
│       ├── kimi_search.json
│       └── xai_search.json
├── benchmarks/                 # Performance benchmarks
│   └── test_performance.py
└── fixtures/                   # Sample test data
    ├── sample_queries.txt
    └── sample_urls.txt
```

## Running Tests

### Using Make (Recommended)

```bash
# Run all tests
make test

# Unit tests only
make test-unit

# Integration tests (no live APIs)
make test-integration

# Live API tests (requires API keys)
make test-live

# Performance benchmarks
make test-benchmark

# Generate coverage report
make coverage

# Run security scans
make security

# Code quality checks
make lint
make format
```

### Using pytest Directly

```bash
# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/unit -v

# Run integration tests
pytest tests/integration -v -m "not live_api"

# Run with coverage
pytest tests/unit -v --cov=scripts --cov-report=html

# Run specific test file
pytest tests/unit/test_config.py -v

# Run specific test
pytest tests/unit/test_config.py::TestConfigValidation::test_load_config_valid_toml -v

# Run with markers
pytest tests/ -v -m "unit"
pytest tests/ -v -m "integration"
pytest tests/ -v -m "slow"
pytest tests/ -v -m "benchmark"
```

### Using the Test Runner Script

```bash
# Run unit tests
python scripts/run_tests.py unit

# Run integration tests
python scripts/run_tests.py integration

# Run all tests
python scripts/run_tests.py all

# Run live API tests
python scripts/run_tests.py live

# Run benchmarks
python scripts/run_tests.py benchmark
```

## Test Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.unit` | Fast unit tests (no external deps) |
| `@pytest.mark.integration` | Integration tests (mocked APIs) |
| `@pytest.mark.slow` | Tests taking >5 seconds |
| `@pytest.mark.benchmark` | Performance benchmarks |
| `@pytest.mark.live_api` | Tests requiring real API keys |

## Coverage Targets

| Module | Target |
|--------|--------|
| config.py | 90% |
| research.py | 80% |
| research_python.py | 75% |
| api_server.py | 80% |
| web_fetch.py | 70% |
| **Overall** | **70%** |

## Mock Data

### API Response Mocks

Located in `tests/mocks/responses/`:

- `gemini_search.json` - Gemini API responses
- `minimax_search.json` - MiniMax API responses
- `kimi_search.json` - Kimi API responses
- `xai_search.json` - xAI API responses

### Factories

Use factories in `tests/mocks/factories.py` to create test data:

```python
from tests.mocks.factories import SearchResultFactory, APIResponseFactory

# Create search results
results = SearchResultFactory.create_batch(5, source="gemini")

# Create API responses
gemini_response = APIResponseFactory.gemini_search(results_count=3)
```

## Fixtures

Common fixtures available in `conftest.py`:

| Fixture | Description |
|---------|-------------|
| `project_root` | Path to project root |
| `scripts_dir` | Path to scripts directory |
| `mock_api_keys` | Mock API keys in environment |
| `temp_config_dir` | Temporary config directory |
| `gemini_search_response` | Mock Gemini response |
| `minimax_search_response` | Mock MiniMax response |
| `kimi_search_response` | Mock Kimi response |
| `sample_search_results` | Sample result data |
| `client` | FastAPI test client |

## Live API Tests

Live API tests require actual API keys:

```bash
# Set API keys
export GEMINI_API_KEY="your-key"
export MINIMAX_API_KEY="your-key"
export KIMI_API_KEY="your-key"
export XAI_API_KEY="your-key"

# Run live tests
make test-live
# or
LIVE_API_TESTS=1 pytest tests/integration -v -m "live_api"
```

## CI/CD Integration

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main`

See `.github/workflows/` for workflow definitions.

## Writing Tests

### Unit Test Example

```python
import pytest
from unittest.mock import patch

class TestMyFeature:
    """Tests for my feature."""
    
    def test_something_works(self):
        """Test that something works."""
        result = my_function()
        assert result == expected
    
    @patch("module.external_call")
    def test_with_mock(self, mock_call):
        """Test with mocked dependency."""
        mock_call.return_value = "mocked"
        result = my_function()
        assert result == "mocked"
```

### Integration Test Example

```python
import responses

class TestAPIIntegration:
    """Integration tests with mocked HTTP."""
    
    @responses.activate
    def test_api_call(self):
        """Test API with mocked response."""
        responses.add(
            responses.GET,
            "https://api.example.com/data",
            json={"key": "value"},
            status=200
        )
        
        result = make_api_call()
        assert result["key"] == "value"
```

## Troubleshooting

### Import Errors

If you see import errors, ensure the scripts directory is in Python path:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/scripts"
```

### Coverage Not Working

Make sure you're running from project root:

```bash
cd /path/to/open-dsearch
pytest tests/ --cov=scripts
```

### Tests Hanging

Some tests may hang if rate limiters are active. Tests should patch rate limiters:

```python
@pytest.fixture(autouse=True)
def disable_rate_limiter(monkeypatch):
    """Disable rate limiting for tests."""
    from research_python import RateLimiter
    monkeypatch.setattr(
        "research_python._rate_limiters",
        {"gemini": RateLimiter(rate=1000, burst=100)}
    )
```

## Contributing

When adding tests:

1. Place unit tests in `tests/unit/`
2. Place integration tests in `tests/integration/`
3. Add fixtures to `conftest.py` if reusable
4. Use markers appropriately (`@pytest.mark.unit`, etc.)
5. Ensure tests pass with `make test`
6. Maintain or improve coverage

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-mock documentation](https://pytest-mock.readthedocs.io/)
- [responses documentation](https://github.com/getsentry/responses)
- [pytest-benchmark documentation](https://pytest-benchmark.readthedocs.io/)

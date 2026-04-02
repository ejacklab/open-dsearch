"""pytest configuration and shared fixtures for Open Dsearch."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Add scripts directory to path (for existing code)
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Add src directory to path (for future code)
SRC_DIR = Path(__file__).parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (may require external services)")
    config.addinivalue_line("markers", "slow: Tests taking >5 seconds")
    config.addinivalue_line("markers", "benchmark: Performance benchmarks")
    config.addinivalue_line("markers", "live_api: Tests requiring live API keys")


# ============================================================================
# Path Fixtures
# ============================================================================

@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def scripts_dir(project_root) -> Path:
    """Return the scripts directory."""
    return project_root / "scripts"


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def mocks_dir() -> Path:
    """Return the mocks directory."""
    return Path(__file__).parent / "mocks"


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory."""
    return tmp_path


# ============================================================================
# Environment Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def clean_env():
    """Clean environment variables before each test."""
    # Store original env vars
    original_env = dict(os.environ)
    
    # Remove API keys from environment
    keys_to_remove = [
        "GEMINI_API_KEY",
        "MINIMAX_API_KEY",
        "KIMI_API_KEY",
        "XAI_API_KEY",
        "TAVILY_API_KEY",
        "EXA_API_KEY",
        "BRAVE_API_KEY",
    ]
    for key in keys_to_remove:
        os.environ.pop(key, None)
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_api_keys(monkeypatch):
    """Set mock API keys in environment."""
    keys = {
        "GEMINI_API_KEY": "test-gemini-key-12345",
        "MINIMAX_API_KEY": "test-minimax-key-67890",
        "KIMI_API_KEY": "test-kimi-key-abcde",
        "XAI_API_KEY": "test-xai-key-xyz789",
    }
    for key, value in keys.items():
        monkeypatch.setenv(key, value)
    return keys


@pytest.fixture
def temp_config_dir(tmp_path, monkeypatch):
    """Create a temporary config directory."""
    config_dir = tmp_path / ".config" / "dsearch"
    config_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(tmp_path))
    return config_dir


# ============================================================================
# Mock Response Fixtures
# ============================================================================

@pytest.fixture
def gemini_search_response() -> Dict[str, Any]:
    """Return a mock Gemini API search response."""
    return {
        "candidates": [{
            "content": {"role": "model", "parts": [{"text": "Search results"}]},
            "groundingMetadata": {
                "groundingChunks": [
                    {"web": {"uri": "https://example.com/doc1", "title": "Documentation Page 1"}},
                    {"web": {"uri": "https://github.com/user/repo", "title": "GitHub Repository"}},
                    {"web": {"uri": "https://docs.python.org/3", "title": "Python Documentation"}},
                ]
            }
        }]
    }


@pytest.fixture
def minimax_search_response() -> Dict[str, Any]:
    """Return a mock MiniMax API search response."""
    return {
        "organic": [
            {"title": "Python Tutorial", "link": "https://docs.python.org/tutorial", "snippet": "Learn Python"},
            {"title": "Rust Book", "link": "https://doc.rust-lang.org/book", "snippet": "The Rust Programming Language"},
            {"title": "FastAPI Docs", "link": "https://fastapi.tiangolo.com", "snippet": "Modern web framework"},
        ]
    }


@pytest.fixture
def kimi_search_response() -> Dict[str, Any]:
    """Return a mock Kimi API search response."""
    return {
        "choices": [{
            "message": {
                "content": """
Here are the search results:

[Python Official Documentation](https://docs.python.org/3)
A comprehensive guide to Python programming.

[Rust Programming Language](https://www.rust-lang.org)
The official Rust website with documentation.

[FastAPI Documentation](https://fastapi.tiangolo.com)
Modern, fast web framework for building APIs.
"""
            }
        }]
    }


@pytest.fixture
def xai_search_response() -> Dict[str, Any]:
    """Return a mock xAI API search response."""
    return {
        "choices": [{
            "message": {
                "content": "Search results with citations",
                "citations": [
                    {"url": "https://example.com/1", "title": "Result 1"},
                    {"url": "https://example.com/2", "title": "Result 2"},
                ]
            }
        }]
    }


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_search_results() -> List[Dict[str, Any]]:
    """Return sample search results for testing."""
    return [
        {
            "title": "Python Tutorial",
            "url": "https://docs.python.org/3/tutorial",
            "snippet": "Python tutorial for beginners",
            "source": "gemini",
            "score": 0.95
        },
        {
            "title": "Rust Book",
            "url": "https://doc.rust-lang.org/book",
            "snippet": "The Rust Programming Language",
            "source": "minimax",
            "score": 0.90
        },
        {
            "title": "FastAPI Docs",
            "url": "https://fastapi.tiangolo.com",
            "snippet": "Modern, fast web framework",
            "source": "kimi",
            "score": 0.85
        },
    ]


@pytest.fixture
def sample_topics() -> List[str]:
    """Return sample research topics for testing."""
    return [
        "Python async programming",
        "Rust memory safety",
        "FastAPI best practices",
        "Machine learning with PyTorch",
        "Docker container optimization",
    ]


# ============================================================================
# FastAPI Test Client
# ============================================================================

@pytest.fixture
def api_client():
    """Create a FastAPI test client."""
    try:
        from fastapi.testclient import TestClient
        import api_server
        return TestClient(api_server.app)
    except ImportError:
        pytest.skip("FastAPI not installed")
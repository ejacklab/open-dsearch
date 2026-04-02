"""Tests for web_fetch.py module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import web_fetch as wf


class TestRustBinaryDetection:
    """Tests for Rust binary detection."""
    
    def test_get_rust_binary_exists(self, tmp_path, monkeypatch):
        """Should return path when binary exists."""
        monkeypatch.setattr(Path, "exists", lambda self: True)
        result = wf.get_rust_binary()
        assert result is not None
        assert "web_fetch" in str(result)
    
    def test_get_rust_binary_missing_returns_none(self, monkeypatch):
        """Should return None when binary not found."""
        monkeypatch.setattr(Path, "exists", lambda self: False)
        result = wf.get_rust_binary()
        assert result is None


class TestFetchRust:
    """Tests for Rust fetch backend."""
    
    @patch("web_fetch.get_rust_binary")
    @patch("subprocess.run")
    def test_fetch_rust_success(self, mock_run, mock_binary):
        """Should fetch successfully with Rust."""
        mock_binary.return_value = MagicMock(exists=True)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="# Markdown Content",
            stderr=""
        )
        
        result = wf.fetch_rust("https://example.com", max_kb=100)
        assert result is not None
        assert result["success"] is True
        assert result["content"] == "# Markdown Content"
    
    @patch("web_fetch.get_rust_binary")
    def test_fetch_rust_binary_not_found(self, mock_binary):
        """Should return None when binary not found."""
        mock_binary.return_value = None
        
        result = wf.fetch_rust("https://example.com")
        assert result is None
    
    @patch("web_fetch.get_rust_binary")
    @patch("subprocess.run")
    def test_fetch_rust_failure(self, mock_run, mock_binary):
        """Should handle Rust binary failure."""
        mock_binary.return_value = MagicMock(exists=True)
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: fetch failed"
        )
        
        result = wf.fetch_rust("https://example.com")
        assert result is not None
        assert result["success"] is False
        assert "error" in result


class TestFetchPython:
    """Tests for Python fetch backend."""
    
    @patch("web_fetch.httpx.get")
    @patch("web_fetch.markdownify")
    def test_fetch_python_success(self, mock_md, mock_get):
        """Should fetch and convert with Python."""
        mock_response = MagicMock()
        mock_response.text = "<html><body><h1>Test</h1></body></html>"
        mock_get.return_value = mock_response
        mock_md.return_value = "# Test"
        
        result = wf.fetch_python("https://example.com", max_kb=100)
        assert result is not None
        assert result["content"] == "# Test"
    
    def test_fetch_python_import_error(self):
        """Should return None when dependencies missing."""
        with patch.dict("sys.modules", {"httpx": None}):
            result = wf.fetch_python("https://example.com")
            assert result is None


class TestFetch:
    """Tests for main fetch function."""
    
    @patch("web_fetch.fetch_rust")
    @patch("web_fetch.fetch_python")
    def test_fetch_prefers_rust(self, mock_python, mock_rust):
        """Should prefer Rust backend when available."""
        mock_rust.return_value = {"success": True, "content": "Rust result"}
        
        result = wf.fetch("https://example.com", prefer_rust=True)
        
        assert result["backend"] == "rust"
        assert result["content"] == "Rust result"
        mock_python.assert_not_called()
    
    @patch("web_fetch.fetch_rust")
    @patch("web_fetch.fetch_python")
    def test_fetch_fallback_to_python(self, mock_python, mock_rust):
        """Should fallback to Python when Rust fails."""
        mock_rust.return_value = {"success": False, "error": "Failed"}
        mock_python.return_value = {"content": "Python result"}
        
        result = wf.fetch("https://example.com", prefer_rust=True)
        
        assert result["backend"] == "python"
        assert result["content"] == "Python result"
    
    @patch("web_fetch.fetch_rust")
    @patch("web_fetch.fetch_python")
    def test_fetch_force_python(self, mock_python, mock_rust):
        """Should use Python when forced."""
        mock_python.return_value = {"content": "Python result"}
        
        result = wf.fetch("https://example.com", prefer_rust=False)
        
        assert result["backend"] == "python"
        mock_rust.assert_not_called()
    
    @patch("web_fetch.fetch_rust")
    @patch("web_fetch.fetch_python")
    def test_fetch_both_fail(self, mock_python, mock_rust):
        """Should return None when both backends fail."""
        mock_rust.return_value = None
        mock_python.return_value = None
        
        result = wf.fetch("https://example.com")
        
        assert result is None


class TestFetchMaxKb:
    """Tests for max_kb parameter."""
    
    @patch("web_fetch.get_rust_binary")
    @patch("subprocess.run")
    def test_fetch_rust_respects_max_kb(self, mock_run, mock_binary):
        """Should pass max_kb to Rust binary."""
        mock_binary.return_value = MagicMock(exists=True)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="content",
            stderr=""
        )
        
        wf.fetch_rust("https://example.com", max_kb=50)
        
        call_args = mock_run.call_args[0][0]
        assert "--max-kb" in call_args
        assert "50" in call_args

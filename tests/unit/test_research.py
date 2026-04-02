"""Tests for research.py module."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import research


class TestTopicValidation:
    """Tests for topic input validation."""
    
    @pytest.mark.parametrize("topic,expected_valid,expected_error", [
        ("valid topic", True, ""),
        ("", False, "Topic cannot be empty"),
        ("   ", False, "Topic cannot be empty"),
        ("x" * 501, False, "Topic too long (max 500 characters)"),
        ("x" * 500, True, ""),
        ("Python async programming", True, ""),
        ("a", True, ""),
    ])
    def test_validate_topic(self, topic, expected_valid, expected_error):
        is_valid, error = research.validate_topic(topic)
        assert is_valid == expected_valid
        if expected_error:
            assert expected_error in error


class TestRustBinaryDetection:
    """Tests for Rust binary detection."""
    
    def test_get_rust_binary_exists(self, tmp_path, monkeypatch):
        """Should return path when binary exists."""
        script_dir = tmp_path / "scripts"
        binary = script_dir / "rust" / "target" / "release" / "research"
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_text("fake binary")
        
        monkeypatch.setattr(Path, "exists", lambda self: True)
        result = research.get_rust_binary()
        assert result is not None
        assert "research" in str(result)
    
    def test_get_rust_binary_missing_returns_none(self, monkeypatch):
        """Should return None when binary not found."""
        monkeypatch.setattr(Path, "exists", lambda self: False)
        result = research.get_rust_binary()
        assert result is None


class TestResearchExecution:
    """Tests for research function execution paths."""
    
    def test_research_with_invalid_topic_returns_none(self):
        """Should return None for invalid topic."""
        result = research.research("")
        assert result is None
    
    def test_research_invalid_top_parameter(self):
        """Should return None for invalid top parameter."""
        result = research.research("topic", top=0)
        assert result is None
    
    def test_research_top_too_high(self):
        """Should return None when top > 50."""
        result = research.research("topic", top=51)
        assert result is None
    
    def test_research_invalid_queries_parameter(self):
        """Should return None for invalid queries parameter."""
        result = research.research("topic", queries=0)
        assert result is None
    
    def test_research_queries_too_high(self):
        """Should return None when queries > 20."""
        result = research.research("topic", queries=21)
        assert result is None
    
    @patch("research.get_rust_binary")
    @patch("subprocess.run")
    def test_research_rust_success(self, mock_run, mock_binary):
        """Should execute Rust binary successfully."""
        mock_binary.return_value = MagicMock(exists=True)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"results": []}',
            stderr=""
        )
        
        result = research.research("test topic")
        assert result is not None
        assert result["success"] is True
    
    @patch("research.get_rust_binary")
    @patch("subprocess.run")
    def test_research_rust_failure_fallback(self, mock_run, mock_binary):
        """Should handle Rust binary failure gracefully."""
        mock_binary.return_value = MagicMock(exists=True)
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: something failed"
        )
        
        result = research.research("test topic")
        assert result is None


class TestResearchModes:
    """Tests for different research output modes."""
    
    @patch("research.get_rust_binary")
    @patch("subprocess.run")
    def test_research_vectors_mode(self, mock_run, mock_binary):
        """Test vectors output mode."""
        mock_binary.return_value = MagicMock(exists=True)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"results": []}',
            stderr=""
        )
        
        result = research.research("topic", mode="vectors")
        assert result is not None
        assert result["success"] is True
    
    @patch("research.get_rust_binary")
    @patch("subprocess.run")
    def test_research_json_mode(self, mock_run, mock_binary):
        """Test JSON output mode."""
        mock_binary.return_value = MagicMock(exists=True)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"results": []}',
            stderr=""
        )
        
        result = research.research("topic", mode="json")
        assert result is not None
    
    @patch("research.get_rust_binary")
    @patch("subprocess.run")
    def test_research_md_mode(self, mock_run, mock_binary):
        """Test markdown output mode."""
        mock_binary.return_value = MagicMock(exists=True)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="# Results",
            stderr=""
        )
        
        result = research.research("topic", mode="md")
        assert result is not None


class TestResearchWithUrls:
    """Tests for research with direct URLs."""
    
    @patch("research.get_rust_binary")
    @patch("subprocess.run")
    def test_research_with_urls(self, mock_run, mock_binary):
        """Should handle direct URLs."""
        mock_binary.return_value = MagicMock(exists=True)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"results": []}',
            stderr=""
        )
        
        urls = ["https://example.com", "https://test.com"]
        result = research.research("topic", urls=urls)
        assert result is not None
        
        # Verify URLs were passed to subprocess
        call_args = mock_run.call_args[0][0]
        for url in urls:
            assert "--urls" in call_args
            assert url in call_args


class TestResearchTimeout:
    """Tests for research timeout handling."""
    
    @patch("research.get_rust_binary")
    @patch("subprocess.run")
    def test_research_custom_timeout(self, mock_run, mock_binary):
        """Should use custom timeout."""
        mock_binary.return_value = MagicMock(exists=True)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"results": []}',
            stderr=""
        )
        
        result = research.research("topic", timeout=600)
        assert result is not None
        
        # Verify timeout was passed
        call_args = mock_run.call_args[0][0]
        assert "--timeout" in call_args

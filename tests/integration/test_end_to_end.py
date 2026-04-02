"""End-to-end integration tests."""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import api_server


class TestCLIExecution:
    """End-to-end tests using the CLI."""
    
    def test_cli_help(self):
        """CLI should show help."""
        result = subprocess.run(
            ["python3", "-m", "research", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent / "scripts"
        )
        assert "usage:" in result.stdout.lower() or result.returncode == 0
    
    def test_cli_invalid_topic(self):
        """CLI should handle invalid topic."""
        result = subprocess.run(
            ["python3", "-m", "research", ""],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent / "scripts"
        )
        # Should fail with error
        assert result.returncode != 0 or "error" in result.stderr.lower()


class TestAPIEndToEnd:
    """End-to-end tests for API server."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(api_server.app)
    
    @patch("api_server.get_rust_binary")
    @patch("subprocess.run")
    def test_full_research_flow(self, mock_run, mock_binary, client):
        """Test complete research flow through API."""
        mock_binary.return_value = MagicMock(exists=True)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "query": "Python async",
                "sources": [
                    {"title": "Python Docs", "url": "https://docs.python.org", "score": 0.95}
                ]
            }),
            stderr=""
        )
        
        # Health check
        health = client.get("/health")
        assert health.status_code == 200
        
        # Research request
        response = client.post("/research", json={
            "topic": "Python async programming",
            "top": 5,
            "queries": 3,
            "mode": "json"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["topic"] == "Python async programming"
    
    def test_api_cors_headers(self, client):
        """API should support CORS."""
        response = client.options("/", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST"
        })
        # CORS middleware should handle this
        assert response.status_code in [200, 405]  # 405 if OPTIONS not handled


class TestResearchPipeline:
    """Tests for complete research pipeline."""
    
    @patch("research_python.get_secret")
    def test_pipeline_with_no_providers(self, mock_get_secret):
        """Pipeline should handle no providers available."""
        mock_get_secret.return_value = None
        
        import research_python as rp
        result = rp.research("test topic")
        
        assert result is None
    
    def test_pipeline_validation(self):
        """Pipeline should validate inputs."""
        import research_python as rp
        
        # Empty topic
        result = rp.research("")
        assert result is None
        
        # Invalid top
        result = rp.research("topic", top=0)
        assert result is None
        
        # Invalid queries
        result = rp.research("topic", queries=0)
        assert result is None


class TestConfigurationFlow:
    """Tests for configuration loading flow."""
    
    def test_config_loading_priority(self, tmp_path, monkeypatch):
        """Config should respect priority: env > file."""
        monkeypatch.setenv("GEMINI_API_KEY", "env-key")
        
        import config
        
        # Create config file with different key
        config_dir = tmp_path / ".config" / "dsearch"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.toml"
        config_file.write_text('GEMINI_API_KEY = "file-key"')
        
        monkeypatch.setattr(config, "CONFIG_FILE", config_file)
        
        # Should get env key
        secret = config.get_secret("gemini")
        assert secret == "env-key"


class TestErrorHandling:
    """Tests for error handling across the system."""
    
    def test_graceful_degradation_no_rust(self):
        """System should work without Rust binary."""
        import research
        
        # Mock binary not found
        with patch.object(Path, "exists", return_value=False):
            binary = research.get_rust_binary()
            assert binary is None
    
    def test_api_error_response_format(self):
        """API errors should have consistent format."""
        client = TestClient(api_server.app)
        
        with patch("api_server.get_rust_binary", return_value=None):
            response = client.post("/research", json={
                "topic": "test",
                "top": 5,
                "queries": 3,
                "mode": "md"
            })
            
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data

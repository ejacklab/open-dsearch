"""Tests for api_server.py module."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import api_server as api


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(api.app)


class TestRootEndpoint:
    """Tests for root endpoint."""
    
    def test_root_returns_api_info(self, client):
        """Root should return API information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Open Dsearch API"
        assert "version" in data
        assert "endpoints" in data


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_returns_status(self, client):
        """Health endpoint should return status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "rust_binary" in data
        assert "python_version" in data
    
    def test_health_status_values(self, client):
        """Health status should be valid."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] in ["healthy", "binary_not_found"]
        assert isinstance(data["rust_binary"], bool)


class TestResearchEndpoint:
    """Tests for research endpoint."""
    
    @patch("api_server.get_rust_binary")
    def test_research_binary_not_found(self, mock_binary, client):
        """Should return 500 when Rust binary not found."""
        mock_binary.return_value = None
        
        response = client.post("/research", json={
            "topic": "test topic",
            "top": 5,
            "queries": 3,
            "mode": "md"
        })
        
        assert response.status_code == 500
        assert "binary not found" in response.json()["detail"].lower()
    
    @patch("api_server.get_rust_binary")
    @patch("subprocess.run")
    def test_research_success(self, mock_run, mock_binary, client):
        """Should execute research successfully."""
        mock_binary.return_value = MagicMock(exists=True)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="# Research Results",
            stderr=""
        )
        
        response = client.post("/research", json={
            "topic": "Python programming",
            "top": 5,
            "queries": 3,
            "mode": "md"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["topic"] == "Python programming"
        assert data["mode"] == "md"
        assert "time_seconds" in data
    
    @patch("api_server.get_rust_binary")
    @patch("subprocess.run")
    def test_research_rust_failure(self, mock_run, mock_binary, client):
        """Should handle Rust binary failure."""
        mock_binary.return_value = MagicMock(exists=True)
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: something went wrong"
        )
        
        response = client.post("/research", json={
            "topic": "test topic",
            "top": 5,
            "queries": 3,
            "mode": "md"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @patch("api_server.get_rust_binary")
    @patch("subprocess.run")
    def test_research_timeout(self, mock_run, mock_binary, client):
        """Should handle timeout."""
        mock_binary.return_value = MagicMock(exists=True)
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)
        
        response = client.post("/research", json={
            "topic": "test topic",
            "top": 5,
            "queries": 3,
            "mode": "md",
            "timeout": 30
        })
        
        assert response.status_code == 408
        assert "timed out" in response.json()["detail"].lower()


class TestResearchSyncEndpoint:
    """Tests for sync research endpoint."""
    
    @patch("api_server.get_rust_binary")
    @patch("subprocess.run")
    def test_research_sync_get(self, mock_run, mock_binary, client):
        """Should accept GET requests for sync endpoint."""
        mock_binary.return_value = MagicMock(exists=True)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="results",
            stderr=""
        )
        
        response = client.get("/research/sync?topic=test&top=5&mode=md")
        assert response.status_code == 200


class TestRequestValidation:
    """Tests for request validation."""
    
    def test_research_request_valid(self):
        """Should accept valid request."""
        request = api.ResearchRequest(
            topic="test topic",
            top=5,
            queries=3,
            mode="md"
        )
        assert request.topic == "test topic"
        assert request.top == 5
    
    def test_research_request_defaults(self):
        """Should have correct defaults."""
        request = api.ResearchRequest(topic="test")
        assert request.top == 5
        assert request.queries == 5
        assert request.mode == "md"
        assert request.timeout == 300


class TestResponseModels:
    """Tests for response models."""
    
    def test_research_response_success(self):
        """Should create success response."""
        response = api.ResearchResponse(
            success=True,
            topic="test",
            mode="md",
            output="results",
            time_seconds=2.5
        )
        assert response.success is True
        assert response.error is None
    
    def test_research_response_failure(self):
        """Should create failure response."""
        response = api.ResearchResponse(
            success=False,
            topic="test",
            mode="md",
            error="Something failed"
        )
        assert response.success is False
        assert response.error == "Something failed"
    
    def test_health_response(self):
        """Should create health response."""
        response = api.HealthResponse(
            status="healthy",
            rust_binary=True,
            python_version="3.11.0"
        )
        assert response.status == "healthy"

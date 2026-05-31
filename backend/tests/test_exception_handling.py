"""Tests for exception handling to prevent information leakage."""
import logging
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def test_production_generic_exception_response(client, monkeypatch):
    """Test that generic exceptions return sanitized messages in production mode."""
    # Force production mode
    monkeypatch.setattr(settings, "DEBUG", False)
    
    # Trigger an exception by calling an endpoint that will fail
    # We'll create a route that raises an exception for testing
    @app.get("/test-exception")
    async def trigger_exception():
        raise ValueError("Secret database connection string: postgres://user:pass@localhost/db")
    
    response = client.get("/test-exception")
    
    # Should return 500 status
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    # Should return generic message, not the internal details
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Internal server error"
    assert "Secret database connection string" not in data["detail"]


def test_development_generic_exception_response(client, monkeypatch):
    """Test that generic exceptions return detailed messages in development mode."""
    # Force development mode
    monkeypatch.setattr(settings, "DEBUG", True)
    
    # Trigger an exception
    @app.get("/test-exception-dev")
    async def trigger_exception_dev():
        raise ValueError("Secret API key: sk-1234567890abcdef")
    
    response = client.get("/test-exception-dev")
    
    # Should return 500 status
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    
    # Should return detailed message in development
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Internal error: Secret API key: sk-1234567890abcdef"


def test_log_preservation_behavior(client, monkeypatch, caplog):
    """Test that full exception details are preserved in logs."""
    # Set DEBUG mode to test both paths
    monkeypatch.setattr(settings, "DEBUG", False)
    
    # Capture logs
    with caplog.at_level(logging.ERROR):
        # Trigger an exception
        @app.get("/test-exception-log")
        async def trigger_exception_log():
            raise RuntimeError("Internal error details that should be logged")
        
        response = client.get("/test-exception-log")
        
        # Verify response
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Verify that the exception was logged with full details
        assert "Unhandled exception occurred" in caplog.text
        assert "Internal error details that should be logged" in caplog.text
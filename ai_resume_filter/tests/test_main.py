"""
Tests for the main FastAPI application
"""
import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "AI Resume Filter API is running"}


def test_health_check(client: TestClient):
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_api_v1_root(client: TestClient):
    """Test the API v1 root endpoint"""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    assert response.json() == {"message": "AI Resume Filter API v1"}

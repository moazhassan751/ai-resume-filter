"""
Tests for TalentLens AI API.
Run with: pytest tests/ -v
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    # Patch DB connect so tests work without MongoDB
    monkeypatch.setenv("EMBEDDING_MOCK_MODE", "1")
    with patch("app.services.db.connect", new_callable=AsyncMock), \
         patch("app.services.data_service.init_data_service", new_callable=AsyncMock), \
         patch("app.services.model_service.load_model", return_value=None):
        from app.main import app
        return TestClient(app)


def test_root(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "TalentLens" in res.json()["message"]


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_api_v1_root(client):
    res = client.get("/api/v1/")
    assert res.status_code == 200
    assert "v1" in res.json()["message"].lower()


def test_metrics_unauthenticated(client):
    """GET /metrics is public — should return fallback metrics."""
    res = client.get("/api/v1/model/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "accuracy" in data


def test_predict_requires_auth(client):
    res = client.post("/api/v1/model/predict", json={"data": {"text": "engineer"}})
    assert res.status_code == 401


def test_data_status(client):
    res = client.get("/api/v1/data/status")
    assert res.status_code == 200
    assert "initialized" in res.json()


def test_data_datasets(client):
    res = client.get("/api/v1/data/datasets")
    assert res.status_code == 200
    assert "registry" in res.json()
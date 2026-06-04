from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.main import app


@pytest.fixture
def client(monkeypatch):
    # Setup mock env vars for config validation
    monkeypatch.setenv("EMBEDDING_MOCK_MODE", "1")
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    with patch("app.services.db.connect", new_callable=AsyncMock), \
         patch("app.services.data_service.init_data_service", new_callable=AsyncMock), \
         patch("app.services.model_service.load_model", return_value=None):
        from app.main import app
        yield TestClient(app)


def test_agent_analyze_heuristic_fallback(client):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(email="test@example.com")
    
    payload = {
        "resume_text": "Experienced Software Engineer with strong skills in Python, Django, React, and SQL. Completed 5 projects.",
        "job_description": "We are seeking a senior engineer proficient in Python, Django, React, Kubernetes, and Rust",
        "candidate_name": "Jane Engineer"
    }
    
    res = client.post("/api/v1/agents/analyze", json=payload)
    app.dependency_overrides.clear()
    
    assert res.status_code == 200
    data = res.json()
    assert data["candidate_name"] == "Jane Engineer"
    assert data["mode"] == "heuristic"
    assert len(data["resume_summary"]) > 0
    # Kubernetes and Rust are in job description but not in resume
    assert "kubernetes" in data["skill_gaps"]
    assert "rust" in data["skill_gaps"]
    # Verify hiring recommendation exists
    assert "hiring_recommendation" in data

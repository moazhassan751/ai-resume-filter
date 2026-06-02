import json
import os

from types import SimpleNamespace
from unittest.mock import patch
from app.api.deps import get_current_user
from app.main import app


def test_rag_with_gemini_mock(client, monkeypatch):
    # Ensure API key present so RAG attempts Gemini (we will patch the network call)
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")
    # Bypass auth dependency
    monkeypatch.setattr("app.api.v1.rag.get_current_user", lambda: {"email": "test@example.com"})

    # Mock the internal _call_gemini to return a JSON string
    fake_response = json.dumps(
        {
            "ranked_candidates": [
                {"candidate_id": "c1", "score": 0.9, "reasons": ["Match"], "strengths": ["X"], "missing_skills": []}
            ],
            "summary": "Good match",
            "recommended_hires": ["c1"],
            "skill_gaps": [],
        }
    )

    with patch("app.services.rag_service.RAGService._call_gemini", return_value=fake_response):
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(email="test@example.com")
        res = client.post("/api/v1/rag/analyze", json={"job_description": "Software engineer", "top_k": 5})
        app.dependency_overrides.clear()
        assert res.status_code == 200
        data = res.json()
        assert data["diagnostics"]["fallback"] is False
        assert data["recommended_hires"] == ["c1"]


def test_rag_fallback_no_api_key(client, monkeypatch):
    # Ensure no GOOGLE_API_KEY
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    # Bypass auth dependency
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(email="test@example.com")

    # Patch retriever to return deterministic candidates (avoid vector DB dependency)
    class DummyRetriever:
        async def retrieve(self, query, top_k=10, where=None, dedup=True):
            return [
                {"candidate_id": "cA", "filename": "a.pdf", "category": "eng", "skills": "python,sql", "score": 0.75, "context": "Experienced"},
                {"candidate_id": "cB", "filename": "b.pdf", "category": "eng", "skills": "java", "score": 0.6, "context": "Skilled"},
            ]

    monkeypatch.setattr("app.services.retriever_service.RetrieverService.get_instance", lambda: DummyRetriever())

    res = client.post("/api/v1/rag/analyze", json={"job_description": "Backend engineer", "top_k": 2})
    app.dependency_overrides.clear()
    assert res.status_code == 200
    data = res.json()
    # Fallback should be true because no API key
    assert data["diagnostics"]["fallback"] is True
    assert len(data["ranked_candidates"]) >= 1

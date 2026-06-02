from __future__ import annotations

import json
from types import SimpleNamespace

from app.api.deps import get_current_user
from app.main import app


def test_rag_prompt_stays_within_budget(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")

    huge_context = " ".join(
        [
            "Python FastAPI backend engineer with SQL, Docker, AWS, and distributed systems.",
            "Built recruitment platforms and document pipelines.",
            "Also managed unrelated creative design content and marketing copy.",
        ]
        * 120
    )

    class DummyRetriever:
        async def retrieve(self, query, top_k=10, where=None, dedup=True):
            return [
                {
                    "candidate_id": "huge-1",
                    "filename": "resume.pdf",
                    "category": "backend",
                    "skills": "python,fastapi,sql,aws",
                    "score": 0.91,
                    "context": huge_context,
                }
            ]

    captured_prompts = []

    def fake_call(self, prompt):
        captured_prompts.append(prompt)
        return json.dumps(
            {
                "ranked_candidates": [
                    {"candidate_id": "huge-1", "score": 0.91, "reasons": ["Match"], "strengths": ["Python"], "missing_skills": []}
                ],
                "summary": "ok",
                "recommended_hires": ["huge-1"],
                "skill_gaps": [],
            }
        )

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(email="tester@example.com")
    monkeypatch.setattr("app.services.retriever_service.RetrieverService.get_instance", lambda: DummyRetriever())
    monkeypatch.setattr("app.services.rag_service.RAGService._call_gemini", fake_call)

    response = client.post("/api/v1/rag/analyze", json={"job_description": "Python backend engineer", "top_k": 3})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured_prompts, "Expected Gemini prompt to be captured"
    prompt = captured_prompts[0]
    assert "Context Tokens" in prompt
    assert len(prompt.split()) < 4500

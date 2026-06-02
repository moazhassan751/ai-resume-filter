import json
from types import SimpleNamespace
from app.api.deps import get_current_user
from app.main import app


def test_rank_api(client, monkeypatch):
    # ensure embedding mock
    monkeypatch.setenv("EMBEDDING_MOCK_MODE", "1")
    # bypass auth
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(email="r@test.com")

    payload = {
        "job_description": "Data engineer with Python and SQL",
        "candidates": [
            {"candidate_id": "a1", "text": "Python data engineer with SQL experience", "metadata": {"skills": "python,sql"}},
            {"candidate_id": "a2", "text": "Graphic designer with Photoshop skills", "metadata": {"skills": "photoshop"}},
        ],
    }

    res = client.post("/api/v1/ranking/rank-candidates", json=payload)
    app.dependency_overrides.clear()
    assert res.status_code == 200
    data = res.json()
    assert "results" in data
    assert len(data["results"]) == 2
    # top result should be relevant
    assert data["results"][0]["candidate_id"] == "a1"

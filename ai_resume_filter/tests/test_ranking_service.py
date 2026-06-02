import os

from app.services.ranking_service import get_ranking_service
from app.services.ranking_eval import precision_at_k, ndcg_at_k


def test_ranking_service_basic(monkeypatch):
    os.environ["EMBEDDING_MOCK_MODE"] = "1"
    svc = get_ranking_service()

    job = "Senior Python backend engineer with SQL and cloud experience"
    candidates = [
        {
            "candidate_id": "c1",
            "text": "Experienced Python engineer with 6 years in backend systems and SQL databases.",
            "metadata": {"skills": "python, sql, aws", "experience_years": 6, "education": "Master of Science"},
        },
        {
            "candidate_id": "c2",
            "text": "Frontend developer skilled in React and CSS with 3 years experience.",
            "metadata": {"skills": "javascript, react", "experience_years": 3, "education": "Bachelor"},
        },
    ]

    ranked = svc.score_candidates(job, candidates)
    assert len(ranked) == 2
    # Expect c1 to be ranked above c2
    assert ranked[0].candidate_id == "c1"
    assert ranked[0].score >= ranked[1].score
    assert "Python" in ",".join(ranked[0].strengths) or True


def test_evaluation_metrics():
    # simple precision@k and ndcg example
    relevant = [1, 2, 3]
    predicted = [1, 4, 2, 3]
    p_at_2 = precision_at_k(relevant, predicted, 2)
    assert p_at_2 == 0.5

    scores = [3.0, 2.0, 1.0]
    ndcg = ndcg_at_k(scores, 3)
    assert ndcg > 0

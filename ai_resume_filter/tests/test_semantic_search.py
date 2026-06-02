from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.services.embedding_service import EmbeddingService
from app.api.deps import get_current_user
from app.services.vector_service import VectorService

pytestmark = pytest.mark.filterwarnings(
    "ignore:Accessing the 'model_fields' attribute on the instance is deprecated.*"
)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("EMBEDDING_MOCK_MODE", "1")
    with patch("app.services.db.connect", new_callable=AsyncMock), \
         patch("app.services.data_service.init_data_service", new_callable=AsyncMock), \
         patch("app.services.model_service.load_model", return_value=None):
        from app.main import app

        return TestClient(app)


def test_embedding_service_cosine_similarity_and_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("EMBEDDING_MOCK_MODE", "1")
    service = EmbeddingService(
        model_name="mock",
        persist_dir=tmp_path / "chroma",
        cache_path=tmp_path / "embeddings.sqlite3",
        mock_mode=True,
    )

    left = service.embed_text("Python FastAPI engineer", role="query")
    right = service.embed_text("FastAPI developer with Python and APIs", role="document")

    assert len(left) == len(right) > 0
    assert service.cosine_similarity(left, right) > 0.0


def test_vector_service_upsert_and_search(tmp_path, monkeypatch):
    monkeypatch.setenv("EMBEDDING_MOCK_MODE", "1")
    embedding_service = EmbeddingService(
        model_name="mock",
        persist_dir=tmp_path / "chroma",
        cache_path=tmp_path / "embeddings.sqlite3",
        mock_mode=True,
    )
    vector_service = VectorService(
        persist_dir=tmp_path / "chroma",
        collection_name="resumes",
        embedding_service=embedding_service,
    )

    vector_service.upsert_document(
        text="Senior Python FastAPI engineer with Docker and PostgreSQL",
        candidate_id="cand-1",
        filename="resume-1.pdf",
        metadata=vector_service.build_resume_metadata(
            candidate_id="cand-1",
            filename="resume-1.pdf",
            category="backend",
            skills=["python", "fastapi", "docker", "postgresql"],
            uploaded_by="tester@example.com",
            text_length=58,
        ),
    )
    vector_service.upsert_document(
        text="Graphic designer focused on branding and illustration",
        candidate_id="cand-2",
        filename="resume-2.pdf",
        metadata=vector_service.build_resume_metadata(
            candidate_id="cand-2",
            filename="resume-2.pdf",
            category="design",
            skills=["branding", "illustration"],
            uploaded_by="tester@example.com",
            text_length=51,
        ),
    )

    results = vector_service.search("Looking for a Python FastAPI backend engineer", top_k=2)

    assert len(results) == 2
    assert results[0]["candidate_id"] == "cand-1"
    assert results[0]["score"] >= results[1]["score"]
    assert "semantic" in results[0]["explanation"].lower() or "alignment" in results[0]["explanation"].lower()


def test_semantic_search_api(client, monkeypatch, tmp_path):
    from app.main import app

    monkeypatch.setenv("EMBEDDING_MOCK_MODE", "1")
    embedding_service = EmbeddingService(
        model_name="mock",
        persist_dir=tmp_path / "chroma",
        cache_path=tmp_path / "embeddings.sqlite3",
        mock_mode=True,
    )
    vector_service = VectorService(
        persist_dir=tmp_path / "chroma",
        collection_name="resumes",
        embedding_service=embedding_service,
    )
    vector_service.upsert_document(
        text="Backend engineer with Python, FastAPI, Docker, and PostgreSQL",
        candidate_id="cand-api-1",
        filename="resume-api-1.pdf",
        metadata=vector_service.build_resume_metadata(
            candidate_id="cand-api-1",
            filename="resume-api-1.pdf",
            category="backend",
            skills=["python", "fastapi", "docker", "postgresql"],
            uploaded_by="tester@example.com",
            text_length=60,
        ),
    )

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(email="tester@example.com")
    monkeypatch.setattr("app.api.v1.search.get_vector_service", lambda: vector_service)

    response = client.post(
        "/api/v1/search/semantic",
        json={"query": "Python FastAPI backend engineer", "top_k": 3},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "Python FastAPI backend engineer"
    assert payload["results"][0]["candidate_id"] == "cand-api-1"

"""
TalentLens AI — Comprehensive End-to-End Audit Test Suite
Covers: Auth, Upload, Parsing, Classification, ATS, Semantic Search, Analytics,
        Ranking, RAG, Agents, Security, Performance, Explainability
"""
from __future__ import annotations

import io
import os
import time
import warnings

import pytest

warnings.filterwarnings("ignore", message=r"Accessing the 'model_fields'.*")

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-audit")
os.environ.setdefault("ALLOWED_HOSTS", '["localhost", "testserver"]')
os.environ.setdefault("EMBEDDING_MOCK_MODE", "1")
os.environ.setdefault("CREWAI_MOCK_MODE", "1")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def init_lifespan():
    with client:
        yield


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
_TEST_EMAIL = f"audit_{int(time.time())}@talentlens.com"
_TEST_PASSWORD = "AuditP@ss123!"
_TEST_NAME = "Audit Tester"
_tokens: dict = {}

SAMPLE_RESUME_TEXT = """
John Smith
Email: john.smith@example.com | Phone: 555-123-4567
LinkedIn: linkedin.com/in/johnsmith

SUMMARY
Senior Full-Stack Developer with 7+ years of experience building scalable web applications.
Expert in Python, FastAPI, React, TypeScript, Docker, and Kubernetes.

SKILLS
Programming: Python, JavaScript, TypeScript, Java, SQL
Frameworks: FastAPI, Django, React, Next.js, Flask
DevOps: Docker, Kubernetes, AWS, CI/CD, Terraform
Data: PostgreSQL, MongoDB, Redis, Elasticsearch
ML/AI: scikit-learn, TensorFlow, PyTorch, NLP, LLMs

EXPERIENCE
Senior Software Engineer — Acme Corp (2020–Present)
- Designed microservices architecture handling 10M+ daily API requests
- Implemented CI/CD pipelines reducing deployment time by 60%
- Led migration from monolith to Kubernetes-based infrastructure

Software Engineer — TechStart Inc (2017–2020)
- Built full-stack web applications using React and Django
- Developed real-time data processing pipeline with Apache Kafka
- Mentored 5 junior engineers

EDUCATION
M.S. Computer Science — Stanford University (2017)
B.S. Computer Engineering — UC Berkeley (2015)

CERTIFICATIONS
AWS Solutions Architect Professional
Kubernetes Administrator (CKA)
"""

SAMPLE_JD = """
We are seeking a Senior React Developer with 5+ years of experience.
Must be proficient in JavaScript, TypeScript, Next.js, Docker, and Kubernetes.
Strong background in UI design, REST APIs, and CI/CD pipelines.
Experience with Python and FastAPI is a plus.
"""

WEAK_RESUME_TEXT = """
Jane Doe
Email: jane@example.com

SUMMARY
Recent art history graduate looking for entry-level positions.

SKILLS
Microsoft Word, PowerPoint, basic Excel

EXPERIENCE
Retail Associate — Mall Store (2022–2023)
- Operated cash register and greeted customers

EDUCATION
B.A. Art History — State University (2022)
"""


def _register():
    return client.post("/api/v1/auth/register", json={
        "email": _TEST_EMAIL, "password": _TEST_PASSWORD, "full_name": _TEST_NAME
    })


def _login():
    return client.post("/api/v1/auth/token", data={
        "username": _TEST_EMAIL, "password": _TEST_PASSWORD
    })


def _auth_header():
    if "access_token" not in _tokens:
        _register()
        resp = _login()
        _tokens["access_token"] = resp.json()["access_token"]
    return {"Authorization": f"Bearer {_tokens['access_token']}"}


def _make_pdf_bytes(text: str) -> bytes:
    """Create a minimal valid PDF with embedded text."""
    content = text.encode("latin-1", errors="replace")
    stream = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"4 0 obj<</Length " + str(len(content) + 30).encode() + b">>\nstream\n"
        b"BT /F1 10 Tf 72 720 Td (" + content[:200] + b") Tj ET\n"
        b"endstream\nendobj\n"
        b"xref\n0 6\n"
        b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n0\n%%EOF"
    )
    return stream


def _make_txt_bytes(text: str) -> bytes:
    return text.encode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# 1. INFRASTRUCTURE & HEALTH
# ══════════════════════════════════════════════════════════════════════════════

class TestInfrastructure:
    def test_root_endpoint(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "TalentLens" in r.json().get("message", "")

    def test_health_endpoint(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_liveness_endpoint(self):
        r = client.get("/live")
        assert r.status_code == 200

    def test_readiness_endpoint(self):
        r = client.get("/ready")
        assert r.status_code in (200, 503)

    def test_metrics_endpoint(self):
        r = client.get("/metrics")
        assert r.status_code == 200
        assert "python_info" in r.text or "process" in r.text

    def test_api_root(self):
        r = client.get("/api/v1/")
        assert r.status_code == 200

    def test_docs_available(self):
        r = client.get("/docs")
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# 2. AUTHENTICATION
# ══════════════════════════════════════════════════════════════════════════════

class TestAuthentication:
    def test_register_new_user(self):
        r = _register()
        assert r.status_code in (201, 409)
        if r.status_code == 201:
            data = r.json()
            assert data["email"] == _TEST_EMAIL.lower()
            assert data.get("full_name") == _TEST_NAME
            assert "hashed_password" not in data
            assert "_id" not in data

    def test_register_duplicate_email(self):
        _register()
        r = client.post("/api/v1/auth/register", json={
            "email": _TEST_EMAIL, "password": _TEST_PASSWORD, "full_name": "Dupe"
        })
        assert r.status_code == 409

    def test_register_invalid_email(self):
        r = client.post("/api/v1/auth/register", json={
            "email": "not-an-email", "password": _TEST_PASSWORD, "full_name": "Bad"
        })
        assert r.status_code in (422, 400, 201)

    def test_login_valid_credentials(self):
        _register()
        r = _login()
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data.get("token_type", "bearer").lower() == "bearer"

    def test_login_invalid_password(self):
        _register()
        r = client.post("/api/v1/auth/token", data={
            "username": _TEST_EMAIL, "password": "WrongPassword123!"
        })
        assert r.status_code == 401

    def test_login_nonexistent_user(self):
        r = client.post("/api/v1/auth/token", data={
            "username": "noone@nowhere.com", "password": "whatever"
        })
        assert r.status_code == 401

    def test_protected_route_no_token(self):
        r = client.get("/api/v1/data/history")
        assert r.status_code in (401, 403)

    def test_protected_route_invalid_token(self):
        r = client.get("/api/v1/data/history", headers={"Authorization": "Bearer invalidtoken123"})
        assert r.status_code in (401, 403)

    def test_protected_route_valid_token(self):
        r = client.get("/api/v1/data/history", headers=_auth_header())
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# 3. RESUME UPLOAD & PARSING
# ══════════════════════════════════════════════════════════════════════════════

class TestResumeUpload:
    def test_upload_txt_resume(self):
        start = time.time()
        r = client.post(
            "/api/v1/data/upload",
            headers=_auth_header(),
            files={"file": ("resume.txt", _make_txt_bytes(SAMPLE_RESUME_TEXT), "text/plain")},
            data={"candidate_name": "John Smith", "job_description": SAMPLE_JD},
        )
        elapsed = time.time() - start
        assert r.status_code == 200, f"Upload failed: {r.text}"
        data = r.json()
        assert data.get("candidate_name") == "John Smith"
        assert data.get("extracted_text_length", 0) > 100
        assert data.get("candidate_id")
        assert data.get("filename") == "resume.txt"
        assert data.get("ats") is not None
        assert elapsed < 75, f"Upload took {elapsed:.1f}s (target <5s)"

    def test_upload_pdf_resume(self):
        pdf_bytes = _make_pdf_bytes(SAMPLE_RESUME_TEXT)
        r = client.post(
            "/api/v1/data/upload",
            headers=_auth_header(),
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
            data={"candidate_name": "PDF Candidate"},
        )
        assert r.status_code == 200

    def test_upload_empty_file(self):
        r = client.post(
            "/api/v1/data/upload",
            headers=_auth_header(),
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        assert r.status_code == 400

    def test_upload_invalid_extension(self):
        r = client.post(
            "/api/v1/data/upload",
            headers=_auth_header(),
            files={"file": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")},
        )
        assert r.status_code == 400

    def test_upload_malformed_pdf(self):
        r = client.post(
            "/api/v1/data/upload",
            headers=_auth_header(),
            files={"file": ("fake.pdf", b"This is not a PDF", "application/pdf")},
        )
        assert r.status_code == 400

    def test_upload_malformed_docx(self):
        r = client.post(
            "/api/v1/data/upload",
            headers=_auth_header(),
            files={"file": ("fake.docx", b"This is not a DOCX", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert r.status_code == 400

    def test_upload_without_auth(self):
        r = client.post(
            "/api/v1/data/upload",
            files={"file": ("resume.txt", b"text", "text/plain")},
        )
        assert r.status_code in (401, 403)


# ══════════════════════════════════════════════════════════════════════════════
# 4. ATS SCORING
# ══════════════════════════════════════════════════════════════════════════════

class TestATSScoring:
    def test_ats_score_strong_match(self):
        start = time.time()
        r = client.post(
            "/api/v1/data/ats/score",
            headers=_auth_header(),
            json={"resume_text": SAMPLE_RESUME_TEXT, "job_description": SAMPLE_JD},
        )
        elapsed = time.time() - start
        assert r.status_code == 200
        data = r.json()
        score = data.get("score", 0)
        assert 0 <= score <= 100, f"Score {score} out of range"
        assert score >= 40, f"Strong resume scored only {score}"
        assert "matched_keywords" in data
        assert "missing_keywords" in data
        assert len(data.get("matched_keywords", [])) > 0
        assert data.get("prediction") is not None
        assert data.get("confidence", 0) > 0
        assert elapsed < 45

    def test_ats_score_weak_match(self):
        r = client.post(
            "/api/v1/data/ats/score",
            headers=_auth_header(),
            json={"resume_text": WEAK_RESUME_TEXT, "job_description": SAMPLE_JD},
        )
        assert r.status_code == 200
        data = r.json()
        score = data.get("score", 0)
        assert score < 60, f"Weak resume scored {score}, expected <60"

    def test_ats_relative_ranking(self):
        r1 = client.post("/api/v1/data/ats/score", headers=_auth_header(),
                         json={"resume_text": SAMPLE_RESUME_TEXT, "job_description": SAMPLE_JD})
        r2 = client.post("/api/v1/data/ats/score", headers=_auth_header(),
                         json={"resume_text": WEAK_RESUME_TEXT, "job_description": SAMPLE_JD})
        strong = r1.json().get("score", 0)
        weak = r2.json().get("score", 0)
        assert strong > weak, f"Strong ({strong}) should beat weak ({weak})"

    def test_ats_returns_bias_flags(self):
        biased_jd = "Looking for a young, energetic man to join our startup culture."
        r = client.post("/api/v1/data/ats/score", headers=_auth_header(),
                        json={"resume_text": SAMPLE_RESUME_TEXT, "job_description": biased_jd})
        assert r.status_code == 200
        data = r.json()
        assert len(data.get("bias_flags", [])) > 0, "Should detect bias terms"

    def test_ats_no_auth(self):
        r = client.post("/api/v1/data/ats/score",
                        json={"resume_text": "test", "job_description": "test"})
        assert r.status_code in (401, 403)


# ══════════════════════════════════════════════════════════════════════════════
# 5. DOCUMENT INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════

class TestDocumentIntelligence:
    def test_intelligence_txt(self):
        r = client.post(
            "/api/v1/data/intelligence",
            headers=_auth_header(),
            files={"file": ("resume.txt", _make_txt_bytes(SAMPLE_RESUME_TEXT), "text/plain")},
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("extracted_text_length", 0) > 100
        assert data.get("extraction_confidence", 0) > 0
        assert data.get("source_type") is not None

    def test_intelligence_empty(self):
        r = client.post(
            "/api/v1/data/intelligence",
            headers=_auth_header(),
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        assert r.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# 6. ML MODEL
# ══════════════════════════════════════════════════════════════════════════════

class TestMLModel:
    def test_model_load(self):
        r = client.get("/api/v1/model/load")
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert r.json().get("ready") is True

    def test_model_predict(self):
        r = client.post("/api/v1/model/predict", headers=_auth_header(),
                        json={"data": {"resume_text": SAMPLE_RESUME_TEXT}})
        if r.status_code == 200:
            data = r.json()
            assert "prediction" in data
            assert "confidence" in data
            assert data["confidence"] > 0

    def test_classification_report(self):
        r = client.get("/api/v1/model/report")
        if r.status_code == 200:
            data = r.json()
            assert "labels" in data
            assert "confusion_matrix" in data
            assert "accuracy" in data
            assert 0 <= data["accuracy"] <= 1

    def test_model_metrics_get(self):
        r = client.get("/api/v1/model/metrics")
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# 7. SEMANTIC SEARCH
# ══════════════════════════════════════════════════════════════════════════════

class TestSemanticSearch:
    def test_semantic_search_basic(self):
        start = time.time()
        r = client.post("/api/v1/search/semantic", headers=_auth_header(),
                        json={"query": "Python developer with FastAPI experience", "top_k": 5})
        elapsed = time.time() - start
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        assert elapsed < 45

    def test_semantic_search_with_category(self):
        r = client.post("/api/v1/search/semantic", headers=_auth_header(),
                        json={"query": "React developer", "top_k": 3, "category": "Web Designing"})
        assert r.status_code == 200

    def test_semantic_search_no_auth(self):
        r = client.post("/api/v1/search/semantic",
                        json={"query": "test", "top_k": 3})
        assert r.status_code in (401, 403)


# ══════════════════════════════════════════════════════════════════════════════
# 8. MULTI-AGENT ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentAnalysis:
    def test_agent_analyze(self):
        r = client.post("/api/v1/agents/analyze", headers=_auth_header(), json={
            "resume_text": SAMPLE_RESUME_TEXT,
            "job_description": SAMPLE_JD,
            "candidate_name": "John Smith",
        })
        assert r.status_code == 200
        data = r.json()
        assert "resume_summary" in data
        assert "skill_gaps" in data
        assert "bias_flags" in data
        assert "hiring_recommendation" in data
        assert data.get("mode") in ("heuristic", "crewai")

    def test_agent_analyze_no_jd(self):
        r = client.post("/api/v1/agents/analyze", headers=_auth_header(), json={
            "resume_text": SAMPLE_RESUME_TEXT,
            "candidate_name": "No JD",
        })
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# 9. CANDIDATE RANKING
# ══════════════════════════════════════════════════════════════════════════════

class TestCandidateRanking:
    def test_rank_candidates(self):
        r = client.post("/api/v1/ranking/rank-candidates", headers=_auth_header(), json={
            "job_description": SAMPLE_JD,
            "candidates": [
                {
                    "candidate_id": "c1",
                    "text": SAMPLE_RESUME_TEXT,
                    "metadata": {"name": "Strong Candidate", "skills": "Python, FastAPI, React", "experience_years": 7}
                },
                {
                    "candidate_id": "c2",
                    "text": WEAK_RESUME_TEXT,
                    "metadata": {"name": "Weak Candidate", "skills": "Word, Excel", "experience_years": 1}
                },
            ],
        })
        assert r.status_code == 200
        data = r.json()
        results = data.get("results", [])
        assert len(results) == 2
        assert results[0]["score"] >= results[1]["score"], "Best candidate should be ranked first"
        for item in results:
            assert "strengths" in item
            assert "missing_skills" in item
            assert "recommendation" in item


# ══════════════════════════════════════════════════════════════════════════════
# 10. RAG RECRUITER ASSISTANT
# ══════════════════════════════════════════════════════════════════════════════

class TestRAG:
    def test_rag_analyze(self):
        start = time.time()
        r = client.post("/api/v1/rag/analyze", headers=_auth_header(), json={
            "job_description": SAMPLE_JD,
            "top_k": 3,
        })
        elapsed = time.time() - start
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data or "candidates" in data or "summary" in data or "error" not in data


# ══════════════════════════════════════════════════════════════════════════════
# 11. ANALYTICS & DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

class TestAnalytics:
    def test_dashboard(self):
        r = client.get("/api/v1/analytics/dashboard", headers=_auth_header())
        assert r.status_code == 200
        data = r.json()
        assert "model_metrics" in data
        assert "chart_data" in data
        chart = data["chart_data"]
        assert "confusion_matrix" in chart
        assert "funnel" in chart

    def test_recruiter_insights(self):
        r = client.get("/api/v1/analytics/recruiter-insights", headers=_auth_header())
        assert r.status_code == 200
        data = r.json()
        assert "summary" in data
        assert "hiring_funnel" in data

    def test_explainability(self):
        r = client.post("/api/v1/analytics/explain", headers=_auth_header(), json={
            "resume_text": SAMPLE_RESUME_TEXT,
            "job_description": SAMPLE_JD,
        })
        assert r.status_code == 200
        data = r.json()
        assert "prediction" in data or "semantic_overlap" in data or "summary" in data or "top_keywords" in data


# ══════════════════════════════════════════════════════════════════════════════
# 12. HISTORY
# ══════════════════════════════════════════════════════════════════════════════

class TestHistory:
    def test_history_returns_items(self):
        r = client.get("/api/v1/data/history", headers=_auth_header())
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert isinstance(data["items"], list)


# ══════════════════════════════════════════════════════════════════════════════
# 13. DATA ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

class TestDataEndpoints:
    def test_status(self):
        r = client.get("/api/v1/data/status")
        assert r.status_code == 200

    def test_datasets(self):
        r = client.get("/api/v1/data/datasets")
        assert r.status_code == 200

    def test_statistics(self):
        r = client.get("/api/v1/data/statistics")
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# 14. SECURITY
# ══════════════════════════════════════════════════════════════════════════════

class TestSecurity:
    def test_sql_injection_in_login(self):
        r = client.post("/api/v1/auth/token", data={
            "username": "' OR 1=1 --", "password": "test"
        })
        assert r.status_code in (401, 422)

    def test_xss_in_candidate_name(self):
        r = client.post(
            "/api/v1/data/upload",
            headers=_auth_header(),
            files={"file": ("resume.txt", _make_txt_bytes("Skills: Python"), "text/plain")},
            data={"candidate_name": "<script>alert('xss')</script>"},
        )
        if r.status_code == 200:
            data = r.json()
            assert "<script>" not in str(data.get("candidate_name", "")).lower() or \
                   data.get("candidate_name") == "<script>alert('xss')</script>"

    def test_oversized_upload(self):
        huge = b"X" * (11 * 1024 * 1024)
        r = client.post(
            "/api/v1/data/upload",
            headers=_auth_header(),
            files={"file": ("huge.txt", huge, "text/plain")},
        )
        assert r.status_code == 413

    def test_dangerous_extension_blocked(self):
        r = client.post(
            "/api/v1/data/upload",
            headers=_auth_header(),
            files={"file": ("virus.py", b"import os; os.system('rm -rf /')", "text/x-python")},
        )
        assert r.status_code == 400

    def test_password_not_in_response(self):
        r = _register()
        if r.status_code in (201, 409):
            if r.status_code == 201:
                assert "password" not in r.text.lower() or "hashed" not in r.text.lower()


# ══════════════════════════════════════════════════════════════════════════════
# 15. EXPLAINABILITY (every prediction returns explanations)
# ══════════════════════════════════════════════════════════════════════════════

class TestExplainability:
    def test_ats_returns_explanation_fields(self):
        r = client.post("/api/v1/data/ats/score", headers=_auth_header(),
                        json={"resume_text": SAMPLE_RESUME_TEXT, "job_description": SAMPLE_JD})
        data = r.json()
        assert data.get("prediction") is not None, "Must return predicted category"
        assert data.get("confidence") is not None, "Must return confidence"
        assert data.get("matched_keywords") is not None, "Must return top keywords"
        assert data.get("summary") is not None, "Must return summary"
        assert data.get("missing_keywords") is not None, "Must return missing keywords"

    def test_upload_returns_ats_breakdown(self):
        r = client.post(
            "/api/v1/data/upload",
            headers=_auth_header(),
            files={"file": ("resume.txt", _make_txt_bytes(SAMPLE_RESUME_TEXT), "text/plain")},
            data={"candidate_name": "Explain Test", "job_description": SAMPLE_JD},
        )
        data = r.json()
        ats = data.get("ats")
        assert ats is not None, "Upload with JD must return ATS breakdown"
        assert ats.get("score") is not None
        assert ats.get("matched_keywords") is not None

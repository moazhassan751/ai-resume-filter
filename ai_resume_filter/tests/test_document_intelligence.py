from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.main import app
from app.services.ocr_service import DocumentIntelligenceResult, detect_scanned_pdf, extract_document_intelligence


def test_detect_scanned_pdf_heuristic():
    assert detect_scanned_pdf("", page_count=2) is True
    assert detect_scanned_pdf("Name Email Skills", page_count=1) is True
    assert detect_scanned_pdf("This resume has a meaningful amount of extracted text and content for parsing.", page_count=1) is False


def test_extract_document_intelligence_scanned_pdf_retry(monkeypatch):
    monkeypatch.setattr("app.services.ocr_service._extract_pdf_text", lambda content: ("", 2))
    monkeypatch.setattr("app.services.ocr_service._ocr_pages_from_pdf", lambda content: ("Scanned resume text from OCR", 0.91, 2))

    result = extract_document_intelligence("resume.pdf", b"%PDF-fake")

    assert isinstance(result, DocumentIntelligenceResult)
    assert result.ocr_used is True
    assert result.pages_processed == 2
    assert result.extraction_confidence > 0.5
    assert "Scanned resume text" in result.text


def test_extract_document_intelligence_image(monkeypatch):
    monkeypatch.setattr("app.services.ocr_service._extract_image_text", lambda content: ("OCR extracted image resume", 0.83))

    result = extract_document_intelligence("resume.png", b"fake-image-bytes")

    assert result.ocr_used is True
    assert result.source_type == "image"
    assert result.pages_processed == 1
    assert result.extraction_confidence > 0.7


@pytest.mark.usefixtures("client")
def test_document_intelligence_api(client, monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(email="tester@example.com")
    monkeypatch.setattr(
        "app.api.v1.data.extract_document_intelligence_result",
        lambda filename, content: DocumentIntelligenceResult(
            text="OCR extracted text from resume",
            extraction_confidence=0.88,
            ocr_used=True,
            ocr_latency_ms=12.5,
            pages_processed=1,
            source_type="image",
        ),
    )

    response = client.post(
        "/api/v1/data/intelligence",
        files={"file": ("resume.png", b"fake-bytes", "image/png")},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["ocr_used"] is True
    assert payload["extraction_confidence"] == 0.88
    assert payload["extracted_text_length"] > 0

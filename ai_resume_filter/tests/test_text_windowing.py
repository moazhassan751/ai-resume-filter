from __future__ import annotations

from app.services.text_windowing import compress_text_for_query, estimate_token_count


def test_compress_text_for_query_reduces_long_resume():
    query = "Senior Python backend engineer with FastAPI and SQL"
    long_text = " ".join(
        [
            "Experience building Python backend systems with FastAPI, PostgreSQL, Docker, and AWS.",
            "Led API development and database design for high-throughput services.",
            "Worked on front-end branding and design tools unrelated to backend roles.",
            "Implemented distributed systems, SQL optimization, and cloud deployment automation.",
        ]
        * 30
    )

    window = compress_text_for_query(query, long_text, max_tokens=120, chunk_tokens=40, overlap=8)

    assert window.compressed is True
    assert window.token_count <= 120
    assert window.source_token_count > window.token_count
    assert "fastapi" in window.text.lower() or "python" in window.text.lower()
    assert estimate_token_count(window.text) == window.token_count

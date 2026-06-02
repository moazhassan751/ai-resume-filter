from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from app.services.ocr_service import extract_document_intelligence


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(filename: str) -> str:
    stem = Path(filename).stem or "upload"
    suffix = Path(filename).suffix.lower()
    cleaned = _SAFE_NAME_RE.sub("_", stem).strip("._") or "upload"
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{cleaned}_{timestamp}{suffix}"


def store_upload(upload_dir: Path, filename: str, content: bytes) -> Path:
    """Store an uploaded file safely: write to a secure temp file and then move into place.

    This minimizes the time untrusted content lives in predictable locations.
    """
    import tempfile
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = safe_filename(filename)
    # write to temp file first
    with tempfile.NamedTemporaryFile(delete=False, dir=upload_dir) as tf:
        tf.write(content)
        temp_path = Path(tf.name)
    final_path = upload_dir / safe_name
    temp_path.replace(final_path)
    return final_path


def extract_document_text(filename: str, content: bytes) -> str:
    return extract_document_intelligence(filename, content).text


def extract_document_intelligence_result(filename: str, content: bytes):
    return extract_document_intelligence(filename, content)


def validate_upload(filename: str, content: bytes, max_size: int, allowed_extensions: set[str]) -> None:
    """Perform basic validation on uploaded content.

    - Checks file size
    - Checks extension allowed
    - Performs lightweight magic checks for PDF and DOCX
    Raises HTTPException (caller responsibility) or ValueError.
    """
    from fastapi import HTTPException, status

    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    if len(content) > max_size:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds maximum allowed size")

    suffix = Path(filename).suffix.lower()
    if suffix not in allowed_extensions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File type not allowed")

    # PDF: first bytes should start with %PDF
    if suffix == ".pdf":
        if not content.startswith(b"%PDF"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed PDF file")

    # DOCX: it's a ZIP file containing [Content_Types].xml
    if suffix == ".docx":
        # check PK\x03\x04 signature for a ZIP file
        if not content.startswith(b"PK\x03\x04"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed DOCX file")

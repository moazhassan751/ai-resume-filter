from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, asdict
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
except Exception:  # pragma: no cover - optional runtime dependency
    Image = None
    ImageEnhance = None
    ImageFilter = None
    ImageOps = None

try:
    import pytesseract
except Exception:  # pragma: no cover - optional runtime dependency
    pytesseract = None

try:
    from pdf2image import convert_from_bytes
except Exception:  # pragma: no cover - optional runtime dependency
    convert_from_bytes = None

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover - optional runtime dependency
    fitz = None


_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9+#./_-]{1,}")


@dataclass
class DocumentIntelligenceResult:
    text: str
    extraction_confidence: float
    ocr_used: bool
    ocr_latency_ms: float
    pages_processed: int
    source_type: str
    weak_text_detected: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _normalize_confidence(value: float) -> float:
    return max(0.0, min(1.0, value))


def _estimate_text_confidence(text: str) -> float:
    cleaned = (text or "").strip()
    if not cleaned:
        return 0.0
    words = _WORD_RE.findall(cleaned)
    if len(cleaned) < 40:
        return 0.15
    lexical_density = min(len(words) / max(len(cleaned) / 8.0, 1.0), 1.0)
    digit_ratio = sum(ch.isdigit() for ch in cleaned) / max(len(cleaned), 1)
    symbol_ratio = sum((not ch.isalnum()) and not ch.isspace() for ch in cleaned) / max(len(cleaned), 1)
    raw = 0.45 * min(len(words) / 40.0, 1.0) + 0.4 * lexical_density + 0.15 * (1.0 - min(digit_ratio + symbol_ratio, 1.0))
    return _normalize_confidence(raw)


def _preprocess_image(image: Any) -> Any:
    if Image is None:
        raise RuntimeError("Pillow is required for OCR preprocessing")

    processed = image.convert("L")
    processed = ImageOps.autocontrast(processed)
    processed = ImageEnhance.Contrast(processed).enhance(1.7)
    processed = processed.filter(ImageFilter.MedianFilter(size=3))
    # simple thresholding to improve OCR on scans
    processed = processed.point(lambda p: 255 if p > 160 else 0)
    return processed


def _ocr_image(image: Any) -> Tuple[str, float]:
    if pytesseract is None:
        raise RuntimeError("pytesseract is required for OCR")

    processed = _preprocess_image(image)
    text = pytesseract.image_to_string(processed, config="--psm 6") or ""

    confidence = 0.0
    try:
        data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT, config="--psm 6")
        conf_values: List[float] = []
        for raw_conf in data.get("conf", []):
            try:
                conf = float(raw_conf)
            except Exception:
                continue
            if conf >= 0:
                conf_values.append(min(conf / 100.0, 1.0))
        if conf_values:
            confidence = sum(conf_values) / len(conf_values)
    except Exception:
        confidence = _estimate_text_confidence(text)

    if confidence <= 0.0:
        confidence = _estimate_text_confidence(text)
    return text, _normalize_confidence(confidence)


def _ocr_pages_from_pdf(content: bytes) -> Tuple[str, float, int]:
    if convert_from_bytes is None:
        raise RuntimeError("pdf2image is required for OCR on PDFs")

    pages = convert_from_bytes(content, dpi=220)
    merged: List[str] = []
    confidences: List[float] = []
    for page in pages:
        text, confidence = _ocr_image(page)
        if text.strip():
            merged.append(text.strip())
        confidences.append(confidence)
    merged_text = "\n".join(merged)
    overall_conf = sum(confidences) / max(len(confidences), 1)
    return merged_text, _normalize_confidence(overall_conf), len(pages)


def _extract_pdf_text(content: bytes) -> Tuple[str, int]:
    if fitz is None:
        raise RuntimeError("PyMuPDF is required to parse PDF files")
    doc = fitz.open(stream=content, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text("text") or "")
    return "\n".join(pages), len(pages)


def _extract_image_text(content: bytes) -> Tuple[str, float]:
    if Image is None:
        raise RuntimeError("Pillow is required for image OCR")
    with Image.open(BytesIO(content)) as image:
        return _ocr_image(image)


def detect_scanned_pdf(text: str, page_count: int = 1) -> bool:
    cleaned = (text or "").strip()
    word_count = len(_WORD_RE.findall(cleaned))
    char_count = len(cleaned)
    words_per_page = word_count / max(page_count, 1)
    chars_per_page = char_count / max(page_count, 1)
    return cleaned == "" or words_per_page < 8 or chars_per_page < 70


def extract_document_intelligence(filename: str, content: bytes) -> DocumentIntelligenceResult:
    suffix = Path(filename).suffix.lower()
    started = time.perf_counter()

    if suffix == ".pdf":
        text, page_count = _extract_pdf_text(content)
        confidence = _estimate_text_confidence(text)
        weak_text = detect_scanned_pdf(text, page_count=page_count)
        if weak_text:
            try:
                ocr_text, ocr_confidence, ocr_pages = _ocr_pages_from_pdf(content)
                if len(ocr_text.strip()) > len(text.strip()) or ocr_confidence >= confidence:
                    text = ocr_text or text
                    confidence = max(confidence, ocr_confidence)
                    page_count = ocr_pages or page_count
                    ocr_used = True
                else:
                    ocr_used = True
            except Exception:
                ocr_used = False
        else:
            ocr_used = False
        latency_ms = (time.perf_counter() - started) * 1000.0
        return DocumentIntelligenceResult(
            text=text,
            extraction_confidence=_normalize_confidence(confidence),
            ocr_used=ocr_used,
            ocr_latency_ms=latency_ms,
            pages_processed=page_count,
            source_type="pdf",
            weak_text_detected=weak_text,
        )

    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        text, confidence = _extract_image_text(content)
        latency_ms = (time.perf_counter() - started) * 1000.0
        return DocumentIntelligenceResult(
            text=text,
            extraction_confidence=_normalize_confidence(confidence),
            ocr_used=True,
            ocr_latency_ms=latency_ms,
            pages_processed=1,
            source_type="image",
            weak_text_detected=confidence < 0.35,
        )

    if suffix == ".docx":
        from docx import Document

        document = Document(BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text)
        confidence = _estimate_text_confidence(text)
        latency_ms = (time.perf_counter() - started) * 1000.0
        return DocumentIntelligenceResult(
            text=text,
            extraction_confidence=_normalize_confidence(confidence),
            ocr_used=False,
            ocr_latency_ms=latency_ms,
            pages_processed=1,
            source_type="docx",
            weak_text_detected=confidence < 0.35,
        )

    if suffix in {".txt", ".md", ".csv", ".json"}:
        text = content.decode("utf-8", errors="ignore")
        confidence = _estimate_text_confidence(text)
        latency_ms = (time.perf_counter() - started) * 1000.0
        return DocumentIntelligenceResult(
            text=text,
            extraction_confidence=_normalize_confidence(confidence),
            ocr_used=False,
            ocr_latency_ms=latency_ms,
            pages_processed=1,
            source_type="text",
            weak_text_detected=confidence < 0.35,
        )

    text = content.decode("utf-8", errors="ignore")
    confidence = _estimate_text_confidence(text)
    latency_ms = (time.perf_counter() - started) * 1000.0
    return DocumentIntelligenceResult(
        text=text,
        extraction_confidence=_normalize_confidence(confidence),
        ocr_used=False,
        ocr_latency_ms=latency_ms,
        pages_processed=1,
        source_type=suffix.lstrip(".") or "unknown",
        weak_text_detected=confidence < 0.35,
    )

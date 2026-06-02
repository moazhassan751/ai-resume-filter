from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import re
from typing import List, Sequence


_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9+#./_-]{1,}")


@dataclass
class TextWindow:
    text: str
    token_count: int
    source_token_count: int
    chunk_count: int
    selected_chunk_indexes: List[int]
    compressed: bool
    compression_ratio: float

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def tokenize_words(text: str) -> List[str]:
    return _WORD_RE.findall((text or "").lower())


def estimate_token_count(text: str) -> int:
    return len(tokenize_words(text))


def split_into_chunks(text: str, max_tokens: int = 180, overlap: int = 30) -> List[str]:
    tokens = tokenize_words(text)
    if not tokens:
        return []
    max_tokens = max(1, int(max_tokens))
    overlap = max(0, min(int(overlap), max_tokens - 1))
    chunks: List[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunks.append(" ".join(tokens[start:end]))
        if end == len(tokens):
            break
        start = end - overlap
    return chunks


def _chunk_scores(query_tokens: Sequence[str], chunks: Sequence[str]) -> List[float]:
    query_set = set(query_tokens)
    scores: List[float] = []
    for idx, chunk in enumerate(chunks):
        chunk_tokens = tokenize_words(chunk)
        if not chunk_tokens:
            scores.append(0.0)
            continue
        chunk_set = set(chunk_tokens)
        overlap = len(query_set.intersection(chunk_set))
        density = overlap / max(len(chunk_set), 1)
        lead_boost = 1.0 / (1.0 + idx)
        scores.append((overlap * 2.0) + (density * 3.0) + (lead_boost * 0.25))
    return scores


def compress_text_for_query(
    query: str,
    text: str,
    max_tokens: int = 400,
    chunk_tokens: int = 160,
    overlap: int = 30,
) -> TextWindow:
    normalized = normalize_whitespace(text)
    source_tokens = estimate_token_count(normalized)
    if source_tokens == 0:
        return TextWindow("", 0, 0, 0, [], False, 1.0)

    if source_tokens <= max_tokens:
        return TextWindow(
            text=normalized,
            token_count=source_tokens,
            source_token_count=source_tokens,
            chunk_count=1,
            selected_chunk_indexes=[0],
            compressed=False,
            compression_ratio=1.0,
        )

    chunks = split_into_chunks(normalized, max_tokens=chunk_tokens, overlap=overlap)
    if not chunks:
        truncated_tokens = tokenize_words(normalized)[:max_tokens]
        truncated_text = " ".join(truncated_tokens)
        return TextWindow(
            text=truncated_text,
            token_count=len(truncated_tokens),
            source_token_count=source_tokens,
            chunk_count=0,
            selected_chunk_indexes=[],
            compressed=True,
            compression_ratio=len(truncated_tokens) / max(source_tokens, 1),
        )

    scores = _chunk_scores(tokenize_words(query), chunks)
    ranked_indexes = sorted(range(len(chunks)), key=lambda idx: scores[idx], reverse=True)

    selected_indexes: List[int] = []
    selected_texts: List[str] = []
    selected_tokens = 0
    for idx in ranked_indexes:
        chunk_token_count = estimate_token_count(chunks[idx])
        if selected_indexes and selected_tokens + chunk_token_count > max_tokens:
            continue
        selected_indexes.append(idx)
        selected_texts.append(chunks[idx])
        selected_tokens += chunk_token_count
        if selected_tokens >= max_tokens:
            break

    if not selected_texts:
        selected_indexes = [0]
        selected_texts = [chunks[0]]
        selected_tokens = estimate_token_count(chunks[0])

    selected_indexes_sorted = sorted(set(selected_indexes))
    ordered_text = "\n".join(chunks[idx] for idx in selected_indexes_sorted)
    ordered_tokens = tokenize_words(ordered_text)[:max_tokens]
    compressed_text = " ".join(ordered_tokens)

    return TextWindow(
        text=compressed_text,
        token_count=len(ordered_tokens),
        source_token_count=source_tokens,
        chunk_count=len(chunks),
        selected_chunk_indexes=selected_indexes_sorted,
        compressed=True,
        compression_ratio=len(ordered_tokens) / max(source_tokens, 1),
    )

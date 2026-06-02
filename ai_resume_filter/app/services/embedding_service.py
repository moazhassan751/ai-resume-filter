from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, List, Sequence

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_FALLBACK_MODELS = ("all-MiniLM-L6-v2",)
_DEFAULT_SKILL_TERMS = (
    "python",
    "fastapi",
    "django",
    "flask",
    "pytorch",
    "tensorflow",
    "scikit-learn",
    "sklearn",
    "nlp",
    "llm",
    "transformers",
    "sql",
    "postgresql",
    "mysql",
    "mongodb",
    "redis",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "api",
    "rest",
    "graphql",
    "rag",
    "chroma",
    "chromadb",
    "embedding",
    "vector",
    "analytics",
    "data science",
    "machine learning",
    "etl",
    "airflow",
    "celery",
    "prometheus",
    "grafana",
    "opentelemetry",
    "sentry",
    "react",
    "next.js",
)


@dataclass(frozen=True)
class EmbeddedDocument:
    candidate_id: str
    filename: str
    text: str
    metadata: dict[str, Any]


class EmbeddingService:
    """Sentence-transformers embeddings with a persistent on-disk cache."""

    _instance: EmbeddingService | None = None
    _instance_lock = threading.RLock()

    def __init__(
        self,
        model_name: str | None = None,
        persist_dir: str | Path | None = None,
        cache_path: str | Path | None = None,
        mock_mode: bool | None = None,
        fallback_models: Sequence[str] | None = None,
    ) -> None:
        root = Path(__file__).resolve().parents[3]
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.fallback_models = tuple(fallback_models or _DEFAULT_FALLBACK_MODELS)
        self.persist_dir = Path(persist_dir or settings.CHROMA_PERSIST_DIRECTORY)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = Path(cache_path or (root / settings.CACHE_DIR / "embeddings.sqlite3"))
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.mock_mode = mock_mode if mock_mode is not None else os.getenv("EMBEDDING_MOCK_MODE", "0") == "1"
        self._model: Any | None = None
        self._model_lock = threading.RLock()
        self._cache_lock = threading.RLock()
        self._memory_cache: dict[str, list[float]] = {}
        self._db_initialised = False
        self._db_lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> EmbeddingService:
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @staticmethod
    def _stable_hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()

    def _normalise_text(self, text: str, role: str = "document") -> str:
        cleaned = re.sub(r"\s+", " ", str(text)).strip()
        if not cleaned:
            return ""
        if "bge" in self.model_name.lower():
            prefix = "query: " if role == "query" else "passage: "
            return f"{prefix}{cleaned}"
        return cleaned

    def _connect_cache(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.cache_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS embedding_cache (
                cache_key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._db_initialised = True
        return conn

    def _cache_get(self, cache_key: str) -> list[float] | None:
        with self._cache_lock:
            if cache_key in self._memory_cache:
                return list(self._memory_cache[cache_key])

        with self._db_lock:
            conn = self._connect_cache()
            try:
                row = conn.execute(
                    "SELECT payload FROM embedding_cache WHERE cache_key = ?",
                    (cache_key,),
                ).fetchone()
            finally:
                conn.close()

        if not row:
            return None
        try:
            payload = json.loads(row[0])
            embedding = [float(value) for value in payload]
        except Exception:
            return None

        with self._cache_lock:
            self._memory_cache[cache_key] = list(embedding)
        return embedding

    def _cache_set(self, cache_key: str, embedding: Sequence[float]) -> None:
        payload = json.dumps([float(value) for value in embedding])
        with self._cache_lock:
            self._memory_cache[cache_key] = [float(value) for value in embedding]

        with self._db_lock:
            conn = self._connect_cache()
            try:
                conn.execute(
                    """
                    INSERT INTO embedding_cache(cache_key, payload, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        payload = excluded.payload,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (cache_key, payload),
                )
                conn.commit()
                self._db_initialised = True
            finally:
                conn.close()

    def _load_sentence_transformer(self) -> Any:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:  # pragma: no cover - dependency failure is runtime only
            raise RuntimeError("sentence-transformers is required: pip install sentence-transformers") from exc

        candidates = (self.model_name, *self.fallback_models)
        errors: list[str] = []
        for candidate in candidates:
            try:
                model = SentenceTransformer(candidate)
                self.model_name = candidate
                logger.info("Loaded embedding model: %s", candidate)
                return model
            except Exception as exc:
                errors.append(f"{candidate}: {exc}")

        raise RuntimeError("Could not load any embedding model: " + "; ".join(errors))

    def load_model(self) -> Any:
        with self._model_lock:
            if self._model is None:
                if self.mock_mode:
                    self._model = _MockSentenceTransformer()
                    logger.info("Loaded deterministic mock embeddings")
                else:
                    self._model = self._load_sentence_transformer()
            return self._model

    def embed_text(self, text: str, role: str = "document") -> list[float]:
        return self.embed_texts([text], role=role)[0]

    def embed_texts(self, texts: Sequence[str], role: str = "document", batch_size: int = 64) -> list[list[float]]:
        if not texts:
            return []

        prepared: list[str] = [self._normalise_text(text, role=role) for text in texts]
        results: list[list[float] | None] = [None] * len(prepared)
        missing_indices: list[int] = []
        missing_texts: list[str] = []

        for index, text in enumerate(prepared):
            cache_key = self._stable_hash(f"{self.model_name}|{role}|{text}")
            cached = self._cache_get(cache_key)
            if cached is None:
                missing_indices.append(index)
                missing_texts.append(text)
                continue
            results[index] = cached

        if missing_texts:
            model = self.load_model()
            for start in range(0, len(missing_texts), batch_size):
                batch = missing_texts[start : start + batch_size]
                embeddings = self._encode_batch(model, batch)
                for offset, embedding in enumerate(embeddings):
                    original_index = missing_indices[start + offset]
                    cache_key = self._stable_hash(f"{self.model_name}|{role}|{batch[offset]}")
                    self._cache_set(cache_key, embedding)
                    results[original_index] = embedding

        return [list(embedding or []) for embedding in results]

    def _encode_batch(self, model: Any, texts: Sequence[str]) -> list[list[float]]:
        if self.mock_mode:
            return [_MockSentenceTransformer.encode_text(text) for text in texts]

        try:
            embeddings = model.encode(
                list(texts),
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
        except TypeError:
            embeddings = model.encode(
                list(texts),
                convert_to_numpy=True,
                show_progress_bar=False,
            )

        array = np.asarray(embeddings, dtype=np.float32)
        if array.ndim == 1:
            array = np.expand_dims(array, axis=0)

        norms = np.linalg.norm(array, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        array = array / norms
        return array.tolist()

    @staticmethod
    def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
        left_arr = np.asarray(left, dtype=np.float32)
        right_arr = np.asarray(right, dtype=np.float32)
        if left_arr.size == 0 or right_arr.size == 0:
            return 0.0
        denom = float(np.linalg.norm(left_arr) * np.linalg.norm(right_arr))
        if denom == 0:
            return 0.0
        return float(np.dot(left_arr, right_arr) / denom)

    def similarity_score(self, left: Sequence[float], right: Sequence[float]) -> float:
        return round(max(0.0, self.cosine_similarity(left, right)), 6)

    def extract_skill_candidates(self, text: str, limit: int = 8) -> list[str]:
        lowered = re.sub(r"[^a-z0-9+.#\-\s]", " ", str(text).lower())
        found: list[str] = []
        for skill in _DEFAULT_SKILL_TERMS:
            if skill in lowered and skill not in found:
                found.append(skill)
            if len(found) >= limit:
                return found

        tokens = [token for token in re.findall(r"[a-z][a-z0-9+.#\-]{2,}", lowered) if token not in {"the", "and", "for", "with", "from", "that", "this"}]
        for token in tokens:
            if token not in found:
                found.append(token)
            if len(found) >= limit:
                break
        return found

    def build_document(self, candidate_id: str, filename: str, text: str, metadata: dict[str, Any] | None = None) -> EmbeddedDocument:
        return EmbeddedDocument(
            candidate_id=candidate_id,
            filename=filename,
            text=text,
            metadata=metadata or {},
        )


class _MockSentenceTransformer:
    """Deterministic tiny embedding backend for tests and CI."""

    dimension = 384

    @staticmethod
    def encode_text(text: str) -> list[float]:
        tokens = re.findall(r"[a-z0-9+.#-]{2,}", text.lower())
        if not tokens:
            tokens = [text.lower()]

        array = np.zeros(_MockSentenceTransformer.dimension, dtype=np.float32)
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8", errors="ignore")).digest()
            index = int.from_bytes(digest[:4], "little") % _MockSentenceTransformer.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 1.0 + (digest[5] / 255.0)
            array[index] += sign * weight

        norm = float(np.linalg.norm(array)) or 1.0
        return (array / norm).tolist()

    def encode(self, texts: Iterable[str], **_: Any) -> list[list[float]]:
        return [self.encode_text(text) for text in texts]


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService.get_instance()

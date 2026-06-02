from __future__ import annotations

import logging
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from app.core.config import settings
from app.services.embedding_service import EmbeddingService, get_embedding_service

logger = logging.getLogger(__name__)


class VectorService:
    """Persistent ChromaDB wrapper for semantic resume retrieval."""

    _instance: VectorService | None = None
    _instance_lock = threading.RLock()

    def __init__(
        self,
        persist_dir: str | Path | None = None,
        collection_name: str = "resumes",
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.persist_dir = Path(persist_dir or settings.CHROMA_PERSIST_DIRECTORY)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.embedding_service = embedding_service or get_embedding_service()
        self._client: Any | None = None
        self._collection: Any | None = None
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> VectorService:
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _load_chromadb(self) -> Any:
        try:
            import chromadb  # type: ignore
        except ImportError as exc:  # pragma: no cover - runtime dependency only
            raise RuntimeError("chromadb is required: pip install chromadb") from exc
        return chromadb

    def initialize(self) -> Any:
        with self._lock:
            if self._collection is not None:
                return self._collection

            chromadb = self._load_chromadb()
            self._client = chromadb.PersistentClient(path=str(self.persist_dir))
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            return self._collection

    def _collection_or_raise(self) -> Any:
        return self.initialize()

    @staticmethod
    def _serialise_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
        cleaned: dict[str, Any] = {}
        for key, value in (metadata or {}).items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                cleaned[key] = value
            elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
                cleaned[key] = ", ".join(str(item) for item in value if item is not None)
            else:
                cleaned[key] = str(value)
        return cleaned

    @staticmethod
    def _candidate_id(filename: str, text: str) -> str:
        import hashlib

        digest = hashlib.sha256(f"{filename}|{text}".encode("utf-8", errors="ignore")).hexdigest()
        return digest[:24]

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def build_resume_metadata(
        candidate_id: str,
        filename: str,
        category: str | None,
        skills: Iterable[str] | str | None,
        uploaded_by: str | None = None,
        text_length: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if isinstance(skills, str):
            skills_value = skills
        elif skills is None:
            skills_value = ""
        else:
            skills_value = ", ".join(str(skill) for skill in skills if skill)

        metadata: dict[str, Any] = {
            "candidate_id": candidate_id,
            "filename": filename,
            "category": category or "",
            "skills": skills_value,
            "timestamp": VectorService._timestamp(),
        }
        if uploaded_by:
            metadata["uploaded_by"] = uploaded_by
        if text_length is not None:
            metadata["text_length"] = int(text_length)
        if extra:
            metadata.update(extra)
        return VectorService._serialise_metadata(metadata)

    def upsert_document(
        self,
        text: str,
        candidate_id: str | None,
        filename: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        collection = self._collection_or_raise()
        candidate_id = candidate_id or self._candidate_id(filename, text)
        embedding = self.embedding_service.embed_text(text, role="document")
        clean_metadata = self._serialise_metadata(metadata)

        collection.upsert(
            ids=[candidate_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[clean_metadata],
        )
        return {"candidate_id": candidate_id, "indexed": True, "metadata": clean_metadata}

    def upsert_documents(self, documents: list[dict[str, Any]]) -> dict[str, Any]:
        if not documents:
            return {"indexed": 0}

        collection = self._collection_or_raise()
        texts = [str(document.get("text", "")) for document in documents]
        embeddings = self.embedding_service.embed_texts(texts, role="document")
        ids: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for document in documents:
            candidate_id = str(document.get("candidate_id") or self._candidate_id(
                str(document.get("filename", "upload")),
                str(document.get("text", "")),
            ))
            ids.append(candidate_id)
            metadatas.append(self._serialise_metadata(document.get("metadata")))

        collection.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
        return {"indexed": len(documents)}

    def delete(self, candidate_id: str) -> None:
        collection = self._collection_or_raise()
        collection.delete(ids=[candidate_id])

    def search(
        self,
        query: str,
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        collection = self._collection_or_raise()
        query_embedding = self.embedding_service.embed_text(query, role="query")
        where_filter = self._serialise_metadata(where)
        query_kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where_filter:
            query_kwargs["where"] = where_filter

        results = collection.query(**query_kwargs)
        ids = results.get("ids", [[]])[0] if results else []
        documents = results.get("documents", [[]])[0] if results else []
        metadatas = results.get("metadatas", [[]])[0] if results else []
        distances = results.get("distances", [[]])[0] if results else []

        output: list[dict[str, Any]] = []
        for index, candidate_id in enumerate(ids):
            distance = float(distances[index]) if index < len(distances) else 1.0
            score = max(0.0, 1.0 - distance)
            metadata = metadatas[index] if index < len(metadatas) and isinstance(metadatas[index], dict) else {}
            document = str(documents[index]) if index < len(documents) else ""
            output.append(
                {
                    "candidate_id": candidate_id,
                    "filename": metadata.get("filename"),
                    "category": metadata.get("category", ""),
                    "skills": metadata.get("skills", ""),
                    "timestamp": metadata.get("timestamp"),
                    "score": round(score, 6),
                    "preview": document[:400],
                    "metadata": metadata,
                    "explanation": self.build_explanation(query, document, metadata, score),
                }
            )

        return sorted(output, key=lambda item: item["score"], reverse=True)

    def build_explanation(
        self,
        query: str,
        document: str,
        metadata: dict[str, Any],
        score: float,
    ) -> str:
        query_terms = set(re.findall(r"[a-z0-9+.#-]{3,}", query.lower()))
        skill_terms = set(re.findall(r"[a-z0-9+.#-]{3,}", str(metadata.get("skills", "")).lower()))
        document_terms = set(re.findall(r"[a-z0-9+.#-]{3,}", document.lower()))
        overlap = sorted((query_terms & document_terms) | (query_terms & skill_terms))[:6]
        if overlap:
            return f"Strong semantic alignment on {', '.join(overlap)} with similarity {score:.2f}."
        if metadata.get("skills"):
            return f"Resume skill profile ({metadata['skills']}) is semantically close to the query with similarity {score:.2f}."
        return f"Semantic similarity score {score:.2f} indicates related resume language and context."


def get_vector_service() -> VectorService:
    return VectorService.get_instance()

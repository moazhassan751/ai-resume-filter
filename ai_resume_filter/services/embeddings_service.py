"""
EmbeddingsService — sentence-transformers embeddings stored in ChromaDB.

Provides:
  load_model()          — load or initialise the SentenceTransformer
  init_chroma()         — connect/create a ChromaDB collection
  index_documents()     — upsert embeddings in batches
  query()               — cosine-similarity search
"""
from __future__ import annotations

import hashlib
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except ImportError as exc:
    raise RuntimeError(
        "sentence-transformers is required: pip install sentence-transformers"
    ) from exc

try:
    import chromadb  # type: ignore
except ImportError as exc:
    raise RuntimeError("chromadb is required: pip install chromadb") from exc

_DEFAULT_BATCH_SIZE = 256


class EmbeddingsService:
    def __init__(
        self,
        persist_dir: Optional[str | Path] = None,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        root = Path(__file__).resolve().parents[3]
        self.persist_dir = (
            Path(persist_dir) if persist_dir else root / "data" / "vector_db" / "chroma"
        )
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.client = None
        self.collection = None

    # ── Model ────────────────────────────────────────────────────────────────

    def load_model(self) -> SentenceTransformer:
        """
        Load the SentenceTransformer model.
        Raises RuntimeError if the model cannot be loaded — never silently falls back.
        """
        if self.model is None:
            try:
                self.model = SentenceTransformer(self.model_name)
                logger.info("Loaded embedding model: %s", self.model_name)
            except Exception as exc:
                raise RuntimeError(
                    f"Could not load embedding model '{self.model_name}': {exc}"
                ) from exc
        return self.model

    # ── ChromaDB ─────────────────────────────────────────────────────────────

    def init_chroma(self, collection_name: str = "resumes") -> Any:
        if self.client is None:
            self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        if self.collection is None or self.collection.name != collection_name:
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},  # explicit — don't rely on default
            )
        return self.collection

    # ── Indexing ─────────────────────────────────────────────────────────────

    def index_documents(
        self,
        docs: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        collection_name: str = "resumes",
        batch_size: int = _DEFAULT_BATCH_SIZE,
    ) -> Dict[str, int]:
        """
        Upsert documents into ChromaDB in batches.
        IDs are content-hashed by default — safe to call multiple times on the same data.
        """
        if not docs:
            return {"indexed": 0}

        coll = self.init_chroma(collection_name)
        model = self.load_model()  # raises if unavailable — no silent fallback

        if ids is None:
            ids = [
                hashlib.sha256(doc.encode()).hexdigest()[:16] for doc in docs
            ]
        if metadatas is None:
            metadatas = [{} for _ in docs]

        total = 0
        for start in range(0, len(docs), batch_size):
            end = start + batch_size
            batch_docs = docs[start:end]
            batch_ids = ids[start:end]
            batch_meta = metadatas[start:end]

            embeddings = (
                model.encode(batch_docs, show_progress_bar=False, convert_to_numpy=True)
                .tolist()
            )
            coll.upsert(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_meta,
                embeddings=embeddings,
            )
            total += len(batch_docs)
            logger.debug("Indexed batch %d–%d", start, end)

        logger.info("Indexed %d documents into '%s'", total, collection_name)
        return {"indexed": total}

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        collection_name: str = "resumes",
    ) -> List[Dict[str, Any]]:
        """
        Return the top-k most similar documents.
        Results include a `similarity` score in [0, 1] — higher is more similar.
        """
        coll = self.init_chroma(collection_name)
        model = self.load_model()

        q_emb = model.encode([query_text], convert_to_numpy=True)[0].tolist()

        results = coll.query(
            query_embeddings=[q_emb],
            n_results=top_k,
            include=["metadatas", "documents", "distances"],
        )

        out = []
        for i in range(len(results["ids"][0])):
            cosine_distance = results["distances"][0][i]
            out.append(
                {
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "similarity": round(1 - cosine_distance, 4),  # convert distance → score
                }
            )

        return sorted(out, key=lambda x: x["similarity"], reverse=True)
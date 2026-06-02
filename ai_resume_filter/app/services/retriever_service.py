from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Iterable, List, Optional

from app.services.vector_service import get_vector_service
from app.services.text_windowing import compress_text_for_query, estimate_token_count

logger = logging.getLogger(__name__)


class RetrieverService:
    """High-level retrieval helpers for RAG.

    - Uses VectorService.search under the hood (Chroma DB)
    - Performs deduplication, metadata filtering, and context compression
    """

    _instance: RetrieverService | None = None

    def __init__(self, vector_service=None, max_context_tokens: int = 650):
        self.vector_service = vector_service or get_vector_service()
        self.max_context_tokens = int(max_context_tokens)

    @classmethod
    def get_instance(cls) -> RetrieverService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        where: Optional[Dict[str, Any]] = None,
        dedup: bool = True,
    ) -> List[Dict[str, Any]]:
        """Retrieve and post-process results.

        Returns a list of candidates with compressed `context` strings and metadata.
        """
        # VectorService is synchronous (wrap via to_thread)
        raw = await asyncio.to_thread(self.vector_service.search, query, top_k=top_k, where=where)

        seen: set[str] = set()
        out: List[Dict[str, Any]] = []
        for item in raw:
            cid = item.get("candidate_id") or item.get("id")
            if dedup and cid in seen:
                continue
            seen.add(cid)

            doc = item.get("preview", "") or item.get("document", "") or item.get("metadata", {}).get("extracted_text", "")
            window = compress_text_for_query(
                query=query,
                text=doc or "",
                max_tokens=self.max_context_tokens,
                chunk_tokens=max(120, self.max_context_tokens // 3),
                overlap=24,
            )
            context = window.text

            out.append(
                {
                    "candidate_id": cid,
                    "filename": item.get("filename") or item.get("metadata", {}).get("filename"),
                    "category": item.get("category") or item.get("metadata", {}).get("category", ""),
                    "skills": item.get("skills") or item.get("metadata", {}).get("skills", ""),
                    "score": float(item.get("score", 0.0)),
                    "context": context,
                    "context_token_count": estimate_token_count(context),
                    "context_chunk_count": window.chunk_count,
                    "compression_ratio": window.compression_ratio,
                    "metadata": item.get("metadata", {}),
                }
            )

        # Ensure we return at most top_k
        return out[:top_k]


def get_retriever_service() -> RetrieverService:
    return RetrieverService.get_instance()

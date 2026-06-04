from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - SDK is expected in production, tests can still patch _call_gemini
    genai = None

from app.services.retriever_service import get_retriever_service
from app.services.vector_service import get_vector_service
from app.services.embedding_service import get_embedding_service
from app.services.text_windowing import estimate_token_count, compress_text_for_query

logger = logging.getLogger(__name__)


class RAGService:
    _instance: RAGService | None = None

    def __init__(self, gemini_api_key: Optional[str] = None):
        self.retriever = get_retriever_service()
        self.vector = get_vector_service()
        self.embedding = get_embedding_service()
        self.gemini_api_key = gemini_api_key or os.environ.get("GOOGLE_API_KEY")
        self.max_prompt_tokens = int(os.environ.get("RAG_MAX_PROMPT_TOKENS", 4500))
        self.max_candidate_tokens = int(os.environ.get("RAG_MAX_CANDIDATE_TOKENS", 260))

    @classmethod
    def get_instance(cls) -> RAGService:
        if cls._instance is None:
            cls._instance = cls()
        else:
            # Refresh dependent services so tests that monkeypatch retriever/vector/embed
            # functions pick up the patched instances without requiring a full process restart.
            try:
                cls._instance.retriever = get_retriever_service()
                cls._instance.vector = get_vector_service()
                cls._instance.embedding = get_embedding_service()
            except Exception:
                # If refreshing fails, keep existing instance to avoid breaking runtime.
                logger.debug("Failed to refresh RAGService dependencies; continuing with existing ones")
        return cls._instance

    async def analyze(self, job_description: str, top_k: int = 10, requester: Optional[str] = None) -> Dict[str, Any]:
        t0 = time.perf_counter()
        try:
            retrieval_start = time.perf_counter()
            candidates = await self.retriever.retrieve(job_description, top_k=top_k)
            retrieval_time = (time.perf_counter() - retrieval_start) * 1000.0
        except Exception as exc:
            logger.exception("Retriever failed in analyze: %s", exc)
            # safe fallback empty candidates
            candidates = []
            retrieval_time = 0.0

        # Build prompt context with token budgeting.
        context_blocks: List[str] = []
        prompt_budget_remaining = self.max_prompt_tokens
        for c in candidates:
            context_window = compress_text_for_query(
                query=job_description,
                text=c.get("context") or "",
                max_tokens=self.max_candidate_tokens,
                chunk_tokens=max(96, self.max_candidate_tokens // 2),
                overlap=18,
            )
            block = (
                f"Candidate ID: {c['candidate_id']}\n"
                f"Filename: {c.get('filename')}\n"
                f"Category: {c.get('category')}\n"
                f"Skills: {c.get('skills')}\n"
                f"Score: {c.get('score')}\n"
                f"Context Tokens: {context_window.token_count}/{context_window.source_token_count}\n"
                f"Context:\n{context_window.text}\n---\n"
            )
            block_tokens = estimate_token_count(block)
            if block_tokens > prompt_budget_remaining and context_blocks:
                break
            if block_tokens > prompt_budget_remaining:
                # last attempt: shorten context more aggressively
                compact_context = compress_text_for_query(
                    query=job_description,
                    text=context_window.text,
                    max_tokens=max(80, prompt_budget_remaining // 4),
                    chunk_tokens=max(48, self.max_candidate_tokens // 4),
                    overlap=12,
                )
                block = (
                    f"Candidate ID: {c['candidate_id']}\n"
                    f"Filename: {c.get('filename')}\n"
                    f"Category: {c.get('category')}\n"
                    f"Skills: {c.get('skills')}\n"
                    f"Score: {c.get('score')}\n"
                    f"Context Tokens: {compact_context.token_count}/{compact_context.source_token_count}\n"
                    f"Context:\n{compact_context.text}\n---\n"
                )
                block_tokens = estimate_token_count(block)
                if block_tokens > prompt_budget_remaining:
                    continue
            prompt_budget_remaining -= block_tokens
            context_blocks.append(block)

        system_instructions = (
            "You are an assistant that evaluates and ranks job candidates against a job description. "
            "Respond ONLY in JSON following the schema described. Provide `ranked_candidates` (list), `summary` (string), "
            "`recommended_hires` (list of candidate_id), and `skill_gaps` (list).")

        json_schema_instructions = (
            "Output JSON fields:\n"
            "ranked_candidates: [{candidate_id: str, score: number, reasons: [str], strengths: [str], missing_skills: [str]}],\n"
            "summary: str,\nrecommended_hires: [candidate_id],\nskill_gaps: [{skill: str, missing_from: [candidate_id]}]"
        )

        prompt = (
            f"SYSTEM: {system_instructions}\n{json_schema_instructions}\n\nJOB DESCRIPTION:\n{job_description}\n\nCONTEXT:\n"
            + "\n".join(context_blocks)
        )

        ai_start = time.perf_counter()
        gemini_resp = None
        use_fallback = False
        try:
            gemini_resp = await asyncio.to_thread(self._call_gemini, prompt)
        except Exception as exc:  # fallback to heuristic
            logger.exception("Gemini call failed, using fallback heuristic: %s", exc)
            use_fallback = True

        ai_time = (time.perf_counter() - ai_start) * 1000.0

        # Try parse response
        parsed: Optional[Dict[str, Any]] = None
        if not use_fallback and gemini_resp:
            # gemini_resp expected to be text; try to extract JSON
            try:
                # direct JSON
                parsed = json.loads(gemini_resp)
            except Exception:
                # try to find first JSON object in text
                import re

                m = re.search(r"\{.*\}", gemini_resp, flags=re.S)
                if m:
                    try:
                        parsed = json.loads(m.group(0))
                    except Exception:
                        parsed = None

        if parsed is None:
            use_fallback = True

        try:
            if use_fallback:
                # Simple fallback: rank by score and return light summary
                ranked = []
                for c in candidates:
                    ranked.append(
                        {
                            "candidate_id": c["candidate_id"],
                            "score": c["score"],
                            "reasons": [f"Vector score {c['score']:.3f}"],
                            "strengths": (c.get("skills") or "").split(",")[:3],
                            "missing_skills": [],
                        }
                    )

                ranked_sorted = sorted(ranked, key=lambda r: r["score"], reverse=True)
                result = {
                    "ranked_candidates": ranked_sorted,
                    "summary": f"Fallback ranking used; {len(ranked_sorted)} candidates scored by vector similarity.",
                    "recommended_hires": [r["candidate_id"] for r in ranked_sorted[:3]],
                    "skill_gaps": [],
                    "diagnostics": {
                        "retrieval_ms": retrieval_time,
                        "ai_ms": ai_time,
                        "total_ms": (time.perf_counter() - t0) * 1000.0,
                        "used_model": "gemini-1.5-flash" if self.gemini_api_key else "none",
                        "fallback": True,
                    },
                }
                return result
        except Exception:
            # protect against unexpected errors while constructing fallback
            logger.exception("Error building fallback response")
            return {
                "ranked_candidates": [],
                "summary": "Fallback due to internal error",
                "recommended_hires": [],
                "skill_gaps": [],
                "diagnostics": {"retrieval_ms": retrieval_time, "ai_ms": 0.0, "total_ms": (time.perf_counter() - t0) * 1000.0, "used_model": None, "fallback": True},
            }

        if use_fallback:
            # Simple fallback: rank by score and return light summary
            ranked = []
            for c in candidates:
                ranked.append(
                    {
                        "candidate_id": c["candidate_id"],
                        "score": c["score"],
                        "reasons": [f"Vector score {c['score']:.3f}"],
                        "strengths": (c.get("skills") or "").split(",")[:3],
                        "missing_skills": [],
                    }
                )

            ranked_sorted = sorted(ranked, key=lambda r: r["score"], reverse=True)
            result = {
                "ranked_candidates": ranked_sorted,
                "summary": f"Fallback ranking used; {len(ranked_sorted)} candidates scored by vector similarity.",
                "recommended_hires": [r["candidate_id"] for r in ranked_sorted[:3]],
                "skill_gaps": [],
                "diagnostics": {
                    "retrieval_ms": retrieval_time,
                    "ai_ms": ai_time,
                    "total_ms": (time.perf_counter() - t0) * 1000.0,
                    "used_model": "gemini-1.5-flash" if self.gemini_api_key else "none",
                    "fallback": True,
                },
            }
            return result

        # success path
        result = {
            "ranked_candidates": parsed.get("ranked_candidates", []),
            "summary": parsed.get("summary", ""),
            "recommended_hires": parsed.get("recommended_hires", []),
            "skill_gaps": parsed.get("skill_gaps", []),
            "diagnostics": {
                "retrieval_ms": retrieval_time,
                "ai_ms": ai_time,
                "total_ms": (time.perf_counter() - t0) * 1000.0,
                "used_model": "gemini-1.5-flash",
                "fallback": False,
                "prompt_tokens_estimated": estimate_token_count(prompt),
                "context_blocks": len(context_blocks),
            },
        }
        return result

    def _call_gemini(self, prompt: str) -> str:
        """Minimal Gemini 1.5 Flash call wrapper using the official SDK.

        Tests can patch this method directly. If the SDK is unavailable, we fail
        fast so the caller can fall back to the heuristic path.
        """
        if not self.gemini_api_key:
            raise RuntimeError("No GOOGLE_API_KEY configured")

        if genai is None:
            raise RuntimeError("google-generativeai SDK is not available")

        genai.configure(api_key=self.gemini_api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 1024,
            },
        )

        text = getattr(response, "text", None)
        if text:
            return text

        candidates = getattr(response, "candidates", None) or []
        if candidates:
            parts: List[str] = []
            for candidate in candidates:
                content = getattr(candidate, "content", None)
                if content and getattr(content, "parts", None):
                    for part in content.parts:
                        piece = getattr(part, "text", None)
                        if piece:
                            parts.append(piece)
            if parts:
                return "\n".join(parts)

        return json.dumps(response.to_dict() if hasattr(response, "to_dict") else {})


def get_rag_service() -> RAGService:
    return RAGService.get_instance()

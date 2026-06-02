from __future__ import annotations

import math
import hashlib
import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel

from app.services.embedding_service import get_embedding_service
from app.services.retriever_service import get_retriever_service
from app.services.text_windowing import compress_text_for_query, estimate_token_count

logger = logging.getLogger(__name__)


class CandidateRank(BaseModel):
    candidate_id: str
    candidate_name: Optional[str] = None
    score: float
    strengths: List[str]
    missing_skills: List[str]
    recommendation: str
    details: Dict[str, Any] = {}


def _normalize(scores: List[float], scale_min: float = 0.0, scale_max: float = 100.0) -> List[float]:
    if not scores:
        return []
    smin = min(scores)
    smax = max(scores)
    if math.isclose(smin, smax):
        # all same -> mid scores
        mid = (scale_min + scale_max) / 2.0
        return [mid for _ in scores]
    out = []
    for s in scores:
        val = (s - smin) / (smax - smin)
        out.append(scale_min + val * (scale_max - scale_min))
    return out


def _tokenize_keywords(text: str) -> List[str]:
    # lightweight keyword tokenization — lowercase, split on non-alpha
    import re

    toks = re.findall(r"[a-zA-Z0-9+#+\-]+", text.lower())
    return toks


class RankingService:
    """Production-grade ranking combining semantic, ATS, skills, experience, education.

    Weights (configurable):
      semantic: 0.40
      ats: 0.25
      skill_overlap: 0.20
      experience: 0.10
      education: 0.05
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        default = {
            "semantic": 0.40,
            "ats": 0.25,
            "skill": 0.20,
            "experience": 0.10,
            "education": 0.05,
        }
        self.weights = weights or default
        self.embedding = get_embedding_service()
        self.retriever = get_retriever_service()

    def score_candidates(
        self,
        job_description: str,
        candidates: Iterable[Dict[str, Any]],
    ) -> List[CandidateRank]:
        """Rank a batch of candidate dicts.

        Candidate dict expected keys: `candidate_id`, `text` (full resume text), `metadata` (dict with `experience_years`, `education`, `skills` list or comma string)
        """
        cand_list = list(candidates)
        if not cand_list:
            return []

        # Compute semantic similarities via embeddings
        job_emb = self.embedding.embed_text(job_description)
        candidate_windows = []
        texts = []
        for c in cand_list:
            raw_text = c.get("text", c.get("context", "")) or ""
            window = compress_text_for_query(
                query=job_description,
                text=raw_text,
                max_tokens=900,
                chunk_tokens=220,
                overlap=40,
            )
            candidate_windows.append(window)
            texts.append(window.text)
        emb_list = self.embedding.embed_texts(texts)

        semantic_scores: List[float] = []
        for e in emb_list:
            # cosine similarity
            dot = sum(a * b for a, b in zip(job_emb, e))
            norm_a = math.sqrt(sum(x * x for x in job_emb))
            norm_b = math.sqrt(sum(x * x for x in e))
            sim = dot / (max(norm_a * norm_b, 1e-8))
            semantic_scores.append(float(sim))

        # ATS keyword score
        job_keywords = set(_tokenize_keywords(job_description))
        ats_scores: List[float] = []
        skill_overlaps: List[float] = []
        exp_scores: List[float] = []
        edu_scores: List[float] = []

        for idx, c in enumerate(cand_list):
            meta = c.get("metadata", {}) or {}
            # ATS: measure proportion of job keywords present in resume text
            text = texts[idx].lower()
            tokens = set(_tokenize_keywords(text))
            if not job_keywords:
                ats = 0.0
            else:
                matched = job_keywords.intersection(tokens)
                ats = len(matched) / max(len(job_keywords), 1)
            ats_scores.append(float(ats))

            # Skills
            skills = meta.get("skills") or meta.get("skill_list") or ""
            if isinstance(skills, str):
                skill_list = [s.strip().lower() for s in skills.split(",") if s.strip()]
            elif isinstance(skills, list):
                skill_list = [s.strip().lower() for s in skills]
            else:
                skill_list = []
            overlap = 0.0
            if job_keywords and skill_list:
                overlap = len(set(skill_list).intersection(job_keywords)) / max(len(job_keywords), 1)
            skill_overlaps.append(float(overlap))

            # Experience relevance: prefer experience_years field or estimate from text
            years = None
            if "experience_years" in meta:
                try:
                    years = float(meta.get("experience_years") or 0.0)
                except Exception:
                    years = None
            if years is None:
                # lightweight heuristic: look for patterns like 'X years'
                import re

                m = re.search(r"(\d+)\+?\s+years", text)
                years = float(m.group(1)) if m else 0.0
            # normalize years to 0-1 using 0-20 range
            exp_scores.append(min(max(years / 20.0, 0.0), 1.0))

            # Education relevance: basic match on degree keywords
            edu = meta.get("education") or ""
            edu_low = (edu or "").lower()
            score_edu = 0.0
            if "phd" in edu_low:
                score_edu = 1.0
            elif "master" in edu_low or "msc" in edu_low or "ms" in edu_low:
                score_edu = 0.8
            elif "bachelor" in edu_low or "bs" in edu_low or "ba" in edu_low:
                score_edu = 0.6
            edu_scores.append(float(score_edu))

        # Normalize component scores
        sem_norm = _normalize(semantic_scores, 0.0, 1.0)
        ats_norm = _normalize(ats_scores, 0.0, 1.0)
        skill_norm = _normalize(skill_overlaps, 0.0, 1.0)
        exp_norm = _normalize(exp_scores, 0.0, 1.0)
        edu_norm = _normalize(edu_scores, 0.0, 1.0)

        composite: List[Tuple[int, float]] = []
        details_list: List[Dict[str, Any]] = []
        for i, c in enumerate(cand_list):
            w = self.weights
            score = (
                sem_norm[i] * w.get("semantic", 0.0)
                + ats_norm[i] * w.get("ats", 0.0)
                + skill_norm[i] * w.get("skill", 0.0)
                + exp_norm[i] * w.get("experience", 0.0)
                + edu_norm[i] * w.get("education", 0.0)
            )
            composite.append((i, float(score)))
            details_list.append(
                {
                    "semantic": sem_norm[i],
                    "ats": ats_norm[i],
                    "skill": skill_norm[i],
                    "experience": exp_norm[i],
                    "education": edu_norm[i],
                }
            )

        # Convert to normalized 0-100
        raw_scores = [s for _, s in composite]
        norm100 = _normalize(raw_scores, 0.0, 100.0)

        ranked: List[CandidateRank] = []
        for rank_idx, (idx, _) in enumerate(sorted(composite, key=lambda x: x[1], reverse=True)):
            c = cand_list[idx]
            score100 = float(norm100[idx])
            meta = c.get("metadata", {}) or {}

            # strengths: pick top skill tokens
            skills_field = meta.get("skills") or ""
            if isinstance(skills_field, str):
                skills_list = [s.strip() for s in skills_field.split(",") if s.strip()]
            else:
                skills_list = list(skills_field)

            # missing skills: job keywords not in candidate skills
            missing = [k for k in _tokenize_keywords(job_description) if k not in [s.lower() for s in skills_list]]

            # recommendation label
            rec = "No Match"
            if score100 >= 85:
                rec = "Strong Match"
            elif score100 >= 70:
                rec = "Good Match"
            elif score100 >= 50:
                rec = "Consider"
            else:
                rec = "Weak Match"

            reasons = []
            d = details_list[idx]
            if d["semantic"] > 0.6:
                reasons.append("High semantic similarity to job description")
            if d["ats"] > 0.5:
                reasons.append("Keywords match the job description")
            if d["skill"] > 0.4:
                reasons.append("Good skill overlap with required skills")
            if d["experience"] > 0.6:
                reasons.append("Relevant years of experience")
            if d["education"] > 0.7:
                reasons.append("Strong educational background")

            ranked.append(
                CandidateRank(
                    candidate_id=str(c.get("candidate_id") or hashlib.sha256(c.get("text", "").encode()).hexdigest()),
                    candidate_name=meta.get("name") or meta.get("candidate_name"),
                    score=round(score100, 2),
                    strengths=skills_list[:5],
                    missing_skills=missing[:10],
                    recommendation=rec,
                    details={
                        "component_scores": d,
                        "raw_score": raw_scores[idx],
                        "compressed_text_tokens": estimate_token_count(texts[idx]),
                        "source_text_tokens": candidate_windows[idx].source_token_count,
                        "compression_ratio": candidate_windows[idx].compression_ratio,
                    },
                )
            )

        return ranked


_global_ranking_service: Optional[RankingService] = None


def get_ranking_service() -> RankingService:
    global _global_ranking_service
    if _global_ranking_service is None:
        _global_ranking_service = RankingService()
    return _global_ranking_service

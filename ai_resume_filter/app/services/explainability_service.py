from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, List, Optional

from app.services.model_service import predict
from app.services.insights_service import tokenize as insights_tokenize


def _tokenize(text: str) -> List[str]:
    return insights_tokenize(text)


def _tf(tokens: List[str]) -> Counter:
    return Counter(tokens)


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _approximate_shap(features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Lightweight SHAP-style approximation: use signed importance relative to prediction signal.
    if not features:
        return []
    total = sum(abs(float(f.get("importance", 0.0))) for f in features) or 1.0
    shap_values = []
    for feature in features:
        importance = float(feature.get("importance", 0.0))
        shap_values.append({
            "feature": feature.get("feature"),
            "shap_value": round(importance / total, 4),
            "direction": "positive" if importance >= 0 else "negative",
        })
    return shap_values


def build_explainability_payload(
    resume_text: str,
    job_description: Optional[str] = None,
    category_hint: Optional[str] = None,
) -> Dict[str, Any]:
    prediction = predict({"resume_text": resume_text, "category_hint": category_hint})
    confidence = float(prediction.get("confidence") or 0.0)
    tokens = _tokenize(resume_text)
    job_tokens = _tokenize(job_description or "")

    resume_counts = _tf(tokens)
    job_counts = _tf(job_tokens)
    common = sorted(set(resume_counts) & set(job_counts), key=lambda term: (-min(resume_counts[term], job_counts[term]), term))

    tfidf_features: List[Dict[str, Any]] = []
    for term in common[:12]:
        tf = resume_counts[term] / max(len(tokens), 1)
        job_boost = job_counts[term] / max(len(job_tokens), 1) if job_tokens else 0.0
        importance = round((0.6 * tf + 0.4 * job_boost) * confidence * 100, 4)
        tfidf_features.append({
            "feature": term,
            "importance": importance,
            "resume_frequency": resume_counts[term],
            "job_frequency": job_counts.get(term, 0),
        })

    top_keywords = prediction.get("top_keywords") or [item["feature"] for item in tfidf_features[:5]]
    feature_importance = sorted(
        [
            {
                "feature": feature["feature"],
                "importance": feature["importance"],
                "direction": "positive" if feature["importance"] >= 0 else "negative",
            }
            for feature in tfidf_features
        ],
        key=lambda item: abs(item["importance"]),
        reverse=True,
    )

    semantic_overlap = _safe_div(len(set(tokens) & set(job_tokens)), max(len(set(job_tokens)), 1)) if job_tokens else 0.0
    skill_gaps = [term for term in dict.fromkeys(job_tokens) if term not in set(tokens)][:15]

    shap_explanations = _approximate_shap(tfidf_features)

    return {
        "prediction": prediction.get("prediction"),
        "prediction_confidence": confidence,
        "semantic_overlap": round(semantic_overlap, 4),
        "top_tfidf_features": tfidf_features[:10],
        "feature_importance": feature_importance[:10],
        "shap_explanations": shap_explanations[:10],
        "top_keywords": top_keywords[:10],
        "matched_terms": common[:12],
        "skill_gaps": skill_gaps,
        "summary": prediction.get("top_keywords") and f"Top extracted signals: {', '.join(top_keywords[:5])}" or "Model explainability computed successfully.",
    }


def build_recruiter_insights(
    ranking_results: Optional[List[Dict[str, Any]]] = None,
    upload_metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ranking_results = ranking_results or []
    upload_metrics = upload_metrics or {}
    score_distribution = [float(item.get("score", 0.0)) for item in ranking_results]
    avg_score = sum(score_distribution) / max(len(score_distribution), 1)
    strong_matches = sum(1 for score in score_distribution if score >= 85)
    watchlist = sum(1 for score in score_distribution if 50 <= score < 85)
    weak = sum(1 for score in score_distribution if score < 50)

    return {
        "summary": {
            "average_score": round(avg_score, 2),
            "strong_matches": strong_matches,
            "watchlist": watchlist,
            "weak_matches": weak,
        },
        "upload_metrics": upload_metrics,
        "hiring_funnel": {
            "applied": int(upload_metrics.get("applied", len(ranking_results))),
            "screened": int(upload_metrics.get("screened", len(ranking_results))),
            "interviewed": int(upload_metrics.get("interviewed", max(strong_matches, 0))),
            "hired": int(upload_metrics.get("hired", 0)),
        },
        "score_breakdown": {
            "semantic_similarity": round(float(upload_metrics.get("semantic_similarity", 0.0)), 3),
            "ats_keyword": round(float(upload_metrics.get("ats_keyword", 0.0)), 3),
            "skill_overlap": round(float(upload_metrics.get("skill_overlap", 0.0)), 3),
            "experience_relevance": round(float(upload_metrics.get("experience_relevance", 0.0)), 3),
            "education_relevance": round(float(upload_metrics.get("education_relevance", 0.0)), 3),
        },
    }

from __future__ import annotations

from typing import Iterable, List

import math


def precision_at_k(relevant: Iterable[int], predicted: Iterable[int], k: int) -> float:
    pred_k = list(predicted)[:k]
    if not pred_k:
        return 0.0
    rel_set = set(relevant)
    hits = sum(1 for p in pred_k if p in rel_set)
    return hits / len(pred_k)


def dcg_at_k(rel_scores: List[float], k: int) -> float:
    rel = rel_scores[:k]
    return sum((2 ** r - 1) / math.log2(i + 2) for i, r in enumerate(rel))


def ndcg_at_k(relevant_scores: List[float], k: int) -> float:
    if not relevant_scores:
        return 0.0
    dcg = dcg_at_k(relevant_scores, k)
    ideal = sorted(relevant_scores, reverse=True)
    idcg = dcg_at_k(ideal, k)
    return dcg / idcg if idcg > 0 else 0.0


def similarity_diagnostics(query_embedding: List[float], candidate_embeddings: List[List[float]]):
    # returns list of cosine similarities
    import math

    sims = []
    norm_q = math.sqrt(sum(x * x for x in query_embedding))
    for e in candidate_embeddings:
        dot = sum(a * b for a, b in zip(query_embedding, e))
        norm_e = math.sqrt(sum(x * x for x in e))
        sims.append(dot / (max(norm_q * norm_e, 1e-8)))
    return sims

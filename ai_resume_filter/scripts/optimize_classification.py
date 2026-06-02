"""
optimize_classification.py

Run quick hyperparameter optimization for TF-IDF + LogisticRegression
and a transformer-embedding baseline using the existing EmbeddingsService.

Outputs saved to `data/models/optimized/`:
  - best_tfidf_model.pkl
  - best_tfidf_vectorizer.pkl
  - embedding_model.pkl
  - metrics.json

Usage:
  python scripts/optimize_classification.py

This script is intentionally conservative in search size to keep runtimes
reasonable on a developer laptop.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

import sys
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, f1_score, classification_report
from sklearn.model_selection import train_test_split

from ai_resume_filter.services.ml_pipeline import load_data, _clean_text
from ai_resume_filter.services.embeddings_service import EmbeddingsService

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def run_tfidf_search(df: pd.DataFrame, out_dir: Path) -> Dict[str, Any]:
    # Detect text/label columns by common names
    TEXT_COLS = ["text", "Text", "Resume_str"]
    LABEL_COLS = ["label", "category", "Category", "Domain"]
    text_col = next((c for c in TEXT_COLS if c in df.columns), None)
    label_col = next((c for c in LABEL_COLS if c in df.columns), None)
    if not text_col or not label_col:
        raise ValueError(f"Could not find text/label columns in dataset. Available: {list(df.columns)}")

    data = df[[text_col, label_col]].dropna()
    data = data[data[text_col].str.len() > 20].copy()
    data[text_col] = data[text_col].astype(str).apply(_clean_text)

    X = data[text_col].values
    y = data[label_col].astype(str).values

    # simple CV
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)

    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(stop_words="english")),
            ("clf", LogisticRegression(max_iter=1000, multi_class="auto")),
        ]
    )

    param_dist = {
        "tfidf__ngram_range": [(1, 1), (1, 2)],
        "tfidf__max_features": [10000, 20000, 50000],
        "tfidf__min_df": [1, 2],
        "clf__C": [0.1, 1.0, 5.0],
        "clf__solver": ["liblinear", "saga"],
        "clf__class_weight": [None, "balanced"],
    }

    search = RandomizedSearchCV(
        pipeline,
        param_distributions=param_dist,
        n_iter=12,
        scoring="f1_macro",
        cv=cv,
        verbose=1,
        n_jobs=-1,
        random_state=42,
    )

    logger.info("Starting TF-IDF randomized search (this may take a few minutes)...")
    search.fit(X, y)
    logger.info("Search complete. Best score: %.4f", search.best_score_)

    # Save artifacts
    out_dir.mkdir(parents=True, exist_ok=True)
    tf_model_path = out_dir / "best_tfidf_model.pkl"
    tf_vec_path = out_dir / "best_tfidf_vectorizer.pkl"
    joblib.dump(search.best_estimator_.named_steps["clf"], tf_model_path)
    joblib.dump(search.best_estimator_.named_steps["tfidf"], tf_vec_path)

    return {
        "type": "tfidf_search",
        "best_score": float(search.best_score_),
        "best_params": search.best_params_,
        "model_path": str(tf_model_path),
        "vectorizer_path": str(tf_vec_path),
    }


def run_embedding_baseline(df: pd.DataFrame, out_dir: Path) -> Dict[str, Any]:
    TEXT_COLS = ["text", "Text", "Resume_str"]
    LABEL_COLS = ["label", "category", "Category", "Domain"]
    text_col = next((c for c in TEXT_COLS if c in df.columns), None)
    label_col = next((c for c in LABEL_COLS if c in df.columns), None)
    if not text_col or not label_col:
        raise ValueError(f"Could not find text/label columns in dataset. Available: {list(df.columns)}")

    data = df[[text_col, label_col]].dropna()
    data = data[data[text_col].str.len() > 20].copy()
    data[text_col] = data[text_col].astype(str).apply(_clean_text)

    X = data[text_col].values
    y = data[label_col].astype(str).values

    # Drop extremely rare classes
    classes, counts = np.unique(y, return_counts=True)
    valid_mask = np.isin(y, classes[counts >= 2])
    X = X[valid_mask]
    y = y[valid_mask]

    svc = EmbeddingsService()
    model = svc.load_model()

    logger.info("Computing embeddings for %d samples...", len(X))
    # Use model.encode in batches to avoid large memory spikes
    batch_size = 256
    embs = []
    for i in range(0, len(X), batch_size):
        batch = X[i : i + batch_size].tolist()
        e = model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
        embs.append(e)
    X_emb = np.vstack(embs)

    # Train / evaluate with a holdout split
    X_tr, X_te, y_tr, y_te = train_test_split(
        X_emb, y, test_size=0.2, stratify=y, random_state=42
    )

    clf = LogisticRegression(max_iter=2000, solver="lbfgs", multi_class="multinomial")
    clf.fit(X_tr, y_tr)

    preds = clf.predict(X_te)
    acc = accuracy_score(y_te, preds)
    f1m = f1_score(y_te, preds, average="macro", zero_division=0)

    emb_model_path = out_dir / "embedding_model.pkl"
    joblib.dump(clf, emb_model_path)

    return {
        "type": "embedding_baseline",
        "accuracy": float(acc),
        "f1_macro": float(f1m),
        "model_path": str(emb_model_path),
        "n_samples": int(len(X_emb)),
    }


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    ds_path = root / "data" / "cache" / "tasks" / "classification_dataset.csv"
    if not ds_path.exists():
        raise SystemExit(f"Dataset not found: {ds_path}")

    df = load_data(ds_path)

    out_dir = root / "data" / "models" / "optimized"
    out_dir.mkdir(parents=True, exist_ok=True)

    results: Dict[str, Any] = {}

    try:
        results["tfidf"] = run_tfidf_search(df, out_dir)
    except Exception as exc:
        logger.exception("TF-IDF search failed: %s", exc)
        results["tfidf_error"] = str(exc)

    try:
        results["embedding"] = run_embedding_baseline(df, out_dir)
    except Exception as exc:
        logger.exception("Embedding baseline failed: %s", exc)
        results["embedding_error"] = str(exc)

    # Save results summary
    metrics_path = out_dir / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info("Optimization complete. Results saved to %s", out_dir)


if __name__ == "__main__":
    main()

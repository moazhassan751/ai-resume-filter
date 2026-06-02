"""
ML pipeline utilities:
  load_data()       — read CSV into DataFrame
  train_baseline()  — TF-IDF + LogisticRegression
  save_artifacts()  — persist model / vectorizer / metrics
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.svm import LinearSVC

logger = logging.getLogger(__name__)


# ── Text cleaning ─────────────────────────────────────────────────────────────

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_EMAIL_RE = re.compile(r"\S+@\S+\.\S+")
_WHITESPACE_RE = re.compile(r"\s+")


def _clean_text(text: str) -> str:
    """Strip URLs, emails, and collapse whitespace."""
    text = _URL_RE.sub(" ", text)
    text = _EMAIL_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


# ── Data loading ──────────────────────────────────────────────────────────────

def load_data(path: Path) -> pd.DataFrame:
    """
    Read a CSV into a DataFrame.
    Raises FileNotFoundError or ValueError with a clear message on failure.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        raise ValueError(f"Could not parse CSV at {path}: {exc}") from exc
    if df.empty:
        raise ValueError(f"CSV at {path} is empty")
    logger.info("Loaded dataset: %s (%d rows, %d cols)", path.name, len(df), len(df.columns))
    return df


# ── Training ──────────────────────────────────────────────────────────────────

def train_baseline(
    df: pd.DataFrame,
    text_col: str = "text",
    label_col: str = "category",
    test_size: float = 0.2,
    random_state: int = 42,
) -> Dict[str, Any]:
    """
    Train a small set of TF-IDF text classifiers and return the best one.
    Returns {"model", "vectorizer", "metrics"}.
    """
    if text_col not in df.columns:
        raise ValueError(
            f"Text column '{text_col}' not found. Available: {list(df.columns)}"
        )
    if label_col not in df.columns or df[label_col].isnull().all():
        raise ValueError(f"Label column '{label_col}' is missing or entirely null.")

    data = df[[text_col, label_col]].dropna()
    data = data[data[text_col].str.len() > 20].copy()

    # Clean text before vectorizing
    data[text_col] = data[text_col].astype(str).apply(_clean_text)

    X = data[text_col].values
    y = data[label_col].astype(str).values

    classes, counts = np.unique(y, return_counts=True)
    if len(classes) < 2:
        raise ValueError("Need at least 2 classes to train a classifier.")

    # Drop classes with fewer than 2 samples (stratify requires ≥ 2)
    valid_mask = np.isin(y, classes[counts >= 2])
    X, y = X[valid_mask], y[valid_mask]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=random_state
    )

    candidates = [
        {
            "name": "TF-IDF + LinearSVC",
            "vectorizer": TfidfVectorizer(
                max_features=50_000,
                ngram_range=(1, 2),
                stop_words="english",
                min_df=2,
            ),
            "model": LinearSVC(class_weight="balanced"),
        },
        {
            "name": "TF-IDF + LogisticRegression",
            "vectorizer": TfidfVectorizer(
                max_features=50_000,
                ngram_range=(1, 2),
                stop_words="english",
                min_df=2,
            ),
            "model": LogisticRegression(
                max_iter=2000,
                solver="lbfgs",
                C=2.0,
                class_weight="balanced",
            ),
        },
    ]

    best_result: Dict[str, Any] | None = None
    best_score = -1.0

    for candidate in candidates:
        vectorizer = candidate["vectorizer"]
        clf = candidate["model"]
        X_tr = vectorizer.fit_transform(X_train)
        X_te = vectorizer.transform(X_test)
        clf.fit(X_tr, y_train)
        preds = clf.predict(X_te)

        accuracy = float(accuracy_score(y_test, preds))
        f1_macro = float(f1_score(y_test, preds, average="macro", zero_division=0))
        logger.info(
            "Candidate '%s' — accuracy: %.4f, f1_macro: %.4f",
            candidate["name"],
            accuracy,
            f1_macro,
        )

        score = f1_macro
        if score > best_score:
            raw_report = classification_report(
                y_test, preds, output_dict=True, zero_division=0
            )
            clean_report = _make_json_safe(raw_report)
            best_score = score
            best_result = {
                "model": clf,
                "vectorizer": vectorizer,
                "metrics": {
                    "accuracy": accuracy,
                    "f1_macro": f1_macro,
                    "classes": classes.tolist(),
                    "train_size": int(len(X_train)),
                    "test_size": int(len(X_test)),
                    "classification_report": clean_report,
                    "model_name": candidate["name"],
                    "trained_at": datetime.now(timezone.utc).isoformat(),
                    "random_state": random_state,
                },
            }

    if best_result is None:
        raise RuntimeError("No model candidates were trained successfully.")

    logger.info(
        "Best model selected — %s (accuracy %.4f, f1_macro %.4f)",
        best_result["metrics"]["model_name"],
        best_result["metrics"]["accuracy"],
        best_result["metrics"]["f1_macro"],
    )
    return best_result


def _make_json_safe(obj: Any) -> Any:
    """Recursively convert numpy scalars to native Python types."""
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


# ── Artifact saving ───────────────────────────────────────────────────────────

def save_artifacts(
    model: Any,
    vectorizer: Any,
    metrics: Dict[str, Any],
    out_dir: Path,
) -> Dict[str, str]:
    """
    Persist model, vectorizer, and metrics to disk.
    Verifies each file is loadable after writing.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model_path = out_dir / "model.pkl"
    vec_path = out_dir / "vectorizer.pkl"
    metrics_path = out_dir / "metrics.json"

    joblib.dump(model, model_path)
    _verify_joblib(model_path)

    joblib.dump(vectorizer, vec_path)
    _verify_joblib(vec_path)

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)  # no default=str — values are already clean

    logger.info("Artifacts saved to %s", out_dir)

    return {
        "model_path": str(model_path),
        "vectorizer_path": str(vec_path),
        "metrics_path": str(metrics_path),
    }


def _verify_joblib(path: Path) -> None:
    """Load a just-written joblib file to confirm it's not corrupt."""
    try:
        joblib.load(path)
    except Exception as exc:
        raise RuntimeError(f"Artifact verification failed for {path}: {exc}") from exc
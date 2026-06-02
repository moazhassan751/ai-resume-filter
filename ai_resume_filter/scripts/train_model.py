"""
train_model.py — train the TF-IDF + LogisticRegression classifier.

Dataset priority:
  1. $TRAIN_DATASET_PATH (env override)
  2. data/cache/tasks/classification_dataset.csv
  3. data/cache/combined_dataset.csv

Usage:
  python scripts/train_model.py
  TRAIN_DATASET_PATH=path/to/data.csv python scripts/train_model.py

Prerequisites:
  Run normalize_datasets.py then data_pipeline.py first.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

# Allow running as a standalone script without installing the package
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_resume_filter.services.ml_pipeline import load_data, save_artifacts, train_baseline

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

MODELS_DIR = ROOT / "data" / "models"
CACHE      = ROOT / "data" / "cache"

# Column name priority — must stay in sync with ml_pipeline.train_baseline defaults
_TEXT_COLS  = ["text", "Text", "Resume_str"]
_LABEL_COLS = ["label", "category", "Category", "Domain"]


def _choose_dataset() -> Path:
    override = os.getenv("TRAIN_DATASET_PATH")
    if override:
        return Path(override)
    for candidate in [
        CACHE / "tasks" / "classification_dataset.csv",
        CACHE / "combined_dataset.csv",
    ]:
        if candidate.exists():
            return candidate
    # Return the preferred path even if missing — caller handles the error
    return CACHE / "tasks" / "classification_dataset.csv"


def _pick_columns(df) -> tuple[str, str]:
    """Detect text and label columns by priority order."""
    text_col  = next((c for c in _TEXT_COLS  if c in df.columns), None)
    label_col = next((c for c in _LABEL_COLS if c in df.columns), None)
    if not text_col:
        raise ValueError(f"No text column found. Available: {list(df.columns)}")
    if not label_col:
        raise ValueError(f"No label column found. Available: {list(df.columns)}")
    return text_col, label_col


def main() -> None:
    dataset = _choose_dataset()

    if not dataset.exists():
        print(
            f"ERROR: Dataset not found: {dataset}\n"
            "Run scripts/normalize_datasets.py then scripts/data_pipeline.py first.",
            file=sys.stderr,
        )
        sys.exit(1)

    logger.info("Loading: %s", dataset)
    df = load_data(dataset)

    text_col, label_col = _pick_columns(df)
    logger.info(
        "Training — text='%s', label='%s', rows=%d",
        text_col, label_col, len(df),
    )

    try:
        artifacts = train_baseline(df, text_col=text_col, label_col=label_col)
    except Exception as exc:
        logger.exception("Training failed: %s", exc)  # full traceback to stderr
        sys.exit(2)

    paths = save_artifacts(
        artifacts["model"],
        artifacts["vectorizer"],
        artifacts["metrics"],
        MODELS_DIR,
    )

    logger.info("Saved artifacts:\n%s", json.dumps(paths, indent=2))

    m = artifacts["metrics"]
    logger.info(
        "Metrics:\n  accuracy : %.4f\n  f1_macro : %.4f",
        m["accuracy"], m["f1_macro"],
    )


if __name__ == "__main__":
    main()
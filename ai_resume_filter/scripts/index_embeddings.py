"""
index_embeddings.py — embed the RAG corpus into ChromaDB.

Source (in priority order):
  1. $RAG_CORPUS_PATH (env override)
  2. data/cache/tasks/rag_corpus.csv
  3. data/cache/combined_dataset.csv

Usage:
  python scripts/index_embeddings.py
  BATCH_SIZE=128 python scripts/index_embeddings.py

Prerequisites:
  Run normalize_datasets.py then data_pipeline.py first.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from ai_resume_filter.services.embeddings_service import EmbeddingsService

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def _choose_source() -> Path:
    override = os.getenv("RAG_CORPUS_PATH")
    if override:
        return Path(override)
    for candidate in [
        ROOT / "data" / "cache" / "tasks" / "rag_corpus.csv",
        ROOT / "data" / "cache" / "combined_dataset.csv",
    ]:
        if candidate.exists():
            return candidate
    return ROOT / "data" / "cache" / "tasks" / "rag_corpus.csv"  # missing — caller handles


def main() -> None:
    batch_size = int(os.getenv("BATCH_SIZE", "256"))
    source = _choose_source()

    if not source.exists():
        print(
            f"ERROR: No corpus found at {source}\n"
            "Run scripts/data_pipeline.py first.",
            file=sys.stderr,
        )
        sys.exit(1)

    df = pd.read_csv(source)

    # Filter out empty/short texts before indexing
    df = df[df["text"].astype(str).str.len() > 20].reset_index(drop=True)

    if df.empty:
        print("ERROR: Corpus is empty after filtering short texts.", file=sys.stderr)
        sys.exit(1)

    texts = df["text"].astype(str).tolist()
    ids   = (
        df["id"].astype(str).tolist()
        if "id" in df.columns
        else df.index.astype(str).tolist()
    )

    if "source" not in df.columns:
        df["source"] = source.name
    if "category" not in df.columns:
        df["category"] = ""

    metas = df[["source", "category"]].fillna("").to_dict(orient="records")

    svc = EmbeddingsService(persist_dir=ROOT / "data" / "vector_db" / "chroma")
    # load_model() raises RuntimeError if model unavailable — intentional, fail fast
    svc.load_model()

    logger.info("Source:   %s", source)
    logger.info("Documents: %d (batch size: %d)", len(texts), batch_size)

    # index_documents handles batching internally — pass full lists directly
    result = svc.index_documents(
        texts,
        metadatas=metas,
        ids=ids,
        collection_name="resumes",
        batch_size=batch_size,
    )

    logger.info("Indexing complete — %d documents indexed.", result["indexed"])


if __name__ == "__main__":
    main()
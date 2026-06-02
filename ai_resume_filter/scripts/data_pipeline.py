"""
data_pipeline.py — build task-specific datasets from all sources.

Prerequisites:
  Run normalize_datasets.py first — build_rag_corpus() depends on
  data/cache/combined_dataset.csv being present.

Outputs under data/cache/tasks/:
  classification_dataset.csv    — for model training
  skill_extraction_dataset.csv  — for ATS scoring / skill gap
  rag_corpus.csv                — for ChromaDB indexing
  document_parsing_manifest.csv
  pipeline_stats.json
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "cache" / "tasks"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Builders ──────────────────────────────────────────────────────────────────

def build_classification() -> pd.DataFrame:
    frames: List[pd.DataFrame] = []

    # CareerCorpus
    p = ROOT / "CareerCorpus  A Comprehensive Dataset of Annotated" / "CareerCorpus.xlsx"
    if p.exists():
        df = pd.read_excel(p)
        frames.append(pd.DataFrame({
            "id":     df.get("ID"),
            "text": (
                df.get("Education",              pd.Series(dtype=str)).fillna("").astype(str)
                + "\n" + df.get("Skills and Achievements", pd.Series(dtype=str)).fillna("").astype(str)
                + "\n" + df.get("Experience",              pd.Series(dtype=str)).fillna("").astype(str)
            ),
            "label":  df.get("Domain",  pd.Series(dtype=str)).fillna("").astype(str),
            "source": "CareerCorpus.xlsx",
        }))

    # Resume/Resume.csv
    p = ROOT / "Resume" / "Resume.csv"
    if p.exists():
        df = pd.read_csv(p)
        frames.append(pd.DataFrame({
            "id":     df.get("ID"),
            "text":   df.get("Resume_str", pd.Series(dtype=str)).fillna("").astype(str),
            "label":  df.get("Category",   pd.Series(dtype=str)).fillna("").astype(str),
            "source": "Resume.csv",
        }))

    if not frames:
        return pd.DataFrame(columns=["id", "text", "label", "source"])

    out = pd.concat(frames, ignore_index=True)
    out = out.dropna(subset=["text", "label"])
    out = out[out["text"].str.len() > 20]
    out = out[out["label"].str.len() > 0]
    return out.drop_duplicates(subset=["text", "label"])


def build_skill_extraction() -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    p = ROOT / "resume_data.csv"
    if p.exists():
        df = pd.read_csv(p)
        frames.append(pd.DataFrame({
            "id":     df.index.astype(str),
            "text": (
                df.get("career_objective",  pd.Series(dtype=str)).fillna("").astype(str)
                + "\n" + df.get("responsibilities", pd.Series(dtype=str)).fillna("").astype(str)
            ),
            "skills": df.get("skills", pd.Series(dtype=str)).fillna("").astype(str),
            "source": "resume_data.csv",
        }))

    if not frames:
        return pd.DataFrame(columns=["id", "text", "skills", "source"])

    out = pd.concat(frames, ignore_index=True)
    return out[out["text"].str.len() > 20]


def build_rag_corpus(include_hf: bool = True) -> pd.DataFrame:
    """
    Depends on data/cache/combined_dataset.csv from normalize_datasets.py.
    Logs a warning if it is missing rather than silently returning an empty corpus.
    """
    rows: List[Dict[str, Any]] = []

    combined = ROOT / "data" / "cache" / "combined_dataset.csv"
    if combined.exists():
        df = pd.read_csv(combined)
        for i, rec in df.iterrows():
            rows.append({
                "id":       str(rec.get("id", i)),
                "text":     str(rec.get("text", "")),
                "category": str(rec.get("category", "")),
                "source":   str(rec.get("source", "combined_dataset.csv")),
            })
        logger.info("RAG: loaded %d records from combined_dataset.csv", len(rows))
    else:
        logger.warning(
            "combined_dataset.csv not found — run normalize_datasets.py first. "
            "RAG corpus will contain HuggingFace data only (if enabled)."
        )

    hf_loaded = False
    if include_hf:
        try:
            from datasets import load_dataset  # type: ignore
            ds = load_dataset("ahmedheakl/resume-atlas", split="train")
            before = len(rows)
            for i, rec in enumerate(ds):
                rows.append({
                    "id":       f"resume-atlas-{i}",
                    "text":     str(rec.get("Text", "")),
                    "category": str(rec.get("Category", "")),
                    "source":   "huggingface:ahmedheakl/resume-atlas",
                })
            hf_loaded = True
            logger.info("RAG: added %d HuggingFace records", len(rows) - before)
        except Exception as exc:
            logger.warning("HuggingFace load skipped: %s", exc)

    if not rows:
        return pd.DataFrame(columns=["id", "text", "category", "source"])

    out = pd.DataFrame(rows)
    out = out[out["text"].str.len() > 20].drop_duplicates(subset=["text"])
    return out


def build_document_manifest() -> pd.DataFrame:
    pdf_root = ROOT / "data" / "data"
    rows: List[Dict[str, Any]] = []
    if pdf_root.exists():
        for cat in sorted(pdf_root.iterdir()):
            if cat.is_dir():
                for pdf in sorted(cat.glob("*.pdf")):
                    rows.append({"id": pdf.stem, "category": cat.name, "path": str(pdf)})
    return pd.DataFrame(rows, columns=["id", "category", "path"])


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    include_hf = os.getenv("INCLUDE_RESUME_ATLAS", "1") != "0"

    classification = build_classification()
    skills         = build_skill_extraction()
    rag            = build_rag_corpus(include_hf=include_hf)
    manifest       = build_document_manifest()

    classification.to_csv(OUT_DIR / "classification_dataset.csv",   index=False)
    skills.to_csv(OUT_DIR / "skill_extraction_dataset.csv",         index=False)
    rag.to_csv(OUT_DIR / "rag_corpus.csv",                          index=False)
    manifest.to_csv(OUT_DIR / "document_parsing_manifest.csv",      index=False)

    hf_present = (
        not rag.empty
        and (rag["source"] == "huggingface:ahmedheakl/resume-atlas").any()
    )

    stats = {
        "classification_rows":    len(classification),
        "skill_extraction_rows":  len(skills),
        "rag_rows":               len(rag),
        "rag_has_resume_atlas":   hf_present,
        "document_manifest_rows": len(manifest),
        "output_dir":             str(OUT_DIR),
    }

    with open(OUT_DIR / "pipeline_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    logger.info(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
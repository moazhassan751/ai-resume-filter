"""
Unified data loader for all resume datasets.
Supports: CSV, JSONL, Excel, HuggingFace, and PDF directories.

This module owns all file-parsing logic.
DataService (app/services/data_service.py) delegates to this for loading
and adds the FastAPI singleton, async lifecycle, and training-split logic.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


# ── Dataset registry ──────────────────────────────────────────────────────────

class DatasetRegistry:
    """Static metadata for every dataset source."""

    DATASETS: Dict[str, Dict[str, Any]] = {
        "resume_data_csv": {
            "type": "csv",
            "path": "resume_data.csv",
            "description": "Structured resume data with 37 columns (skills, education, experience)",
            "columns": 37,
        },
        "resume_csv": {
            "type": "csv",
            "path": "Resume/Resume.csv",
            "description": "Resume dataset with job category labels",
        },
        "resumes_jsonl": {
            "type": "jsonl",
            "path": "resumes_dataset.jsonl",
            "description": "JSONL formatted resumes (16 MB, structured records)",
        },
        "career_corpus": {
            "type": "excel",
            "path": "CareerCorpus  A Comprehensive Dataset of Annotated/CareerCorpus.xlsx",
            "description": "Career corpus with annotated data",
        },
        "resume_pdfs_by_category": {
            "type": "pdf_directory",
            "path": "data/data",
            "description": "2,484 PDF resumes organised by job category (24 categories)",
            "categories": 24,
            "total_files": 2484,
            "requires_ocr": True,
        },
        "resume_atlas_hf": {
            "type": "huggingface",
            "path": "ahmedheakl/resume-atlas",
            "description": "HuggingFace dataset — 13,389 labelled resumes (Category + Text)",
            "train_examples": 13389,
            "features": ["Category", "Text"],
        },
    }

    @classmethod
    def list_datasets(cls) -> Dict[str, Dict[str, Any]]:
        return cls.DATASETS

    @classmethod
    def get_info(cls, name: str) -> Optional[Dict[str, Any]]:
        return cls.DATASETS.get(name)


# ── Low-level loaders ─────────────────────────────────────────────────────────

class DataLoader:
    """
    Synchronous, format-specific file loaders.
    Each method raises on failure — callers decide whether to swallow or propagate.
    """

    def __init__(self, base_path: str | Path = "."):
        self.base_path = Path(base_path)

    def load_csv(self, file_path: str | Path) -> pd.DataFrame:
        full = self.base_path / file_path
        if not full.exists():
            raise FileNotFoundError(f"CSV not found: {full}")
        df = pd.read_csv(full)
        logger.info("Loaded CSV %s (%d rows, %d cols)", full.name, len(df), len(df.columns))
        return df

    def load_jsonl(self, file_path: str | Path) -> List[Dict[str, Any]]:
        full = self.base_path / file_path
        if not full.exists():
            raise FileNotFoundError(f"JSONL not found: {full}")
        records = []
        with open(full, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        logger.info("Loaded JSONL %s (%d records)", full.name, len(records))
        return records

    def load_excel(self, file_path: str | Path) -> pd.DataFrame:
        full = self.base_path / file_path
        if not full.exists():
            raise FileNotFoundError(f"Excel not found: {full}")
        df = pd.read_excel(full)
        logger.info("Loaded Excel %s (%d rows, %d cols)", full.name, len(df), len(df.columns))
        return df

    def load_pdf_directory(self, dir_path: str | Path) -> Dict[str, Any]:
        """
        Scan a directory of per-category PDF subdirectories.
        Returns {category_name: {"count": int, "files": [path, ...]}}
        Full file lists are preserved here (unlike DataService which caps at 3).
        """
        full = self.base_path / dir_path
        if not full.exists():
            raise FileNotFoundError(f"PDF directory not found: {full}")
        cats: Dict[str, Any] = {}
        for cat_dir in sorted(full.iterdir()):
            if cat_dir.is_dir():
                pdfs = sorted(cat_dir.glob("*.pdf"))
                cats[cat_dir.name] = {
                    "count": len(pdfs),
                    "files": [str(p) for p in pdfs],
                }
                logger.debug("  %s: %d PDFs", cat_dir.name, len(pdfs))
        total = sum(v["count"] for v in cats.values())
        logger.info("Scanned PDF dir %s — %d categories, %d files", full.name, len(cats), total)
        return cats

    def load_huggingface(self, dataset_name: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Load a HuggingFace dataset and return (records, column_names).
        Records are plain dicts — no HF Dataset object is retained.
        """
        try:
            from datasets import load_dataset  # type: ignore
        except ImportError as exc:
            raise RuntimeError("datasets package required: pip install datasets") from exc

        ds = load_dataset(dataset_name, split="train")
        records = [dict(item) for item in ds]
        logger.info("Loaded HuggingFace %s (%d records)", dataset_name, len(records))
        return records, ds.column_names


# ── Pipeline (scripts / CLI use) ──────────────────────────────────────────────

class DataPipeline:
    """
    Loads all datasets via DataLoader and provides stats + export.
    Intended for offline scripts and exploration — not for the FastAPI app.
    Use DataService (app/services/data_service.py) for the runtime singleton.
    """

    def __init__(self, base_path: str | Path = ".", cache_dir: str | Path = "data/cache"):
        self.loader = DataLoader(base_path)
        self.base_path = Path(base_path)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.datasets: Dict[str, Any] = {}

    def load_all_datasets(self, skip_hf: bool = False) -> Dict[str, Any]:
        """Load every dataset, logging errors without aborting the whole run."""
        _loaders = [
            ("resume_data_csv",        lambda: self.loader.load_csv("resume_data.csv")),
            ("resume_csv",             lambda: self.loader.load_csv("Resume/Resume.csv")),
            ("resumes_jsonl",          lambda: self.loader.load_jsonl("resumes_dataset.jsonl")),
            ("career_corpus",          lambda: self.loader.load_excel(
                "CareerCorpus  A Comprehensive Dataset of Annotated/CareerCorpus.xlsx"
            )),
            ("resume_pdfs_by_category", lambda: self.loader.load_pdf_directory("data/data")),
        ]

        for key, fn in _loaders:
            try:
                self.datasets[key] = fn()
            except Exception as exc:
                logger.error("Failed to load %s: %s", key, exc)

        if not skip_hf:
            try:
                records, columns = self.loader.load_huggingface("ahmedheakl/resume-atlas")
                self.datasets["resume_atlas_hf"] = {"records": records, "columns": columns}
            except Exception as exc:
                logger.warning("HuggingFace load skipped: %s", exc)

        return self.datasets

    def get_dataset_stats(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        for name, data in self.datasets.items():
            if isinstance(data, pd.DataFrame):
                stats[name] = {
                    "type": "dataframe",
                    "rows": len(data),
                    "columns": len(data.columns),
                    "memory_mb": round(data.memory_usage(deep=True).sum() / 1024 ** 2, 2),
                }
            elif isinstance(data, list):
                stats[name] = {
                    "type": "list",
                    "records": len(data),
                    "keys": list(data[0].keys()) if data and isinstance(data[0], dict) else [],
                }
            elif isinstance(data, dict) and "records" in data:
                stats[name] = {
                    "type": "huggingface",
                    "records": len(data["records"]),
                    "columns": data.get("columns", []),
                }
            elif isinstance(data, dict):
                stats[name] = {
                    "type": "pdf_directory",
                    "categories": len(data),
                    "total_files": sum(v.get("count", 0) for v in data.values()),
                }
            else:
                stats[name] = {"type": type(data).__name__}
        return stats

    def export_stats(self, output_file: str | Path = "data/cache/dataset_stats.json") -> Path:
        """Write dataset stats to JSON. Values are properly typed — no default=str hack."""
        stats = self.get_dataset_stats()
        out = self.base_path / output_file
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
        logger.info("Stats exported to %s", out)
        return out


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(level=logging.INFO)

    print("\n" + "=" * 70)
    print("DATASET REGISTRY")
    print("=" * 70)
    for name, info in DatasetRegistry.list_datasets().items():
        print(f"\n{name}:")
        for k, v in info.items():
            print(f"  {k}: {v}")

    print("\n" + "=" * 70)
    print("LOADING (HuggingFace skipped)")
    print("=" * 70 + "\n")

    pipeline = DataPipeline(base_path="../..")
    pipeline.load_all_datasets(skip_hf=True)

    print("\n" + "=" * 70)
    print("STATISTICS")
    print("=" * 70)
    for name, stat in pipeline.get_dataset_stats().items():
        print(f"\n{name}:")
        for k, v in stat.items():
            print(f"  {k}: {v}")

    pipeline.export_stats("../../data/cache/dataset_stats.json")


if __name__ == "__main__":
    main()
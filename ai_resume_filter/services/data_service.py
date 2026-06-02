"""
Unified data service — loads and normalises all resume datasets at startup.

Dataset routing:
  resume_data_csv       → skill extraction / ATS scoring
  resume_csv            → classification training
  resumes_jsonl         → classification + skill labels
  career_corpus         → classification quality control
  resume_pdfs_by_cat    → document parsing examples
  resume_atlas_hf       → RAG / semantic search corpus (ChromaDB)

File-parsing logic lives in data_loader.DataLoader.
This service adds the FastAPI singleton, async lifecycle, thread safety,
dataset normalization, and training-split helpers.
"""
from __future__ import annotations

import ast
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .data_loader import DataLoader  # single source of parsing logic

logger = logging.getLogger(__name__)

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parents[2]


class DataService:
    def __init__(self):
        self.datasets: Dict[str, Any] = {}
        self.loaded: bool = False
        self._lock = threading.Lock()
        # Resolve a robust base path for dataset files. Prefer the current working
        # directory if it appears to be the project root (contains expected files),
        # otherwise fall back to the repository-based _PROJECT_ROOT.
        cwd = Path.cwd()
        candidates = [cwd, _PROJECT_ROOT]
        selected = _PROJECT_ROOT
        for c in candidates:
            if (c / "resume_data.csv").exists() or (c / "data").exists() or (c / "Resume").exists():
                selected = c
                break
        self._loader = DataLoader(base_path=selected)

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        with self._lock:
            if self.loaded:
                return
            skip_hf = os.getenv("SKIP_HF_DATASET", "0") == "1"
            await self._load_all(skip_hf=skip_hf)
            self.loaded = True
            logger.info("DataService ready — %d datasets loaded", len(self.datasets))

    async def shutdown(self) -> None:
        self.datasets.clear()
        self.loaded = False

    # ── Internal loading — delegates to DataLoader ────────────────────────────

    async def _load_all(self, skip_hf: bool = False) -> None:
        """
        Load every dataset via DataLoader.
        Missing files are logged and skipped — app still starts.
        """
        _sources = [
            ("resume_data_csv", lambda: self._loader.load_csv("resume_data.csv")),
            ("resume_csv",      lambda: self._loader.load_csv("Resume/Resume.csv")),
            ("resumes_jsonl",   lambda: self._loader.load_jsonl("resumes_dataset.jsonl")),
            ("career_corpus",   lambda: self._loader.load_excel(
                "CareerCorpus  A Comprehensive Dataset of Annotated/CareerCorpus.xlsx"
            )),
        ]

        for key, fn in _sources:
            try:
                self.datasets[key] = fn()
            except FileNotFoundError:
                logger.debug("Dataset file not found, skipping: %s", key)
            except Exception as exc:
                logger.warning("Could not load %s: %s", key, exc)

        # PDF scan — returns metadata dict, not a DataFrame
        try:
            raw = self._loader.load_pdf_directory("data/data")
            # DataService stores trimmed metadata (3 sample files per category)
            # Full file lists remain available via DataLoader directly
            self.datasets["resume_pdfs_by_cat"] = {
                cat: {"count": v["count"], "files": v["files"][:3]}
                for cat, v in raw.items()
            }
        except FileNotFoundError:
            logger.debug("PDF directory not found, skipping")
        except Exception as exc:
            logger.warning("Could not scan PDF directory: %s", exc)

        # HuggingFace — optional, may be slow
        if not skip_hf:
            try:
                records, columns = self._loader.load_huggingface("ahmedheakl/resume-atlas")
                # DataService wraps in a size/features dict for stats compatibility
                self.datasets["resume_atlas_hf"] = {
                    "records": records,
                    "size": len(records),
                    "features": columns,
                }
            except Exception as exc:
                logger.warning("HuggingFace dataset unavailable: %s", exc)

    # ── Public accessors ─────────────────────────────────────────────────────

    def get_dataset(self, name: str) -> Optional[Any]:
        return self.datasets.get(name)

    def list_datasets(self) -> List[str]:
        return list(self.datasets.keys())

    def get_dataset_stats(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        for name, data in self.datasets.items():
            if isinstance(data, pd.DataFrame):
                stats[name] = {
                    "type": "dataframe",
                    "rows": len(data),
                    "columns": len(data.columns),
                    "size_mb": round(data.memory_usage(deep=True).sum() / 1024 ** 2, 2),
                }
            elif isinstance(data, list):
                stats[name] = {"type": "list", "count": len(data)}
            elif isinstance(data, dict) and "size" in data:
                stats[name] = {"type": "huggingface", "count": data["size"]}
            elif isinstance(data, dict):
                total = sum(v.get("count", 0) for v in data.values() if isinstance(v, dict))
                stats[name] = {
                    "type": "pdf_directory",
                    "categories": len(data),
                    "total_files": total,
                }
        return stats

    # ── Normalisation ─────────────────────────────────────────────────────────

    def normalize_resume(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise field names across all dataset sources into a unified schema."""
        return {
            "id":       record.get("id") or record.get("ResumeID") or record.get("ID"),
            "text":     record.get("text") or record.get("Resume_str") or record.get("Text"),
            "category": record.get("category") or record.get("Category"),
            "skills":   self._parse_skills(record.get("skills") or record.get("Skills")),
            "source":   record.get("source"),
        }

    @staticmethod
    def _parse_skills(raw: Any) -> List[str]:
        if isinstance(raw, list):
            return raw
        if isinstance(raw, str):
            try:
                parsed = ast.literal_eval(raw)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
            return [s.strip() for s in raw.split(",") if s.strip()]
        return []

    # ── Training split ────────────────────────────────────────────────────────

    async def get_training_split(
        self,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
    ) -> Dict[str, Any]:
        if not self.loaded:
            await self.initialize()

        df: Optional[pd.DataFrame] = self.datasets.get("resume_csv")
        if df is None or df.empty:
            raise RuntimeError(
                "resume_csv dataset not loaded — cannot generate training split"
            )

        df = df.sample(frac=1, random_state=42).reset_index(drop=True)

        n = len(df)
        t_end = int(n * train_ratio)
        v_end = t_end + int(n * val_ratio)

        train = df.iloc[:t_end].to_dict("records")
        val   = df.iloc[t_end:v_end].to_dict("records")
        test  = df.iloc[v_end:].to_dict("records")

        cc: Optional[pd.DataFrame] = self.datasets.get("career_corpus")
        if cc is not None and not cc.empty:
            test.extend(cc.to_dict("records"))

        return {
            "train": train,
            "validation": val,
            "test": test,
            "stats": {
                "train_size":   len(train),
                "val_size":     len(val),
                "test_size":    len(test),
                "shuffle_seed": 42,
            },
        }


# ── Singleton ────────────────────────────────────────────────────────────────

_instance: Optional[DataService] = None
_instance_lock = threading.Lock()


def get_data_service() -> DataService:
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = DataService()
    return _instance


async def init_data_service() -> None:
    await get_data_service().initialize()


async def shutdown_data_service() -> None:
    await get_data_service().shutdown()
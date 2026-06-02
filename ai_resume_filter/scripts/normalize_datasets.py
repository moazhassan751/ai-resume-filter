"""
normalize_datasets.py — unify all resume sources into data/cache/combined_dataset.csv

Sources consumed:
  resume_data.csv           → skill-annotated tech resumes
  Resume/Resume.csv         → categorised resume text
  resumes_dataset.jsonl     → structured JSONL corpus
  CareerCorpus.xlsx         → annotated career dataset

Outputs:
  data/cache/combined_dataset.csv
  data/cache/normalize_stats.json

Run BEFORE data_pipeline.py — its build_rag_corpus() depends on combined_dataset.csv.
"""
from __future__ import annotations

import ast
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

# Separators tried in order when parsing skill strings
_SKILL_SEPS = ["|", ";", ",", "\n"]
# Minimum character count to treat a string as a valid separator-delimited skill list
_MIN_SKILL_STR_LEN = 3


# ── Helpers ──────────────────────────────────────────────────────────────────

def _text_from_row(row: Dict[str, Any]) -> str:
    for key in ("text", "Resume_str", "Resume_html", "Text", "Summary"):
        if row.get(key):
            return str(row[key])
    parts = [str(v) for v in row.values() if isinstance(v, str) and len(v) > 20]
    return "\n".join(parts)


def _parse_skills(val: Any) -> List[str]:
    if isinstance(val, list):
        return [s for s in val if isinstance(s, str) and s.strip()]
    if isinstance(val, str):
        try:
            parsed = ast.literal_eval(val)
            if isinstance(parsed, list):
                return [s for s in parsed if isinstance(s, str) and s.strip()]
        except Exception:
            pass
        for sep in _SKILL_SEPS:
            if sep in val:
                return [s.strip() for s in val.split(sep) if s.strip()]
        # No recognised separator — don't treat a long sentence as a single skill
        return []
    return []


def _hash(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


# ── Loaders ──────────────────────────────────────────────────────────────────

def _load_csv(path: Path) -> List[Dict[str, Any]]:
    df = pd.read_csv(path)
    records = df.to_dict("records")
    for r in records:
        r["source"] = path.name
    return records


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                r["source"] = path.name
                records.append(r)
    return records


def _load_excel(path: Path) -> List[Dict[str, Any]]:
    df = pd.read_excel(path)
    records = df.to_dict("records")
    for r in records:
        r["source"] = path.name
    return records


# ── Normalisation ─────────────────────────────────────────────────────────────

def _unify(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for r in records:
        text = _text_from_row(r)
        if len(text.strip()) < 30:
            continue
        skills = _parse_skills(
            r.get("skills") or r.get("Skills") or r.get("certification_skills")
        )
        # id is best-effort — may be None for sources without a natural key
        record_id = r.get("id") or r.get("ResumeID") or r.get("ID")
        out.append({
            "id":       record_id,
            "text":     text,
            "category": r.get("category") or r.get("Category") or r.get("Domain") or "",
            "skills":   skills,
            "source":   r.get("source", ""),
        })
    return out


def _dedupe(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate by text hash. When duplicates are found:
    - skills are merged (union)
    - category is taken from whichever record has one
    """
    seen: Dict[str, Dict[str, Any]] = {}
    for r in records:
        h = _hash(r["text"])
        if h in seen:
            merged_skills = list({*seen[h]["skills"], *r["skills"]})
            seen[h] = {**seen[h].copy(), "skills": merged_skills}
            if not seen[h]["category"] and r["category"]:
                seen[h]["category"] = r["category"]
        else:
            seen[h] = r.copy()  # copy to avoid mutating original
    return list(seen.values())


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    raw: List[Dict[str, Any]] = []

    sources = [
        (ROOT / "resume_data.csv",                                                              _load_csv),
        (ROOT / "Resume" / "Resume.csv",                                                        _load_csv),
        (ROOT / "resumes_dataset.jsonl",                                                        _load_jsonl),
        (ROOT / "CareerCorpus  A Comprehensive Dataset of Annotated" / "CareerCorpus.xlsx",     _load_excel),
    ]

    for path, loader in sources:
        if path.exists():
            logger.info("Loading %s …", path.name)
            raw.extend(loader(path))
        else:
            logger.info("Skipped (not found): %s", path.name)

    logger.info("Raw records:   %d", len(raw))
    unified = _unify(raw)
    logger.info("Unified:       %d", len(unified))
    deduped = _dedupe(unified)
    logger.info("After dedupe:  %d", len(deduped))

    out_path = CACHE / "combined_dataset.csv"
    pd.DataFrame(deduped).to_csv(out_path, index=False)
    logger.info("Saved → %s", out_path)

    stats = {"raw": len(raw), "unified": len(unified), "deduped": len(deduped)}
    with open(CACHE / "normalize_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    logger.info("Stats → data/cache/normalize_stats.json")


if __name__ == "__main__":
    main()
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from app.core.celery_app import celery_app
from services.data_loader import DataLoader
from services.ml_pipeline import save_artifacts, train_baseline


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _load_training_frame():
    loader = DataLoader(base_path=PROJECT_ROOT)
    for path in ("Resume/Resume.csv", "resume_csv", "resume_data.csv"):
        try:
            return loader.load_csv(path)
        except Exception:
            continue
    raise RuntimeError("No training dataset found for async training")


@celery_app.task(name="talentlens.train_baseline")
def train_baseline_task() -> Dict[str, Any]:
    frame = _load_training_frame()
    result = train_baseline(frame)
    out_dir = PROJECT_ROOT / "data" / "models"
    artifacts = save_artifacts(
        result["model"],
        result["vectorizer"],
        result["metrics"],
        out_dir,
    )
    return {"metrics": result["metrics"], "artifacts": artifacts}

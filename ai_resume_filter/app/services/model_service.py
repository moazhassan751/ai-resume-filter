"""ML model service: load a joblib pipeline and run inference."""
from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib

logger = logging.getLogger(__name__)

_MODEL = None
_VECTORIZER = None
_lock = threading.Lock()  # prevents double-load under concurrent startup requests


class ModelNotLoadedError(RuntimeError):
    """Raised when inference is attempted before the model is loaded."""


class InferenceError(RuntimeError):
    """Raised when prediction fails."""


def load_model(path: Optional[str] = None) -> Any:
    """
    Load model and vectorizer from disk. Idempotent — safe to call multiple times.
    Raises FileNotFoundError if the model file is missing.
    """
    global _MODEL, _VECTORIZER

    if _MODEL is not None:
        return _MODEL

    with _lock:
        if _MODEL is not None:  # re-check after acquiring lock
            return _MODEL

        model_path = Path(path or os.environ.get("MODEL_PATH", "./data/models/model.pkl"))
        vec_path = Path(os.environ.get("VECTORIZER_PATH", "./data/models/vectorizer.pkl"))

        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found: {model_path}. Run train_model.py first."
            )

        _MODEL = joblib.load(model_path)
        logger.info("Model loaded from %s", model_path)

        if vec_path.exists():
            _VECTORIZER = joblib.load(vec_path)
            logger.info("Vectorizer loaded from %s", vec_path)
        else:
            logger.warning("Vectorizer not found at %s — text inference unavailable", vec_path)

    return _MODEL


def get_vectorizer(path: Optional[str] = None) -> Any:
    """Return the fitted vectorizer, loading it from disk if needed."""
    global _VECTORIZER

    if _VECTORIZER is not None:
        return _VECTORIZER

    with _lock:
        if _VECTORIZER is not None:
            return _VECTORIZER

        vec_path = Path(path or os.environ.get("VECTORIZER_PATH", "./data/models/vectorizer.pkl"))
        if not vec_path.exists():
            raise FileNotFoundError(
                f"Vectorizer file not found: {vec_path}. Run train_model.py first."
            )
        _VECTORIZER = joblib.load(vec_path)
        logger.info("Vectorizer loaded from %s", vec_path)

    return _VECTORIZER


def predict(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run classification inference.

    input_data can be either:
    - {"text": "raw resume text …"}       → uses stored vectorizer (preferred)
    - {"features": [f1, f2, …]}           → explicit ordered feature vector (legacy)

    Raises:
        ModelNotLoadedError: if load_model() has not been called successfully.
        InferenceError:      if prediction fails for any reason.
    """
    if _MODEL is None:
        raise ModelNotLoadedError("Model not loaded — call load_model() at startup")

    try:
        payload = input_data
        if not isinstance(payload, dict) and hasattr(payload, "model_dump"):
            payload = payload.model_dump()

        text_value = payload.get("text") or payload.get("resume_text")
        if text_value:
            vectorizer = _VECTORIZER or get_vectorizer()
            X = vectorizer.transform([str(text_value)])
        elif "features" in payload:
            # Caller is responsible for correct feature order matching training
            X = [list(payload["features"])]
        else:
            raise ValueError(
                "input_data must contain either 'text'/'resume_text' (str) or 'features' (list)"
            )

        pred = _MODEL.predict(X)
        result: Dict[str, Any] = {"prediction": str(pred[0])}

        if hasattr(_MODEL, "predict_proba"):
            probs = _MODEL.predict_proba(X)[0]
            classes: List[str] = [str(c) for c in _MODEL.classes_]
            result["probabilities"] = {c: float(p) for c, p in zip(classes, probs)}
            result["confidence"] = float(max(probs))
        else:
            result["confidence"] = 1.0

        # Top TF-IDF keywords for explainability
        if text_value:
            feat_names = ( _VECTORIZER or get_vectorizer() ).get_feature_names_out()
            arr = X.toarray()[0] if hasattr(X, "toarray") else X[0]
            top_idx = sorted(range(len(arr)), key=lambda i: arr[i], reverse=True)[:10]
            result["top_keywords"] = [feat_names[i] for i in top_idx if arr[i] > 0]

        return result

    except (ModelNotLoadedError, ValueError):
        raise  # let these propagate as-is
    except Exception as exc:
        logger.exception("Inference failed: %s", exc)
        raise InferenceError(f"Inference failed: {exc}") from exc

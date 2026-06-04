from __future__ import annotations

import logging
import os
import re
import json
from typing import Any, Dict, List, Optional
from pathlib import Path

import numpy as np
from sklearn.metrics import classification_report, confusion_matrix

try:
    from jsonschema import validate as jsonschema_validate
    from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
except Exception:  # pragma: no cover
    jsonschema_validate = None

    class JsonSchemaValidationError(Exception):
        pass

from app.services.model_service import get_vectorizer, load_model, predict
from services.data_service import get_data_service
from app.core.config import settings

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#.-]{1,}")
_BIASED_TERMS = {
    "young",
    "recent graduate",
    "native",
    "he",
    "she",
    "his",
    "her",
    "man",
    "woman",
    "startup culture",
    "bachelor required",
    "married",
}


def tokenize(text: str) -> List[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text or "")]


def summarize_text(text: str, limit: int = 280) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def detect_bias_flags(resume_text: str, job_description: Optional[str] = None) -> List[str]:
    source = f"{resume_text} {job_description or ''}".lower()
    flags = []
    for term in sorted(_BIASED_TERMS):
        if term in source:
            flags.append(f"Potential bias term detected: {term}")
    return flags


def score_resume_against_job(
    resume_text: str,
    job_description: str,
    category_hint: Optional[str] = None,
) -> Dict[str, Any]:
    resume_tokens = set(tokenize(resume_text))
    job_tokens = tokenize(job_description)
    job_vocab = [token for token in job_tokens if len(token) > 2]
    job_unique = list(dict.fromkeys(job_vocab))

    matched = sorted(set(job_unique) & resume_tokens)
    missing = [term for term in job_unique if term not in resume_tokens][:15]
    overlap = len(matched) / max(len(set(job_unique)) or 1, 1)
    keyword_score = min(1.0, overlap * 1.4)

    model_confidence = 0.0
    predicted_category = None
    try:
        prediction = predict({"resume_text": resume_text, "category_hint": category_hint})
        predicted_category = prediction.get("prediction")
        model_confidence = float(prediction.get("confidence") or 0.0)
    except Exception as exc:
        logger.debug("ATS model prediction unavailable: %s", exc)

    bias_flags = detect_bias_flags(resume_text, job_description)
    score = int(round(100 * (0.68 * keyword_score + 0.32 * model_confidence)))
    score = max(0, min(100, score))

    return {
        "score": score,
        "confidence": round(max(model_confidence, keyword_score), 4),
        "prediction": predicted_category,
        "matched_keywords": matched[:15],
        "missing_keywords": missing,
        "summary": summarize_text(resume_text),
        "bias_flags": bias_flags,
    }


def run_multi_agent_analysis(
    resume_text: str,
    job_description: Optional[str] = None,
) -> Dict[str, Any]:
    base = {
        "resume_summary": summarize_text(resume_text),
        "skill_gaps": [],
        "bias_flags": detect_bias_flags(resume_text, job_description),
        "hiring_recommendation": "Consider",
        "crew_output": None,
    }

    if job_description:
        resume_tokens = set(tokenize(resume_text))
        job_terms = [term for term in tokenize(job_description) if len(term) > 2]
        base["skill_gaps"] = [term for term in dict.fromkeys(job_terms) if term not in resume_tokens][:12]
        if len(base["skill_gaps"]) <= 3:
            base["hiring_recommendation"] = "Strong fit"
        elif len(base["skill_gaps"]) <= 7:
            base["hiring_recommendation"] = "Review with recruiter"
        else:
            base["hiring_recommendation"] = "Needs targeted upskilling"

    api_keys_present = any(os.environ.get(name) for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"))
    if not api_keys_present:
        return {**base, "mode": "heuristic"}

    # Guard input size to reduce token usage and cost; prefer summarised content
    # but keep enough context for agents to reason reliably.
    resume_text = summarize_text(resume_text, limit=8000)
    job_description = summarize_text(job_description or "", limit=4000)

    def _load_schema(name: str) -> Dict[str, Any]:
        schema_path = Path(__file__).resolve().parents[1] / "schemas" / "agents" / name
        with schema_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def _extract_first_json_blob(text: str) -> Optional[Any]:
        if not text:
            return None
        # prefer fenced JSON
        m = re.search(r"```json\s*(\{.*?\}|\[.*?\])\s*```", text, flags=re.DOTALL)
        candidates = []
        if m:
            candidates.append(m.group(1))
        # try direct object/array spans
        candidates.extend(re.findall(r"(\{[^\{\}]*\})", text, flags=re.DOTALL))
        candidates.extend(re.findall(r"(\[[^\[\]]*\])", text, flags=re.DOTALL))
        for c in candidates:
            try:
                return json.loads(c)
            except Exception:
                continue
        # maybe whole text is json
        try:
            return json.loads(text)
        except Exception:
            return None

    def _repair_payload(agent_key: str, payload: Any) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            payload = {}
        if agent_key == "resume_analyzer":
            payload.setdefault("summary", "")
            payload.setdefault("strengths", [])
            payload.setdefault("top_experiences", [])
            if not isinstance(payload.get("strengths"), list):
                payload["strengths"] = [str(payload.get("strengths"))]
            if not isinstance(payload.get("top_experiences"), list):
                payload["top_experiences"] = [str(payload.get("top_experiences"))]
        elif agent_key == "skill_gap_agent":
            payload.setdefault("skill_gaps", [])
            payload.setdefault("priorities", {})
            if not isinstance(payload.get("skill_gaps"), list):
                payload["skill_gaps"] = [str(payload.get("skill_gaps"))]
            if not isinstance(payload.get("priorities"), dict):
                payload["priorities"] = {}
        elif agent_key == "bias_agent":
            payload.setdefault("bias_flags", [])
            if not isinstance(payload.get("bias_flags"), list):
                payload["bias_flags"] = [str(payload.get("bias_flags"))]
        return payload

    def _validate_with_schema(schema: Dict[str, Any], payload: Dict[str, Any]) -> Optional[str]:
        if jsonschema_validate is None:
            return "jsonschema_not_installed"
        try:
            jsonschema_validate(instance=payload, schema=schema)
            return None
        except JsonSchemaValidationError as exc:
            return str(exc)

    try:
        from app.agents.crew_client import run_crew_work, crew_available, get_crew_settings  # type: ignore

        resume_schema_def = {
            "summary": "string",
            "strengths": ["string"],
            "top_experiences": ["string"],
        }
        skill_gap_schema_def = {"skill_gaps": ["string"], "priorities": {"skill": 1}}
        bias_schema_def = {"bias_flags": ["string"]}

        agent_configs = [
            {
                "role": "Resume Analyzer",
                "goal": "Produce concise factual JSON summary",
                "backstory": "You read resumes and output only valid JSON.",
            },
            {
                "role": "Skill Gap Specialist",
                "goal": "Produce JSON with missing skills and priorities",
                "backstory": "You compare resume and job description and output only valid JSON.",
            },
            {
                "role": "Bias Detection Agent",
                "goal": "Produce JSON array of bias flags",
                "backstory": "You inspect language for fairness risks and output only valid JSON.",
            },
        ]

        task_configs = [
            {
                "description": f"Return ONLY valid JSON matching this schema: {json.dumps(resume_schema_def)}. Input: resume_text.",
                "expected_output": json.dumps(resume_schema_def),
                "agent_index": 0,
            },
            {
                "description": f"Return ONLY valid JSON matching this schema: {json.dumps(skill_gap_schema_def)}. Inputs: resume_text, job_description.",
                "expected_output": json.dumps(skill_gap_schema_def),
                "agent_index": 1,
            },
            {
                "description": f"Return ONLY valid JSON matching this schema: {json.dumps(bias_schema_def)}. Inputs: resume_text, job_description.",
                "expected_output": json.dumps(bias_schema_def),
                "agent_index": 2,
            },
        ]

        if not crew_available() and not (os.environ.get("CREWAI_MOCK_MODE", "0") in {"1", "true", "True"}):
            raise RuntimeError("CrewAI not available")

        cfg = get_crew_settings()
        raw_result = run_crew_work(
            agent_configs,
            task_configs,
            {"resume_text": resume_text, "job_description": job_description or ""},
            parallel=cfg["parallel"],
            timeout_seconds=cfg["timeout_seconds"],
            temperature=cfg["temperature"],
        )

        schema_map = {
            "Resume Analyzer": ("resume_analyzer", _load_schema("resume_analyzer_schema.json")),
            "Skill Gap Specialist": ("skill_gap_agent", _load_schema("skill_gap_schema.json")),
            "Bias Detection Agent": ("bias_agent", _load_schema("bias_schema.json")),
        }

        diagnostics: Dict[str, Any] = {"agents": []}
        crew_structured: Dict[str, Any] = {}

        for item in (raw_result or {}).get("results", []):
            agent_name = item.get("agent")
            key_schema = schema_map.get(agent_name)
            if not key_schema:
                continue
            output_key, schema = key_schema

            raw_output = item.get("output")
            parsed = raw_output if isinstance(raw_output, dict) else _extract_first_json_blob(str(raw_output or ""))
            repaired = _repair_payload(output_key, parsed)

            err = _validate_with_schema(schema, repaired)
            repaired_again = None
            if err:
                repaired_again = _repair_payload(output_key, repaired)
                err2 = _validate_with_schema(schema, repaired_again)
                if err2 is None:
                    repaired = repaired_again
                    err = None

            if err is None:
                crew_structured[output_key] = repaired

            diagnostics["agents"].append(
                {
                    "agent": agent_name,
                    "status": item.get("status"),
                    "latency_seconds": item.get("latency_seconds"),
                    "schema_valid": err is None,
                    "validation_error": err,
                    "attempted_repair": repaired_again is not None,
                }
            )

        # merge validated outputs only
        ra = crew_structured.get("resume_analyzer") or {}
        sg = crew_structured.get("skill_gap_agent") or {}
        ba = crew_structured.get("bias_agent") or {}

        if ra.get("summary"):
            base["resume_summary"] = ra["summary"]
        if sg.get("skill_gaps"):
            base["skill_gaps"] = sg["skill_gaps"]
        if ba.get("bias_flags") is not None:
            base["bias_flags"] = ba["bias_flags"]

        return {
            **base,
            "mode": "crewai",
            "crew_output": {
                "structured": crew_structured,
                "diagnostics": diagnostics,
                "settings": {k: v for k, v in cfg.items() if k != "mock_mode"},
            },
        }
    except Exception as exc:
        logger.warning("CrewAI pipeline fallback used: %s", exc)
        return {**base, "mode": "heuristic", "crew_output": str(exc)}


async def build_classification_report() -> Dict[str, Any]:
    data_service = get_data_service()
    if not data_service.loaded:
        await data_service.initialize()

    try:
        split = await data_service.get_training_split()
    except Exception as exc:
        logger.warning("Could not generate training split: %s", exc)
        return {"error": "Training data unavailable"}

    records = [data_service.normalize_resume(item) for item in split["test"]]
    rows = [row for row in records if row.get("text") and row.get("category")]
    if not rows:
        raise RuntimeError("No evaluation records available")

    vectorizer = get_vectorizer()
    model = load_model()
    X = vectorizer.transform([row["text"] for row in rows])
    y_true = [str(row["category"]) for row in rows]
    y_pred = [str(item) for item in model.predict(X)]
    labels = sorted(set(y_true) | set(y_pred))

    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    report = classification_report(
        y_true,
        y_pred,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )
    accuracy = float((np.array(y_true) == np.array(y_pred)).mean())

    return {
        "labels": labels,
        "confusion_matrix": matrix.tolist(),
        "classification_report": report,
        "samples": len(rows),
        "accuracy": round(accuracy, 4),
    }

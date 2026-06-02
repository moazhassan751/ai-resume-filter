from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional
import concurrent.futures
import time

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

CREW_AGENT_SUCCESS_TOTAL = Counter(
    "crew_agent_success_total",
    "Total successful CrewAI agent task executions",
    ["agent"],
)
CREW_AGENT_FAILURE_TOTAL = Counter(
    "crew_agent_failure_total",
    "Total failed CrewAI agent task executions",
    ["agent"],
)
CREW_AGENT_LATENCY_SECONDS = Histogram(
    "crew_agent_latency_seconds",
    "CrewAI agent task latency in seconds",
    ["agent"],
)
CREW_AGENT_LAST_STATUS = Gauge(
    "crew_agent_last_status",
    "Last CrewAI agent status (1=success, 0=failure)",
    ["agent"],
)


def get_crew_settings() -> Dict[str, Any]:
    provider = os.environ.get("CREWAI_PROVIDER", "gemini").strip().lower()
    default_model = "gemini/gemini-1.5-flash" if provider == "gemini" else "gpt-4o-mini"
    return {
        "timeout_seconds": int(os.environ.get("CREWAI_TASK_TIMEOUT", "20")),
        "temperature": float(os.environ.get("CREWAI_TEMPERATURE", "0")),
        "parallel": os.environ.get("CREWAI_PARALLEL", "1") in {"1", "true", "True"},
        "mock_mode": os.environ.get("CREWAI_MOCK_MODE", "0") in {"1", "true", "True"},
        "max_retries": int(os.environ.get("CREWAI_MAX_RETRIES", "2")),
        "provider": provider,
        "model": os.environ.get("CREWAI_MODEL", default_model),
    }


def crew_available() -> bool:
    try:
        import crewai  # type: ignore

        return True
    except Exception:
        return False


def run_crew_work(
    agent_configs: List[Dict[str, Any]],
    task_configs: List[Dict[str, Any]],
    inputs: Dict[str, Any],
    parallel: Optional[bool] = None,
    timeout_seconds: Optional[int] = None,
    temperature: Optional[float] = 0.0,
) -> Any:
    """Run CrewAI tasks and return structured results + diagnostics.

    agent_configs: list of dicts with keys role, goal, backstory
    task_configs: list of dicts with keys description, expected_output, agent_index
    """
    settings = get_crew_settings()
    if parallel is None:
        parallel = settings["parallel"]
    if timeout_seconds is None:
        timeout_seconds = settings["timeout_seconds"]
    if temperature is None:
        temperature = settings["temperature"]

    if settings["mock_mode"]:
        # Lightweight deterministic sandbox for tests/CI
        results = []
        for t in task_configs:
            agent_name = agent_configs[t.get("agent_index", 0)].get("role", "agent")
            start = time.perf_counter()
            payload = {
                "summary": "Mock summary",
                "strengths": ["python", "communication"],
                "top_experiences": ["Engineer at Example (3y)"],
                "skill_gaps": ["kubernetes", "airflow"],
                "priorities": {"kubernetes": 1},
                "bias_flags": [],
            }
            latency = time.perf_counter() - start
            CREW_AGENT_SUCCESS_TOTAL.labels(agent=agent_name).inc()
            CREW_AGENT_LATENCY_SECONDS.labels(agent=agent_name).observe(latency)
            CREW_AGENT_LAST_STATUS.labels(agent=agent_name).set(1)
            results.append(
                {
                    "agent": agent_name,
                    "status": "success",
                    "latency_seconds": latency,
                    "output": payload,
                }
            )
        return {"mode": "mock", "results": results}

    if not crew_available():
        raise RuntimeError("CrewAI not installed or unavailable")

    try:
        from crewai import Agent, Crew, Process, Task  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"Failed importing crewai: {exc}")

    # Build LLM binding for CrewAI agents.
    # Gemini is default provider; if GOOGLE_API_KEY exists, map it to GEMINI_API_KEY
    # for runtimes that expect the latter.
    llm_binding: Optional[str] = None
    provider = settings.get("provider")
    model = settings.get("model")
    if provider == "gemini":
        google_key = os.environ.get("GOOGLE_API_KEY")
        if google_key and not os.environ.get("GEMINI_API_KEY"):
            os.environ["GEMINI_API_KEY"] = google_key
        llm_binding = model or "gemini/gemini-1.5-flash"
    elif provider == "openai":
        llm_binding = model or "gpt-4o-mini"
    elif provider == "anthropic":
        llm_binding = model or "claude-3-5-sonnet-latest"

    agents = []
    for cfg in agent_configs:
        kwargs: Dict[str, Any] = {
            "role": cfg.get("role"),
            "goal": cfg.get("goal"),
            "backstory": cfg.get("backstory"),
            "verbose": False,
        }
        if llm_binding:
            kwargs["llm"] = llm_binding
        try:
            agents.append(Agent(**kwargs))
        except TypeError:
            # Backward compatibility for CrewAI versions that don't accept llm in Agent ctor.
            kwargs.pop("llm", None)
            agents.append(Agent(**kwargs))

    def _run_single_task(task_cfg: Dict[str, Any]) -> Dict[str, Any]:
        agent_idx = task_cfg.get("agent_index", 0)
        agent = agents[agent_idx]
        agent_name = agent_configs[agent_idx].get("role", f"agent_{agent_idx}")
        task = Task(description=task_cfg.get("description"), expected_output=task_cfg.get("expected_output"), agent=agent)
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)

        kickoff_kwargs = {"inputs": inputs}
        if temperature is not None:
            kickoff_kwargs["temperature"] = temperature

        start = time.perf_counter()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(crew.kickoff, **kickoff_kwargs)
                result = fut.result(timeout=timeout_seconds)
            latency = time.perf_counter() - start
            CREW_AGENT_SUCCESS_TOTAL.labels(agent=agent_name).inc()
            CREW_AGENT_LATENCY_SECONDS.labels(agent=agent_name).observe(latency)
            CREW_AGENT_LAST_STATUS.labels(agent=agent_name).set(1)
            return {
                "agent": agent_name,
                "status": "success",
                "latency_seconds": latency,
                "output": str(result),
            }
        except Exception as exc:
            latency = time.perf_counter() - start
            CREW_AGENT_FAILURE_TOTAL.labels(agent=agent_name).inc()
            CREW_AGENT_LATENCY_SECONDS.labels(agent=agent_name).observe(latency)
            CREW_AGENT_LAST_STATUS.labels(agent=agent_name).set(0)
            return {
                "agent": agent_name,
                "status": "failure",
                "latency_seconds": latency,
                "error": str(exc),
            }

    results: List[Dict[str, Any]] = []
    if parallel:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(task_configs) or 1) as ex:
            futs = [ex.submit(_run_single_task, t) for t in task_configs]
            for f in futs:
                results.append(f.result())
    else:
        for t in task_configs:
            results.append(_run_single_task(t))

    return {"mode": "crewai", "results": results}

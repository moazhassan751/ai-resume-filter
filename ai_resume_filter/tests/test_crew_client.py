from __future__ import annotations

import os

from app.agents.crew_client import get_crew_settings, run_crew_work


def test_crew_client_mock_mode(monkeypatch):
    monkeypatch.setenv("CREWAI_MOCK_MODE", "1")
    monkeypatch.setenv("CREWAI_PARALLEL", "1")
    monkeypatch.setenv("CREWAI_TASK_TIMEOUT", "5")
    monkeypatch.setenv("CREWAI_TEMPERATURE", "0")

    agent_configs = [
        {"role": "Resume Analyzer", "goal": "x", "backstory": "x"},
        {"role": "Skill Gap Specialist", "goal": "x", "backstory": "x"},
        {"role": "Bias Detection Agent", "goal": "x", "backstory": "x"},
    ]
    task_configs = [
        {"description": "task1", "expected_output": "{}", "agent_index": 0},
        {"description": "task2", "expected_output": "{}", "agent_index": 1},
        {"description": "task3", "expected_output": "{}", "agent_index": 2},
    ]

    result = run_crew_work(
        agent_configs=agent_configs,
        task_configs=task_configs,
        inputs={"resume_text": "sample", "job_description": "sample"},
    )

    assert result["mode"] == "mock"
    assert len(result["results"]) == 3
    assert all(item["status"] == "success" for item in result["results"])


def test_crew_settings_from_env(monkeypatch):
    monkeypatch.setenv("CREWAI_TASK_TIMEOUT", "12")
    monkeypatch.setenv("CREWAI_TEMPERATURE", "0")
    monkeypatch.setenv("CREWAI_PARALLEL", "0")
    monkeypatch.setenv("CREWAI_MOCK_MODE", "1")
    monkeypatch.setenv("CREWAI_MAX_RETRIES", "3")

    cfg = get_crew_settings()
    assert cfg["timeout_seconds"] == 12
    assert cfg["temperature"] == 0.0
    assert cfg["parallel"] is False
    assert cfg["mock_mode"] is True
    assert cfg["max_retries"] == 3

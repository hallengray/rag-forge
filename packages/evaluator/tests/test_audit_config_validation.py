"""Audit config must reject silently-misbehaving combinations.

Background: the RAGAS evaluation engine uses its own internal OpenAI judge
regardless of the --judge flag at the top level. This means
'--evaluator ragas --judge claude' silently ignores the user's judge
choice. A customer who doesn't have an OpenAI key would burn time and
money on a misconfigured run before hitting an opaque auth error mid-way.

The fix is to fail loudly *before* any judge calls run.
"""
from pathlib import Path

import pytest

from rag_forge_evaluator.audit import (
    AuditConfig,
    AuditOrchestrator,
    ConfigurationError,
)


def test_ragas_with_claude_judge_raises_at_init() -> None:
    """RAGAS engine + claude judge must raise immediately, before any judge calls."""
    config = AuditConfig(
        input_path=Path("does-not-matter.jsonl"),
        judge_model="claude",
        evaluator_engine="ragas",
        output_dir=Path("./reports"),
    )
    with pytest.raises(ConfigurationError) as exc:
        AuditOrchestrator(config)
    msg = str(exc.value)
    assert "ragas" in msg.lower()
    assert "claude" in msg.lower()
    assert "openai" in msg.lower()


def test_ragas_with_claude_sonnet_alias_also_raises() -> None:
    config = AuditConfig(
        input_path=Path("x.jsonl"),
        judge_model="claude-sonnet",
        evaluator_engine="ragas",
    )
    with pytest.raises(ConfigurationError):
        AuditOrchestrator(config)


def test_ragas_with_openai_judge_is_allowed() -> None:
    config = AuditConfig(
        input_path=Path("x.jsonl"),
        judge_model="openai",
        evaluator_engine="ragas",
    )
    # Should not raise during construction.
    AuditOrchestrator(config)


def test_ragas_with_mock_judge_is_allowed() -> None:
    """Mock runs are free and explicitly for testing — never block them."""
    config = AuditConfig(
        input_path=Path("x.jsonl"),
        judge_model="mock",
        evaluator_engine="ragas",
    )
    AuditOrchestrator(config)


def test_llm_judge_with_claude_is_allowed() -> None:
    """The default llm-judge engine honors --judge claude properly — no guard."""
    config = AuditConfig(
        input_path=Path("x.jsonl"),
        judge_model="claude",
        evaluator_engine="llm-judge",
    )
    AuditOrchestrator(config)


def test_llm_judge_with_openai_is_allowed() -> None:
    config = AuditConfig(
        input_path=Path("x.jsonl"),
        judge_model="openai",
        evaluator_engine="llm-judge",
    )
    AuditOrchestrator(config)

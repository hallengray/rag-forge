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




def test_ragas_with_mock_judge_is_allowed() -> None:
    """Mock IS allowed with ragas in v0.2.0: the RAGAS engine now uses a
    RagForgeRagasLLM wrapper that honors the configured judge end-to-end,
    so mock no longer bypasses the cost gate while silently spending real
    OpenAI tokens. This replaces the old 'mock is blocked' test.
    """
    config = AuditConfig(
        input_path=Path("x.jsonl"),
        judge_model="mock",
        evaluator_engine="ragas",
    )
    orchestrator = AuditOrchestrator(config)
    assert orchestrator.config is config


def test_unknown_judge_alias_raises() -> None:
    """Typos like '--judge claud' must fail loudly, not downgrade to mock."""
    from rag_forge_evaluator.audit import _create_judge

    with pytest.raises(ConfigurationError) as exc:
        _create_judge("claud")
    msg = str(exc.value)
    assert "claud" in msg
    assert "claude" in msg.lower()  # suggestion in error message


def test_unknown_judge_alias_via_orchestrator_raises(tmp_path: Path) -> None:
    """Same typo, but routed through the orchestrator (where users hit it)."""
    jsonl = tmp_path / "in.jsonl"
    jsonl.write_text(
        '{"query": "q", "contexts": ["c"], "response": "r"}\n',
        encoding="utf-8",
    )
    config = AuditConfig(
        input_path=jsonl,
        judge_model="claud",  # typo
        evaluator_engine="llm-judge",
        output_dir=tmp_path / "reports",
    )
    # Validation happens at __init__; _create_judge runs in run().
    # The orchestrator constructs successfully (no ragas mismatch)
    # but the run() call should hit the typo guard.
    orchestrator = AuditOrchestrator(config)
    with pytest.raises(ConfigurationError):
        orchestrator.run()


def test_ragas_with_openai_judge_is_allowed() -> None:
    config = AuditConfig(
        input_path=Path("x.jsonl"),
        judge_model="openai",
        evaluator_engine="ragas",
    )
    orchestrator = AuditOrchestrator(config)
    assert orchestrator.config is config


def test_llm_judge_with_claude_is_allowed() -> None:
    """The default llm-judge engine honors --judge claude properly — no guard."""
    config = AuditConfig(
        input_path=Path("x.jsonl"),
        judge_model="claude",
        evaluator_engine="llm-judge",
    )
    orchestrator = AuditOrchestrator(config)
    assert orchestrator.config is config


def test_llm_judge_with_openai_is_allowed() -> None:
    config = AuditConfig(
        input_path=Path("x.jsonl"),
        judge_model="openai",
        evaluator_engine="llm-judge",
    )
    orchestrator = AuditOrchestrator(config)
    assert orchestrator.config is config


def test_ragas_claude_combo_is_allowed_when_voyageai_available(tmp_path: Path) -> None:
    from unittest.mock import patch

    fixture = tmp_path / "tiny.json"
    fixture.write_text('{"samples": []}')

    config = AuditConfig(
        input_path=None,
        golden_set_path=str(fixture),
        evaluator_engine="ragas",
        judge_model="claude",
        judge_model_name="claude-sonnet-4-6",
        assume_yes=True,
    )

    with patch("rag_forge_evaluator.audit._voyageai_installed", return_value=True):
        # Construction should succeed — no ConfigurationError.
        AuditOrchestrator(config)


def test_ragas_claude_combo_errors_when_voyageai_missing(tmp_path: Path) -> None:
    from unittest.mock import patch

    fixture = tmp_path / "tiny.json"
    fixture.write_text('{"samples": []}')

    config = AuditConfig(
        input_path=None,
        golden_set_path=str(fixture),
        evaluator_engine="ragas",
        judge_model="claude",
        judge_model_name="claude-sonnet-4-6",
        assume_yes=True,
    )

    with patch("rag_forge_evaluator.audit._voyageai_installed", return_value=False):
        with pytest.raises(ConfigurationError, match="ragas-voyage"):
            AuditOrchestrator(config)


def test_audit_config_refusal_aware_default_on() -> None:
    config = AuditConfig(
        input_path=Path("tests/fixtures/tiny.jsonl"),
        evaluator_engine="llm-judge",
        judge_model="mock",
    )
    assert config.refusal_aware is True


def test_audit_config_ragas_max_tokens_default_8192() -> None:
    config = AuditConfig(
        input_path=Path("tests/fixtures/tiny.jsonl"),
        evaluator_engine="ragas",
        judge_model="openai",
    )
    assert config.ragas_max_tokens == 8192
    assert config.ragas_embeddings_provider is None

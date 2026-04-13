"""Tests for the shared LLM-judge response parser (Bug #8 fix)."""
from rag_forge_evaluator.judge.response_parser import parse_judge_json


def test_parses_clean_json() -> None:
    raw = '{"score": 0.87, "reason": "ok"}'
    outcome = parse_judge_json(raw)
    assert outcome.ok is True
    assert outcome.data == {"score": 0.87, "reason": "ok"}
    assert outcome.error is None
    assert outcome.skipped is False


def test_parses_json_with_trailing_prose() -> None:
    raw = '{"score": 0.87}\n\nHere is my reasoning: the response was grounded.'
    outcome = parse_judge_json(raw)
    assert outcome.ok is True
    assert outcome.data == {"score": 0.87}


def test_parses_json_with_leading_prose() -> None:
    raw = 'Sure, here is the evaluation:\n{"score": 0.42}'
    outcome = parse_judge_json(raw)
    assert outcome.ok is True
    assert outcome.data == {"score": 0.42}


def test_parses_json_in_code_fence() -> None:
    raw = '```json\n{"score": 0.42}\n```'
    outcome = parse_judge_json(raw)
    assert outcome.ok is True
    assert outcome.data == {"score": 0.42}


def test_parses_json_in_unlabeled_code_fence() -> None:
    raw = '```\n{"score": 0.55}\n```'
    outcome = parse_judge_json(raw)
    assert outcome.ok is True
    assert outcome.data == {"score": 0.55}


def test_empty_string_is_skipped_not_zero() -> None:
    outcome = parse_judge_json("")
    assert outcome.ok is False
    assert outcome.skipped is True
    assert outcome.data is None
    assert outcome.error is not None
    assert "empty" in outcome.error.lower()


def test_whitespace_only_is_skipped() -> None:
    outcome = parse_judge_json("   \n\t  ")
    assert outcome.ok is False
    assert outcome.skipped is True


def test_unrecoverable_garbage_is_skipped() -> None:
    outcome = parse_judge_json("not json at all, no braces anywhere")
    assert outcome.ok is False
    assert outcome.skipped is True
    assert outcome.error is not None


def test_truncated_json_is_skipped() -> None:
    # Simulates the PearMedica truncation case: judge ran out of tokens
    # mid-array and the response cuts off without closing the object.
    raw = '{"claims": [{"text": "claim 1", "supported": true}, {"text": "clai'
    outcome = parse_judge_json(raw)
    assert outcome.ok is False
    assert outcome.skipped is True

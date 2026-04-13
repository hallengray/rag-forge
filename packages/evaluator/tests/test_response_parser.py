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


def test_fully_truncated_outer_object_is_skipped() -> None:
    """A truncation that doesn't even leave a valid nested object skips."""
    # Outer object truncated mid-key, no closed nested object inside.
    raw = '{"score": 0.8, "details": {"claims": [{"tex'
    outcome = parse_judge_json(raw)
    assert outcome.ok is False
    assert outcome.skipped is True
    # Error message hints at the truncation cause.
    assert outcome.error is not None
    assert "truncated" in outcome.error.lower() or "{" in outcome.error


def test_truncated_outer_with_valid_nested_returns_fragment() -> None:
    """When truncation leaves a valid nested object, the parser may extract it.

    The metric layer is responsible for catching missing required fields
    and marking the sample as skipped at that layer (see
    test_llm_judge_aggregation.test_missing_field_is_skipped_not_zero).
    Documenting this as intentional so future changes don't 'fix' it
    in a way that breaks the parser's other use cases.
    """
    raw = '{"claims": [{"text": "claim 1", "supported": true}, {"text": "clai'
    outcome = parse_judge_json(raw)
    # Parser succeeds at extracting the first valid nested object...
    assert outcome.ok is True
    assert outcome.data is not None
    # ...but the data does NOT contain the metric's expected top-level keys
    # ('score', 'mean_score', etc.), so the metric layer will still skip it.
    assert "score" not in outcome.data
    assert "mean_score" not in outcome.data


def test_parses_nested_json_object() -> None:
    """Nested objects must round-trip via the parser (regex regression test)."""
    raw = '{"score": 0.9, "breakdown": {"clarity": 0.95, "accuracy": 0.85}}'
    outcome = parse_judge_json(raw)
    assert outcome.ok is True
    assert outcome.data is not None
    assert outcome.data["score"] == 0.9
    assert outcome.data["breakdown"]["clarity"] == 0.95
    assert outcome.data["breakdown"]["accuracy"] == 0.85


def test_picks_first_object_when_response_has_multiple() -> None:
    """The previous greedy regex would span first { to last } and fail.

    Per CodeRabbit: responses like `prefix {"a":1} suffix {"b":2}` were
    being sliced into `{"a":1} suffix {"b":2}` which json.loads rejects.
    The new raw_decode-based fallback returns the first valid object.
    """
    raw = 'Sure, here you go: {"score": 0.9} and also {"reason": "tangent"}'
    outcome = parse_judge_json(raw)
    assert outcome.ok is True
    assert outcome.data == {"score": 0.9}


def test_parses_deeply_nested_object_with_arrays() -> None:
    raw = (
        '{"claims": [{"text": "c1", "supported": true}, '
        '{"text": "c2", "supported": false}], "score": 0.5}'
    )
    outcome = parse_judge_json(raw)
    assert outcome.ok is True
    assert outcome.data is not None
    assert outcome.data["score"] == 0.5
    assert len(outcome.data["claims"]) == 2

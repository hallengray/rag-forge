"""Robust JSON parser for LLM-judge responses.

Addresses Bug #8 from the 2026-04-13 PearMedica audit: judges sometimes return
empty strings, code-fenced JSON, leading/trailing prose, or truncated output
when they run out of tokens. The original implementation called json.loads()
directly and coerced every failure into score=0.0, which silently polluted
aggregate metrics by up to 4x downward.

The parser returns a ``ParseOutcome``. Callers must treat ok=False outcomes
as *skipped*, not failed - aggregation should be over successfully parsed
samples only.
"""

import json
import re
from dataclasses import dataclass
from typing import Any

_CODE_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)
_OBJECT_START = re.compile(r"\{")
_DECODER = json.JSONDecoder()


@dataclass(frozen=True)
class ParseOutcome:
    """Result of attempting to parse a judge response into a JSON object."""

    ok: bool
    data: dict[str, Any] | None
    error: str | None
    skipped: bool


def parse_judge_json(raw: str) -> ParseOutcome:
    """Parse a judge response that should contain a JSON object.

    Tolerates: empty strings, leading prose, trailing prose, code fences
    (with or without a language tag), nested objects, and multi-object
    responses where the first object is the one we want.

    Returns ``skipped=True`` for any unrecoverable outcome so callers can
    exclude the sample from aggregation rather than scoring it as zero.
    Truncated JSON (e.g. judge ran out of output tokens mid-array) is
    treated as skipped because we cannot know what the missing values
    would have been.
    """
    if raw is None or not raw.strip():
        return ParseOutcome(
            ok=False,
            data=None,
            error="empty response from judge",
            skipped=True,
        )

    text = raw.strip()

    # 1. Strip ```json ... ``` or ``` ... ``` if present.
    fence = _CODE_FENCE.search(text)
    if fence:
        text = fence.group(1).strip()

    # 2. Try parsing as a clean JSON object.
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return ParseOutcome(ok=True, data=obj, error=None, skipped=False)
    except json.JSONDecodeError:
        pass

    # 3. Fall back to scanning for the first decodable JSON object using
    #    JSONDecoder.raw_decode, which correctly handles nested braces and
    #    multi-object responses. The previous regex-based approach
    #    (`r"\{.*\}"`) was greedy and would span from the first `{` to the
    #    last `}`, breaking on inputs like `prefix {"a":1} suffix {"b":2}`.
    saw_object_start = False
    for match in _OBJECT_START.finditer(text):
        saw_object_start = True
        candidate = text[match.start():]
        try:
            obj, _ = _DECODER.raw_decode(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return ParseOutcome(ok=True, data=obj, error=None, skipped=False)

    if saw_object_start:
        return ParseOutcome(
            ok=False,
            data=None,
            error="found '{' but no decodable JSON object (likely truncated)",
            skipped=True,
        )

    return ParseOutcome(
        ok=False,
        data=None,
        error="no JSON object found in response",
        skipped=True,
    )

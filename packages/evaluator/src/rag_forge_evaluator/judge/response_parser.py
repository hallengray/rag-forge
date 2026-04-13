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
_FIRST_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


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
    (with or without a language tag), and whitespace.

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

    # 3. Fall back to extracting the first {...} block from prose.
    #    Greedy match is intentional - judges often emit nested JSON
    #    and we want to capture the outermost balanced object.
    match = _FIRST_OBJECT.search(text)
    if match:
        try:
            obj = json.loads(match.group(0))
            if isinstance(obj, dict):
                return ParseOutcome(ok=True, data=obj, error=None, skipped=False)
        except json.JSONDecodeError as e:
            return ParseOutcome(
                ok=False,
                data=None,
                error=f"extracted object failed to parse: {e}",
                skipped=True,
            )

    return ParseOutcome(
        ok=False,
        data=None,
        error="no JSON object found in response",
        skipped=True,
    )

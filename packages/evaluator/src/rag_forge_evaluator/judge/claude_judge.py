"""Claude judge provider via Anthropic SDK.

Configuration precedence (highest wins):
1. Constructor argument
2. ``RAG_FORGE_JUDGE_MODEL`` / ``RAG_FORGE_JUDGE_MAX_TOKENS`` /
   ``RAG_FORGE_JUDGE_MAX_RETRIES`` environment variables
3. Built-in defaults (``claude-sonnet-4-20250514``, 4096 tokens, 5 retries)

The 4096-token default replaces the previous 1024 after the 2026-04-13
PearMedica audit, where the faithfulness metric truncated mid-array on
long clinical responses and silently scored 0.

The Anthropic SDK's built-in retry loop handles 408/429/500/502/503/504
but does NOT cover 529 Overloaded — 529 is an Anthropic-specific status
that propagates as ``OverloadedError`` and crashes long-running audits
during capacity events. We layer an explicit retry wrapper on top that
catches 529 with exponential backoff (2, 4, 8, 16, 32s), while still
delegating all other retriable errors to the SDK.
"""
import os
import time
from collections.abc import Callable
from typing import TypeVar

from anthropic import Anthropic, APIStatusError

_DEFAULT_MODEL = "claude-sonnet-4-20250514"
_DEFAULT_MAX_TOKENS = 4096
_DEFAULT_MAX_RETRIES = 5
_OVERLOADED_STATUS = 529
_OVERLOADED_BACKOFF_BASE_SECONDS = 2.0

T = TypeVar("T")


def _resolve_int(env_var: str, default: int) -> int:
    raw = os.environ.get(env_var)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _validate_positive_int(name: str, value: int) -> int:
    """Reject zero/negative values before they hit the SDK."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        msg = f"{name} must be a positive integer, got {value!r}"
        raise ValueError(msg)
    return value


class ClaudeJudge:
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        max_tokens: int | None = None,
        max_retries: int | None = None,
    ) -> None:
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            msg = (
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment "
                "variable or pass api_key to ClaudeJudge."
            )
            raise ValueError(msg)
        resolved_model = model or os.environ.get("RAG_FORGE_JUDGE_MODEL") or _DEFAULT_MODEL
        resolved_max_tokens = _validate_positive_int(
            "max_tokens",
            max_tokens
            if max_tokens is not None
            else _resolve_int("RAG_FORGE_JUDGE_MAX_TOKENS", _DEFAULT_MAX_TOKENS),
        )
        resolved_max_retries = _validate_positive_int(
            "max_retries",
            max_retries
            if max_retries is not None
            else _resolve_int("RAG_FORGE_JUDGE_MAX_RETRIES", _DEFAULT_MAX_RETRIES),
        )
        self._client = Anthropic(api_key=key, max_retries=resolved_max_retries)
        self._model = resolved_model
        self._max_tokens = resolved_max_tokens
        self._max_retries = resolved_max_retries

    def _call_with_overloaded_retry(self, fn: Callable[[], T]) -> T:
        for attempt in range(self._max_retries + 1):
            try:
                return fn()
            except APIStatusError as exc:
                status = getattr(exc, "status_code", None)
                if status != _OVERLOADED_STATUS or attempt == self._max_retries:
                    raise
                time.sleep(_OVERLOADED_BACKOFF_BASE_SECONDS * (2**attempt))
        msg = "unreachable: retry loop exited without returning or raising"
        raise RuntimeError(msg)

    def judge(self, system_prompt: str, user_prompt: str) -> str:
        response = self._call_with_overloaded_retry(
            lambda: self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        )
        block = response.content[0]
        return block.text if hasattr(block, "text") else str(block)

    def model_name(self) -> str:
        return self._model

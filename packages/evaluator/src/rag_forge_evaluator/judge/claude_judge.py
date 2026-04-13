"""Claude judge provider via Anthropic SDK.

Configuration precedence (highest wins):
1. Constructor argument
2. ``RAG_FORGE_JUDGE_MODEL`` / ``RAG_FORGE_JUDGE_MAX_TOKENS`` /
   ``RAG_FORGE_JUDGE_MAX_RETRIES`` / ``RAG_FORGE_JUDGE_OVERLOAD_BUDGET_SECONDS``
   environment variables
3. Built-in defaults (``claude-sonnet-4-20250514``, 4096 tokens, 5 retries,
   300-second overload budget)

The 4096-token default replaces the previous 1024 after the 2026-04-13
PearMedica audit, where the faithfulness metric truncated mid-array on
long clinical responses and silently scored 0.

The Anthropic SDK's built-in retry loop handles 408/429/500/502/503/504
but does NOT cover 529 Overloaded — 529 is an Anthropic-specific status
that propagates as ``OverloadedError`` and crashes long-running audits
during capacity events. We layer an explicit retry wrapper on top that
catches 529 with exponential backoff (2, 4, 8, 16, 32s), bounded by both
an attempt cap (``max_retries``) and a wall-clock budget
(``overload_budget_seconds``). Whichever bound trips first wins.

Callers who want visibility into retry activity can pass an ``on_retry``
callback; it receives ``(attempt, elapsed_seconds, budget_seconds)`` on
every retry fire and is called before the ``time.sleep``. Default is a
no-op so library and test contexts stay quiet.
"""
import os
import time
from collections.abc import Callable
from typing import TypeVar

from anthropic import Anthropic, APIStatusError

_DEFAULT_MODEL = "claude-sonnet-4-20250514"
_DEFAULT_MAX_TOKENS = 4096
_DEFAULT_MAX_RETRIES = 5
_DEFAULT_OVERLOAD_BUDGET_SECONDS = 300.0
_OVERLOADED_STATUS = 529
_OVERLOADED_BACKOFF_BASE_SECONDS = 2.0

T = TypeVar("T")

OnRetryCallback = Callable[[int, float, float], None]


def _noop_on_retry(attempt: int, elapsed: float, budget: float) -> None:
    del attempt, elapsed, budget


def _resolve_int(env_var: str, default: int) -> int:
    raw = os.environ.get(env_var)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _resolve_float(env_var: str, default: float) -> float:
    raw = os.environ.get(env_var)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _validate_positive_int(name: str, value: int) -> int:
    """Reject zero/negative values before they hit the SDK."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        msg = f"{name} must be a positive integer, got {value!r}"
        raise ValueError(msg)
    return value


def _validate_positive_float(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        msg = f"{name} must be a positive number, got {value!r}"
        raise ValueError(msg)
    return float(value)


class OverloadBudgetExhaustedError(RuntimeError):
    """Raised when the 529 retry wall-clock budget is exhausted.

    Wraps the final ``APIStatusError(529)`` so callers can distinguish a
    sustained capacity event from a one-off overload. The CLI catches
    this and prints a fallback-options hint before propagating.
    """

    def __init__(self, budget_seconds: float, attempts: int, original: APIStatusError) -> None:
        super().__init__(
            f"Anthropic 529 Overloaded persisted for {budget_seconds:.0f}s "
            f"across {attempts} attempts (retry budget exhausted)."
        )
        self.budget_seconds = budget_seconds
        self.attempts = attempts
        self.original = original


class ClaudeJudge:
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        max_tokens: int | None = None,
        max_retries: int | None = None,
        overload_budget_seconds: float | None = None,
        on_retry: OnRetryCallback | None = None,
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
        resolved_budget = _validate_positive_float(
            "overload_budget_seconds",
            overload_budget_seconds
            if overload_budget_seconds is not None
            else _resolve_float(
                "RAG_FORGE_JUDGE_OVERLOAD_BUDGET_SECONDS",
                _DEFAULT_OVERLOAD_BUDGET_SECONDS,
            ),
        )
        self._client = Anthropic(api_key=key, max_retries=resolved_max_retries)
        self._model = resolved_model
        self._max_tokens = resolved_max_tokens
        self._max_retries = resolved_max_retries
        self._overload_budget_seconds = resolved_budget
        self._on_retry: OnRetryCallback = on_retry or _noop_on_retry

    def _call_with_overloaded_retry(self, fn: Callable[[], T]) -> T:
        start = time.monotonic()
        attempts = 0
        while True:
            attempts += 1
            try:
                return fn()
            except APIStatusError as exc:
                status = getattr(exc, "status_code", None)
                if status != _OVERLOADED_STATUS:
                    raise
                elapsed = time.monotonic() - start
                backoff = _OVERLOADED_BACKOFF_BASE_SECONDS * (2 ** (attempts - 1))
                would_exceed_budget = (elapsed + backoff) >= self._overload_budget_seconds
                attempts_exhausted = attempts > self._max_retries
                if attempts_exhausted or would_exceed_budget:
                    raise OverloadBudgetExhaustedError(
                        budget_seconds=self._overload_budget_seconds,
                        attempts=attempts,
                        original=exc,
                    ) from exc
                self._on_retry(attempts, elapsed, self._overload_budget_seconds)
                time.sleep(backoff)

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

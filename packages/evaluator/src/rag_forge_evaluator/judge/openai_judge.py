"""OpenAI judge provider via OpenAI SDK.

Configuration precedence and defaults match ClaudeJudge — see that module
for the rationale on the 4096-token default and 5-retry default.
"""
import os

from openai import OpenAI

_DEFAULT_MODEL = "gpt-4o"
_DEFAULT_MAX_TOKENS = 4096
_DEFAULT_MAX_RETRIES = 5


def _resolve_int(env_var: str, default: int) -> int:
    raw = os.environ.get(env_var)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class OpenAIJudge:
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        max_tokens: int | None = None,
        max_retries: int | None = None,
    ) -> None:
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            msg = (
                "OpenAI API key not found. Set OPENAI_API_KEY environment "
                "variable or pass api_key to OpenAIJudge."
            )
            raise ValueError(msg)
        resolved_model = model or os.environ.get("RAG_FORGE_JUDGE_MODEL") or _DEFAULT_MODEL
        resolved_max_tokens = (
            max_tokens
            if max_tokens is not None
            else _resolve_int("RAG_FORGE_JUDGE_MAX_TOKENS", _DEFAULT_MAX_TOKENS)
        )
        resolved_max_retries = (
            max_retries
            if max_retries is not None
            else _resolve_int("RAG_FORGE_JUDGE_MAX_RETRIES", _DEFAULT_MAX_RETRIES)
        )
        self._client = OpenAI(api_key=key, max_retries=resolved_max_retries)
        self._model = resolved_model
        self._max_tokens = resolved_max_tokens

    def judge(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""

    def model_name(self) -> str:
        return self._model

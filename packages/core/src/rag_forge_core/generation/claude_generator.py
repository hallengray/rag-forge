"""Claude generation provider via Anthropic SDK."""

import os

from anthropic import Anthropic


class ClaudeGenerator:
    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
        max_tokens: int = 2048,
    ) -> None:
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            msg = (
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment "
                "variable or pass api_key to ClaudeGenerator."
            )
            raise ValueError(msg)
        self._client = Anthropic(api_key=key)
        self._model = model
        self._max_tokens = max_tokens

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    def model_name(self) -> str:
        return self._model

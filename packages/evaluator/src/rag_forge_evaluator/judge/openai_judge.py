"""OpenAI judge provider via OpenAI SDK."""
import os

from openai import OpenAI


class OpenAIJudge:
    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        max_tokens: int = 1024,
    ) -> None:
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            msg = (
                "OpenAI API key not found. Set OPENAI_API_KEY environment "
                "variable or pass api_key to OpenAIJudge."
            )
            raise ValueError(msg)
        self._client = OpenAI(api_key=key)
        self._model = model
        self._max_tokens = max_tokens

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

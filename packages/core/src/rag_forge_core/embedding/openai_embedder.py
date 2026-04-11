"""OpenAI embedding provider using text-embedding-3-small."""

import os

from openai import OpenAI


class OpenAIEmbedder:
    """Embeds text using OpenAI's text-embedding-3-small model.

    Reads OPENAI_API_KEY from environment. Batches up to 2048 texts per API call.
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str | None = None,
        batch_size: int = 2048,
    ) -> None:
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            msg = (
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or pass api_key to OpenAIEmbedder."
            )
            raise ValueError(msg)
        self._client = OpenAI(api_key=key)
        self._model = model
        self._batch_size = batch_size
        self._dimension_cache: int | None = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings, batching if needed."""
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            response = self._client.embeddings.create(model=self._model, input=batch)
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

            if self._dimension_cache is None and batch_embeddings:
                self._dimension_cache = len(batch_embeddings[0])

        return all_embeddings

    def dimension(self) -> int:
        if self._dimension_cache is not None:
            return self._dimension_cache
        dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return dimensions.get(self._model, 1536)

    def model_name(self) -> str:
        return self._model

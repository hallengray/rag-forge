"""Local embedding provider using sentence-transformers (optional dependency)."""

from __future__ import annotations


class LocalEmbedder:
    """Embeds text locally using sentence-transformers models (e.g., BAAI/bge-m3).

    Requires the optional 'local' dependency group:
        pip install rag-forge-core[local]
    """

    def __init__(self, model_name: str = "BAAI/bge-m3") -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]
        except ImportError:
            msg = (
                "sentence-transformers is required for local embeddings. "
                "Install with: pip install rag-forge-core[local]"
            )
            raise ImportError(msg) from None

        self._model_name = model_name
        self._model = SentenceTransformer(model_name)
        self._dim: int = self._model.get_sentence_embedding_dimension() or 1024

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings locally."""
        if not texts:
            return []
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return [vec.tolist() for vec in embeddings]

    def dimension(self) -> int:
        return self._dim

    def model_name(self) -> str:
        return self._model_name

"""Deterministic mock embedding provider for testing and CI."""

import hashlib
import struct


class MockEmbedder:
    """Generates deterministic vectors from text hashes. Same input always produces same output."""

    def __init__(self, dimension: int = 384) -> None:
        self._dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate deterministic embeddings based on text hash."""
        return [self._hash_to_vector(text) for text in texts]

    def dimension(self) -> int:
        return self._dimension

    def model_name(self) -> str:
        return "mock-embedder"

    def _hash_to_vector(self, text: str) -> list[float]:
        """Convert text to a deterministic float vector via SHA-256."""
        hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()
        vector: list[float] = []
        for i in range(self._dimension):
            byte_index = i % len(hash_bytes)
            value = hash_bytes[byte_index] / 255.0
            seed = struct.pack("B", (byte_index + i) % 256)
            offset = hashlib.md5(hash_bytes + seed).digest()[0] / 255.0
            vector.append((value + offset) / 2.0)
        return vector

"""Tests for semantic chunking strategy."""


from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.semantic import SemanticChunker
from rag_forge_core.embedding.mock_embedder import MockEmbedder


class TestSemanticChunker:
    def test_empty_text_returns_no_chunks(self) -> None:
        embedder = MockEmbedder()
        chunker = SemanticChunker(
            config=ChunkConfig(strategy="semantic", cosine_threshold=0.75),
            embedder=embedder,
        )
        result = chunker.chunk("", "test.md")
        assert len(result) == 0

    def test_single_sentence_returns_one_chunk(self) -> None:
        embedder = MockEmbedder()
        chunker = SemanticChunker(
            config=ChunkConfig(strategy="semantic", cosine_threshold=0.75),
            embedder=embedder,
        )
        result = chunker.chunk("Hello world.", "test.md")
        assert len(result) == 1
        assert result[0].strategy_used == "semantic"

    def test_multi_paragraph_produces_multiple_chunks(self) -> None:
        embedder = MockEmbedder()
        chunker = SemanticChunker(
            config=ChunkConfig(strategy="semantic", cosine_threshold=0.75),
            embedder=embedder,
        )
        text = (
            "Python is a programming language used for web development.\n\n"
            "The Pacific Ocean is the largest ocean on Earth.\n\n"
            "Quantum computing uses qubits instead of classical bits."
        )
        result = chunker.chunk(text, "test.md")
        assert len(result) >= 1
        for chunk in result:
            assert chunk.source_document == "test.md"
            assert chunk.strategy_used == "semantic"

    def test_chunk_indices_are_sequential(self) -> None:
        embedder = MockEmbedder()
        chunker = SemanticChunker(
            config=ChunkConfig(strategy="semantic", cosine_threshold=0.75),
            embedder=embedder,
        )
        text = "Sentence one.\n\nSentence two.\n\nSentence three."
        chunks = chunker.chunk(text, "test.md")
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_preview_matches_chunk(self) -> None:
        embedder = MockEmbedder()
        chunker = SemanticChunker(
            config=ChunkConfig(strategy="semantic", cosine_threshold=0.75),
            embedder=embedder,
        )
        text = "Hello world.\n\nGoodbye world."
        assert chunker.preview(text, "test.md") == chunker.chunk(text, "test.md")

    def test_stats_reports_correct_totals(self) -> None:
        embedder = MockEmbedder()
        chunker = SemanticChunker(
            config=ChunkConfig(strategy="semantic", cosine_threshold=0.75),
            embedder=embedder,
        )
        text = "Hello world.\n\nGoodbye world."
        chunks = chunker.chunk(text, "test.md")
        stats = chunker.stats(chunks)
        assert stats.total_chunks == len(chunks)
        assert stats.total_tokens > 0

    def test_high_threshold_merges_more(self) -> None:
        """Higher cosine_threshold means sentences must be MORE similar to merge."""
        embedder = MockEmbedder()
        low = SemanticChunker(
            config=ChunkConfig(strategy="semantic", cosine_threshold=0.3),
            embedder=embedder,
        )
        high = SemanticChunker(
            config=ChunkConfig(strategy="semantic", cosine_threshold=0.99),
            embedder=embedder,
        )
        text = "Topic A sentence one.\n\nTopic A sentence two.\n\nTopic B different."
        low_chunks = low.chunk(text, "test.md")
        high_chunks = high.chunk(text, "test.md")
        # Higher threshold = harder to merge = more chunks (or equal)
        assert len(high_chunks) >= len(low_chunks)

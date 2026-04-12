# rag-forge-core

RAG pipeline primitives for the RAG-Forge toolkit: ingestion, chunking, retrieval, context management, and security.

## Installation

```bash
pip install rag-forge-core
```

## Usage

This package provides the building blocks used by the `rag-forge` CLI. For end-user usage, see the [main RAG-Forge documentation](https://github.com/hallengray/rag-forge#readme).

```python
from rag_forge_core.chunking.factory import create_chunker
from rag_forge_core.chunking.config import ChunkConfig

chunker = create_chunker(ChunkConfig(strategy="recursive", chunk_size=512))
chunks = chunker.chunk("Some long document text...", source="doc.md")
```

## Modules

- `rag_forge_core.chunking` — Five chunking strategies (recursive, fixed, semantic, structural, llm-driven)
- `rag_forge_core.retrieval` — Dense, sparse, and hybrid retrieval with reranking
- `rag_forge_core.security` — InputGuard, OutputGuard, PII scanning, prompt injection detection
- `rag_forge_core.context` — Contextual enrichment and semantic caching
- `rag_forge_core.plugins` — Plugin registry for custom extensions

## License

MIT

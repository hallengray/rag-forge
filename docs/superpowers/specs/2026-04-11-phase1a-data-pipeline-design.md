# Phase 1A: Data Pipeline Design Spec

## Context

RAG-Forge Phase 1 "Foundation" requires a working `rag-forge index --source ./docs` command that parses documents, chunks them, generates embeddings, and stores vectors. This spec covers Sub-project A of Phase 1: the complete data pipeline from raw files to indexed vectors.

## Scope

**In scope:** Document parsing, chunking enhancement, embedding provider abstraction, vector store abstraction, ingestion pipeline orchestrator, CLI `index` command, Python CLI bridge entry point.

**Out of scope:** Evaluation engine, audit reports, `init` command scaffolding, query/retrieval (Sub-projects B and C).

## Architecture

Strategy pattern with dependency injection. Each pipeline stage is an independent component behind a protocol. The `IngestionPipeline` orchestrator receives all components via constructor and coordinates the flow.

```
rag-forge index --source ./docs
       │
       ▼
  TypeScript CLI (index command)
       │
       ▼ (Python bridge: uv run python -m rag_forge_core.cli)
       │
  Python CLI entry point
       │
       ▼
  IngestionPipeline.run(source_path)
       │
       ├─ 1. DirectoryParser.parse_directory(source_path)
       │      └─ Routes to: MarkdownParser | PlainTextParser | PDFParser | HTMLParser
       │      └─ Returns: list[Document]
       │
       ├─ 2. ChunkStrategy.chunk(document.text, document.source_path)
       │      └─ RecursiveChunker (default, with overlap + tiktoken)
       │      └─ Returns: list[Chunk]
       │
       ├─ 3. EmbeddingProvider.embed(chunk_texts)
       │      └─ OpenAIEmbedder | LocalEmbedder | MockEmbedder
       │      └─ Returns: list[list[float]]
       │
       └─ 4. VectorStore.upsert(collection, items)
              └─ QdrantStore (in-memory default)
              └─ Returns: count indexed
```

## Components

### 1. Document Parsing Module

**Location:** `packages/core/src/rag_forge_core/parsing/`

**Protocol:**
```python
@dataclass
class Document:
    text: str
    source_path: str
    metadata: dict[str, str | int | float]

class DocumentParser(Protocol):
    def parse(self, path: Path) -> list[Document]: ...
    def supported_extensions(self) -> list[str]: ...
```

**Implementations:**

| File | Class | Extensions | Library | Notes |
|------|-------|-----------|---------|-------|
| `markdown.py` | `MarkdownParser` | `.md` | Built-in | Strips YAML frontmatter, preserves headers as section metadata |
| `plaintext.py` | `PlainTextParser` | `.txt` | Built-in | Direct UTF-8 read |
| `pdf.py` | `PDFParser` | `.pdf` | `pymupdf` | Page-by-page extraction, page numbers in metadata |
| `html.py` | `HTMLParser` | `.html`, `.htm` | `beautifulsoup4` | Strips tags, extracts `<title>` |
| `directory.py` | `DirectoryParser` | All above | — | Walks directory, routes by extension, skips unsupported, collects errors |

**Error handling:** `DirectoryParser` continues on individual file failures, collecting errors in a list. The caller decides whether to abort.

### 2. Chunking Enhancement

**Location:** `packages/core/src/rag_forge_core/chunking/recursive.py` (modify existing)

**Changes to `RecursiveChunker`:**
1. **Overlap handling:** After splitting, carry forward `config.overlap_tokens` tokens from the end of chunk N to the beginning of chunk N+1. This ensures continuity across chunk boundaries.
2. **Token counting:** Replace `len(text.split())` with `tiktoken` encoding (model: `cl100k_base`) for accurate token counts. The `ChunkConfig.chunk_size` now truly represents tokens, not words.

**No changes to:** `ChunkStrategy` ABC, `ChunkConfig`, `Chunk` dataclass, `ChunkStats` (all already correct).

### 3. Embedding Provider Module

**Location:** `packages/core/src/rag_forge_core/embedding/`

**Protocol:**
```python
class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
    def dimension(self) -> int: ...
    def model_name(self) -> str: ...
```

**Implementations:**

| File | Class | Model | Dimension | Dependency | Notes |
|------|-------|-------|-----------|------------|-------|
| `openai_embedder.py` | `OpenAIEmbedder` | text-embedding-3-small | 1536 | `openai` | Reads `OPENAI_API_KEY` from env. Batches up to 2048 texts per API call. |
| `local_embedder.py` | `LocalEmbedder` | BAAI/bge-m3 | 1024 | `sentence-transformers` (optional) | Checks for import availability; raises clear error if not installed. |
| `mock_embedder.py` | `MockEmbedder` | Hash-based | 384 | None | Deterministic: same text → same vector. Used in tests and CI. |

**Optional dependency:** `sentence-transformers` is declared under `[project.optional-dependencies] local = ["sentence-transformers"]` in `pyproject.toml`. Core install stays lean.

**Provider selection:** Via config field `embedding_provider: "openai" | "local" | "mock"`.

### 4. Vector Store Module

**Location:** `packages/core/src/rag_forge_core/storage/`

**Protocol:**
```python
@dataclass
class VectorItem:
    id: str
    vector: list[float]
    text: str
    metadata: dict[str, str | int | float]

@dataclass
class SearchResult:
    id: str
    text: str
    score: float
    metadata: dict[str, str | int | float]

class VectorStore(Protocol):
    def create_collection(self, name: str, dimension: int) -> None: ...
    def upsert(self, collection: str, items: list[VectorItem]) -> int: ...
    def search(self, collection: str, vector: list[float], top_k: int) -> list[SearchResult]: ...
    def count(self, collection: str) -> int: ...
    def delete_collection(self, collection: str) -> None: ...
```

**`QdrantStore` implementation:**
- Default: `location=":memory:"` (zero config, no Docker)
- Config: `qdrant_path` for file-based persistence, `qdrant_url` for remote server
- Distance metric: Cosine similarity
- Index: HNSW (Qdrant default)
- Stores chunk text + all metadata as Qdrant payload

### 5. Ingestion Pipeline (Enhanced)

**Location:** `packages/core/src/rag_forge_core/ingestion/pipeline.py` (modify existing)

```python
class IngestionPipeline:
    def __init__(
        self,
        parser: DirectoryParser,
        chunker: ChunkStrategy,
        embedder: EmbeddingProvider,
        store: VectorStore,
        collection_name: str = "rag-forge",
    ) -> None: ...

    def run(self, source_path: Path) -> IngestionResult: ...
```

**Pipeline flow:**
1. Parse: `parser.parse_directory(source_path)` → `list[Document]`
2. Chunk: For each document, `chunker.chunk(doc.text, doc.source_path)` → flat `list[Chunk]`
3. Embed: Batch chunks through `embedder.embed([c.text for c in chunks])` → `list[list[float]]`
4. Create collection: `store.create_collection(collection_name, embedder.dimension())`
5. Upsert: `store.upsert(collection_name, vector_items)` → count
6. Return: `IngestionResult` with stats

**Embedding batching:** If total chunks exceed 2048, split into batches of 2048 before calling `embedder.embed()`.

**Error handling:** File-level errors collected, not fatal. Embedding/storage errors are fatal (raise).

### 6. CLI Integration

**New TypeScript command:** `packages/cli/src/commands/index.ts`
```
rag-forge index --source <dir> [--collection <name>] [--embedding <provider>] [--strategy <name>]
```

**Config flow:** The TypeScript CLI reads `rag-forge.config.ts` via cosmiconfig, then passes relevant config values as a JSON string to the Python subprocess via `--config-json` flag. The Python CLI never reads the TypeScript config file directly.

**New Python CLI entry point:** `packages/core/src/rag_forge_core/cli.py`
- Receives config as `--config-json '{"embedding_provider": "openai", ...}'` from the TS bridge
- Also accepts CLI flags that override config values (e.g., `--source`, `--collection`, `--embedding`)
- Constructs pipeline with correct providers based on merged config
- Runs pipeline, outputs JSON result to stdout
- TypeScript CLI parses JSON and displays formatted output with chalk/ora

**Register in CLI:** Add `registerIndexCommand(program)` to `packages/cli/src/index.ts`.

## Dependencies to Add

**`packages/core/pyproject.toml`:**
```toml
dependencies = [
    "pydantic>=2.0",
    "rich>=13.0",
    "tiktoken>=0.7",
    "pymupdf>=1.24",
    "beautifulsoup4>=4.12",
    "lxml>=5.0",
    "openai>=1.30",
    "qdrant-client>=1.9",
]

[project.optional-dependencies]
local = ["sentence-transformers>=3.0"]
```

## Files to Create/Modify

### New Files (16)
- `packages/core/src/rag_forge_core/parsing/__init__.py`
- `packages/core/src/rag_forge_core/parsing/base.py`
- `packages/core/src/rag_forge_core/parsing/markdown.py`
- `packages/core/src/rag_forge_core/parsing/plaintext.py`
- `packages/core/src/rag_forge_core/parsing/pdf.py`
- `packages/core/src/rag_forge_core/parsing/html.py`
- `packages/core/src/rag_forge_core/parsing/directory.py`
- `packages/core/src/rag_forge_core/embedding/__init__.py`
- `packages/core/src/rag_forge_core/embedding/base.py`
- `packages/core/src/rag_forge_core/embedding/openai_embedder.py`
- `packages/core/src/rag_forge_core/embedding/local_embedder.py`
- `packages/core/src/rag_forge_core/embedding/mock_embedder.py`
- `packages/core/src/rag_forge_core/storage/__init__.py`
- `packages/core/src/rag_forge_core/storage/base.py`
- `packages/core/src/rag_forge_core/storage/qdrant.py`
- `packages/core/src/rag_forge_core/cli.py`
- `packages/cli/src/commands/index.ts`

### Modified Files (4)
- `packages/core/src/rag_forge_core/chunking/recursive.py` (overlap + tiktoken)
- `packages/core/src/rag_forge_core/ingestion/pipeline.py` (real implementation)
- `packages/cli/src/index.ts` (register index command)
- `packages/core/pyproject.toml` (add dependencies)

### New Test Files (4)
- `packages/core/tests/test_parsing.py`
- `packages/core/tests/test_embedding.py`
- `packages/core/tests/test_storage.py`
- `packages/core/tests/test_pipeline_integration.py`

## Testing Strategy

- **Unit tests:** Each parser, embedder, and store implementation tested independently using MockEmbedder and in-memory Qdrant.
- **Integration test:** Full pipeline test: create temp directory with .md and .txt files → run pipeline with MockEmbedder + in-memory Qdrant → verify chunks are indexed and searchable.
- **No external API calls in tests.** All tests use MockEmbedder. OpenAI integration verified manually.

## Verification

After implementation, verify:
1. `uv run pytest packages/core/tests/` — all new tests pass
2. `uv run ruff check .` — zero lint errors
3. `uv run mypy packages/core/src` — zero type errors
4. `pnpm run build` — CLI builds with new index command
5. Manual test: create a `test-docs/` directory with a few .md files, run `rag-forge index --source ./test-docs`, verify output shows chunks indexed

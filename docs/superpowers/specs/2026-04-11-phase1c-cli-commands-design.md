# Phase 1C: CLI Commands Design Spec (init + query)

## Context

Phase 1A built the data pipeline (`rag-forge index`). Phase 1B built the evaluation pipeline (`rag-forge audit`). Phase 1C completes the Phase 1 exit criteria by implementing the remaining two CLI commands: `rag-forge init` (project scaffolding) and `rag-forge query` (RAG query with generation).

After this, a developer can run the full flow: `rag-forge init basic && rag-forge index --source ./docs && rag-forge audit --golden-set qa.json`.

## Scope

**In scope:** `rag-forge init [template]` command (TypeScript, file copying), `rag-forge query "question"` command (Python bridge, retrieval + LLM generation), `GenerationProvider` abstraction (Claude + GPT-4o + mock), `QueryEngine` class, Python CLI `query` subcommand.

**Out of scope:** Multi-query decomposition (`--agent-mode`), hybrid retrieval (BM25), reranking. These are Phase 2 features.

## Component 1: `rag-forge init` (TypeScript)

**Location:** `packages/cli/src/commands/init.ts` (modify existing stub)

**Command:** `rag-forge init [template] [-d, --directory <dir>] [--no-install]`

**Flow:**
1. Validate template name against `AVAILABLE_TEMPLATES` (already in stub)
2. Resolve target directory: use `--directory` value, default to `./<template>` (e.g., `./basic`)
3. Check target directory doesn't already exist (error if it does, unless it's `.`)
4. Locate template files: resolve `templates/<template>/project/` relative to the CLI package root via `import.meta.url`
5. Copy all files from template to target directory recursively
6. Replace `my-rag-pipeline` in `pyproject.toml` with the directory name as the project name
7. If `--no-install` not set, run `uv sync` in the target directory
8. Print success message listing created files and suggested next steps

**Template resolution:** The `templates/` directory ships alongside the CLI package. At build time, tsup bundles the CLI source but templates are static files. They'll be resolved via `fileURLToPath(import.meta.url)` to find the package root, then `../../templates/` relative to the dist directory.

**Dependencies:** `fs-extra` for recursive directory copy (or use Node.js built-in `cp` with `recursive: true` from `fs/promises` — Node 20+ supports this natively, no extra dep needed).

## Component 2: `rag-forge query` (Python Bridge)

### GenerationProvider Abstraction

**Location:** `packages/core/src/rag_forge_core/generation/`

**Protocol:**
```python
class GenerationProvider(Protocol):
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...
    def model_name(self) -> str: ...
```

**Implementations:**

| File | Class | SDK | API Key Env Var | Notes |
|------|-------|-----|-----------------|-------|
| `claude_generator.py` | `ClaudeGenerator` | `anthropic` | `ANTHROPIC_API_KEY` | Claude Sonnet by default |
| `openai_generator.py` | `OpenAIGenerator` | `openai` | `OPENAI_API_KEY` | GPT-4o by default |
| `mock_generator.py` | `MockGenerator` | None | None | Returns configurable fixed response for tests |

Same pattern as `JudgeProvider` and `EmbeddingProvider`. The `anthropic` and `openai` SDKs are already installed in the core package.

### QueryEngine

**Location:** `packages/core/src/rag_forge_core/query/engine.py`

```python
@dataclass
class QueryResult:
    answer: str
    sources: list[SearchResult]
    model_used: str
    chunks_retrieved: int

class QueryEngine:
    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        generator: GenerationProvider,
        collection_name: str = "rag-forge",
        top_k: int = 5,
    ) -> None: ...

    def query(self, question: str) -> QueryResult: ...
```

**Query flow:**
1. Embed the question: `embedder.embed([question])` → query vector
2. Search Qdrant: `store.search(collection, query_vector, top_k)` → list of `SearchResult`
3. Build RAG prompt:
   - System: "Answer the question based only on the provided context. If the context doesn't contain the answer, say so."
   - User: formatted context chunks + the question
4. Generate: `generator.generate(system_prompt, user_prompt)` → answer text
5. Return `QueryResult` with answer, sources, model name, chunk count

### Python CLI Addition

**Modify:** `packages/core/src/rag_forge_core/cli.py` — add `query` subcommand

```
uv run python -m rag_forge_core.cli query --question "What is...?" --embedding mock --generator mock --collection rag-forge --top-k 5
```

Outputs JSON: `{"answer": "...", "sources": [...], "model_used": "...", "chunks_retrieved": 5}`

### TypeScript CLI

**Modify:** `packages/cli/src/commands/query.ts` — wire to Python bridge

Calls `runPythonModule` with `rag_forge_core.cli query --question ...`, parses JSON, displays answer with source citations.

## Files to Create/Modify

### New Files (8)
- `packages/core/src/rag_forge_core/generation/__init__.py`
- `packages/core/src/rag_forge_core/generation/base.py`
- `packages/core/src/rag_forge_core/generation/claude_generator.py`
- `packages/core/src/rag_forge_core/generation/openai_generator.py`
- `packages/core/src/rag_forge_core/generation/mock_generator.py`
- `packages/core/src/rag_forge_core/query/__init__.py`
- `packages/core/src/rag_forge_core/query/engine.py`
- `packages/core/tests/test_query.py`

### Modified Files (4)
- `packages/cli/src/commands/init.ts` (real template copying)
- `packages/cli/src/commands/query.ts` (wire to Python bridge)
- `packages/core/src/rag_forge_core/cli.py` (add query subcommand)
- `packages/cli/__tests__/cli.test.ts` (add init test)

## Testing Strategy

- **Init tests:** Create temp directory, run init logic, verify files exist with correct content. Test template-not-found error. Test `--no-install` flag.
- **Query tests:** Use MockEmbedder + in-memory QdrantStore + MockGenerator. Index a few docs, query, verify answer contains expected text and sources are returned.
- **No external API calls in tests.** All tests use mock providers.

## Verification

After implementation:
1. All Python tests pass
2. All TypeScript tests pass
3. Zero lint/typecheck errors
4. Manual e2e: `rag-forge init basic -d ./test-project`, verify files created
5. Manual e2e: index some docs, then `rag-forge query "What is Python?" --embedding mock --generator mock`, verify answer returned

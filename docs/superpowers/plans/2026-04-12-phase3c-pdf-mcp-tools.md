# Phase 3C: PDF Report Export + MCP Ingest/Inspect Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PDF report export via Playwright headless, and wire the two remaining MCP tools (`rag_ingest` for document indexing and `rag_inspect` for chunk lookup by ID).

**Architecture:** PDF export uses Playwright (optional dep) to render the existing HTML report to PDF. MCP tools call Python CLI subcommands via the shared bridge. A new `inspect` subcommand and `VectorStore.get_by_id()` method enable chunk lookup. All tools registered in the MCP server's `index.ts`.

**Tech Stack:** Python (playwright optional), TypeScript (@modelcontextprotocol/sdk, zod, @rag-forge/shared).

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `packages/evaluator/src/rag_forge_evaluator/report/pdf.py` | PDF generation via Playwright |
| `packages/mcp/src/tools/rag-ingest.ts` | MCP tool for document indexing |
| `packages/mcp/src/tools/rag-inspect.ts` | MCP tool for chunk inspection |
| `packages/core/tests/test_get_by_id.py` | VectorStore.get_by_id() tests |
| `packages/evaluator/tests/test_pdf_generator.py` | PDF generator tests |

### Modified Files

| File | Change |
|------|--------|
| `packages/evaluator/pyproject.toml` | Add playwright optional dep |
| `packages/core/src/rag_forge_core/storage/base.py` | Add get_by_id to protocol |
| `packages/core/src/rag_forge_core/storage/qdrant.py` | Implement get_by_id |
| `packages/core/src/rag_forge_core/cli.py` | Add inspect subcommand |
| `packages/evaluator/src/rag_forge_evaluator/audit.py` | Add PDF generation step |
| `packages/evaluator/src/rag_forge_evaluator/cli.py` | Add --pdf arg |
| `packages/mcp/src/index.ts` | Register rag_ingest + rag_inspect |
| `packages/cli/src/commands/audit.ts` | Add --pdf flag |

---

## Task 1: Add Playwright Optional Dependency

**Files:**
- Modify: `packages/evaluator/pyproject.toml`

- [ ] **Step 1: Add playwright to optional deps**

Read `packages/evaluator/pyproject.toml`. Add `pdf` to `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
ragas = ["ragas>=0.2"]
deepeval = ["deepeval>=1.0"]
pdf = ["playwright>=1.40"]
```

- [ ] **Step 2: Commit**

```bash
git add packages/evaluator/pyproject.toml
git commit -m "chore(evaluator): add playwright optional dependency for PDF export"
```

---

## Task 2: VectorStore.get_by_id()

**Files:**
- Modify: `packages/core/src/rag_forge_core/storage/base.py`
- Modify: `packages/core/src/rag_forge_core/storage/qdrant.py`
- Test: `packages/core/tests/test_get_by_id.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/core/tests/test_get_by_id.py`:

```python
"""Tests for VectorStore.get_by_id()."""

from rag_forge_core.storage.base import VectorItem
from rag_forge_core.storage.qdrant import QdrantStore


class TestGetById:
    def test_get_existing_item(self) -> None:
        store = QdrantStore()
        store.create_collection("test", dimension=4)
        items = [
            VectorItem(id="item-1", vector=[0.1, 0.2, 0.3, 0.4], text="Hello world", metadata={"source_document": "doc.md"}),
            VectorItem(id="item-2", vector=[0.5, 0.6, 0.7, 0.8], text="Goodbye world", metadata={"source_document": "doc2.md"}),
        ]
        store.upsert("test", items)

        result = store.get_by_id("test", "item-1")
        assert result is not None
        assert result.id == "item-1"
        assert result.text == "Hello world"
        assert result.metadata["source_document"] == "doc.md"

    def test_get_missing_item(self) -> None:
        store = QdrantStore()
        store.create_collection("test", dimension=4)
        store.upsert("test", [
            VectorItem(id="item-1", vector=[0.1, 0.2, 0.3, 0.4], text="Hello", metadata={}),
        ])

        result = store.get_by_id("test", "nonexistent")
        assert result is None

    def test_get_from_nonexistent_collection(self) -> None:
        store = QdrantStore()
        result = store.get_by_id("nonexistent", "item-1")
        assert result is None

    def test_get_preserves_metadata(self) -> None:
        store = QdrantStore()
        store.create_collection("test", dimension=4)
        store.upsert("test", [
            VectorItem(id="item-1", vector=[0.1, 0.2, 0.3, 0.4], text="Test",
                       metadata={"source_document": "readme.md", "chunk_index": 3, "strategy": "recursive"}),
        ])

        result = store.get_by_id("test", "item-1")
        assert result is not None
        assert result.metadata["source_document"] == "readme.md"
        assert result.metadata["chunk_index"] == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/core && uv run pytest tests/test_get_by_id.py -v`
Expected: FAIL — `QdrantStore` has no `get_by_id` method.

- [ ] **Step 3: Add get_by_id to VectorStore protocol**

In `packages/core/src/rag_forge_core/storage/base.py`, add to the `VectorStore` protocol:

```python
    def get_by_id(self, collection: str, item_id: str) -> VectorItem | None:
        """Retrieve a single item by its application-level ID. Returns None if not found."""
        ...
```

- [ ] **Step 4: Implement get_by_id in QdrantStore**

In `packages/core/src/rag_forge_core/storage/qdrant.py`, add this method to `QdrantStore`:

IMPORTANT: The QdrantStore uses integer indices as Qdrant point IDs. The application-level UUID `item_id` is stored in the payload as `item_id`. So we need to scroll/filter by payload field, not by Qdrant point ID.

```python
    def get_by_id(self, collection: str, item_id: str) -> VectorItem | None:
        """Retrieve a single item by its application-level ID."""
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            results = self._client.scroll(
                collection_name=collection,
                scroll_filter=Filter(
                    must=[FieldCondition(key="item_id", match=MatchValue(value=item_id))]
                ),
                limit=1,
                with_vectors=False,
            )
            points = results[0]
            if not points:
                return None

            point = points[0]
            payload = dict(point.payload or {})
            text = str(payload.pop("text", ""))
            payload.pop("item_id", None)
            meta = {k: v for k, v in payload.items() if isinstance(v, (str, int, float))}

            return VectorItem(id=item_id, vector=[], text=text, metadata=meta)
        except Exception:
            return None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/core && uv run pytest tests/test_get_by_id.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/core/src/rag_forge_core/storage/ packages/core/tests/test_get_by_id.py
git commit -m "feat(core): add VectorStore.get_by_id() for chunk lookup"
```

---

## Task 3: Python `inspect` Subcommand

**Files:**
- Modify: `packages/core/src/rag_forge_core/cli.py`

- [ ] **Step 1: Add inspect subcommand**

Read `packages/core/src/rag_forge_core/cli.py`. Add:

1. New function after `cmd_status`:

```python
def cmd_inspect(args: argparse.Namespace) -> None:
    """Inspect a specific chunk by ID."""
    collection = args.collection or "rag-forge"
    chunk_id = args.chunk_id
    store = QdrantStore()

    result = store.get_by_id(collection, chunk_id)
    if result is None:
        json.dump({"found": False, "chunk_id": chunk_id, "collection": collection}, sys.stdout)
        return

    output = {
        "found": True,
        "chunk_id": chunk_id,
        "text": result.text,
        "metadata": result.metadata,
        "collection": collection,
    }
    json.dump(output, sys.stdout)
```

2. In `main()`, add subparser:

```python
    inspect_parser = subparsers.add_parser("inspect", help="Inspect a chunk by ID")
    inspect_parser.add_argument("--chunk-id", required=True, help="The chunk ID to inspect")
    inspect_parser.add_argument("--collection", help="Collection name", default="rag-forge")
```

3. Add dispatch:

```python
    elif args.command == "inspect":
        cmd_inspect(args)
```

- [ ] **Step 2: Verify**

Run: `cd packages/core && uv run python -m rag_forge_core.cli inspect --help`
Expected: Shows `--chunk-id` and `--collection` args.

Run: `cd packages/core && uv run python -m rag_forge_core.cli inspect --chunk-id test123`
Expected: `{"found": false, "chunk_id": "test123", "collection": "rag-forge"}`

- [ ] **Step 3: Commit**

```bash
git add packages/core/src/rag_forge_core/cli.py
git commit -m "feat(core): add inspect subcommand for chunk lookup by ID"
```

---

## Task 4: PDF Generator

**Files:**
- Create: `packages/evaluator/src/rag_forge_evaluator/report/pdf.py`
- Test: `packages/evaluator/tests/test_pdf_generator.py`

- [ ] **Step 1: Write the test**

Create `packages/evaluator/tests/test_pdf_generator.py`:

```python
"""Tests for PDF report generator."""

import pytest

from rag_forge_evaluator.report.pdf import PDFGenerator


class TestPDFGenerator:
    def test_import_error_when_playwright_missing(self) -> None:
        """PDFGenerator.generate() should raise ImportError if playwright not installed."""
        try:
            import playwright  # noqa: F401
            pytest.skip("Playwright is installed — cannot test import error path")
        except ImportError:
            pass

        from pathlib import Path

        generator = PDFGenerator()
        with pytest.raises(ImportError, match="Playwright"):
            generator.generate(Path("nonexistent.html"))

    def test_pdf_generator_instantiates(self) -> None:
        """PDFGenerator should be constructable without playwright installed."""
        generator = PDFGenerator()
        assert generator is not None
```

- [ ] **Step 2: Write the implementation**

Create `packages/evaluator/src/rag_forge_evaluator/report/pdf.py`:

```python
"""PDF report generation via Playwright headless Chromium.

Requires: pip install rag-forge-evaluator[pdf] && playwright install chromium
"""

from pathlib import Path


class PDFGenerator:
    """Generates PDF from an HTML audit report via Playwright.

    Launches headless Chromium, opens the HTML file, and prints to PDF.
    """

    def generate(self, html_path: Path) -> Path:
        """Convert HTML report to PDF. Returns path to generated PDF.

        Raises ImportError if Playwright is not installed.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError(
                "Playwright is not installed. Install with: "
                "pip install rag-forge-evaluator[pdf] && playwright install chromium"
            ) from None

        pdf_path = html_path.with_suffix(".pdf")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"file://{html_path.resolve()}")
            page.pdf(path=str(pdf_path), format="A4", print_background=True)
            browser.close()

        return pdf_path
```

- [ ] **Step 3: Run tests**

Run: `cd packages/evaluator && uv run pytest tests/test_pdf_generator.py -v`
Expected: Tests PASS (skip test if playwright is installed).

- [ ] **Step 4: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/report/pdf.py packages/evaluator/tests/test_pdf_generator.py
git commit -m "feat(evaluator): add PDF report generator via Playwright"
```

---

## Task 5: Wire PDF into AuditOrchestrator + CLIs

**Files:**
- Modify: `packages/evaluator/src/rag_forge_evaluator/audit.py`
- Modify: `packages/evaluator/src/rag_forge_evaluator/cli.py`
- Modify: `packages/cli/src/commands/audit.ts`

- [ ] **Step 1: Update AuditOrchestrator**

Read `packages/evaluator/src/rag_forge_evaluator/audit.py`. Add after the report generation block (after `json_report_path = generator.generate_json(...)`):

```python
        # 8. Generate PDF (optional)
        pdf_report_path: Path | None = None
        if self.config.generate_pdf:
            from rag_forge_evaluator.report.pdf import PDFGenerator
            pdf_report_path = PDFGenerator().generate(report_path)
```

Add `pdf_report_path` to `AuditReport`:

```python
@dataclass
class AuditReport:
    evaluation: EvaluationResult
    rmm_level: RMMLevel
    report_path: Path
    json_report_path: Path
    samples_evaluated: int
    pdf_report_path: Path | None = None
```

Pass `pdf_report_path=pdf_report_path` in the return.

- [ ] **Step 2: Update evaluator CLI**

Read `packages/evaluator/src/rag_forge_evaluator/cli.py`. Add `--pdf` arg to the audit parser:

```python
    audit_parser.add_argument("--pdf", action="store_true", help="Generate PDF report")
```

Pass `generate_pdf=args.pdf` in `AuditConfig`:

```python
    config = AuditConfig(
        ...
        generate_pdf=args.pdf,
    )
```

Add to output dict:

```python
        "pdf_report_path": str(report.pdf_report_path) if report.pdf_report_path else None,
```

- [ ] **Step 3: Update TypeScript CLI**

Read `packages/cli/src/commands/audit.ts`. Add option:

```typescript
    .option("--pdf", "Generate PDF report (requires Playwright)")
```

Add to options type: `pdf?: boolean;`

Add to args forwarding:
```typescript
          if (options.pdf) {
            args.push("--pdf");
          }
```

Add to `AuditResult` interface: `pdf_report_path: string | null;`

After `logger.success(...)`, add:
```typescript
          if (output.pdf_report_path) {
            logger.success(`PDF report: ${output.pdf_report_path}`);
          }
```

- [ ] **Step 4: Build and verify**

Run: `cd packages/cli && pnpm run build && pnpm run typecheck`
Run: `cd packages/evaluator && uv run python -m rag_forge_evaluator.cli audit --help` — should show `--pdf`

- [ ] **Step 5: Commit**

```bash
git add packages/evaluator/src/rag_forge_evaluator/audit.py packages/evaluator/src/rag_forge_evaluator/cli.py packages/cli/src/commands/audit.ts
git commit -m "feat(cli): wire PDF export into audit command with --pdf flag"
```

---

## Task 6: MCP Ingest + Inspect Tools

**Files:**
- Create: `packages/mcp/src/tools/rag-ingest.ts`
- Create: `packages/mcp/src/tools/rag-inspect.ts`
- Modify: `packages/mcp/src/index.ts`

- [ ] **Step 1: Create rag-ingest.ts**

Create `packages/mcp/src/tools/rag-ingest.ts`:

```typescript
import { z } from "zod";
import { runPythonModule } from "@rag-forge/shared";

export const ragIngestSchema = z.object({
  source_path: z.string().describe("Path to source directory of documents to index"),
  collection: z.string().default("rag-forge").describe("Collection name"),
  embedding: z.string().default("mock").describe("Embedding provider: openai | local | mock"),
  enrich: z.boolean().default(false).describe("Enable contextual enrichment"),
  sparse_index_path: z.string().optional().describe("Path to persist BM25 sparse index"),
});

export type RagIngestInput = z.infer<typeof ragIngestSchema>;

export async function handleRagIngest(input: RagIngestInput): Promise<string> {
  const args = [
    "index",
    "--source", input.source_path,
    "--collection", input.collection,
    "--embedding", input.embedding,
  ];

  if (input.enrich) {
    args.push("--enrich");
  }
  if (input.sparse_index_path) {
    args.push("--sparse-index-path", input.sparse_index_path);
  }

  const result = await runPythonModule({
    module: "rag_forge_core.cli",
    args,
  });

  if (result.exitCode !== 0) {
    return result.stdout || JSON.stringify({
      status: "error",
      message: result.stderr || "Indexing failed",
    });
  }

  return result.stdout;
}
```

- [ ] **Step 2: Create rag-inspect.ts**

Create `packages/mcp/src/tools/rag-inspect.ts`:

```typescript
import { z } from "zod";
import { runPythonModule } from "@rag-forge/shared";

export const ragInspectSchema = z.object({
  chunk_id: z.string().describe("The ID of the chunk to inspect"),
  collection: z.string().default("rag-forge").describe("Collection name"),
});

export type RagInspectInput = z.infer<typeof ragInspectSchema>;

export async function handleRagInspect(input: RagInspectInput): Promise<string> {
  const result = await runPythonModule({
    module: "rag_forge_core.cli",
    args: [
      "inspect",
      "--chunk-id", input.chunk_id,
      "--collection", input.collection,
    ],
  });

  if (result.exitCode !== 0) {
    return result.stdout || JSON.stringify({
      status: "error",
      message: result.stderr || "Inspect failed",
    });
  }

  return result.stdout;
}
```

- [ ] **Step 3: Update MCP server index.ts**

Read `packages/mcp/src/index.ts`. Add imports and tool registrations:

Add at top:
```typescript
import { ragIngestSchema, handleRagIngest } from "./tools/rag-ingest.js";
import { ragInspectSchema, handleRagInspect } from "./tools/rag-inspect.js";
```

Add inside `createServer()` before `return server;`:
```typescript
  server.tool("rag_ingest", "Index new documents into the pipeline", ragIngestSchema.shape, async (input) => {
    const result = await handleRagIngest(ragIngestSchema.parse(input));
    return { content: [{ type: "text" as const, text: result }] };
  });

  server.tool("rag_inspect", "Debug a specific chunk by ID", ragInspectSchema.shape, async (input) => {
    const result = await handleRagInspect(ragInspectSchema.parse(input));
    return { content: [{ type: "text" as const, text: result }] };
  });
```

- [ ] **Step 4: Build and typecheck**

Run: `cd packages/mcp && pnpm run build && pnpm run typecheck`
Expected: Both succeed.

- [ ] **Step 5: Commit**

```bash
git add packages/mcp/src/tools/rag-ingest.ts packages/mcp/src/tools/rag-inspect.ts packages/mcp/src/index.ts
git commit -m "feat(mcp): add rag_ingest and rag_inspect tools"
```

---

## Task 7: Run Full Test Suite and Lint

- [ ] **Step 1: Run all Python tests**

Run: `uv run pytest -v`
Expected: All tests pass.

- [ ] **Step 2: Run Python linter**

Run: `uv run ruff check .`

- [ ] **Step 3: Run Python type checker**

Run: `uv run mypy packages/core/src packages/evaluator/src packages/observability/src`
NOTE: Add `playwright.*` to mypy ignore overrides if needed.

- [ ] **Step 4: Build TypeScript**

Run: `pnpm run build`

- [ ] **Step 5: Run TypeScript lint and typecheck**

Run: `pnpm run lint && pnpm run typecheck`

- [ ] **Step 6: Fix any issues, commit**

```bash
git add -A
git commit -m "chore: fix lint and type errors from Phase 3C implementation"
```

- [ ] **Step 7: Push**

```bash
git push
```

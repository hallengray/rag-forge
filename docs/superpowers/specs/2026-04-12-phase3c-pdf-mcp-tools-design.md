# Phase 3C: PDF Report Export + MCP Ingest/Inspect Design Spec

## Context

RAG-Forge Phase 3B delivered semantic caching. Phase 3C adds PDF report export via Playwright and wires the two remaining MCP tools (`rag_ingest` and `rag_inspect`).

## Scope

**In scope:**
- PDF report generation from existing HTML via Playwright headless Chromium
- Playwright as optional dependency (`rag-forge-evaluator[pdf]`)
- `--pdf` flag on `rag-forge audit` CLI command
- `rag_ingest` MCP tool calling Python `index` subcommand
- `rag_inspect` MCP tool calling a new Python `inspect` subcommand
- Python `inspect` subcommand to look up a chunk by ID in QdrantStore
- MCP server `index.ts` updated to register the two new tools
- Updated TypeScript CLI `audit.ts` to forward `--pdf` flag

**Out of scope:** Custom PDF templates, PDF watermarking, MCP SSE/HTTP transport (Phase 3D), `rag_ingest` with raw content (separate feature).

## Architecture

### PDF Export

The `ReportGenerator` gains a `generate_pdf()` method. It opens the already-generated HTML file in headless Chromium via Playwright, calls `page.pdf()`, and saves the result. Playwright is an optional dependency — if not installed and `--pdf` is requested, a clear error is raised.

```
rag-forge audit --golden-set eval/golden_set.json --pdf
    │
    ├─ Normal audit pipeline → HTML + JSON reports
    │
    └─ generate_pdf(html_path) → audit-report.pdf
         └─ Playwright:
              chromium.launch(headless=True)
              page.goto(f"file://{html_path}")
              page.pdf(path=pdf_path)
              browser.close()
```

### MCP Tools

```
MCP Server (index.ts)
    ├─ rag_query   [existing]
    ├─ rag_audit   [existing]
    ├─ rag_status  [existing]
    ├─ rag_ingest  [NEW] → shared bridge → rag_forge_core.cli index
    └─ rag_inspect [NEW] → shared bridge → rag_forge_core.cli inspect
```

## Components

### 1. PDF Report Generator

**Location:** `packages/evaluator/src/rag_forge_evaluator/report/pdf.py`

```python
class PDFGenerator:
    """Generates PDF from an HTML audit report via Playwright.

    Requires: pip install rag-forge-evaluator[pdf] && playwright install chromium
    """

    def generate(self, html_path: Path) -> Path:
        """Convert HTML report to PDF. Returns path to generated PDF."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError(
                "Playwright is not installed. Install with: "
                "pip install rag-forge-evaluator[pdf] && playwright install chromium"
            )

        pdf_path = html_path.with_suffix(".pdf")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"file://{html_path.resolve()}")
            page.pdf(path=str(pdf_path), format="A4", print_background=True)
            browser.close()

        return pdf_path
```

### 2. Updated AuditOrchestrator

**Location:** `packages/evaluator/src/rag_forge_evaluator/audit.py` (modify existing)

After generating HTML and JSON reports, if `config.generate_pdf` is True:

```python
        # 8. Generate PDF (optional)
        pdf_path: Path | None = None
        if self.config.generate_pdf:
            from rag_forge_evaluator.report.pdf import PDFGenerator
            pdf_path = PDFGenerator().generate(report_path)
```

`AuditReport` gains `pdf_report_path: Path | None = None` field.

### 3. Python `inspect` Subcommand

**Location:** `packages/core/src/rag_forge_core/cli.py` (modify existing)

New subcommand:

```python
def cmd_inspect(args: argparse.Namespace) -> None:
    """Inspect a specific chunk by ID."""
    collection = args.collection or "rag-forge"
    chunk_id = args.chunk_id
    store = QdrantStore()

    try:
        # Search for the chunk by ID using Qdrant's scroll/retrieve
        result = store.get_by_id(collection, chunk_id)
        if result is None:
            json.dump({"found": False, "chunk_id": chunk_id}, sys.stdout)
            return

        output = {
            "found": True,
            "chunk_id": chunk_id,
            "text": result.text,
            "metadata": result.metadata,
            "collection": collection,
        }
        json.dump(output, sys.stdout)
    except (ValueError, KeyError):
        json.dump({"found": False, "chunk_id": chunk_id, "error": "Collection not found"}, sys.stdout)
```

This requires adding a `get_by_id()` method to `QdrantStore` and the `VectorStore` protocol.

### 4. VectorStore.get_by_id()

**Location:** `packages/core/src/rag_forge_core/storage/base.py` (modify existing)

Add to `VectorStore` protocol:

```python
def get_by_id(self, collection: str, item_id: str) -> VectorItem | None:
    """Retrieve a single item by ID. Returns None if not found."""
    ...
```

**Location:** `packages/core/src/rag_forge_core/storage/qdrant.py` (modify existing)

Implement using Qdrant's `retrieve()` method:

```python
def get_by_id(self, collection: str, item_id: str) -> VectorItem | None:
    points = self._client.retrieve(collection, ids=[item_id], with_payload=True, with_vectors=False)
    if not points:
        return None
    point = points[0]
    return VectorItem(
        id=str(point.id),
        vector=[],
        text=point.payload.get("text", ""),
        metadata={k: v for k, v in point.payload.items() if k != "text"},
    )
```

### 5. MCP Tool: rag_ingest

**Location:** `packages/mcp/src/tools/rag-ingest.ts` (create new)

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
    if (input.enrich) args.push("--enrich");
    if (input.sparse_index_path) args.push("--sparse-index-path", input.sparse_index_path);

    const result = await runPythonModule({ module: "rag_forge_core.cli", args });

    if (result.exitCode !== 0) {
        return result.stdout || JSON.stringify({ status: "error", message: result.stderr || "Indexing failed" });
    }
    return result.stdout;
}
```

### 6. MCP Tool: rag_inspect

**Location:** `packages/mcp/src/tools/rag-inspect.ts` (create new)

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
        args: ["inspect", "--chunk-id", input.chunk_id, "--collection", input.collection],
    });

    if (result.exitCode !== 0) {
        return result.stdout || JSON.stringify({ status: "error", message: result.stderr || "Inspect failed" });
    }
    return result.stdout;
}
```

### 7. Updated MCP Server Index

**Location:** `packages/mcp/src/index.ts` (modify existing)

Register the two new tools:

```typescript
import { ragIngestSchema, handleRagIngest } from "./tools/rag-ingest.js";
import { ragInspectSchema, handleRagInspect } from "./tools/rag-inspect.js";

// In createServer():
server.tool("rag_ingest", "Index new documents into the pipeline", ragIngestSchema.shape, async (input) => {
    const result = await handleRagIngest(ragIngestSchema.parse(input));
    return { content: [{ type: "text" as const, text: result }] };
});

server.tool("rag_inspect", "Debug a specific chunk by ID", ragInspectSchema.shape, async (input) => {
    const result = await handleRagInspect(ragInspectSchema.parse(input));
    return { content: [{ type: "text" as const, text: result }] };
});
```

### 8. Updated CLI

**Location:** `packages/cli/src/commands/audit.ts` (modify existing)

Add `--pdf` flag. Forward to Python bridge.

**Location:** `packages/evaluator/src/rag_forge_evaluator/cli.py` (modify existing)

Add `--pdf` argument. Set `generate_pdf=args.pdf` in `AuditConfig`.

## Dependencies

### New optional dependency (packages/evaluator/pyproject.toml)

```toml
[project.optional-dependencies]
pdf = ["playwright>=1.40"]
```

## Testing Strategy

### Unit Tests

1. `test_pdf_generator.py` — Test `PDFGenerator` raises ImportError when Playwright not installed. (Actual PDF generation tested only when Playwright is available — skip if not installed.)

2. `test_get_by_id.py` — Test `QdrantStore.get_by_id()` returns item, returns None for missing ID.

3. `test_inspect_cli.py` — Test `cmd_inspect` returns JSON with chunk details.

## File Summary

### New files:
- `packages/evaluator/src/rag_forge_evaluator/report/pdf.py`
- `packages/mcp/src/tools/rag-ingest.ts`
- `packages/mcp/src/tools/rag-inspect.ts`
- `packages/core/tests/test_get_by_id.py`
- `packages/evaluator/tests/test_pdf_generator.py`

### Modified files:
- `packages/evaluator/pyproject.toml` (add playwright optional dep)
- `packages/evaluator/src/rag_forge_evaluator/audit.py` (add PDF generation step)
- `packages/evaluator/src/rag_forge_evaluator/cli.py` (add --pdf arg)
- `packages/core/src/rag_forge_core/storage/base.py` (add get_by_id to protocol)
- `packages/core/src/rag_forge_core/storage/qdrant.py` (implement get_by_id)
- `packages/core/src/rag_forge_core/cli.py` (add inspect subcommand)
- `packages/mcp/src/index.ts` (register new tools)
- `packages/cli/src/commands/audit.ts` (add --pdf flag)

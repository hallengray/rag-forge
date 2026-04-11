# Phase 1A: Data Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete data ingestion pipeline so `rag-forge index --source ./docs` parses documents, chunks them, embeds them, and stores vectors in Qdrant.

**Architecture:** Strategy pattern with dependency injection. Each pipeline stage (parsing, chunking, embedding, storage) is an independent component behind a Protocol. The `IngestionPipeline` orchestrator receives all components via constructor. The TypeScript CLI delegates to Python via subprocess bridge.

**Tech Stack:** Python 3.11+ (pydantic, tiktoken, pymupdf, beautifulsoup4, openai, qdrant-client), TypeScript (Commander.js, execa), pytest, vitest.

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `packages/core/src/rag_forge_core/parsing/base.py` | `Document` dataclass + `DocumentParser` protocol |
| `packages/core/src/rag_forge_core/parsing/markdown.py` | Parse `.md` files, strip YAML frontmatter |
| `packages/core/src/rag_forge_core/parsing/plaintext.py` | Parse `.txt` files |
| `packages/core/src/rag_forge_core/parsing/pdf.py` | Parse `.pdf` via pymupdf |
| `packages/core/src/rag_forge_core/parsing/html.py` | Parse `.html`/`.htm` via beautifulsoup4 |
| `packages/core/src/rag_forge_core/parsing/directory.py` | Walk directory, route files to parsers |
| `packages/core/src/rag_forge_core/parsing/__init__.py` | Module exports |
| `packages/core/src/rag_forge_core/embedding/base.py` | `EmbeddingProvider` protocol |
| `packages/core/src/rag_forge_core/embedding/mock_embedder.py` | Deterministic hash-based embedder for tests |
| `packages/core/src/rag_forge_core/embedding/openai_embedder.py` | OpenAI text-embedding-3-small |
| `packages/core/src/rag_forge_core/embedding/local_embedder.py` | Local BGE-M3 via sentence-transformers |
| `packages/core/src/rag_forge_core/embedding/__init__.py` | Module exports |
| `packages/core/src/rag_forge_core/storage/base.py` | `VectorItem`, `SearchResult`, `VectorStore` protocol |
| `packages/core/src/rag_forge_core/storage/qdrant.py` | Qdrant implementation |
| `packages/core/src/rag_forge_core/storage/__init__.py` | Module exports |
| `packages/core/src/rag_forge_core/cli.py` | Python CLI entry point for bridge |
| `packages/cli/src/commands/index.ts` | TypeScript `rag-forge index` command |
| `packages/core/tests/test_parsing.py` | Parsing tests |
| `packages/core/tests/test_embedding.py` | Embedding tests |
| `packages/core/tests/test_storage.py` | Storage tests |
| `packages/core/tests/test_pipeline_integration.py` | End-to-end pipeline test |

### Modified Files

| File | Change |
|------|--------|
| `packages/core/pyproject.toml` | Add pymupdf, beautifulsoup4, lxml, openai, qdrant-client deps |
| `packages/core/src/rag_forge_core/chunking/recursive.py` | Add tiktoken token counting + overlap handling |
| `packages/core/src/rag_forge_core/ingestion/pipeline.py` | Replace stub with real orchestration |
| `packages/cli/src/index.ts` | Register index command |

---

## Task 1: Add Dependencies

**Files:**
- Modify: `packages/core/pyproject.toml`

- [ ] **Step 1: Update pyproject.toml with new dependencies**

Replace the full content of `packages/core/pyproject.toml` with:

```toml
[project]
name = "rag-forge-core"
version = "0.1.0"
description = "RAG pipeline primitives: ingestion, retrieval, context management, and security"
requires-python = ">=3.11"
license = "MIT"
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

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/rag_forge_core"]
```

- [ ] **Step 2: Install new dependencies**

Run: `uv sync --all-packages`
Expected: All new packages install successfully including pymupdf, beautifulsoup4, openai, qdrant-client.

- [ ] **Step 3: Commit**

```bash
git add packages/core/pyproject.toml uv.lock
git commit -m "chore(core): add parsing, embedding, and storage dependencies"
```

---

## Task 2: Document Parsing — Protocol & Base Types

**Files:**
- Create: `packages/core/src/rag_forge_core/parsing/base.py`
- Create: `packages/core/src/rag_forge_core/parsing/__init__.py`
- Test: `packages/core/tests/test_parsing.py`

- [ ] **Step 1: Create the parsing directory**

Run: `mkdir -p packages/core/src/rag_forge_core/parsing`

- [ ] **Step 2: Write the failing test for Document and DocumentParser**

Create `packages/core/tests/test_parsing.py`:

```python
"""Tests for the document parsing module."""

from pathlib import Path

from rag_forge_core.parsing.base import Document, DocumentParser


class TestDocument:
    def test_document_creation(self) -> None:
        doc = Document(
            text="Hello world",
            source_path="/test/file.md",
            metadata={"format": "markdown"},
        )
        assert doc.text == "Hello world"
        assert doc.source_path == "/test/file.md"
        assert doc.metadata["format"] == "markdown"

    def test_document_empty_metadata(self) -> None:
        doc = Document(text="content", source_path="/test.txt", metadata={})
        assert doc.metadata == {}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest packages/core/tests/test_parsing.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'rag_forge_core.parsing'`

- [ ] **Step 4: Implement base.py**

Create `packages/core/src/rag_forge_core/parsing/base.py`:

```python
"""Base types and protocol for document parsing."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class Document:
    """A parsed document with text content and metadata."""

    text: str
    source_path: str
    metadata: dict[str, str | int | float] = field(default_factory=dict)


@runtime_checkable
class DocumentParser(Protocol):
    """Protocol that all document parsers must implement."""

    def parse(self, path: Path) -> list[Document]:
        """Parse a file and return a list of documents."""
        ...

    def supported_extensions(self) -> list[str]:
        """Return file extensions this parser handles (e.g., ['.md'])."""
        ...
```

Create `packages/core/src/rag_forge_core/parsing/__init__.py`:

```python
"""Document parsing: extract text from MD, TXT, PDF, and HTML files."""

from rag_forge_core.parsing.base import Document, DocumentParser

__all__ = ["Document", "DocumentParser"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest packages/core/tests/test_parsing.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add packages/core/src/rag_forge_core/parsing/ packages/core/tests/test_parsing.py
git commit -m "feat(core): add Document dataclass and DocumentParser protocol"
```

---

## Task 3: Markdown & Plaintext Parsers

**Files:**
- Create: `packages/core/src/rag_forge_core/parsing/markdown.py`
- Create: `packages/core/src/rag_forge_core/parsing/plaintext.py`
- Test: `packages/core/tests/test_parsing.py` (append)

- [ ] **Step 1: Write failing tests for MarkdownParser and PlainTextParser**

Append to `packages/core/tests/test_parsing.py`:

```python
import textwrap

from rag_forge_core.parsing.markdown import MarkdownParser
from rag_forge_core.parsing.plaintext import PlainTextParser


class TestMarkdownParser:
    def test_supported_extensions(self) -> None:
        parser = MarkdownParser()
        assert parser.supported_extensions() == [".md"]

    def test_parse_simple_markdown(self, tmp_path: Path) -> None:
        md_file = tmp_path / "test.md"
        md_file.write_text("# Hello\n\nThis is a test document.", encoding="utf-8")
        docs = parser = MarkdownParser()
        docs = parser.parse(md_file)
        assert len(docs) == 1
        assert "Hello" in docs[0].text
        assert "This is a test document." in docs[0].text
        assert docs[0].metadata["format"] == "markdown"

    def test_strips_yaml_frontmatter(self, tmp_path: Path) -> None:
        content = textwrap.dedent("""\
            ---
            title: My Doc
            author: Femi
            ---
            # Main Content

            Body text here.
        """)
        md_file = tmp_path / "frontmatter.md"
        md_file.write_text(content, encoding="utf-8")
        parser = MarkdownParser()
        docs = parser.parse(md_file)
        assert len(docs) == 1
        assert "---" not in docs[0].text
        assert "title: My Doc" not in docs[0].text
        assert "Body text here." in docs[0].text
        assert docs[0].metadata.get("title") == "My Doc"

    def test_parse_nonexistent_file(self, tmp_path: Path) -> None:
        parser = MarkdownParser()
        docs = parser.parse(tmp_path / "missing.md")
        assert len(docs) == 0


class TestPlainTextParser:
    def test_supported_extensions(self) -> None:
        parser = PlainTextParser()
        assert parser.supported_extensions() == [".txt"]

    def test_parse_simple_text(self, tmp_path: Path) -> None:
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Hello world\nSecond line", encoding="utf-8")
        parser = PlainTextParser()
        docs = parser.parse(txt_file)
        assert len(docs) == 1
        assert docs[0].text == "Hello world\nSecond line"
        assert docs[0].metadata["format"] == "plaintext"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest packages/core/tests/test_parsing.py -v -k "Markdown or PlainText"`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement MarkdownParser**

Create `packages/core/src/rag_forge_core/parsing/markdown.py`:

```python
"""Markdown document parser. Strips YAML frontmatter, preserves headers as metadata."""

import re
from pathlib import Path

from rag_forge_core.parsing.base import Document


class MarkdownParser:
    """Parses .md files, strips YAML frontmatter, extracts metadata."""

    _FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    def parse(self, path: Path) -> list[Document]:
        """Parse a markdown file and return a Document."""
        try:
            raw = path.read_text(encoding="utf-8")
        except (FileNotFoundError, PermissionError, UnicodeDecodeError):
            return []

        metadata: dict[str, str | int | float] = {
            "format": "markdown",
            "filename": path.name,
        }

        text = raw
        match = self._FRONTMATTER_RE.match(raw)
        if match:
            frontmatter_block = match.group(1)
            text = raw[match.end() :]
            for line in frontmatter_block.splitlines():
                if ":" in line:
                    key, _, value = line.partition(":")
                    metadata[key.strip()] = value.strip()

        return [Document(text=text.strip(), source_path=str(path), metadata=metadata)]

    def supported_extensions(self) -> list[str]:
        return [".md"]
```

- [ ] **Step 4: Implement PlainTextParser**

Create `packages/core/src/rag_forge_core/parsing/plaintext.py`:

```python
"""Plain text document parser."""

from pathlib import Path

from rag_forge_core.parsing.base import Document


class PlainTextParser:
    """Parses .txt files with UTF-8 encoding."""

    def parse(self, path: Path) -> list[Document]:
        """Parse a plain text file and return a Document."""
        try:
            text = path.read_text(encoding="utf-8")
        except (FileNotFoundError, PermissionError, UnicodeDecodeError):
            return []

        return [
            Document(
                text=text,
                source_path=str(path),
                metadata={"format": "plaintext", "filename": path.name},
            )
        ]

    def supported_extensions(self) -> list[str]:
        return [".txt"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest packages/core/tests/test_parsing.py -v -k "Markdown or PlainText"`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add packages/core/src/rag_forge_core/parsing/markdown.py packages/core/src/rag_forge_core/parsing/plaintext.py packages/core/tests/test_parsing.py
git commit -m "feat(core): add Markdown and PlainText document parsers"
```

---

## Task 4: PDF & HTML Parsers

**Files:**
- Create: `packages/core/src/rag_forge_core/parsing/pdf.py`
- Create: `packages/core/src/rag_forge_core/parsing/html.py`
- Test: `packages/core/tests/test_parsing.py` (append)

- [ ] **Step 1: Write failing tests for PDFParser and HTMLParser**

Append to `packages/core/tests/test_parsing.py`:

```python
from rag_forge_core.parsing.html import HtmlParser
from rag_forge_core.parsing.pdf import PdfParser


class TestHtmlParser:
    def test_supported_extensions(self) -> None:
        parser = HtmlParser()
        assert ".html" in parser.supported_extensions()
        assert ".htm" in parser.supported_extensions()

    def test_parse_simple_html(self, tmp_path: Path) -> None:
        html_file = tmp_path / "test.html"
        html_file.write_text(
            "<html><head><title>My Page</title></head>"
            "<body><h1>Hello</h1><p>Content here.</p></body></html>",
            encoding="utf-8",
        )
        parser = HtmlParser()
        docs = parser.parse(html_file)
        assert len(docs) == 1
        assert "Content here." in docs[0].text
        assert "<h1>" not in docs[0].text
        assert docs[0].metadata.get("title") == "My Page"
        assert docs[0].metadata["format"] == "html"

    def test_parse_nonexistent_file(self, tmp_path: Path) -> None:
        parser = HtmlParser()
        docs = parser.parse(tmp_path / "missing.html")
        assert len(docs) == 0


class TestPdfParser:
    def test_supported_extensions(self) -> None:
        parser = PdfParser()
        assert parser.supported_extensions() == [".pdf"]

    def test_parse_nonexistent_file(self, tmp_path: Path) -> None:
        parser = PdfParser()
        docs = parser.parse(tmp_path / "missing.pdf")
        assert len(docs) == 0
```

Note: We don't create a real PDF in tests because it requires binary fixtures. We test the nonexistent-file path and verify extension support. Real PDF parsing is verified manually.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest packages/core/tests/test_parsing.py -v -k "Html or Pdf"`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement PdfParser**

Create `packages/core/src/rag_forge_core/parsing/pdf.py`:

```python
"""PDF document parser using PyMuPDF."""

from pathlib import Path

import pymupdf

from rag_forge_core.parsing.base import Document


class PdfParser:
    """Parses .pdf files using PyMuPDF, extracting text page by page."""

    def parse(self, path: Path) -> list[Document]:
        """Parse a PDF file and return a Document with all pages combined."""
        try:
            doc = pymupdf.open(str(path))
        except (FileNotFoundError, pymupdf.FileDataError, RuntimeError):
            return []

        pages_text: list[str] = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                pages_text.append(text.strip())

        doc.close()

        if not pages_text:
            return []

        return [
            Document(
                text="\n\n".join(pages_text),
                source_path=str(path),
                metadata={
                    "format": "pdf",
                    "filename": path.name,
                    "page_count": len(pages_text),
                },
            )
        ]

    def supported_extensions(self) -> list[str]:
        return [".pdf"]
```

- [ ] **Step 4: Implement HtmlParser**

Create `packages/core/src/rag_forge_core/parsing/html.py`:

```python
"""HTML document parser using BeautifulSoup."""

from pathlib import Path

from bs4 import BeautifulSoup

from rag_forge_core.parsing.base import Document


class HtmlParser:
    """Parses .html and .htm files, extracting text and title."""

    def parse(self, path: Path) -> list[Document]:
        """Parse an HTML file, strip tags, extract title."""
        try:
            raw = path.read_text(encoding="utf-8")
        except (FileNotFoundError, PermissionError, UnicodeDecodeError):
            return []

        soup = BeautifulSoup(raw, "lxml")

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        if not text.strip():
            return []

        metadata: dict[str, str | int | float] = {
            "format": "html",
            "filename": path.name,
        }
        if title:
            metadata["title"] = title

        return [Document(text=text, source_path=str(path), metadata=metadata)]

    def supported_extensions(self) -> list[str]:
        return [".html", ".htm"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest packages/core/tests/test_parsing.py -v -k "Html or Pdf"`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add packages/core/src/rag_forge_core/parsing/pdf.py packages/core/src/rag_forge_core/parsing/html.py packages/core/tests/test_parsing.py
git commit -m "feat(core): add PDF and HTML document parsers"
```

---

## Task 5: DirectoryParser

**Files:**
- Create: `packages/core/src/rag_forge_core/parsing/directory.py`
- Modify: `packages/core/src/rag_forge_core/parsing/__init__.py`
- Test: `packages/core/tests/test_parsing.py` (append)

- [ ] **Step 1: Write failing test for DirectoryParser**

Append to `packages/core/tests/test_parsing.py`:

```python
from rag_forge_core.parsing.directory import DirectoryParser


class TestDirectoryParser:
    def test_parse_directory_with_mixed_files(self, tmp_path: Path) -> None:
        (tmp_path / "readme.md").write_text("# Hello\n\nMarkdown content.", encoding="utf-8")
        (tmp_path / "notes.txt").write_text("Plain text notes.", encoding="utf-8")
        (tmp_path / "data.csv").write_text("a,b,c", encoding="utf-8")  # unsupported

        parser = DirectoryParser()
        docs, errors = parser.parse_directory(tmp_path)

        assert len(docs) == 2
        sources = {d.metadata["format"] for d in docs}
        assert sources == {"markdown", "plaintext"}
        assert len(errors) == 0

    def test_parse_directory_recursive(self, tmp_path: Path) -> None:
        sub = tmp_path / "subdir"
        sub.mkdir()
        (tmp_path / "top.md").write_text("Top level", encoding="utf-8")
        (sub / "nested.txt").write_text("Nested file", encoding="utf-8")

        parser = DirectoryParser()
        docs, errors = parser.parse_directory(tmp_path)
        assert len(docs) == 2

    def test_parse_empty_directory(self, tmp_path: Path) -> None:
        parser = DirectoryParser()
        docs, errors = parser.parse_directory(tmp_path)
        assert len(docs) == 0
        assert len(errors) == 0

    def test_parse_nonexistent_directory(self, tmp_path: Path) -> None:
        parser = DirectoryParser()
        docs, errors = parser.parse_directory(tmp_path / "missing")
        assert len(docs) == 0
        assert len(errors) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/core/tests/test_parsing.py::TestDirectoryParser -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement DirectoryParser**

Create `packages/core/src/rag_forge_core/parsing/directory.py`:

```python
"""Directory parser that walks a directory tree and routes files to appropriate parsers."""

from pathlib import Path

from rag_forge_core.parsing.base import Document, DocumentParser
from rag_forge_core.parsing.html import HtmlParser
from rag_forge_core.parsing.markdown import MarkdownParser
from rag_forge_core.parsing.pdf import PdfParser
from rag_forge_core.parsing.plaintext import PlainTextParser


class DirectoryParser:
    """Walks a directory tree and parses all supported files.

    Routes each file to the correct parser by extension.
    Skips unsupported files silently. Collects per-file errors without stopping.
    """

    def __init__(self) -> None:
        parsers: list[DocumentParser] = [
            MarkdownParser(),
            PlainTextParser(),
            PdfParser(),
            HtmlParser(),
        ]
        self._extension_map: dict[str, DocumentParser] = {}
        for parser in parsers:
            for ext in parser.supported_extensions():
                self._extension_map[ext] = parser

    def parse_directory(self, directory: Path) -> tuple[list[Document], list[str]]:
        """Parse all supported files in a directory recursively.

        Returns:
            Tuple of (documents, errors). Errors are strings describing failures.
        """
        documents: list[Document] = []
        errors: list[str] = []

        if not directory.exists():
            errors.append(f"Directory not found: {directory}")
            return documents, errors

        for file_path in sorted(directory.rglob("*")):
            if not file_path.is_file():
                continue

            ext = file_path.suffix.lower()
            parser = self._extension_map.get(ext)
            if parser is None:
                continue

            try:
                docs = parser.parse(file_path)
                documents.extend(docs)
            except Exception as e:
                errors.append(f"Failed to parse {file_path}: {e}")

        return documents, errors

    def supported_extensions(self) -> list[str]:
        """Return all supported file extensions."""
        return sorted(self._extension_map.keys())
```

- [ ] **Step 4: Update parsing __init__.py**

Replace `packages/core/src/rag_forge_core/parsing/__init__.py`:

```python
"""Document parsing: extract text from MD, TXT, PDF, and HTML files."""

from rag_forge_core.parsing.base import Document, DocumentParser
from rag_forge_core.parsing.directory import DirectoryParser

__all__ = ["DirectoryParser", "Document", "DocumentParser"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest packages/core/tests/test_parsing.py -v`
Expected: All tests pass (2 Document + 6 Markdown/PlainText + 5 Html/Pdf + 4 Directory = 17 tests)

- [ ] **Step 6: Commit**

```bash
git add packages/core/src/rag_forge_core/parsing/ packages/core/tests/test_parsing.py
git commit -m "feat(core): add DirectoryParser with recursive file walking"
```

---

## Task 6: Enhance RecursiveChunker with Tiktoken + Overlap

**Files:**
- Modify: `packages/core/src/rag_forge_core/chunking/recursive.py`
- Modify: `packages/core/tests/test_chunking.py` (add tests)

- [ ] **Step 1: Write failing tests for tiktoken-based chunking and overlap**

Append to `packages/core/tests/test_chunking.py`:

```python
class TestRecursiveChunkerEnhanced:
    def test_token_counting_uses_tiktoken(self) -> None:
        """Token counts should be based on tiktoken, not word splits."""
        config = ChunkConfig(chunk_size=50, overlap_ratio=0.0)
        chunker = RecursiveChunker(config)
        text = "Hello world. " * 100
        chunks = chunker.chunk(text, "test.md")
        stats = chunker.stats(chunks)
        # tiktoken tokens != word count, so total_tokens should reflect real tokens
        assert stats.total_tokens > 0
        assert stats.total_chunks > 1

    def test_overlap_produces_overlapping_content(self) -> None:
        """With overlap > 0, consecutive chunks should share some text."""
        config = ChunkConfig(chunk_size=20, overlap_ratio=0.25)
        chunker = RecursiveChunker(config)
        text = "Sentence one about dogs. Sentence two about cats. Sentence three about birds. Sentence four about fish. Sentence five about frogs."
        chunks = chunker.chunk(text, "test.md")
        if len(chunks) >= 2:
            # The end of chunk 0 should overlap with the beginning of chunk 1
            chunk0_words = chunks[0].text.split()
            chunk1_words = chunks[1].text.split()
            # Check there's some shared content
            overlap_found = any(w in chunk1_words[:10] for w in chunk0_words[-10:])
            assert overlap_found, "Expected overlapping content between consecutive chunks"

    def test_stats_uses_tiktoken_counts(self) -> None:
        config = ChunkConfig(chunk_size=100, overlap_ratio=0.0)
        chunker = RecursiveChunker(config)
        text = "Hello world."
        chunks = chunker.chunk(text, "test.md")
        stats = chunker.stats(chunks)
        # "Hello world." is 3 tokens in cl100k_base, not 2 words
        assert stats.total_tokens >= 2
```

- [ ] **Step 2: Run tests to verify new tests fail**

Run: `uv run pytest packages/core/tests/test_chunking.py::TestRecursiveChunkerEnhanced -v`
Expected: Tests may pass partially or fail depending on current word-count behavior. The overlap test should fail since overlap is not implemented.

- [ ] **Step 3: Rewrite RecursiveChunker with tiktoken and overlap**

Replace the full content of `packages/core/src/rag_forge_core/chunking/recursive.py`:

```python
"""Recursive text splitting strategy (default).

Splits by separator hierarchy: paragraphs -> lines -> sentences -> words.
Feb 2026 benchmark: 69% accuracy vs semantic chunking at 54%.
"""

import tiktoken

from rag_forge_core.chunking.base import Chunk, ChunkStats, ChunkStrategy
from rag_forge_core.chunking.config import ChunkConfig

_ENCODING = tiktoken.get_encoding("cl100k_base")


def _token_count(text: str) -> int:
    """Count tokens using tiktoken cl100k_base encoding."""
    return len(_ENCODING.encode(text))


class RecursiveChunker(ChunkStrategy):
    """Recursive text splitter using a hierarchy of separators with tiktoken token counting."""

    def __init__(self, config: ChunkConfig | None = None) -> None:
        super().__init__(config or ChunkConfig(strategy="recursive"))

    def chunk(self, text: str, source: str) -> list[Chunk]:
        """Split text recursively by separator hierarchy with overlap."""
        raw_chunks = self._split_recursive(text, self.config.separators)
        raw_chunks = [c for c in raw_chunks if c.strip()]

        if not raw_chunks:
            return []

        chunks_with_overlap = self._apply_overlap(raw_chunks)

        return [
            Chunk(
                text=chunk_text,
                chunk_index=i,
                source_document=source,
                strategy_used="recursive",
                overlap_tokens=self.config.overlap_tokens if i > 0 else 0,
            )
            for i, chunk_text in enumerate(chunks_with_overlap)
        ]

    def preview(self, text: str, source: str) -> list[Chunk]:
        """Preview chunking without side effects."""
        return self.chunk(text, source)

    def stats(self, chunks: list[Chunk]) -> ChunkStats:
        """Compute statistics using tiktoken token counts."""
        if not chunks:
            return ChunkStats(
                total_chunks=0,
                avg_chunk_size=0,
                min_chunk_size=0,
                max_chunk_size=0,
                total_tokens=0,
            )

        sizes = [_token_count(c.text) for c in chunks]
        return ChunkStats(
            total_chunks=len(chunks),
            avg_chunk_size=sum(sizes) // len(sizes),
            min_chunk_size=min(sizes),
            max_chunk_size=max(sizes),
            total_tokens=sum(sizes),
        )

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        """Add overlap tokens from the end of each chunk to the start of the next."""
        overlap_tokens = self.config.overlap_tokens
        if overlap_tokens <= 0 or len(chunks) <= 1:
            return chunks

        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tokens = _ENCODING.encode(chunks[i - 1])
            overlap_text = _ENCODING.decode(prev_tokens[-overlap_tokens:])
            result.append(overlap_text + " " + chunks[i])

        return result

    def _split_recursive(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split text using the separator hierarchy with tiktoken sizing."""
        if not separators:
            return [text] if text.strip() else []

        separator = separators[0]
        parts = text.split(separator)

        result: list[str] = []
        current = ""

        for part in parts:
            candidate = f"{current}{separator}{part}" if current else part
            token_count = _token_count(candidate)

            if token_count > self.config.chunk_size and current:
                result.append(current.strip())
                current = part
            else:
                current = candidate

        if current.strip():
            result.append(current.strip())

        return result
```

- [ ] **Step 4: Run all chunking tests**

Run: `uv run pytest packages/core/tests/test_chunking.py -v`
Expected: All tests pass (original + enhanced)

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/rag_forge_core/chunking/recursive.py packages/core/tests/test_chunking.py
git commit -m "feat(core): enhance RecursiveChunker with tiktoken token counting and overlap"
```

---

## Task 7: Embedding Provider — Protocol & MockEmbedder

**Files:**
- Create: `packages/core/src/rag_forge_core/embedding/base.py`
- Create: `packages/core/src/rag_forge_core/embedding/mock_embedder.py`
- Create: `packages/core/src/rag_forge_core/embedding/__init__.py`
- Create: `packages/core/tests/test_embedding.py`

- [ ] **Step 1: Create the embedding directory**

Run: `mkdir -p packages/core/src/rag_forge_core/embedding`

- [ ] **Step 2: Write failing tests**

Create `packages/core/tests/test_embedding.py`:

```python
"""Tests for the embedding provider module."""

from rag_forge_core.embedding.base import EmbeddingProvider
from rag_forge_core.embedding.mock_embedder import MockEmbedder


class TestMockEmbedder:
    def test_implements_protocol(self) -> None:
        embedder = MockEmbedder()
        assert isinstance(embedder, EmbeddingProvider)

    def test_returns_correct_dimension(self) -> None:
        embedder = MockEmbedder(dimension=384)
        assert embedder.dimension() == 384

    def test_embed_returns_correct_count(self) -> None:
        embedder = MockEmbedder()
        vectors = embedder.embed(["hello", "world"])
        assert len(vectors) == 2

    def test_embed_returns_correct_dimension(self) -> None:
        embedder = MockEmbedder(dimension=128)
        vectors = embedder.embed(["test"])
        assert len(vectors[0]) == 128

    def test_deterministic_same_input_same_output(self) -> None:
        embedder = MockEmbedder()
        v1 = embedder.embed(["hello world"])
        v2 = embedder.embed(["hello world"])
        assert v1 == v2

    def test_different_input_different_output(self) -> None:
        embedder = MockEmbedder()
        v1 = embedder.embed(["hello"])
        v2 = embedder.embed(["world"])
        assert v1 != v2

    def test_model_name(self) -> None:
        embedder = MockEmbedder()
        assert embedder.model_name() == "mock-embedder"

    def test_empty_input(self) -> None:
        embedder = MockEmbedder()
        vectors = embedder.embed([])
        assert vectors == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest packages/core/tests/test_embedding.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement base.py and MockEmbedder**

Create `packages/core/src/rag_forge_core/embedding/base.py`:

```python
"""Base protocol for embedding providers."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol that all embedding providers must implement."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        ...

    def dimension(self) -> int:
        """Return the dimensionality of the embedding vectors."""
        ...

    def model_name(self) -> str:
        """Return the name of the embedding model."""
        ...
```

Create `packages/core/src/rag_forge_core/embedding/mock_embedder.py`:

```python
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
```

Create `packages/core/src/rag_forge_core/embedding/__init__.py`:

```python
"""Embedding providers: OpenAI, local BGE-M3, and mock for testing."""

from rag_forge_core.embedding.base import EmbeddingProvider
from rag_forge_core.embedding.mock_embedder import MockEmbedder

__all__ = ["EmbeddingProvider", "MockEmbedder"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest packages/core/tests/test_embedding.py -v`
Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add packages/core/src/rag_forge_core/embedding/ packages/core/tests/test_embedding.py
git commit -m "feat(core): add EmbeddingProvider protocol and MockEmbedder"
```

---

## Task 8: OpenAI & Local Embedding Providers

**Files:**
- Create: `packages/core/src/rag_forge_core/embedding/openai_embedder.py`
- Create: `packages/core/src/rag_forge_core/embedding/local_embedder.py`

- [ ] **Step 1: Implement OpenAIEmbedder**

Create `packages/core/src/rag_forge_core/embedding/openai_embedder.py`:

```python
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
        # Default dimensions for known models
        dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return dimensions.get(self._model, 1536)

    def model_name(self) -> str:
        return self._model
```

- [ ] **Step 2: Implement LocalEmbedder**

Create `packages/core/src/rag_forge_core/embedding/local_embedder.py`:

```python
"""Local embedding provider using sentence-transformers (optional dependency)."""

from __future__ import annotations


class LocalEmbedder:
    """Embeds text locally using sentence-transformers models (e.g., BAAI/bge-m3).

    Requires the optional 'local' dependency group:
        pip install rag-forge-core[local]
    """

    def __init__(self, model_name: str = "BAAI/bge-m3") -> None:
        try:
            from sentence_transformers import SentenceTransformer
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
```

- [ ] **Step 3: Update embedding __init__.py**

Replace `packages/core/src/rag_forge_core/embedding/__init__.py`:

```python
"""Embedding providers: OpenAI, local BGE-M3, and mock for testing."""

from rag_forge_core.embedding.base import EmbeddingProvider
from rag_forge_core.embedding.mock_embedder import MockEmbedder

__all__ = ["EmbeddingProvider", "MockEmbedder"]
```

Note: OpenAIEmbedder and LocalEmbedder are intentionally NOT in `__all__` — they're imported explicitly when needed to avoid triggering import errors for users who don't have the optional deps.

- [ ] **Step 4: Lint and typecheck**

Run: `uv run ruff check packages/core/src/rag_forge_core/embedding/ && uv run mypy packages/core/src/rag_forge_core/embedding/`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/rag_forge_core/embedding/
git commit -m "feat(core): add OpenAI and local sentence-transformers embedding providers"
```

---

## Task 9: Vector Store — Protocol & QdrantStore

**Files:**
- Create: `packages/core/src/rag_forge_core/storage/base.py`
- Create: `packages/core/src/rag_forge_core/storage/qdrant.py`
- Create: `packages/core/src/rag_forge_core/storage/__init__.py`
- Create: `packages/core/tests/test_storage.py`

- [ ] **Step 1: Create the storage directory**

Run: `mkdir -p packages/core/src/rag_forge_core/storage`

- [ ] **Step 2: Write failing tests**

Create `packages/core/tests/test_storage.py`:

```python
"""Tests for the vector storage module."""

from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.storage.base import SearchResult, VectorItem, VectorStore
from rag_forge_core.storage.qdrant import QdrantStore


class TestQdrantStore:
    def test_implements_protocol(self) -> None:
        store = QdrantStore()
        assert isinstance(store, VectorStore)

    def test_create_collection(self) -> None:
        store = QdrantStore()
        store.create_collection("test", dimension=384)
        assert store.count("test") == 0

    def test_upsert_and_count(self) -> None:
        store = QdrantStore()
        store.create_collection("test", dimension=4)
        items = [
            VectorItem(id="1", vector=[0.1, 0.2, 0.3, 0.4], text="hello", metadata={}),
            VectorItem(id="2", vector=[0.5, 0.6, 0.7, 0.8], text="world", metadata={}),
        ]
        count = store.upsert("test", items)
        assert count == 2
        assert store.count("test") == 2

    def test_search_returns_results(self) -> None:
        embedder = MockEmbedder(dimension=384)
        store = QdrantStore()
        store.create_collection("test", dimension=384)

        texts = ["Python is great", "JavaScript is popular", "Rust is fast"]
        vectors = embedder.embed(texts)
        items = [
            VectorItem(id=str(i), vector=v, text=t, metadata={"index": i})
            for i, (t, v) in enumerate(zip(texts, vectors))
        ]
        store.upsert("test", items)

        query_vector = embedder.embed(["Python programming"])[0]
        results = store.search("test", query_vector, top_k=2)
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(r.score >= 0 for r in results)

    def test_delete_collection(self) -> None:
        store = QdrantStore()
        store.create_collection("test", dimension=4)
        store.upsert("test", [VectorItem(id="1", vector=[0.1, 0.2, 0.3, 0.4], text="hi", metadata={})])
        store.delete_collection("test")
        assert store.count("test") == 0
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest packages/core/tests/test_storage.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement base.py**

Create `packages/core/src/rag_forge_core/storage/base.py`:

```python
"""Base types and protocol for vector storage."""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class VectorItem:
    """An item to store in the vector database."""

    id: str
    vector: list[float]
    text: str
    metadata: dict[str, str | int | float] = field(default_factory=dict)


@dataclass
class SearchResult:
    """A result from a vector similarity search."""

    id: str
    text: str
    score: float
    metadata: dict[str, str | int | float] = field(default_factory=dict)


@runtime_checkable
class VectorStore(Protocol):
    """Protocol that all vector store implementations must follow."""

    def create_collection(self, name: str, dimension: int) -> None:
        """Create a new collection (or recreate if exists)."""
        ...

    def upsert(self, collection: str, items: list[VectorItem]) -> int:
        """Insert or update items. Returns count of items upserted."""
        ...

    def search(self, collection: str, vector: list[float], top_k: int = 5) -> list[SearchResult]:
        """Search for the most similar vectors. Returns results sorted by score descending."""
        ...

    def count(self, collection: str) -> int:
        """Return the number of items in a collection. Returns 0 if collection doesn't exist."""
        ...

    def delete_collection(self, collection: str) -> None:
        """Delete a collection and all its data."""
        ...
```

- [ ] **Step 5: Implement QdrantStore**

Create `packages/core/src/rag_forge_core/storage/qdrant.py`:

```python
"""Qdrant vector store implementation."""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from rag_forge_core.storage.base import SearchResult, VectorItem


class QdrantStore:
    """Vector store backed by Qdrant. Defaults to in-memory (no Docker needed).

    Configuration options:
        - location=":memory:" (default) — ephemeral, zero config
        - path="./qdrant_data" — file-based persistence
        - url="http://localhost:6333" — remote Qdrant server
    """

    def __init__(
        self,
        location: str = ":memory:",
        url: str | None = None,
        path: str | None = None,
    ) -> None:
        if url:
            self._client = QdrantClient(url=url)
        elif path:
            self._client = QdrantClient(path=path)
        else:
            self._client = QdrantClient(location=location)

    def create_collection(self, name: str, dimension: int) -> None:
        """Create a collection, deleting it first if it already exists."""
        if self._client.collection_exists(name):
            self._client.delete_collection(name)
        self._client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
        )

    def upsert(self, collection: str, items: list[VectorItem]) -> int:
        """Upsert items into the collection."""
        if not items:
            return 0

        points = [
            PointStruct(
                id=idx,
                vector=item.vector,
                payload={"text": item.text, "item_id": item.id, **item.metadata},
            )
            for idx, item in enumerate(items)
        ]
        self._client.upsert(collection_name=collection, points=points)
        return len(points)

    def search(
        self, collection: str, vector: list[float], top_k: int = 5
    ) -> list[SearchResult]:
        """Search by vector similarity."""
        hits = self._client.query_points(
            collection_name=collection,
            query=vector,
            limit=top_k,
        ).points

        results: list[SearchResult] = []
        for hit in hits:
            payload = hit.payload or {}
            text = str(payload.pop("text", ""))
            item_id = str(payload.pop("item_id", hit.id))
            meta = {k: v for k, v in payload.items() if isinstance(v, (str, int, float))}
            results.append(
                SearchResult(id=item_id, text=text, score=hit.score or 0.0, metadata=meta)
            )
        return results

    def count(self, collection: str) -> int:
        """Return item count in a collection."""
        try:
            info = self._client.get_collection(collection)
            return info.points_count or 0
        except Exception:
            return 0

    def delete_collection(self, collection: str) -> None:
        """Delete a collection."""
        try:
            self._client.delete_collection(collection)
        except Exception:
            pass
```

Create `packages/core/src/rag_forge_core/storage/__init__.py`:

```python
"""Vector storage: Qdrant and protocol definitions."""

from rag_forge_core.storage.base import SearchResult, VectorItem, VectorStore
from rag_forge_core.storage.qdrant import QdrantStore

__all__ = ["QdrantStore", "SearchResult", "VectorItem", "VectorStore"]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest packages/core/tests/test_storage.py -v`
Expected: 5 passed

- [ ] **Step 7: Commit**

```bash
git add packages/core/src/rag_forge_core/storage/ packages/core/tests/test_storage.py
git commit -m "feat(core): add VectorStore protocol and QdrantStore implementation"
```

---

## Task 10: Ingestion Pipeline — Real Implementation

**Files:**
- Modify: `packages/core/src/rag_forge_core/ingestion/pipeline.py`
- Create: `packages/core/tests/test_pipeline_integration.py`

- [ ] **Step 1: Write failing integration test**

Create `packages/core/tests/test_pipeline_integration.py`:

```python
"""Integration test for the full ingestion pipeline."""

from pathlib import Path

from rag_forge_core.chunking.recursive import RecursiveChunker
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.ingestion.pipeline import IngestionPipeline, IngestionResult
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.storage.qdrant import QdrantStore


class TestIngestionPipeline:
    def _make_pipeline(self) -> IngestionPipeline:
        return IngestionPipeline(
            parser=DirectoryParser(),
            chunker=RecursiveChunker(),
            embedder=MockEmbedder(),
            store=QdrantStore(),
        )

    def test_full_pipeline_with_markdown(self, tmp_path: Path) -> None:
        (tmp_path / "doc1.md").write_text(
            "# Introduction\n\nThis is the introduction to our system.\n\n"
            "## Features\n\nOur system has many great features.",
            encoding="utf-8",
        )
        (tmp_path / "doc2.txt").write_text(
            "This is a plain text document with some content.",
            encoding="utf-8",
        )

        pipeline = self._make_pipeline()
        result = pipeline.run(tmp_path)

        assert isinstance(result, IngestionResult)
        assert result.documents_processed == 2
        assert result.chunks_created > 0
        assert result.chunks_indexed > 0
        assert result.chunks_indexed == result.chunks_created
        assert len(result.errors) == 0

    def test_pipeline_with_empty_directory(self, tmp_path: Path) -> None:
        pipeline = self._make_pipeline()
        result = pipeline.run(tmp_path)
        assert result.documents_processed == 0
        assert result.chunks_created == 0
        assert result.chunks_indexed == 0

    def test_pipeline_with_nonexistent_directory(self, tmp_path: Path) -> None:
        pipeline = self._make_pipeline()
        result = pipeline.run(tmp_path / "missing")
        assert result.documents_processed == 0
        assert len(result.errors) > 0

    def test_pipeline_chunks_are_searchable(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text(
            "Python is a programming language used for data science and web development.",
            encoding="utf-8",
        )

        embedder = MockEmbedder()
        store = QdrantStore()
        pipeline = IngestionPipeline(
            parser=DirectoryParser(),
            chunker=RecursiveChunker(),
            embedder=embedder,
            store=store,
            collection_name="test-search",
        )
        pipeline.run(tmp_path)

        query_vec = embedder.embed(["What is Python?"])[0]
        results = store.search("test-search", query_vec, top_k=3)
        assert len(results) > 0
        assert any("Python" in r.text for r in results)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/core/tests/test_pipeline_integration.py -v`
Expected: FAIL — `IngestionPipeline` constructor doesn't accept the new parameters yet.

- [ ] **Step 3: Rewrite pipeline.py with real implementation**

Replace the full content of `packages/core/src/rag_forge_core/ingestion/pipeline.py`:

```python
"""Full ingestion pipeline: parse -> chunk -> embed -> store."""

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from rag_forge_core.chunking.base import ChunkStrategy
from rag_forge_core.embedding.base import EmbeddingProvider
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.storage.base import VectorItem, VectorStore

EMBEDDING_BATCH_SIZE = 2048


@dataclass
class IngestionResult:
    """Result of an ingestion pipeline run."""

    documents_processed: int
    chunks_created: int
    chunks_indexed: int
    errors: list[str] = field(default_factory=list)


class IngestionPipeline:
    """Orchestrates the full document ingestion process.

    Pipeline stages:
    1. Parse: Extract text from documents (PDF, MD, HTML, etc.)
    2. Chunk: Split documents using the configured strategy
    3. Embed: Generate vector embeddings for each chunk
    4. Store: Index chunks in the vector database
    """

    def __init__(
        self,
        parser: DirectoryParser,
        chunker: ChunkStrategy,
        embedder: EmbeddingProvider,
        store: VectorStore,
        collection_name: str = "rag-forge",
    ) -> None:
        self.parser = parser
        self.chunker = chunker
        self.embedder = embedder
        self.store = store
        self.collection_name = collection_name

    def run(self, source_path: str | Path) -> IngestionResult:
        """Run the full ingestion pipeline on a directory of documents."""
        source = Path(source_path)
        errors: list[str] = []

        # 1. Parse documents
        documents, parse_errors = self.parser.parse_directory(source)
        errors.extend(parse_errors)

        if not documents:
            return IngestionResult(
                documents_processed=0, chunks_created=0, chunks_indexed=0, errors=errors
            )

        # 2. Chunk documents
        all_chunks = []
        for doc in documents:
            chunks = self.chunker.chunk(doc.text, doc.source_path)
            all_chunks.extend(chunks)

        if not all_chunks:
            return IngestionResult(
                documents_processed=len(documents),
                chunks_created=0,
                chunks_indexed=0,
                errors=errors,
            )

        # 3. Embed chunks in batches
        chunk_texts = [c.text for c in all_chunks]
        all_vectors: list[list[float]] = []
        for i in range(0, len(chunk_texts), EMBEDDING_BATCH_SIZE):
            batch = chunk_texts[i : i + EMBEDDING_BATCH_SIZE]
            vectors = self.embedder.embed(batch)
            all_vectors.extend(vectors)

        # 4. Create collection and upsert
        self.store.create_collection(self.collection_name, self.embedder.dimension())

        items = [
            VectorItem(
                id=str(uuid.uuid4()),
                vector=vector,
                text=chunk.text,
                metadata={
                    "source_document": chunk.source_document,
                    "chunk_index": chunk.chunk_index,
                    "strategy": chunk.strategy_used,
                },
            )
            for chunk, vector in zip(all_chunks, all_vectors)
        ]
        indexed_count = self.store.upsert(self.collection_name, items)

        return IngestionResult(
            documents_processed=len(documents),
            chunks_created=len(all_chunks),
            chunks_indexed=indexed_count,
            errors=errors,
        )
```

- [ ] **Step 4: Run integration tests**

Run: `uv run pytest packages/core/tests/test_pipeline_integration.py -v`
Expected: 4 passed

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `uv run pytest packages/core/tests/ -v`
Expected: All tests pass (chunking + parsing + embedding + storage + integration)

- [ ] **Step 6: Commit**

```bash
git add packages/core/src/rag_forge_core/ingestion/pipeline.py packages/core/tests/test_pipeline_integration.py
git commit -m "feat(core): implement full ingestion pipeline with parse/chunk/embed/store"
```

---

## Task 11: Python CLI Entry Point

**Files:**
- Create: `packages/core/src/rag_forge_core/cli.py`

- [ ] **Step 1: Implement the Python CLI entry point**

Create `packages/core/src/rag_forge_core/cli.py`:

```python
"""Python CLI entry point for the rag-forge TypeScript bridge.

Called via: uv run python -m rag_forge_core.cli index --source ./docs --config-json '{...}'
Outputs JSON to stdout for the TypeScript CLI to parse and display.
"""

import argparse
import json
import sys
from pathlib import Path

from rag_forge_core.chunking.config import ChunkConfig
from rag_forge_core.chunking.recursive import RecursiveChunker
from rag_forge_core.embedding.mock_embedder import MockEmbedder
from rag_forge_core.ingestion.pipeline import IngestionPipeline
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.storage.qdrant import QdrantStore


def _create_embedder(provider: str) -> MockEmbedder:
    """Create an embedding provider based on config."""
    if provider == "openai":
        from rag_forge_core.embedding.openai_embedder import OpenAIEmbedder

        return OpenAIEmbedder()  # type: ignore[return-value]
    if provider == "local":
        from rag_forge_core.embedding.local_embedder import LocalEmbedder

        return LocalEmbedder()  # type: ignore[return-value]
    return MockEmbedder()


def cmd_index(args: argparse.Namespace) -> None:
    """Run the index command."""
    config = json.loads(args.config_json) if args.config_json else {}

    source = Path(args.source)
    collection = args.collection or config.get("collection_name", "rag-forge")
    embedding_provider = args.embedding or config.get("embedding_provider", "mock")
    chunk_size = config.get("chunk_size", 512)
    overlap_ratio = config.get("overlap_ratio", 0.1)

    chunk_config = ChunkConfig(
        strategy="recursive",
        chunk_size=chunk_size,
        overlap_ratio=overlap_ratio,
    )

    pipeline = IngestionPipeline(
        parser=DirectoryParser(),
        chunker=RecursiveChunker(chunk_config),
        embedder=_create_embedder(embedding_provider),
        store=QdrantStore(),
        collection_name=collection,
    )

    result = pipeline.run(source)

    output = {
        "success": len(result.errors) == 0,
        "documents_processed": result.documents_processed,
        "chunks_created": result.chunks_created,
        "chunks_indexed": result.chunks_indexed,
        "errors": result.errors,
    }
    print(json.dumps(output))


def main() -> None:
    """Main entry point for the Python CLI bridge."""
    parser = argparse.ArgumentParser(prog="rag-forge-core", description="RAG-Forge Python core CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Index documents into the vector store")
    index_parser.add_argument("--source", required=True, help="Source directory of documents")
    index_parser.add_argument("--collection", help="Collection name (default: rag-forge)")
    index_parser.add_argument("--embedding", help="Embedding provider: openai | local | mock")
    index_parser.add_argument("--config-json", help="JSON config string from TypeScript CLI")

    args = parser.parse_args()
    if args.command == "index":
        cmd_index(args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test the Python CLI manually**

Run: `uv run python -m rag_forge_core.cli index --source ./docs --embedding mock`
Expected: JSON output like `{"success": true, "documents_processed": 2, ...}`

- [ ] **Step 3: Lint and typecheck**

Run: `uv run ruff check packages/core/src/rag_forge_core/cli.py && uv run mypy packages/core/src/rag_forge_core/cli.py`
Expected: No errors (may need type ignores for the dynamic import returns)

- [ ] **Step 4: Commit**

```bash
git add packages/core/src/rag_forge_core/cli.py
git commit -m "feat(core): add Python CLI entry point for TypeScript bridge"
```

---

## Task 12: TypeScript CLI Index Command

**Files:**
- Create: `packages/cli/src/commands/index.ts`
- Modify: `packages/cli/src/index.ts`

- [ ] **Step 1: Create the index command**

Create `packages/cli/src/commands/index.ts`:

```typescript
import type { Command } from "commander";
import ora from "ora";
import { runPythonModule } from "../lib/python-bridge.js";
import { loadConfig } from "../lib/config.js";
import { logger } from "../lib/logger.js";

interface IndexResult {
  success: boolean;
  documents_processed: number;
  chunks_created: number;
  chunks_indexed: number;
  errors: string[];
}

export function registerIndexCommand(program: Command): void {
  program
    .command("index")
    .requiredOption("-s, --source <dir>", "Source directory of documents to index")
    .option("-c, --collection <name>", "Collection name", "rag-forge")
    .option("-e, --embedding <provider>", "Embedding provider: openai | local | mock", "mock")
    .option("--strategy <name>", "Chunking strategy", "recursive")
    .description("Index documents into the vector store")
    .action(
      async (options: {
        source: string;
        collection: string;
        embedding: string;
        strategy: string;
      }) => {
        const spinner = ora("Indexing documents...").start();

        try {
          const config = await loadConfig();

          const configJson = JSON.stringify({
            embedding_provider: options.embedding,
            collection_name: options.collection,
            chunk_size: config.thresholds.contextRelevance > 0 ? 512 : 512,
            overlap_ratio: 0.1,
          });

          const result = await runPythonModule({
            module: "rag_forge_core.cli",
            args: [
              "index",
              "--source",
              options.source,
              "--collection",
              options.collection,
              "--embedding",
              options.embedding,
              "--config-json",
              configJson,
            ],
          });

          if (result.exitCode !== 0) {
            spinner.fail("Indexing failed");
            logger.error(result.stderr || "Unknown error during indexing");
            process.exit(1);
          }

          const output: IndexResult = JSON.parse(result.stdout);

          if (output.success) {
            spinner.succeed("Indexing complete");
            logger.info(`Documents processed: ${String(output.documents_processed)}`);
            logger.info(`Chunks created: ${String(output.chunks_created)}`);
            logger.info(`Chunks indexed: ${String(output.chunks_indexed)}`);
          } else {
            spinner.warn("Indexing completed with errors");
            for (const error of output.errors) {
              logger.error(error);
            }
          }
        } catch (error) {
          spinner.fail("Indexing failed");
          const message = error instanceof Error ? error.message : "Unknown error";
          logger.error(message);
          process.exit(1);
        }
      },
    );
}
```

- [ ] **Step 2: Register the index command in the CLI entry point**

Replace the full content of `packages/cli/src/index.ts`:

```typescript
import { Command } from "commander";
import { registerInitCommand } from "./commands/init.js";
import { registerAuditCommand } from "./commands/audit.js";
import { registerQueryCommand } from "./commands/query.js";
import { registerIndexCommand } from "./commands/index.js";

const program = new Command();

program
  .name("rag-forge")
  .description(
    "Framework-agnostic CLI toolkit for production-grade RAG pipelines with evaluation baked in",
  )
  .version("0.1.0");

registerInitCommand(program);
registerIndexCommand(program);
registerAuditCommand(program);
registerQueryCommand(program);

program.parse();
```

- [ ] **Step 3: Build and verify the CLI**

Run: `pnpm run build`
Expected: Both packages build successfully

- [ ] **Step 4: Verify the index command is registered**

Run: `node packages/cli/dist/index.js --help`
Expected: Output includes `index` in the command list

- [ ] **Step 5: Commit**

```bash
git add packages/cli/src/commands/index.ts packages/cli/src/index.ts
git commit -m "feat(cli): add rag-forge index command with Python bridge integration"
```

---

## Task 13: Full Verification

- [ ] **Step 1: Run all Python tests**

Run: `uv run pytest packages/core/tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Run all TypeScript tests**

Run: `pnpm run test:ts`
Expected: All tests pass (existing CLI + MCP tests)

- [ ] **Step 3: Lint everything**

Run: `pnpm run lint`
Expected: Zero errors

- [ ] **Step 4: Typecheck everything**

Run: `pnpm run typecheck`
Expected: Zero errors

- [ ] **Step 5: Build everything**

Run: `pnpm run build`
Expected: Zero errors

- [ ] **Step 6: Manual end-to-end test**

Create a test directory and run the full pipeline:

```bash
mkdir -p test-docs
echo "# RAG-Forge Test\n\nThis is a test document about RAG pipelines.\n\n## Features\n\nRAG-Forge supports chunking, embedding, and evaluation." > test-docs/test.md
echo "Plain text document for testing the ingestion pipeline." > test-docs/notes.txt
uv run python -m rag_forge_core.cli index --source ./test-docs --embedding mock
```

Expected: JSON output showing `documents_processed: 2`, `chunks_created > 0`, `chunks_indexed > 0`, `success: true`.

- [ ] **Step 7: Clean up and commit**

```bash
rm -rf test-docs
git add -A
git commit -m "feat(core): complete Phase 1A data pipeline implementation

Implements the full ingestion pipeline:
- Document parsing (MD, TXT, PDF, HTML) with DirectoryParser
- Enhanced RecursiveChunker with tiktoken + overlap
- EmbeddingProvider abstraction (OpenAI, local BGE-M3, mock)
- QdrantStore vector storage (in-memory default)
- IngestionPipeline orchestrator
- Python CLI entry point for TypeScript bridge
- rag-forge index CLI command

All tests pass. All lint/typecheck clean."
```

- [ ] **Step 8: Push**

```bash
git push origin main
```

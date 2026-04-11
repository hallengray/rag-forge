"""Tests for the document parsing module."""

import textwrap
from pathlib import Path

from rag_forge_core.parsing.base import Document
from rag_forge_core.parsing.directory import DirectoryParser
from rag_forge_core.parsing.html import HtmlParser
from rag_forge_core.parsing.markdown import MarkdownParser
from rag_forge_core.parsing.pdf import PdfParser
from rag_forge_core.parsing.plaintext import PlainTextParser


class TestDocument:
    def test_document_creation(self) -> None:
        doc = Document(text="Hello", source_path="/test.md", metadata={"format": "markdown"})
        assert doc.text == "Hello"
        assert doc.source_path == "/test.md"
        assert doc.metadata["format"] == "markdown"

    def test_document_empty_metadata(self) -> None:
        doc = Document(text="content", source_path="/test.txt", metadata={})
        assert doc.metadata == {}


class TestMarkdownParser:
    def test_supported_extensions(self) -> None:
        assert MarkdownParser().supported_extensions() == [".md"]

    def test_parse_simple_markdown(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_text("# Hello\n\nContent here.", encoding="utf-8")
        docs = MarkdownParser().parse(f)
        assert len(docs) == 1
        assert "Hello" in docs[0].text
        assert "Content here." in docs[0].text
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
        f = tmp_path / "fm.md"
        f.write_text(content, encoding="utf-8")
        docs = MarkdownParser().parse(f)
        assert len(docs) == 1
        assert "---" not in docs[0].text
        assert "Body text here." in docs[0].text
        assert docs[0].metadata.get("title") == "My Doc"

    def test_parse_nonexistent(self, tmp_path: Path) -> None:
        assert MarkdownParser().parse(tmp_path / "missing.md") == []


class TestPlainTextParser:
    def test_supported_extensions(self) -> None:
        assert PlainTextParser().supported_extensions() == [".txt"]

    def test_parse_simple_text(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("Hello world\nLine 2", encoding="utf-8")
        docs = PlainTextParser().parse(f)
        assert len(docs) == 1
        assert docs[0].text == "Hello world\nLine 2"
        assert docs[0].metadata["format"] == "plaintext"

    def test_parse_nonexistent(self, tmp_path: Path) -> None:
        assert PlainTextParser().parse(tmp_path / "missing.txt") == []


class TestHtmlParser:
    def test_supported_extensions(self) -> None:
        exts = HtmlParser().supported_extensions()
        assert ".html" in exts
        assert ".htm" in exts

    def test_parse_simple_html(self, tmp_path: Path) -> None:
        f = tmp_path / "test.html"
        f.write_text(
            "<html><head><title>My Page</title></head>"
            "<body><h1>Hello</h1><p>Content here.</p></body></html>",
            encoding="utf-8",
        )
        docs = HtmlParser().parse(f)
        assert len(docs) == 1
        assert "Content here." in docs[0].text
        assert "<h1>" not in docs[0].text
        assert docs[0].metadata.get("title") == "My Page"
        assert docs[0].metadata["format"] == "html"

    def test_parse_nonexistent(self, tmp_path: Path) -> None:
        assert HtmlParser().parse(tmp_path / "missing.html") == []


class TestPdfParser:
    def test_supported_extensions(self) -> None:
        assert PdfParser().supported_extensions() == [".pdf"]

    def test_parse_nonexistent(self, tmp_path: Path) -> None:
        assert PdfParser().parse(tmp_path / "missing.pdf") == []


class TestDirectoryParser:
    def test_parse_mixed_files(self, tmp_path: Path) -> None:
        (tmp_path / "readme.md").write_text("# Hello\n\nMarkdown.", encoding="utf-8")
        (tmp_path / "notes.txt").write_text("Plain text.", encoding="utf-8")
        (tmp_path / "data.csv").write_text("a,b,c", encoding="utf-8")
        docs, errors = DirectoryParser().parse_directory(tmp_path)
        assert len(docs) == 2
        assert {d.metadata["format"] for d in docs} == {"markdown", "plaintext"}
        assert len(errors) == 0

    def test_parse_recursive(self, tmp_path: Path) -> None:
        sub = tmp_path / "subdir"
        sub.mkdir()
        (tmp_path / "top.md").write_text("Top", encoding="utf-8")
        (sub / "nested.txt").write_text("Nested", encoding="utf-8")
        docs, _errors = DirectoryParser().parse_directory(tmp_path)
        assert len(docs) == 2

    def test_empty_directory(self, tmp_path: Path) -> None:
        docs, errors = DirectoryParser().parse_directory(tmp_path)
        assert len(docs) == 0
        assert len(errors) == 0

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        docs, errors = DirectoryParser().parse_directory(tmp_path / "missing")
        assert len(docs) == 0
        assert len(errors) == 1

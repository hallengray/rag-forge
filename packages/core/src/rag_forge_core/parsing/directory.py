"""Directory-level parser that dispatches files to the correct parser."""

from pathlib import Path

from .base import Document, DocumentParser
from .html import HtmlParser
from .markdown import MarkdownParser
from .pdf import PdfParser
from .plaintext import PlainTextParser


class DirectoryParser:
    """Recursively parse a directory, routing each file to the appropriate parser.

    Unsupported file extensions are silently skipped.  Per-file exceptions are
    caught and recorded in the errors list returned alongside the documents.
    """

    def __init__(self) -> None:
        parsers: list[DocumentParser] = [
            MarkdownParser(),
            PlainTextParser(),
            PdfParser(),
            HtmlParser(),
        ]
        # Build a flat extension → parser lookup table
        self._extension_map: dict[str, DocumentParser] = {}
        for parser in parsers:
            for ext in parser.supported_extensions():
                self._extension_map[ext] = parser

    def parse_directory(
        self,
        directory: Path,
    ) -> tuple[list[Document], list[str]]:
        """Walk *directory* recursively and parse every supported file.

        Args:
            directory: Root directory to scan.

        Returns:
            A tuple of ``(documents, errors)`` where *errors* is a list of
            human-readable strings describing any problems encountered.
        """
        documents: list[Document] = []
        errors: list[str] = []

        if not directory.is_dir():
            errors.append(f"Path is not a directory: {directory}")
            return documents, errors

        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue

            ext = file_path.suffix.lower()
            parser = self._extension_map.get(ext)
            if parser is None:
                continue  # silently skip unsupported extensions

            try:
                docs = parser.parse(file_path)
                documents.extend(docs)
            except Exception as exc:
                errors.append(f"Failed to parse {file_path}: {exc}")

        return documents, errors

"""PDF document parser using PyMuPDF (pymupdf)."""

from pathlib import Path
from typing import Any

import pymupdf  # type: ignore[import-untyped]

from .base import Document as ParsedDocument


class PdfParser:
    """Parse PDF files into :class:`ParsedDocument` objects using PyMuPDF."""

    def parse(self, path: Path) -> list[ParsedDocument]:
        """Open *path* as a PDF, extract all page text, and return a document.

        Pages are joined with a blank line between them.  Returns an empty list
        if the file cannot be opened or read.
        """
        try:
            pdf_file: Any = pymupdf.open(str(path))
            pages: list[str] = [pdf_file[i].get_text() for i in range(len(pdf_file))]
            text = "\n\n".join(pages)
            page_count: int = len(pages)
        except Exception:
            return []

        return [
            ParsedDocument(
                text=text,
                source_path=str(path),
                metadata={
                    "format": "pdf",
                    "page_count": page_count,
                },
            )
        ]

    def supported_extensions(self) -> list[str]:
        """Return the list of file extensions this parser handles."""
        return [".pdf"]

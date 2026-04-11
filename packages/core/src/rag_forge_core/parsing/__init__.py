"""Document parsing sub-package for RAG-Forge Core.

Public surface:
    Document        — dataclass holding parsed text + metadata
    DocumentParser  — structural Protocol all parsers must satisfy
    MarkdownParser  — parses .md files, strips YAML frontmatter
    PlainTextParser — parses .txt files
    PdfParser       — parses .pdf files via PyMuPDF
    HtmlParser      — parses .html/.htm files via BeautifulSoup4
    DirectoryParser — walks a directory and dispatches to sub-parsers
"""

from .base import Document, DocumentParser
from .directory import DirectoryParser
from .html import HtmlParser
from .markdown import MarkdownParser
from .pdf import PdfParser
from .plaintext import PlainTextParser

__all__ = [
    "DirectoryParser",
    "Document",
    "DocumentParser",
    "HtmlParser",
    "MarkdownParser",
    "PdfParser",
    "PlainTextParser",
]

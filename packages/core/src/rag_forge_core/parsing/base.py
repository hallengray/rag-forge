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

    def parse(self, path: Path) -> list[Document]: ...

    def supported_extensions(self) -> list[str]: ...

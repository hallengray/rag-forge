"""Plain-text document parser."""

from pathlib import Path

from .base import Document


class PlainTextParser:
    """Parse plain-text (.txt) files into :class:`Document` objects."""

    def parse(self, path: Path) -> list[Document]:
        """Read *path* and return a single-element list with the parsed document.

        Returns an empty list if the file cannot be read (e.g. does not exist).
        """
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return []

        return [
            Document(
                text=text,
                source_path=str(path),
                metadata={"format": "plaintext"},
            )
        ]

    def supported_extensions(self) -> list[str]:
        """Return the list of file extensions this parser handles."""
        return [".txt"]

"""HTML document parser using BeautifulSoup4 + lxml."""

from pathlib import Path

from bs4 import BeautifulSoup  # type: ignore[import-untyped]

from .base import Document

# Tags whose content we want to discard entirely before extracting visible text.
_NOISE_TAGS: list[str] = ["script", "style", "nav", "footer", "header"]


class HtmlParser:
    """Parse HTML (.html / .htm) files into :class:`Document` objects."""

    def parse(self, path: Path) -> list[Document]:
        """Read *path*, strip boilerplate tags, and return extracted text.

        Returns an empty list if the file cannot be read or parsed.
        """
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return []

        try:
            soup = BeautifulSoup(raw, "lxml")
        except Exception:
            return []

        # Extract <title> before we decompose any tags
        title_tag = soup.find("title")
        title: str = title_tag.get_text(strip=True) if title_tag else ""

        # Remove noise tags in-place
        for tag_name in _NOISE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        text = soup.get_text(separator="\n", strip=True)

        metadata: dict[str, str | int | float] = {"format": "html"}
        if title:
            metadata["title"] = title

        return [
            Document(
                text=text,
                source_path=str(path),
                metadata=metadata,
            )
        ]

    def supported_extensions(self) -> list[str]:
        """Return the list of file extensions this parser handles."""
        return [".html", ".htm"]

"""Markdown document parser."""

import re
from pathlib import Path

from rag_forge_core.parsing.base import Document

# Matches YAML frontmatter block at the start of a file: --- ... ---
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Matches a single YAML key: value line
_YAML_KEY_VALUE_RE = re.compile(r"^(?P<key>\w[\w\s]*?)\s*:\s*(?P<value>.+)$")


def _parse_frontmatter(raw: str) -> tuple[str, dict[str, str | int | float]]:
    """Strip YAML frontmatter from *raw* text and return (body, metadata).

    Only scalar string/int/float values are extracted; nested structures are
    left as raw strings so the return type stays ``dict[str, str | int | float]``.
    """
    metadata: dict[str, str | int | float] = {}
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        return raw, metadata

    frontmatter_block = match.group(1)
    body = raw[match.end():]

    for line in frontmatter_block.splitlines():
        kv = _YAML_KEY_VALUE_RE.match(line.strip())
        if kv:
            key = kv.group("key").strip()
            raw_value = kv.group("value").strip()
            # Attempt numeric coercion; fall back to string
            value: str | int | float
            try:
                value = int(raw_value)
            except ValueError:
                try:
                    value = float(raw_value)
                except ValueError:
                    value = raw_value
            metadata[key] = value

    return body, metadata


class MarkdownParser:
    """Parse Markdown (.md) files into :class:`Document` objects."""

    def parse(self, path: Path) -> list[Document]:
        """Read *path* and return a single-element list with the parsed document.

        Returns an empty list if the file cannot be read (e.g. does not exist).
        """
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return []

        body, metadata = _parse_frontmatter(raw)
        metadata["format"] = "markdown"

        return [
            Document(
                text=body,
                source_path=str(path),
                metadata=metadata,
            )
        ]

    def supported_extensions(self) -> list[str]:
        """Return the list of file extensions this parser handles."""
        return [".md"]

"""Tests for PDF report generator."""

import importlib.util
from pathlib import Path

import pytest

from rag_forge_evaluator.report.pdf import PDFGenerator


class TestPDFGenerator:
    def test_file_not_found_error(self) -> None:
        generator = PDFGenerator()
        with pytest.raises(FileNotFoundError, match="HTML report not found"):
            generator.generate(Path("nonexistent.html"))

    def test_import_error_when_playwright_missing(self, tmp_path: Path) -> None:
        if importlib.util.find_spec("playwright") is not None:
            pytest.skip("Playwright is installed")
        html_file = tmp_path / "report.html"
        html_file.write_text("<html><body>test</body></html>")
        generator = PDFGenerator()
        with pytest.raises(ImportError, match="Playwright"):
            generator.generate(html_file)

    def test_pdf_generator_instantiates(self) -> None:
        generator = PDFGenerator()
        assert generator is not None

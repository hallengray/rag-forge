"""Tests for PDF report generator."""

import pytest

from rag_forge_evaluator.report.pdf import PDFGenerator


class TestPDFGenerator:
    def test_import_error_when_playwright_missing(self) -> None:
        try:
            import playwright
            pytest.skip("Playwright is installed")
        except ImportError:
            pass
        from pathlib import Path
        generator = PDFGenerator()
        with pytest.raises(ImportError, match="Playwright"):
            generator.generate(Path("nonexistent.html"))

    def test_pdf_generator_instantiates(self) -> None:
        generator = PDFGenerator()
        assert generator is not None

"""Tests for PDF report generator."""

import importlib.util

import pytest

from rag_forge_evaluator.report.pdf import PDFGenerator


class TestPDFGenerator:
    def test_import_error_when_playwright_missing(self) -> None:
        if importlib.util.find_spec("playwright") is not None:
            pytest.skip("Playwright is installed")
        from pathlib import Path
        generator = PDFGenerator()
        with pytest.raises(ImportError, match="Playwright"):
            generator.generate(Path("nonexistent.html"))

    def test_pdf_generator_instantiates(self) -> None:
        generator = PDFGenerator()
        assert generator is not None

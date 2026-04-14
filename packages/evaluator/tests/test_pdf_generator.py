"""Tests for PDF report generator."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

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

    @pytest.mark.skipif(
        importlib.util.find_spec("playwright") is None,
        reason="Playwright not installed",
    )
    def test_pdf_generator_invokes_emulate_media_print(self, tmp_path: Path) -> None:
        """Assert that pdf generation calls page.emulate_media with media=print
        so the audit template's @media print rules are actually applied."""
        # Create mock page object that tracks method calls
        mock_page = MagicMock()
        mock_page.pdf.return_value = None

        # Create mock browser
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page

        # Create mock chromium
        mock_chromium = MagicMock()
        mock_chromium.launch.return_value = mock_browser

        # Create mock playwright context
        mock_playwright = MagicMock()
        mock_playwright.chromium = mock_chromium
        mock_playwright.__enter__ = MagicMock(return_value=mock_playwright)
        mock_playwright.__exit__ = MagicMock(return_value=False)

        html_file = tmp_path / "report.html"
        html_file.write_text("<html><body>test report</body></html>")

        with patch("playwright.sync_api.sync_playwright", return_value=mock_playwright):
            generator = PDFGenerator()
            generator.generate(html_file)

        # Assert that emulate_media was called with media='print'
        # This must happen before set_content or goto
        calls = mock_page.method_calls
        emulate_calls = [c for c in calls if c[0] == "emulate_media"]
        assert emulate_calls, "emulate_media was never called"
        assert emulate_calls[0][1] == ()  # No positional args
        assert emulate_calls[0][2].get("media") == "print"

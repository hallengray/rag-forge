"""PDF report generation via Playwright headless Chromium."""

from pathlib import Path


class PDFGenerator:
    def generate(self, html_path: Path) -> Path:
        """Render an HTML file to PDF using a headless Chromium browser.

        Args:
            html_path: Path to the HTML report file to convert.

        Returns:
            Path to the generated PDF file (same name, .pdf extension).

        Raises:
            FileNotFoundError: If the HTML report file does not exist.
            ImportError: If Playwright is not installed.
        """
        if not html_path.exists():
            raise FileNotFoundError(f"HTML report not found: {html_path}")

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError(
                "Playwright is not installed. Install with: "
                "pip install rag-forge-evaluator[pdf] && playwright install chromium"
            ) from None

        pdf_path = html_path.with_suffix(".pdf")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"file://{html_path.resolve()}")
            page.pdf(path=str(pdf_path), format="A4", print_background=True)
            browser.close()
        return pdf_path

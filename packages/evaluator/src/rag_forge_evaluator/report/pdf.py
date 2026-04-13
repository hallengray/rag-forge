"""PDF report generation via Playwright headless Chromium."""

from pathlib import Path


def is_available() -> tuple[bool, str | None]:
    """Return (ok, error_message) for whether PDF generation can run.

    Checks both that the playwright package is importable and that the
    Chromium browser binary has been downloaded via
    ``playwright install chromium``. Used by AuditOrchestrator to fail
    fast before judge calls run, instead of crashing at the very end of
    a paid audit.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return (
            False,
            "Playwright not installed. Run: pip install 'rag-forge-evaluator[pdf]' "
            "&& playwright install chromium",
        )
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            exe_path = p.chromium.executable_path
            if not exe_path:
                return (False, "Chromium binary not found. Run: playwright install chromium")
    except Exception as e:
        return (False, f"Playwright chromium not available: {e}")
    return (True, None)


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

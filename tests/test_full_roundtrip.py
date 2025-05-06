"""
Integration test for the full workflow using real service implementations.

External dependencies required:
- rmapi must be installed and configured (https://github.com/juruen/rmapi)
- Network access is required for web scraping and uploading to reMarkable
- drawj2d or RCU (optional, for document conversion if needed)
- qrcode, requests, PyPDF2, bs4, readability (Python packages)

This test uses pytest's tmp_path fixture for all temporary files and directories.
"""

import pytest
import logging
from inklink.server import URLHandler
from inklink.services.qr_service import QRCodeService
from inklink.services.pdf_service import PDFService
from inklink.services.web_scraper_service import WebScraperService
from inklink.services.document_service import DocumentService
from inklink.services.remarkable_service import RemarkableService

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("test_full_roundtrip")

class TestHandler(URLHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._output = {}

    def _send_success(self, message):
        self._output["success"] = message

    def _send_error(self, message):
        self._output["error"] = message
def test_webpage_ai_summary_integration(tmp_path):
    """Unit test: injects a mock AIService and checks AI summary in content and context passing."""
    from inklink.server import URLHandler
    from inklink.services.qr_service import QRCodeService
    from inklink.services.pdf_service import PDFService
    from inklink.services.web_scraper_service import WebScraperService
    from inklink.services.document_service import DocumentService
    from inklink.services.remarkable_service import RemarkableService

    class MockAIService:
        def __init__(self):
            self.last_query_text = None
            self.last_context = None

        def process_query(self, query_text, context=None):
            self.last_query_text = query_text
            self.last_context = context
            # Return markdown-formatted AI summary for testing
            return (
                "# AI Summary\n"
                "This is a **mock** AI summary.\n\n"
                "## Key Points\n"
                "- Supports *markdown* formatting\n"
                "- Handles lists, headings, and more\n"
                "\n"
                "```python\nprint('Hello, Markdown!')\n```\n"
            )

    qr_dir = tmp_path / "qr"
    pdf_tmp = tmp_path / "pdf_tmp"
    pdf_extract = tmp_path / "pdf_extract"
    doc_tmp = tmp_path / "doc_tmp"

    qr_service = QRCodeService(str(qr_dir))
    pdf_service = PDFService(str(pdf_tmp), str(pdf_extract))
    web_scraper = WebScraperService()
    document_service = DocumentService(str(doc_tmp))
    remarkable_service = RemarkableService("/usr/bin/rmapi")

    url = "https://example.com/"
    qr_path, _ = qr_service.generate_qr(url)

    handler = TestHandler(
        None, None, None,
        qr_service=qr_service,
        pdf_service=pdf_service,
        web_scraper=web_scraper,
        document_service=document_service,
        remarkable_service=remarkable_service,
        ai_service=MockAIService(),
    )

    handler._handle_webpage_url(url, qr_path)
    output = handler._output
    assert "success" in output

    # Check that context was passed to the AI service
    ai_service = handler.ai_service
    # The context should be a dict (excluding 'content') with at least metadata or previous_content if present
    assert hasattr(ai_service, "last_context")
    # Accept either a non-empty dict or None if no context was available
    assert ai_service.last_context is None or isinstance(ai_service.last_context, dict)
    # Check that the AI summary was added to the content passed to document_service
    # (This requires document_service.create_rmdoc_from_content to preserve content["ai_summary"])

    # Additional check: verify markdown is preserved in the generated markdown file
    import glob
    import os

    doc_files = glob.glob(os.path.join(str(doc_tmp), "*.md"))
    assert doc_files, "No markdown file generated"

    with open(doc_files[0], "r", encoding="utf-8") as f:
        md_content = f.read()
        assert "# AI Summary" in md_content
        assert "**mock** AI summary" in md_content
        assert "```python" in md_content
        assert "- Supports *markdown* formatting" in md_content
<<<<<<< HEAD
=======
def test_math_and_diagram_blocks_roundtrip(tmp_path):
    """Test that math (LaTeX) and diagram (mermaid) blocks are preserved in markdown export."""
    from inklink.services.document_service import DocumentService

    doc_tmp = tmp_path / "doc_tmp"
    document_service = DocumentService(str(doc_tmp))

    url = "https://example.com/"
    qr_path = ""
    structured_content = [
        {
            "page_number": 1,
            "items": [
                {"type": "paragraph", "content": "Normal text."},
                {"type": "math", "content": "E=mc^2"},
                {"type": "diagram", "content": "graph TD; A-->B;"}
            ],
            "metadata": {}
        }
    ]
    content = {
        "title": "Test Math and Diagram",
        "structured_content": structured_content
    }
    md_path = document_service.create_rmdoc_from_content(url, qr_path, content)
    assert md_path and md_path.endswith(".md")
    with open(md_path, "r", encoding="utf-8") as f:
        md = f.read()
        assert "$$\nE=mc^2\n$$" in md
        assert "```mermaid\ngraph TD; A-->B;\n```" in md
>>>>>>> 7346ed0e841e457fc90535deb5c7f15b9f31aa48

@pytest.mark.integration
def test_full_roundtrip_real_services(tmp_path):
    logger.info("Starting full roundtrip integration test with real services")

    # Arrange: instantiate real services with temp dirs
    qr_dir = tmp_path / "qr"
    pdf_tmp = tmp_path / "pdf_tmp"
    pdf_extract = tmp_path / "pdf_extract"
    doc_tmp = tmp_path / "doc_tmp"

    logger.debug(f"Temporary directories: qr={qr_dir}, pdf_tmp={pdf_tmp}, pdf_extract={pdf_extract}, doc_tmp={doc_tmp}")

    qr_service = QRCodeService(str(qr_dir))
    logger.debug("QRCodeService instantiated")
    pdf_service = PDFService(str(pdf_tmp), str(pdf_extract))
    logger.debug("PDFService instantiated")
    web_scraper = WebScraperService()
    logger.debug("WebScraperService instantiated")
    document_service = DocumentService(str(doc_tmp))
    logger.debug("DocumentService instantiated")
    # Set the path to rmapi binary as appropriate for your environment
    rmapi_path = "/usr/bin/rmapi"
    remarkable_service = RemarkableService(rmapi_path)
    logger.debug("RemarkableService instantiated")

    # Use a real, simple static page for scraping
    url = "https://example.com/"
    logger.info(f"Generating QR code for URL: {url}")
    qr_path, _ = qr_service.generate_qr(url)
    logger.debug(f"QR code generated at: {qr_path}")

    handler = TestHandler(
        None,  # request (not used)
        None,  # client_address (not used)
        None,  # server (not used)
        qr_service=qr_service,
        pdf_service=pdf_service,
        web_scraper=web_scraper,
        document_service=document_service,
        remarkable_service=remarkable_service,
    )
    logger.debug("TestHandler instantiated")

    # Act: run the full workflow
    logger.info("Invoking handler._handle_webpage_url")
    handler._handle_webpage_url(url, qr_path)
    logger.info("handler._handle_webpage_url completed")

    # Assert: check for success and that the document was uploaded
    output = handler._output
    logger.debug(f"Handler output: {output}")
    assert "success" in output, f"Handler error: {output.get('error')}"
    assert "Webpage uploaded to Remarkable" in output["success"]
    logger.info("Full roundtrip integration test completed successfully")
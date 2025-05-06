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
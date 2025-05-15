"""
Mock integration test for the basic InkLink functionality.

This test uses mock services to test the core flow without requiring
external dependencies like rmapi or Neo4j.
"""

import os
import json
import logging
from unittest.mock import MagicMock
from typing import Dict, Any, Optional

# Import required modules
from inklink.pipeline.factory import PipelineFactory
from inklink.controllers.share_controller import ShareController
from inklink.services.web_scraper_service import WebScraperService
from inklink.services.interfaces import (
    IQRCodeService,
    IDocumentService,
    IRemarkableService,
)

# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("test_mock_roundtrip")


class MockRequest:
    """Mock HTTP request."""

    def __init__(self, body=None):
        """Initialize with request body."""
        self.body = body or {}
        self.method = "POST"
        self.path = "/"

    async def json(self):
        """Return request body as JSON."""
        return self.body


class MockResponse:
    """Mock HTTP response."""

    def __init__(self):
        """Initialize response capture."""
        self.status = None
        self.headers = {}
        self.body = None

    async def text(self):
        """Return response body as text."""
        return self.body


class MockQRService(IQRCodeService):
    """Mock QR service."""

    def __init__(self, temp_dir=None):
        """Initialize with temp directory."""
        self.temp_dir = temp_dir or "/tmp"

    def generate_qr(self, url):
        """Generate QR code for URL."""
        # Return a mock QR code path
        qr_path = os.path.join(self.temp_dir, "mock_qr.png")
        return qr_path, "mock_qr.png"

    def generate_svg_qr(self, url):
        """Generate SVG QR code for URL."""
        qr_path = os.path.join(self.temp_dir, "mock_qr.svg")
        return qr_path, "mock_qr.svg"

    def generate_custom_qr(self, url, config, svg=False):
        """Generate custom QR code."""
        if svg:
            return self.generate_svg_qr(url)
        return self.generate_qr(url)


class MockDocumentService(IDocumentService):
    """Mock document service."""

    def __init__(self, temp_dir=None):
        """Initialize with temp directory."""
        self.temp_dir = temp_dir or "/tmp"

    def create_hcl(self, url, qr_path, content):
        """Create HCL script from content."""
        hcl_path = os.path.join(self.temp_dir, "mock_document.hcl")
        return hcl_path

    def create_rmdoc(self, hcl_path, url):
        """Convert HCL to Remarkable document."""
        rm_path = os.path.join(self.temp_dir, "mock_document.rm")
        return rm_path

    def create_rmdoc_from_content(self, url, qr_path, content):
        """Create reMarkable document from content."""
        # Return a mock document path
        rm_path = os.path.join(self.temp_dir, "mock_document.rm")
        return rm_path

    def create_rmdoc_from_html(self, url, qr_path, html_content, title=None):
        """Create reMarkable document directly from HTML content."""
        rm_path = os.path.join(self.temp_dir, "mock_document.rm")
        return rm_path


class MockRemarkableService(IRemarkableService):
    """Mock reMarkable service."""

    def __init__(self, rmapi_path=None):
        """Initialize with rmapi path."""
        self.rmapi_path = rmapi_path or "/usr/bin/rmapi"

    def upload(self, doc_path, title):
        """Upload document to reMarkable cloud."""
        # Return success
        return True, f"Uploaded {title} to reMarkable"


def test_share_controller_with_mocks():
    """Test the ShareController with mock services."""
    # Create temporary directory
    tmp_dir = "/tmp/inklink_test"
    os.makedirs(tmp_dir, exist_ok=True)

    # Create mock services
    qr_service = MockQRService(tmp_dir)
    document_service = MockDocumentService(tmp_dir)
    remarkable_service = MockRemarkableService()
    web_scraper = WebScraperService()  # Use the real web scraper for URL content

    # Create mock handler
    mock_handler = MagicMock()

    # Create services dictionary
    services = {
        "qr_service": qr_service,
        "document_service": document_service,
        "remarkable_service": remarkable_service,
        "web_scraper": web_scraper,
    }

    # Create the controller
    controller = ShareController(handler=mock_handler, services=services)

    # Set up the controller with a mock URL
    url = "https://example.com/"

    # Patch the pipeline process method
    original_process = PipelineFactory.create_pipeline_for_url

    # Create a mock pipeline that always succeeds
    mock_pipeline = MagicMock()
    mock_pipeline.process.side_effect = lambda ctx: _mock_pipeline_process(ctx)

    # Register our mock pipeline creator
    PipelineFactory.create_pipeline_for_url = MagicMock(return_value=mock_pipeline)

    # Mock the required methods on the controller
    json_data = json.dumps({"url": url}).encode("utf-8")
    controller.read_request_data = MagicMock(
        return_value=(json_data, "application/json")
    )
    controller.get_accept_header = MagicMock(return_value="application/json")
    controller.send_json = MagicMock()
    controller.send_error = MagicMock()

    try:
        # Execute the controller
        controller.handle(method="POST", path="/share")

        # Verify the controller sent a JSON response (success)
        controller.send_json.assert_called_once()
        controller.send_error.assert_not_called()

        # Verify mock pipeline was called
        mock_pipeline.process.assert_called_once()

    finally:
        # Restore original pipeline method
        PipelineFactory.create_pipeline_for_url = original_process


def _mock_pipeline_process(context):
    """Mock pipeline process function."""
    # Add success artifacts to the context
    context.add_artifact("document_title", "Example Domain")
    context.add_artifact("rm_path", "/tmp/mock.rm")
    context.add_artifact("upload_success", True)
    context.add_artifact(
        "upload_message", "Document uploaded to Remarkable: Example Domain"
    )
    return context


def test_web_scraper_with_real_url():
    """Test the WebScraperService with a real URL."""
    # Create the web scraper
    web_scraper = WebScraperService()

    # Scrape a simple static page
    result = web_scraper.scrape("https://example.com/")

    # Verify the result
    assert result is not None
    assert "title" in result
    assert "title" in result and "Example Domain" in result["title"]
    # Check for the expected structure - it may not have 'content' directly
    assert "structured_content" in result
    assert isinstance(result["structured_content"], list)


if __name__ == "__main__":
    # Run the tests directly
    logging.basicConfig(level=logging.DEBUG)
    test_share_controller_with_mocks()
    test_web_scraper_with_real_url()
    print("All tests passed!")

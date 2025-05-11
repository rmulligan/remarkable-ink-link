import os
import shutil
from io import BytesIO
import pytest
from unittest.mock import MagicMock, patch

from inklink.services.pdf_service import PDFService
from inklink.adapters.pdf_adapter import PDFAdapter
from inklink.adapters.http_adapter import HTTPAdapter


@pytest.fixture
def mock_http_adapter():
    """Create a mock HTTP adapter."""
    adapter = MagicMock(spec=HTTPAdapter)

    # Configure default behaviors
    # This will be overridden in specific tests
    adapter.get.return_value = (False, "Not configured")
    adapter.download_file.return_value = True

    return adapter


@pytest.fixture
def mock_pdf_adapter():
    """Create a mock PDF adapter."""
    adapter = MagicMock(spec=PDFAdapter)

    # Configure default return values
    adapter.ping.return_value = True
    adapter.extract_title.return_value = "Test PDF Document"
    adapter.extract_metadata.return_value = {
        "title": "Test PDF Document",
        "author": "Test Author",
        "page_count": 2,
    }
    adapter.convert_to_images.return_value = [
        "/tmp/test_page_1.png",
        "/tmp/test_page_2.png",
    ]
    adapter.extract_text.return_value = ["Page 1 content", "Page 2 content"]
    adapter.add_watermark.return_value = True
    adapter.generate_graph_pdf.return_value = True

    return adapter


@pytest.fixture
def pdf_service(tmp_path, mock_http_adapter, mock_pdf_adapter):
    """Create a PDF service instance with mock adapters."""
    temp_dir = tmp_path / "temp"
    out_dir = tmp_path / "out"
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    return PDFService(
        str(temp_dir),
        str(out_dir),
        pdf_adapter=mock_pdf_adapter,
        http_adapter=mock_http_adapter,
    )


def test_is_pdf_url_extension(pdf_service, mock_http_adapter):
    """Test PDF URL detection based on file extension."""
    # Configure HTTP adapter to return non-PDF content type
    # This ensures .txt won't be detected as PDF through content-type
    mock_http_adapter.get.return_value = (True, {"Content-Type": "text/plain"})

    # Extension-based detection should work regardless of adapter response
    assert pdf_service.is_pdf_url("http://example.com/file.pdf")
    assert pdf_service.is_pdf_url("http://example.com/file.PDF")

    # This should use the adapter and fail based on content type
    assert not pdf_service.is_pdf_url("http://example.com/file.txt")

    # Adapter should be called once for the .txt file (not for .pdf files)
    assert mock_http_adapter.get.call_count == 1


def test_is_pdf_url_content_type(pdf_service, mock_http_adapter):
    """Test PDF URL detection based on Content-Type header."""
    # Configure mock adapter response for content type test
    mock_http_adapter.get.return_value = (True, {"Content-Type": "application/pdf"})

    # URL without PDF extension should check content type
    assert pdf_service.is_pdf_url("http://example.com/document")
    mock_http_adapter.get.assert_called_once_with(
        "http://example.com/document", headers={"Range": "bytes=0-0"}
    )

    # Reset mock and test non-PDF content type
    mock_http_adapter.reset_mock()
    mock_http_adapter.get.return_value = (True, {"Content-Type": "text/html"})

    assert not pdf_service.is_pdf_url("http://example.com/webpage")
    mock_http_adapter.get.assert_called_once()


def test_is_pdf_url_error_handling(pdf_service, mock_http_adapter):
    """Test handling of errors during PDF URL detection."""
    # Configure mock adapter to simulate request failure
    mock_http_adapter.get.return_value = (False, "Connection error")

    # Should handle error gracefully and return False
    assert not pdf_service.is_pdf_url("http://example.com/error")
    mock_http_adapter.get.assert_called_once()


def test_process_pdf_success(
    pdf_service, mock_http_adapter, mock_pdf_adapter, tmp_path
):
    """Test successful PDF processing."""
    url = "http://example.com/test.pdf"
    qr_path = str(tmp_path / "qr.png")

    # Create a dummy QR file
    with open(qr_path, "w") as f:
        f.write("dummy QR")

    # Process the PDF
    result = pdf_service.process_pdf(url, qr_path)

    # Verify adapters were called correctly
    mock_http_adapter.download_file.assert_called_once()
    mock_pdf_adapter.extract_title.assert_called_once()

    # Check result format
    assert result is not None
    assert "title" in result
    assert result["title"] == "Test PDF Document"
    assert "pdf_path" in result


def test_process_pdf_download_failure(pdf_service, mock_http_adapter):
    """Test PDF processing when download fails."""
    # Configure download to fail
    mock_http_adapter.download_file.return_value = False

    result = pdf_service.process_pdf("http://example.com/test.pdf", "qr_path")

    # Should handle error and return None
    assert result is None
    mock_http_adapter.download_file.assert_called_once()


def test_convert_to_images(pdf_service, mock_pdf_adapter):
    """Test PDF to image conversion."""
    pdf_path = "/path/to/test.pdf"

    # Call the service method
    image_paths = pdf_service.convert_to_images(pdf_path)

    # Verify adapter was called correctly
    mock_pdf_adapter.convert_to_images.assert_called_once_with(
        pdf_path, output_dir=pdf_service.extract_dir
    )

    # Check result
    assert len(image_paths) == 2
    assert all(path.endswith(".png") for path in image_paths)


def test_extract_text(pdf_service, mock_pdf_adapter):
    """Test PDF text extraction."""
    pdf_path = "/path/to/test.pdf"

    # Call the service method
    text_pages = pdf_service.extract_text(pdf_path)

    # Verify adapter was called correctly
    mock_pdf_adapter.extract_text.assert_called_once_with(pdf_path)

    # Check result
    assert len(text_pages) == 2
    assert text_pages[0] == "Page 1 content"
    assert text_pages[1] == "Page 2 content"


def test_add_watermark(pdf_service, mock_pdf_adapter):
    """Test adding watermark to PDF."""
    pdf_path = "/path/to/test.pdf"
    watermark_path = "/path/to/watermark.pdf"
    output_path = "/path/to/output.pdf"

    # Call the service method
    result = pdf_service.add_watermark(pdf_path, watermark_path, output_path)

    # Verify adapter was called correctly
    mock_pdf_adapter.add_watermark.assert_called_once_with(
        pdf_path, watermark_path, output_path
    )

    # Check result
    assert result is True


def test_generate_index_notebook(pdf_service, mock_pdf_adapter):
    """Test generating an index notebook PDF."""
    # Create test pages data
    pages = [
        {
            "page_number": 1,
            "title": "Page One",
            "summary": "This is page one",
            "device_location": "location1",
            "links": [2],
        },
        {
            "page_number": 2,
            "title": "Page Two",
            "summary": "This is page two",
            "device_location": "location2",
        },
    ]

    output_path = "/path/to/index.pdf"

    # Call the service method
    result = pdf_service.generate_index_notebook(pages, output_path, "Test Graph")

    # Verify adapter was called correctly with converted nodes and edges
    mock_pdf_adapter.generate_graph_pdf.assert_called_once()

    # Check the call arguments
    call_args = mock_pdf_adapter.generate_graph_pdf.call_args[1]
    assert call_args["output_path"] == output_path
    assert call_args["title"] == "Test Graph"
    assert call_args["include_table"] is True

    # Check nodes conversion
    nodes = call_args["nodes"]
    assert len(nodes) == 2
    assert nodes[0]["id"] == 1
    assert nodes[0]["title"] == "Page One"

    # Check edges conversion
    edges = call_args["edges"]
    assert len(edges) == 1
    assert edges[0] == ("1", "2")

    # Check result
    assert result is True

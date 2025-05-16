import os
from unittest.mock import MagicMock

import pytest

from inklink.services.document_service import DocumentService


# Test fixtures
@pytest.fixture
def document_service(tmp_path):
    # Set up the document service with a temporary directory
    service = DocumentService(str(tmp_path))
    return service


def test_initialize_converters(document_service):
    """Test that converters are properly initialized."""
    assert document_service.converters is not None
    assert len(document_service.converters) >= 2


def test_create_rmdoc_from_content_basic(document_service, monkeypatch):
    """Test creation of a basic document from structured content."""

    # Mock the appropriate converter
    def mock_convert(content_dict, output_path=None):
        # Create a mock markdown file
        md_path = os.path.join(document_service.temp_dir, "test.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Test Heading\nTest content.")
        return md_path

    # Find the appropriate converter and mock its convert method
    for converter in document_service.converters:
        if converter.__class__.__name__ == "MarkdownConverter":
            monkeypatch.setattr(converter, "convert", mock_convert)
            break

    # Mock the renderer to ensure we get a valid result
    def mock_render(content, output_path=None):
        # Create a mock output file
        output_path = os.path.join(document_service.temp_dir, "output.rm")
        with open(output_path, "wb") as f:
            f.write(b"Mock RM content")
        return output_path

    monkeypatch.setattr(document_service.hcl_renderer, "render", mock_render)

    # Test with minimal content
    url = "https://example.com"
    qr_path = ""
    content = {
        "title": "Test Page",
        "structured_content": [
            {"type": "heading", "content": "Test Heading"},
            {"type": "paragraph", "content": "Test content."},
        ],
    }

    # Call the document service method
    result = document_service.create_rmdoc_from_content(url, qr_path, content)

    # Verify result
    assert result is not None
    assert os.path.exists(result)


def test_create_rmdoc_multi_page(document_service, monkeypatch):
    """Test creation of markdown from multi-page structured content."""

    # Mock the appropriate converter
    def mock_convert(content_dict, output_path=None):
        # Create a mock markdown file
        md_path = os.path.join(document_service.temp_dir, "test.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(
                "# Page 1 Heading\nContent on page 1.\n\n# Page 2 Heading\nContent on page 2."
            )
        return md_path

    # Find the markdown converter and patch its convert method
    for converter in document_service.converters:
        if converter.__class__.__name__ == "MarkdownConverter":
            monkeypatch.setattr(converter, "convert", mock_convert)
            break

    # Mock the renderer to return a successful conversion
    def mock_render(content, output_path=None):
        if output_path:
            with open(output_path, "wb") as f:
                f.write(b"Mock RM content")
            return output_path
        # Create a dummy output file
        output_path = os.path.join(document_service.temp_dir, "output.rm")
        with open(output_path, "wb") as f:
            f.write(b"Mock RM content")
        return output_path

    monkeypatch.setattr(document_service.hcl_renderer, "render", mock_render)

    # Test multi-page content
    content = {
        "title": "Multi-Page Test",
        "pages": [
            {
                "page_number": 1,
                "items": [
                    {"type": "heading", "content": "Page 1 Heading"},
                    {"type": "paragraph", "content": "Content on page 1."},
                ],
                "metadata": {},
            },
            {
                "page_number": 2,
                "items": [
                    {"type": "heading", "content": "Page 2 Heading"},
                    {"type": "paragraph", "content": "Content on page 2."},
                ],
                "metadata": {},
            },
        ],
    }
    url = "https://example.com"
    qr_path = ""

    # Call the service method
    result = document_service.create_rmdoc_from_content(url, qr_path, content)

    # Verify result
    assert result is not None
    assert os.path.exists(result)


@pytest.mark.skip(reason="Test needs to be updated for the new architecture")
def test_create_pdf_hcl_with_images(document_service, tmp_path, monkeypatch):
    """Test creation of PDF HCL embedding raster images."""
    # TODO: Update this test for the new architecture with dependency injection
    from PIL import Image

    # Create dummy images
    img1 = tmp_path / "img1.png"
    img2 = tmp_path / "img2.png"
    for path, size in [(img1, (50, 100)), (img2, (200, 100))]:
        Image.new("RGB", size).save(str(path))

    images = [str(img1), str(img2)]

    # Find the PDF converter and mock its convert method
    for converter in document_service.converters:
        if converter.__class__.__name__ == "PDFConverter":
            # Mock the create_hcl_with_images method
            def mock_create_hcl_with_images(pdf_path, title, images, output_dir):
                hcl_path = os.path.join(output_dir, "test_pdf.hcl")
                with open(hcl_path, "w", encoding="utf-8") as f:
                    f.write(f'puts "size 2160 1620"\n')
                    f.write(f'puts "text 120 120 \\"{title}\\""\n')
                    for img in images:
                        f.write('puts "newpage"\n')
                        f.write(f'puts "image 120 120 {img}"\n')
                return hcl_path

            monkeypatch.setattr(
                converter, "create_hcl_with_images", mock_create_hcl_with_images
            )
            break

    # Create test content
    content = {
        "title": "Test Page",
        "content_type": "pdf",
        "pdf_path": "dummy.pdf",
        "images": images,
    }

    # Generate document through the service
    result = document_service.create_rmdoc_from_content("test-url", "", content)

    # Verify result
    assert result is not None
    assert os.path.exists(result)


def test_handle_mixed_content(document_service, tmp_path, monkeypatch):
    """Test handling of plain text input with mixed valid/invalid content."""

    # Mock the appropriate converter methods
    def mock_convert(content_dict, output_path=None):
        # Create a mock output file based on the title
        title = content_dict.get("title", "Untitled")
        safe_title = title.lower().replace(" ", "_")
        output_path = os.path.join(document_service.temp_dir, f"{safe_title}.md")

        # Write mock content
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")

            # Add structured content
            structured_content = content_dict.get("structured_content", [])
            for item in structured_content:
                item_type = item.get("type", "paragraph")
                if item_type == "paragraph":
                    f.write(f"{item.get('content', '')}\n\n")
                elif item_type in ["h1", "heading"]:
                    f.write(f"# {item.get('content', '')}\n\n")
                elif item_type == "code":
                    f.write(f"```\n{item.get('content', '')}\n```\n\n")
                elif item_type == "list" and "items" in item:
                    for list_item in item["items"]:
                        f.write(f"* {list_item}\n")
                    f.write("\n")

        return output_path

    # Find the appropriate converter and mock its convert method
    for converter in document_service.converters:
        if converter.__class__.__name__ == "MarkdownConverter":
            monkeypatch.setattr(converter, "convert", mock_convert)
            break

    # Mock the renderer to ensure we get a valid result
    def mock_render(content, output_path=None):
        # Create a mock output file
        if not output_path:
            output_path = os.path.join(document_service.temp_dir, "output.rm")

        with open(output_path, "wb") as f:
            f.write(b"Mock RM content")
        return output_path

    monkeypatch.setattr(document_service.hcl_renderer, "render", mock_render)

    # Test case 1: Mixed valid and invalid URLs
    url_test_content = {
        "title": "Mixed URL Content",
        "structured_content": [
            {
                "type": "paragraph",
                "content": "Valid URL: https://example.com\nInvalid URL: example.com/not-valid",
            },
            {
                "type": "list",
                "items": [
                    "Item with valid link: https://item1.com",
                    "Item with invalid link: item2.com",
                ],
            },
        ],
    }

    # Test with mixed content
    result = document_service.create_rmdoc_from_content(
        url="https://example.com/test", qr_path="", content=url_test_content
    )

    # Verify result
    assert result is not None
    assert os.path.exists(result)


@pytest.mark.skip(reason="Test needs to be updated for proper rendering")
def test_create_rmdoc_legacy(document_service, monkeypatch):
    """Test the legacy method for creating RM documents."""

    # Set up the mock for HCL creation
    def mock_create_hcl(url, qr_path, content, temp_dir):
        hcl_path = os.path.join(temp_dir, "test.hcl")
        with open(hcl_path, "w", encoding="utf-8") as f:
            f.write('puts "size 2160 1620"\n')
            f.write('puts "text 120 120 \\"Legacy Test\\""\n')
        return hcl_path

    monkeypatch.setattr(
        "inklink.utils.hcl_render.create_hcl_from_content", mock_create_hcl
    )

    # Set up the mock for drawj2d conversion
    # Replace the render method so we don't need drawj2d
    def mock_render(content, output_path=None):
        output_path = os.path.join(document_service.temp_dir, "output.rm")
        with open(output_path, "wb") as f:
            f.write(b"Mock RM content")
        return output_path

    monkeypatch.setattr(document_service.hcl_renderer, "render", mock_render)

    # Test data
    url = "https://example.com"
    qr_path = ""
    content = {
        "title": "Legacy Test",
        "structured_content": [
            {"type": "heading", "content": "Legacy Heading"},
            {"type": "paragraph", "content": "Legacy content."},
        ],
    }

    # Call service legacy method
    result = document_service.create_rmdoc_legacy(url, qr_path, content)

    # Verify
    assert result is not None
    assert os.path.exists(result)


@pytest.mark.skip(reason="Test needs to be updated for RCU availability")
def test_create_rmdoc_from_html(document_service, monkeypatch):
    """Test creation of documents directly from HTML content."""
    # Mock the RCU availability check
    monkeypatch.setattr("inklink.utils.ensure_rcu_available", lambda: True)
    document_service.use_rcu = True

    # Mock the HTML converter
    def mock_html_convert(content_dict, output_path=None):
        # Create a mock output file
        output_path = os.path.join(document_service.temp_dir, "output.rm")
        with open(output_path, "wb") as f:
            f.write(b"Mock RM content")
        return output_path

    # Find the HTML converter and patch it
    for converter in document_service.converters:
        if converter.__class__.__name__ == "HTMLConverter":
            monkeypatch.setattr(converter, "convert", mock_html_convert)
            break

    # Test data
    url = "https://example.com"
    qr_path = ""
    html_content = (
        "<html><body><h1>Test HTML</h1><p>Test HTML content.</p></body></html>"
    )
    title = "HTML Test"

    # Call service method
    result = document_service.create_rmdoc_from_html(url, qr_path, html_content, title)

    # Verify
    assert result is not None
    assert os.path.exists(result)


def test_create_pdf_rmdoc(document_service, monkeypatch):
    """Test creation of RM documents from PDF files."""

    # Mock the PDF converter
    def mock_pdf_convert(content_dict, output_path=None):
        # Create a mock output file
        output_path = os.path.join(document_service.temp_dir, "output.rm")
        with open(output_path, "wb") as f:
            f.write(b"Mock RM content")
        return output_path

    # Find the PDF converter and patch it
    for converter in document_service.converters:
        if converter.__class__.__name__ == "PDFConverter":
            monkeypatch.setattr(converter, "convert", mock_pdf_convert)
            break

    # Create a temporary PDF file
    pdf_path = os.path.join(document_service.temp_dir, "test.pdf")
    with open(pdf_path, "wb") as f:
        f.write(b"Fake PDF content")

    # Call service method
    result = document_service.create_pdf_rmdoc(pdf_path, "PDF Test")

    # Verify
    assert result is not None
    assert os.path.exists(result)


@pytest.mark.skip(reason="Test needs to be updated for PDF service")
def test_index_notebook_update(document_service, monkeypatch):
    """Test the index notebook update feature."""
    # Create a mock PDF service
    mock_pdf_service = MagicMock()
    document_service.pdf_service = mock_pdf_service

    # Block thread creation to ensure synchronous execution for testing
    monkeypatch.setattr("threading.Thread.start", lambda x: None)

    # Test with minimal content
    content = {
        "title": "Test Document",
        "summary": "Test summary",
        "cross_page_links": [2, 3, 4],
    }

    # Call the update method directly
    document_service._update_index_notebook(content)

    # Verify that the PDF service was called with expected parameters
    mock_pdf_service.generate_index_notebook.assert_called_once()
    call_args = mock_pdf_service.generate_index_notebook.call_args[1]
    assert call_args["graph_title"] == "Index Node Graph"
    assert len(call_args["pages"]) == 1
    assert call_args["pages"][0]["title"] == "Test Document"
    assert call_args["pages"][0]["summary"] == "Test summary"
    assert call_args["pages"][0]["links"] == [2, 3, 4]

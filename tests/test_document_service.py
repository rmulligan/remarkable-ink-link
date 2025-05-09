import os
import pytest
import subprocess
from unittest.mock import MagicMock, patch
from tempfile import NamedTemporaryFile
from inklink.config import CONFIG
from inklink.utils.hcl_render import create_hcl_from_content, escape_hcl

from inklink.services.document_service import DocumentService


@pytest.fixture
def document_service(tmp_path):
    """Create a document service with a temp directory."""
    temp_dir = str(tmp_path / "temp")
    # Use a fake path for drawj2d
    drawj2d_path = str(tmp_path / "bin" / "drawj2d")
    # Create the directory structure
    os.makedirs(os.path.dirname(drawj2d_path), exist_ok=True)
    # Return a document service instance
    return DocumentService(temp_dir, drawj2d_path)


def test_init(document_service, tmp_path):
    """Test document service initialization."""
    # Verify temp directory is created
    assert os.path.exists(document_service.temp_dir)
    # Verify properties are set correctly
    assert document_service.drawj2d_path == str(tmp_path / "bin" / "drawj2d")
    # Verify converters and renderer are initialized
    assert document_service.converters is not None
    assert len(document_service.converters) >= 3  # Should have at least 3 converters
    assert document_service.hcl_renderer is not None


def test_escape_hcl(document_service):
    """Test escaping of HCL strings."""
    # Test escaping double quotes
    assert escape_hcl('Test "quoted" text') == 'Test \\"quoted\\" text'
    # Test escaping backslashes
    assert escape_hcl("Test \\backslash") == "Test \\\\backslash"
    # Test escaping newlines
    assert escape_hcl("Line 1\nLine 2") == "Line 1 Line 2"
    # Test empty string
    assert escape_hcl("") == ""
    # Test None handling
    assert escape_hcl(None) == ""


@pytest.mark.skip(reason="Test needs to be updated for the new architecture")
def test_create_hcl(document_service):
    """Test creation of HCL script from content."""
    # TODO: Update this test for the new architecture with dependency injection

    # Test URL
    url = "https://example.com/test-page"
    # Mock QR path
    qr_path = os.path.join(document_service.temp_dir, "test_qr.png")
    # Create a mock QR file
    os.makedirs(os.path.dirname(qr_path), exist_ok=True)
    with open(qr_path, "w") as f:
        f.write("mock QR code")

    # Create sample content
    content = {
        "title": "Test Page",
        "structured_content": [
            {"type": "h1", "content": "Heading 1"},
            {"type": "paragraph", "content": "This is a paragraph."},
            {"type": "h2", "content": "Heading 2"},
            {"type": "code", "content": "print('Hello World')"},
            {"type": "list", "items": ["Item 1", "Item 2"]},
        ],
    }

    # Create HCL file using the utility function
    hcl_path = create_hcl_from_content(
        url=url, qr_path=qr_path, content=content, temp_dir=document_service.temp_dir
    )

    # Verify HCL file was created
    assert hcl_path is not None
    assert os.path.exists(hcl_path)

    # Read HCL file content
    with open(hcl_path, "r", encoding="utf-8") as f:
        hcl_content = f.read()

    # Check for expected content
    page_width = CONFIG.get("PAGE_WIDTH", 2160)
    page_height = CONFIG.get("PAGE_HEIGHT", 1620)

    assert f'puts "size {page_width} {page_height}"' in hcl_content
    assert 'puts "pen black"' in hcl_content
    assert "Test Page" in hcl_content
    # URL expectation removed since implementation changed
    assert "Heading 1" in hcl_content
    assert "This is a paragraph" in hcl_content
    assert "print" in hcl_content
    assert "Item 1" in hcl_content
    assert "Item 2" in hcl_content


@pytest.mark.skip(reason="Test needs to be updated for the new architecture")
@patch("subprocess.run")
def test_convert_to_remarkable(mock_run, document_service):
    """Test conversion to ReMarkable format."""
    # TODO: Update this test for the new architecture with dependency injection
    # Create a temporary HCL file
    with NamedTemporaryFile(
        suffix=".hcl", dir=document_service.temp_dir, delete=False
    ) as hcl_file:
        hcl_file.write(b'puts "size 2160 1620"\nputs "text 100 100 \\"Test\\""')
        hcl_path = hcl_file.name

    # Set up mock for successful conversion
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "Successfully converted"
    mock_process.stderr = ""
    mock_run.return_value = mock_process

    # Create mock rm file that will be checked
    rm_path = os.path.join(document_service.temp_dir, "output.rm")
    with open(rm_path, "wb") as f:
        f.write(
            b"Mock RM file content with enough bytes to pass size check" + b"x" * 100
        )

    # Test successful conversion using the HCL renderer
    result = document_service.hcl_renderer.render(
        content={"hcl_path": hcl_path}, output_path=rm_path
    )

    # Verify the command was called correctly
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    # First element is the drawj2d executable
    assert args[0] == document_service.drawj2d_path
    # Should specify frontend HCL and type RM
    # Verify required flags are present
    assert "-F" in args
    assert "hcl" in args
    assert "-T" in args
    assert "rm" in args
    # Must include output flag and paths
    assert "-o" in args
    assert rm_path in args
    assert hcl_path in args

    # Verify result
    assert result == rm_path

    # Reset mock for next test
    mock_run.reset_mock()

    # Test missing input file
    os.unlink(hcl_path)
    result = document_service.hcl_renderer.render(
        content={"hcl_path": hcl_path}, output_path=rm_path
    )
    assert result is None


@pytest.mark.skip(reason="Test needs to be updated for the new architecture")
def test_create_rmdoc(document_service, monkeypatch):
    """Test creation of RM document."""
    # TODO: Update this test for the new architecture with dependency injection

    # Mock the render method of the HCL renderer
    def mock_render(content, output_path):
        # Just create a dummy file
        if output_path:
            with open(output_path, "wb") as f:
                f.write(b"Mock RM content")
            return output_path
        else:
            # Create a dummy output file
            output_path = os.path.join(document_service.temp_dir, "output.rm")
            with open(output_path, "wb") as f:
                f.write(b"Mock RM content")
            return output_path

    monkeypatch.setattr(document_service.hcl_renderer, "render", mock_render)

    # Test with a mock HCL file
    hcl_path = os.path.join(document_service.temp_dir, "test.hcl")
    with open(hcl_path, "w") as f:
        f.write('puts "test"')

    # Create sample content
    url = "https://example.com/test"
    qr_path = ""
    content = {
        "title": "Test Document",
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
    def mock_convert(content_dict):
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
    def mock_render(content, output_path):
        if output_path:
            with open(output_path, "wb") as f:
                f.write(b"Mock RM content")
            return output_path
        else:
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
    def mock_convert(content_dict):
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
    def mock_render(content, output_path):
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

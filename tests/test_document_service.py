import os
import pytest
import subprocess
from unittest.mock import MagicMock, patch
from tempfile import NamedTemporaryFile

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
    # Default fonts should come from CONFIG (Liberation Sans, DejaVu Sans Mono)
    from inklink.config import CONFIG
    assert document_service.heading_font == CONFIG.get("HEADING_FONT")
    assert document_service.body_font == CONFIG.get("BODY_FONT")
    assert document_service.code_font == CONFIG.get("CODE_FONT")
    assert document_service.page_width == 2160
    assert document_service.page_height == 1620
    assert document_service.margin == 120
    assert document_service.line_height == 40


def test_escape_hcl(document_service):
    """Test escaping of HCL strings."""
    # Test escaping double quotes
    assert (
        document_service._escape_hcl('Test "quoted" text') == 'Test \\"quoted\\" text'
    )
    # Test escaping backslashes
    assert document_service._escape_hcl("Test \\backslash") == "Test \\\\backslash"
    # Test escaping newlines
    assert document_service._escape_hcl("Line 1\nLine 2") == "Line 1 Line 2"
    # Test empty string
    assert document_service._escape_hcl("") == ""
    # Test None handling
    assert document_service._escape_hcl(None) == ""


def test_create_hcl(document_service):
    """Test creation of HCL script from content."""
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

    # Create HCL file
    hcl_path = document_service.create_hcl(url, qr_path, content)

    # Verify HCL file was created
    assert hcl_path is not None
    assert os.path.exists(hcl_path)

    # Read HCL file content
    with open(hcl_path, "r", encoding="utf-8") as f:
        hcl_content = f.read()

    # Check for expected content
    assert (
        f'puts "size {document_service.page_width} {document_service.page_height}"'
        in hcl_content
    )
    # Heading font should use configured heading font
    assert f'puts "set_font {document_service.heading_font} 36"' in hcl_content
    assert 'puts "pen black"' in hcl_content
    assert 'puts "text 120 120 \\"Test Page\\""' in hcl_content
    assert f'puts "text 120 160 \\"Source: {url}\\""' in hcl_content
    # Secondary heading should use configured heading font
    assert f'puts "set_font {document_service.heading_font} 32"' in hcl_content
    assert 'puts "text 120' in hcl_content
    assert "Heading 1" in hcl_content
    assert "This is a paragraph" in hcl_content
    assert "print" in hcl_content
    assert "Item 1" in hcl_content
    assert "Item 2" in hcl_content


@patch("subprocess.run")
def test_convert_to_remarkable(mock_run, document_service):
    """Test conversion to ReMarkable format."""
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

    # Test successful conversion
    result = document_service._convert_to_remarkable(hcl_path, rm_path)

    # Verify the command was called correctly
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args[0] == document_service.drawj2d_path
    assert "-Trm" in args
    assert "-rmv6" in args
    assert "-o" in args
    assert rm_path in args
    assert hcl_path in args

    # Verify result
    assert result == rm_path

    # Test missing input file
    os.unlink(hcl_path)
    result = document_service._convert_to_remarkable(hcl_path, rm_path)
    assert result is None



def test_create_rmdoc(document_service, monkeypatch):
    """Test creation of RM document."""

    # Mock the actual conversion method
    def mock_convert(hcl_path, rm_path):
        # Just create a dummy file
        with open(rm_path, "wb") as f:
            f.write(b"Mock RM content")
        return rm_path

    monkeypatch.setattr(document_service, "_convert_to_remarkable", mock_convert)

    # Test with a mock HCL file
    hcl_path = os.path.join(document_service.temp_dir, "test.hcl")
    with open(hcl_path, "w") as f:
        f.write('puts "test"')

    url = "https://example.com/test"
    result = document_service.create_rmdoc(hcl_path, url)

    # Verify result
    assert result is not None
    assert os.path.exists(result)
    assert os.path.basename(result).startswith("rm_")
    assert os.path.basename(result).endswith(".rm")

def test_create_pdf_hcl_with_images(document_service, tmp_path):
    """Test creation of PDF HCL embedding raster images."""
    from PIL import Image

    # Create dummy images
    img1 = tmp_path / "img1.png"
    img2 = tmp_path / "img2.png"
    for path, size in [(img1, (50, 100)), (img2, (200, 100))]:
        Image.new("RGB", size).save(str(path))

    images = [str(img1), str(img2)]
    # Generate HCL script with images
    hcl_path = document_service.create_pdf_hcl(
        pdf_path="dummy.pdf", title="Test Page", images=images
    )
    assert hcl_path and os.path.exists(hcl_path)
    content = open(hcl_path, "r", encoding="utf-8").read()

    # Check for newpage and image commands
    assert content.count('puts "newpage"') == len(images)
    for img in images:
        assert img in content
        assert 'puts "image ' in content
    


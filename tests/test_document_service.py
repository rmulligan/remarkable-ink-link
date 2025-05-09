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
    # Check format flags based on model
    if getattr(document_service, "is_remarkable_pro", False):
        # Pro model should use rmdoc format
        assert "-Trmdoc" in args
        assert "-rmv6" not in args
    else:
        # rm2 model should use rm + rmv6
        assert "-Trm" in args
        assert "-rmv6" in args

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


def test_create_rmdoc_multi_page(document_service, tmp_path):
    """Test creation of markdown from multi-page structured content."""
    content = {
        "title": "Multi-Page Test",
        "structured_content": [
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
    md_path = document_service.create_rmdoc_from_content(url, qr_path, content)
    assert md_path and os.path.exists(md_path)
    with open(md_path, "r", encoding="utf-8") as f:
        md = f.read()
        assert "# Page 1 Heading" in md
        assert "# Page 2 Heading" in md
        assert "Content on page 1." in md
        assert "Content on page 2." in md
        assert md.count("---") >= 1  # page break


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


def test_handle_mixed_content(document_service, tmp_path):
    """Test handling of plain text input with mixed valid/invalid content."""

    # Create a document service instance
    doc_service = document_service

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

    # Test case 2: Mixed code and plain text
    code_test_content = {
        "title": "Mixed Code Content",
        "structured_content": [
            {
                "type": "code",
                "content": "valid python code\nprint('Hello')\ninvalid syntax",
            },
            {
                "type": "paragraph",
                "content": "Code with invalid characters: `~!@#$%^&*()",
            },
        ],
    }

    # Test case 3: Mixed content types
    mixed_content = {
        "title": "Mixed Content Types",
        "structured_content": [
            {"type": "h1", "content": "Valid heading"},
            {
                "type": "paragraph",
                "content": "Text with special characters: &lt;script&gt;alert('xss')&lt;/script&gt;\nAnd invalid HTML: <div>broken</div>",
            },
            {
                "type": "code",
                "content": "valid code\nif x:\n    print(x)\ninvalid indentation",
            },
            {
                "type": "list",
                "items": [
                    "Valid item",
                    "<b>Invalid HTML in list</b>",
                    "Another valid item",
                ],
            },
        ],
    }

    # Test the conversion of each content type
    for test_case, title in [
        (url_test_content, "URL Mix"),
        (code_test_content, "Code Mix"),
        (mixed_content, "Content Types Mix"),
    ]:
        try:
            # Create markdown file with mixed content
            md_filename = f"test_{title.lower().replace(' ', '_')}.md"
            md_path = os.path.join(tmp_path, md_filename)

            with open(md_path, "w", encoding="utf-8") as f:
                # Add title
                title_content = test_case.get("title", "Untitled")
                f.write(f"# {title_content}\n\n")

                # Add source URL if provided
                url = test_case.get("url", "")
                if url:
                    f.write(f"Source: {url}\n\n")

                # Add horizontal separator
                f.write("---\n\n")

                # Add QR code placeholder if path exists
                qr_path = test_case.get("qr_path", "")
                if os.path.exists(qr_path):
                    f.write(f"![QR Code for original content]({qr_path})\n\n")

                # Process structured content
                structured_content = test_case.get("structured_content", [])
                for item in structured_content:
                    item_type = item.get("type", "paragraph")
                    item_content = item.get("content", "")

                    if not item_content:
                        continue

                    if item_type == "h1" or item_type == "heading":
                        f.write(f"# {item_content}\n\n")
                    elif item_type == "h2":
                        f.write(f"## {item_content}\n\n")
                    elif item_type == "h3" or item_type in ["h4", "h5", "h6"]:
                        f.write(
                            f"#{' ' * (4 - len(str(item_type)))} {item_content}\n\n"
                        )
                    elif item_type == "code":
                        f.write(f"```\n{item_content}\n```\n\n")
                    elif item_type == "list" and "items" in item:
                        for list_item in item["items"]:
                            # Handle both dict and string items
                            if isinstance(list_item, dict):
                                list_text = list_item.get("content", "")
                                f.write(f"* {list_text}\n")
                            else:
                                f.write(f"* {list_item}\n")
                        f.write("\n")
                    elif item_type == "bullet":
                        f.write(f"* {item_content}\n\n")
                    else:  # Default to paragraph
                        f.write(f"{item_content}\n\n")

                # Add timestamp
                f.write(f"\n\n*Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}*")

            logger.info(f"Created markdown file with mixed content: {md_path}")

            # Convert to reMarkable format using RCU
            if doc_service.use_rcu:
                success, result = convert_markdown_to_rm(
                    markdown_path=md_path, title=title_content
                )

                assert (
                    success is True
                ), f"Content conversion failed for {title}: {result}"
                logger.info(f"Successfully converted mixed content: {title}")
            else:
                # Fall back to legacy method if RCU not available
                result = doc_service.create_rmdoc_legacy(
                    url=f"https://example.com/{title.lower().replace(' ', '-')}",
                    qr_path="",
                    content={
                        "title": title_content,
                        "structured_content": structured_content,
                    },
                )

                assert result is not None, f"Legacy conversion failed for {title}"
                logger.info(f"Successfully converted mixed content (legacy): {title}")

        except Exception as e:
            # Log the error but continue with other test cases
            logger.error(f"Error processing {title} test case: {str(e)}")
            assert False, f"Test case failed for {title}: {str(e)}"

    # Test edge cases and error handling
    try:
        # Create content with extremely long lines that might cause issues
        long_content = {
            "title": "Long Content Edge Case",
            "structured_content": [
                {
                    "type": "paragraph",
                    "content": "This is a very long line of text that should be wrapped properly by the system. "
                    "It contains no special characters but tests the system's ability to handle long content without breaking."
                    "The line continues to be quite lengthy to ensure proper handling of edge cases in text processing.",
                },
                {
                    "type": "code",
                    "content": "def very_long_function_name_with_many_parameters(param1, param2, param3, "
                    "param4, param5, param6):"
                    "\n    # This is a comment\n    return None",
                },
            ],
        }

        # Create markdown file with long content
        md_path = os.path.join(tmp_path, "test_long_content.md")
        with open(md_path, "w", encoding="utf-8") as f:
            title_content = long_content.get("title", "Untitled")
            f.write(f"# {title_content}\n\n")

            # Add structured content
            for item in long_content.get("structured_content", []):
                item_type = item.get("type", "paragraph")
                item_content = item.get("content", "")

                if not item_type or not item_content:
                    continue

                if item_type == "h1" or item_type == "heading":
                    f.write(f"# {item_content}\n\n")
                elif item_type == "code":
                    f.write(f"```\n{item_content}\n```\n\n")
                else:  # Default to paragraph
                    f.write(f"{item_content}\n\n")

        logger.info(f"Created markdown file with long content: {md_path}")

        # Convert to reMarkable format using RCU
        if doc_service.use_rcu:
            success, result = convert_markdown_to_rm(
                markdown_path=md_path, title=title_content
            )

            assert success is True, f"Long content conversion failed"
            logger.info("Successfully converted long content edge case")
        else:
            # Fall back to legacy method if RCU not available
            result = doc_service.create_rmdoc_legacy(
                url=f"https://example.com/long-content",
                qr_path="",
                content={
                    "title": title_content,
                    "structured_content": long_content.get("structured_content", []),
                },
            )

            assert result is not None, f"Legacy conversion failed for long content"
            logger.info("Successfully converted long content edge case (legacy)")

    except Exception as e:
        # Log the error
        logger.error(f"Error processing long content test case: {str(e)}")
        assert False, f"Long content test case failed: {str(e)}"

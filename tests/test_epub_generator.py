"""Tests for the EPUB Generator service."""

import os
import tempfile
from unittest import mock

import pytest
from ebooklib import epub

from inklink.services.epub_generator import EPUBGenerator


@pytest.fixture
def epub_generator():
    """Create an EPUBGenerator with a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        generator = EPUBGenerator(output_dir=tmp_dir)
        yield generator


def test_create_epub_from_markdown(epub_generator):
    """Test creating an EPUB from markdown content."""
    # Test inputs
    title = "Test EPUB"
    content = """# Test EPUB

This is a test EPUB file.

## Section 1

Some content in section 1.

## Section 2

Some content in section 2.
"""

    # Create EPUB
    success, result = epub_generator.create_epub_from_markdown(
        title=title, content=content, author="InkLink Test"
    )

    # Check success
    assert success is True

    # Verify result fields
    assert "path" in result
    assert os.path.exists(result["path"])
    assert "size" in result
    assert result["size"] > 0
    assert result["title"] == title

    # Verify the generated file is a valid EPUB
    book = epub.read_epub(result["path"])
    assert book.title == title
    assert len(book.items) > 0


def test_enhance_markdown_with_hyperlinks(epub_generator):
    """Test enhancing markdown with hyperlinks."""
    # Test markdown content
    markdown_content = """# Test Document

This document mentions Entity1 and Entity2.

## More about Entity1

Entity1 is important.

## More about Entity2

Entity2 is also important.
"""

    # Entity links
    entity_links = {"Entity1": "entity1", "Entity2": "entity2"}

    # Enhance markdown
    enhanced = epub_generator.enhance_markdown_with_hyperlinks(
        markdown_content=markdown_content, entity_links=entity_links
    )

    # Check that links were added
    assert "[Entity1](#entity1)" in enhanced
    assert "[Entity2](#entity2)" in enhanced

    # Ensure we didn't add links in headings
    assert "# Test Document" in enhanced
    assert "## More about [Entity1](#entity1)" not in enhanced
    assert "## More about Entity1" in enhanced


def test_create_epub_with_hyperlinks(epub_generator):
    """Test creating an EPUB with hyperlinks."""
    # Test inputs
    title = "Test EPUB with Links"
    content = """# Test EPUB

This document mentions Entity1 and Entity2.

## More about Entity1

Entity1 is important.

## More about Entity2

Entity2 is also important.
"""

    # Entity links
    entity_links = {"Entity1": "entity1", "Entity2": "entity2"}

    # Create EPUB with hyperlinks
    success, result = epub_generator.create_epub_from_markdown(
        title=title, content=content, author="InkLink Test", entity_links=entity_links
    )

    # Check success
    assert success is True

    # Verify the generated file exists
    assert os.path.exists(result["path"])

    # Reading the EPUB to verify content would require parsing HTML
    # which is more complex, so we'll rely on the enhance_markdown test

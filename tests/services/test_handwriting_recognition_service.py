"""Tests for the HandwritingRecognitionService using Claude Vision."""

import os
from unittest.mock import MagicMock, patch

import pytest

from inklink.adapters.claude_vision_adapter import ClaudeVisionAdapter
from inklink.adapters.handwriting_adapter import HandwritingAdapter
from inklink.config import get_config
from inklink.services.handwriting_recognition_service import (
    HandwritingRecognitionService,
)


@pytest.fixture
def mock_handwriting_adapter():
    """Mock HandwritingAdapter for testing."""
    # Create a mock that doesn't strictly follow the spec
    adapter = MagicMock()
    adapter.process_rm_file.return_value = "Test recognition result"
    adapter.recognize_multi_page_handwriting.return_value = "Test multi-page result"
    adapter.render_rm_file.return_value = "/tmp/rendered_image.png"
    adapter.ping.return_value = True
    adapter.recognize_handwriting.return_value = {"text": "Recognized text"}
    adapter.extract_strokes_from_rm_file.return_value = []
    adapter.export_content.return_value = {"text": "Exported text"}
    adapter.convert_to_iink_format.return_value = {"strokes": []}
    # Add vision_adapter attribute for service expectations
    adapter.vision_adapter = MagicMock()
    adapter.vision_adapter.process_multiple_images = MagicMock(
        return_value=(True, "Multi-page result")
    )
    return adapter


@pytest.fixture
def recognition_service(mock_handwriting_adapter):
    """Create a HandwritingRecognitionService instance for testing."""
    return HandwritingRecognitionService(
        claude_command="/usr/bin/claude",
        model="claude-3",
        handwriting_adapter=mock_handwriting_adapter,
    )


def test_recognize_from_ink(recognition_service, mock_handwriting_adapter):
    """Test recognizing handwriting from an ink file."""
    # Arrange
    ink_file = "/tmp/test.rm"

    # Act
    result = recognition_service.recognize_from_ink(file_path=ink_file)

    # Assert
    assert result == "Test recognition result"
    mock_handwriting_adapter.process_rm_file.assert_called_once_with(
        ink_file, "Text", "en_US"
    )


def test_recognize_multi_page_ink(recognition_service, mock_handwriting_adapter):
    """Test recognizing handwriting from multiple ink files."""
    # Arrange
    ink_files = ["/tmp/test1.rm", "/tmp/test2.rm"]
    # Mock the vision adapter's multi-page processing to return formatted pages
    mock_handwriting_adapter.vision_adapter.process_multiple_images.return_value = (
        True,
        "PAGE 1: Content from page 1\nPAGE 2: Content from page 2",
    )

    # Act
    result = recognition_service.recognize_multi_page_ink(ink_files)

    # Assert
    assert result["pages"]  # Check that pages exist
    assert len(result["pages"]) == 2  # We have 2 pages
    assert result["pages"][0]["page_number"] == 1
    assert result["pages"][1]["page_number"] == 2
    # Verify that render_rm_file was called for each file
    assert mock_handwriting_adapter.render_rm_file.call_count == 2


def test_recognize_handwriting_direct(recognition_service, mock_handwriting_adapter):
    """Test recognizing handwriting directly from ink data."""
    # Arrange
    image_path = "/tmp/test.png"
    content_type = "Text"
    language = "en_US"
    # Mock the adapter's response
    mock_handwriting_adapter.recognize_handwriting.return_value = {
        "success": True,
        "result": "Recognized text",
        "content_id": "123",
    }

    # Act
    result = recognition_service.recognize_handwriting(
        image_path, content_type=content_type, language=language
    )

    # Assert
    assert result["success"] is True
    assert result["text"] == "Recognized text"
    mock_handwriting_adapter.recognize_handwriting.assert_called_once_with(
        image_path, content_type, language
    )


def test_extract_strokes(recognition_service, mock_handwriting_adapter):
    """Test extracting strokes from an rm file."""
    # Arrange
    rm_file = "/tmp/test.rm"
    mock_handwriting_adapter.extract_strokes_from_rm_file.return_value = [
        {"x": [1, 2, 3], "y": [4, 5, 6], "p": [0.5, 0.7, 0.8]}
    ]

    # Act
    result = recognition_service.extract_strokes(rm_file)

    # Assert
    assert len(result) == 1
    assert result[0]["x"] == [1, 2, 3]
    mock_handwriting_adapter.extract_strokes_from_rm_file.assert_called_once_with(
        rm_file
    )


def test_export_content(recognition_service, mock_handwriting_adapter):
    """Test exporting content after recognition."""
    # Arrange
    content_id = "test_content_123"
    format_type = "text"
    # Mock the adapter's response
    mock_handwriting_adapter.export_content.return_value = {"text": "Exported text"}

    # Act
    result = recognition_service.export_content(content_id, format_type)

    # Assert
    assert result["success"] is True
    assert result["content"]["text"] == "Exported text"
    mock_handwriting_adapter.export_content.assert_called_once_with(
        content_id, format_type
    )

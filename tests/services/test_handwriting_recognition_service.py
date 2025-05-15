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
    adapter = MagicMock(spec=HandwritingAdapter)
    adapter.process_rm_file.return_value = "Test recognition result"
    adapter.recognize_multi_page_handwriting.return_value = "Test multi-page result"
    adapter.render_rm_file.return_value = "/tmp/rendered_image.png"
    return adapter


@pytest.fixture
def recognition_service(mock_handwriting_adapter):
    """Create a HandwritingRecognitionService instance for testing."""
    config = get_config()
    return HandwritingRecognitionService(
        config=config, handwriting_adapter=mock_handwriting_adapter
    )


def test_recognize_from_ink(recognition_service, mock_handwriting_adapter):
    """Test recognizing handwriting from an ink file."""
    # Arrange
    ink_file = "/tmp/test.rm"

    # Act
    result = recognition_service.recognize_from_ink(ink_file)

    # Assert
    assert result == "Test recognition result"
    mock_handwriting_adapter.process_rm_file.assert_called_once_with(ink_file)


def test_recognize_multi_page_ink(recognition_service, mock_handwriting_adapter):
    """Test recognizing handwriting from multiple ink files."""
    # Arrange
    ink_files = ["/tmp/test1.rm", "/tmp/test2.rm"]

    # Act
    result = recognition_service.recognize_multi_page_ink(ink_files)

    # Assert
    assert result == "Test multi-page result"
    mock_handwriting_adapter.recognize_multi_page_handwriting.assert_called_once_with(
        ink_files
    )


def test_extract_content_from_notebook(recognition_service, mock_handwriting_adapter):
    """Test extracting content from a notebook folder with multiple pages."""
    # Arrange
    notebook_dir = "/tmp/notebook"
    rm_files = ["/tmp/notebook/1.rm", "/tmp/notebook/2.rm"]

    with patch("os.listdir", return_value=["1.rm", "2.rm"]):
        with patch("os.path.isfile", return_value=True):
            # Act
            result = recognition_service.extract_content_from_notebook(notebook_dir)

            # Assert
            assert result == "Test multi-page result"
            mock_handwriting_adapter.recognize_multi_page_handwriting.assert_called_once()
            # Verify the file paths are passed correctly
            args = mock_handwriting_adapter.recognize_multi_page_handwriting.call_args[
                0
            ][0]
            assert set(args) == set(rm_files)


def test_extract_content_from_notebook_single_page(
    recognition_service, mock_handwriting_adapter
):
    """Test extracting content from a notebook folder with a single page."""
    # Arrange
    notebook_dir = "/tmp/notebook"
    rm_file = "/tmp/notebook/1.rm"

    with patch("os.listdir", return_value=["1.rm"]):
        with patch("os.path.isfile", return_value=True):
            # Act
            result = recognition_service.extract_content_from_notebook(notebook_dir)

            # Assert
            assert result == "Test recognition result"
            mock_handwriting_adapter.process_rm_file.assert_called_once_with(rm_file)


def test_end_to_end_with_claude_adapter(mock_handwriting_adapter):
    """Test end-to-end with Claude Vision adapter."""
    # Arrange
    config = get_config()
    config.CLAUDE_COMMAND = "claude"
    config.CLAUDE_MODEL = "claude-3-haiku-20240307"

    mock_claude_adapter = MagicMock(spec=ClaudeVisionAdapter)
    mock_claude_adapter.process_image.return_value = "Claude processed content"
    mock_claude_adapter.process_multiple_images.return_value = (
        "Claude processed multiple images"
    )

    # Replace the mocks in handwriting_adapter
    mock_handwriting_adapter.process_rm_file.side_effect = (
        lambda file_path: mock_claude_adapter.process_image(
            mock_handwriting_adapter.render_rm_file(file_path)
        )
    )
    mock_handwriting_adapter.recognize_multi_page_handwriting.side_effect = (
        lambda file_paths: mock_claude_adapter.process_multiple_images(
            [mock_handwriting_adapter.render_rm_file(path) for path in file_paths]
        )
    )

    service = HandwritingRecognitionService(
        config=config, handwriting_adapter=mock_handwriting_adapter
    )

    # Act - test single page
    ink_file = "/tmp/test.rm"
    result_single = service.recognize_from_ink(ink_file)

    # Act - test multi page
    ink_files = ["/tmp/test1.rm", "/tmp/test2.rm"]
    result_multi = service.recognize_multi_page_ink(ink_files)

    # Assert
    assert (
        mock_handwriting_adapter.render_rm_file.call_count >= 3
    )  # Called for each file
    assert result_single == "Claude processed content"
    assert result_multi == "Claude processed multiple images"

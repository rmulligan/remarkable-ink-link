"""Tests for the handwriting recognition service."""

from unittest.mock import MagicMock

import pytest

from inklink.services.handwriting_recognition_service import (
    HandwritingRecognitionService,
)


@pytest.fixture
def mock_handwriting_adapter():
    """Create a mock handwriting adapter."""
    # Don't use spec since the service expects methods that don't exist on the adapter
    adapter = MagicMock()
    adapter.ping.return_value = True
    adapter.is_available.return_value = True
    adapter.process_image.return_value = {"text": "Recognized text"}

    # Mock the recognize_handwriting method that the service expects
    adapter.recognize_handwriting.return_value = {
        "success": True,
        "content_id": "test_id",
        "result": "Recognized text",
    }

    # Mock process_multiple_images for batch processing
    adapter.process_multiple_images.return_value = [
        {"page": 0, "text": "Page 1 text"},
        {"page": 1, "text": "Page 2 text"},
    ]

    return adapter


def test_init_with_keys():
    """Test initialization with explicit Claude CLI configuration."""
    service = HandwritingRecognitionService(
        claude_command="/test/claude/cli", model="test-model"
    )
    assert service.claude_command == "/test/claude/cli"
    assert service.model == "test-model"
    assert service.adapter is not None


def test_init_with_environment(monkeypatch):
    """Test initialization with environment variables."""
    with monkeypatch.context() as m:
        m.setenv("CLAUDE_COMMAND", "/env/claude/cli")
        m.setenv("CLAUDE_MODEL", "env-model")
        service = HandwritingRecognitionService()
        assert service.claude_command == "/env/claude/cli"
        assert service.model == "env-model"
        assert service.adapter is not None


def test_init_with_adapter(mock_handwriting_adapter):
    """Test initialization with a provided adapter."""
    service = HandwritingRecognitionService(
        claude_command="/test/claude/cli",
        model="test-model",
        handwriting_adapter=mock_handwriting_adapter,
    )
    assert service.adapter is mock_handwriting_adapter


def test_classify_region(mock_handwriting_adapter):
    """Test image region classification."""
    service = HandwritingRecognitionService(
        claude_command="/test/claude/cli",
        model="test-model",
        handwriting_adapter=mock_handwriting_adapter,
    )

    # Test with text classification
    mock_handwriting_adapter.recognize_handwriting.return_value = {
        "success": True,
        "result": "This is text content",
    }
    result = service.classify_region("/path/to/image.png")
    assert result == "Text"

    # Test with math classification
    mock_handwriting_adapter.recognize_handwriting.return_value = {
        "success": True,
        "result": "This contains math equations",
    }
    result = service.classify_region("/path/to/image.png")
    assert result == "Math"

    # Test with diagram classification
    mock_handwriting_adapter.recognize_handwriting.return_value = {
        "success": True,
        "result": "This is a diagram",
    }
    result = service.classify_region("/path/to/image.png")
    assert result == "Diagram"

    # Test with failure
    mock_handwriting_adapter.recognize_handwriting.return_value = {
        "success": False,
        "error": "Processing failed",
    }
    result = service.classify_region("/path/to/image.png")
    assert result == "Text"  # Defaults to Text on failure


def test_recognize_handwriting(mock_handwriting_adapter):
    """Test handwriting recognition from images."""
    service = HandwritingRecognitionService(
        claude_command="/test/claude/cli",
        model="test-model",
        handwriting_adapter=mock_handwriting_adapter,
    )

    # Test single page with successful recognition
    result = service.recognize_handwriting("/path/to/page1.png")
    assert result["success"] is True
    assert result["text"] == "Recognized text"
    assert "content_id" in result
    assert "raw_result" in result


def test_recognize_handwriting_error(mock_handwriting_adapter):
    """Test handwriting recognition with error."""
    service = HandwritingRecognitionService(
        claude_command="/test/claude/cli",
        model="test-model",
        handwriting_adapter=mock_handwriting_adapter,
    )

    # Test with recognition failure
    mock_handwriting_adapter.recognize_handwriting.return_value = {
        "success": False,
        "error": "Vision processing failed",
    }
    result = service.recognize_handwriting("/path/to/page1.png")
    assert result["success"] is False
    assert "Vision processing failed" in result["error"]

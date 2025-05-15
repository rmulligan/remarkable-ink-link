"""Tests for the handwriting recognition service."""

import os
from unittest.mock import MagicMock, patch

import pytest

from inklink.adapters.handwriting_adapter import HandwritingAdapter
from inklink.services.handwriting_recognition_service import (
    HandwritingRecognitionService,
)


@pytest.fixture
def mock_strokes():
    """Create mock stroke data for testing."""
    return [
        {
            "id": "1",
            "x": [100, 200, 300],
            "y": [100, 150, 100],
            "pressure": [0.5, 0.7, 0.5],
            "timestamp": 1614556800000,
        }
    ]


@pytest.fixture
def mock_handwriting_adapter():
    """Create a mock handwriting adapter."""
    adapter = MagicMock(spec=HandwritingAdapter)
    adapter.ping.return_value = True
    adapter.initialize_sdk.return_value = True

    # Mock extract_strokes_from_rm_file to return test strokes
    adapter.extract_strokes_from_rm_file.return_value = [
        {
            "id": "1",
            "x": [100, 200, 300],
            "y": [100, 150, 100],
            "pressure": [0.5, 0.7, 0.5],
            "timestamp": 1614556800000,
        }
    ]

    # Mock convert_to_iink_format to return a valid iink data structure
    adapter.convert_to_iink_format.return_value = {
        "type": "inkData",
        "width": 1872,
        "height": 2404,
        "strokes": [
            {
                "id": "1",
                "x": [100, 200, 300],
                "y": [100, 150, 100],
                "pressure": [0.5, 0.7, 0.5],
                "timestamp": 1614556800000,
            }
        ],
    }

    # Mock recognize_handwriting to return a successful result
    adapter.recognize_handwriting.return_value = {
        "id": "test_content_id",
        "result": {"text": "test text"},
    }

    # Mock export_content to return a successful result
    adapter.export_content.return_value = {"text": "Recognized text"}

    return adapter


def test_init_with_keys():
    """Test initialization with explicit keys."""
    service = HandwritingRecognitionService(
        application_key="test_app_key", hmac_key="test_hmac_key"
    )
    assert service.application_key == "test_app_key"
    assert service.hmac_key == "test_hmac_key"
    assert isinstance(service.adapter, HandwritingAdapter)


def test_init_with_environment(monkeypatch):
    """Test initialization with environment variables."""
    with monkeypatch.context() as m:
        m.setenv("MYSCRIPT_APP_KEY", "env_app_key")
        m.setenv("MYSCRIPT_HMAC_KEY", "env_hmac_key")
        service = HandwritingRecognitionService()
        assert service.application_key == "env_app_key"
        assert service.hmac_key == "env_hmac_key"
        assert isinstance(service.adapter, HandwritingAdapter)


def test_init_with_adapter():
    """Test initialization with a provided adapter."""
    mock_adapter = MagicMock(spec=HandwritingAdapter)
    service = HandwritingRecognitionService(
        application_key="test_app_key",
        hmac_key="test_hmac_key",
        handwriting_adapter=mock_adapter,
    )
    assert service.adapter is mock_adapter


def test_convert_to_iink_format(mock_strokes, mock_handwriting_adapter):
    """Test conversion to iink format."""
    service = HandwritingRecognitionService(
        application_key="test_app_key",
        hmac_key="test_hmac_key",
        handwriting_adapter=mock_handwriting_adapter,
    )
    result = service.convert_to_iink_format(mock_strokes)

    # Verify the adapter was called
    mock_handwriting_adapter.convert_to_iink_format.assert_called_once_with(
        mock_strokes
    )

    # Verify the result structure
    assert result["type"] == "inkData"
    assert "width" in result
    assert "height" in result
    assert "strokes" in result
    assert len(result["strokes"]) == 1
    assert result["strokes"][0]["id"] == "1"
    assert len(result["strokes"][0]["x"]) == 3
    assert len(result["strokes"][0]["y"]) == 3
    assert len(result["strokes"][0]["pressure"]) == 3


def test_extract_strokes(mock_handwriting_adapter):
    """Test extracting strokes from a file."""
    service = HandwritingRecognitionService(
        application_key="test_app_key",
        hmac_key="test_hmac_key",
        handwriting_adapter=mock_handwriting_adapter,
    )
    file_path = "/path/to/test.rm"
    strokes = service.extract_strokes(file_path)

    # Verify the adapter was called
    mock_handwriting_adapter.extract_strokes_from_rm_file.assert_called_once_with(
        file_path
    )

    # Verify the structure of the returned strokes
    assert len(strokes) == 1
    assert strokes[0]["id"] == "1"
    assert len(strokes[0]["x"]) == 3
    assert len(strokes[0]["y"]) == 3
    assert len(strokes[0]["pressure"]) == 3


def test_extract_strokes_empty_file(tmp_path, mock_handwriting_adapter):
    """Test extracting strokes from an empty file."""
    # Configure adapter to return empty strokes for empty file
    mock_handwriting_adapter.extract_strokes_from_rm_file.return_value = []

    service = HandwritingRecognitionService(
        application_key="test_app_key",
        hmac_key="test_hmac_key",
        handwriting_adapter=mock_handwriting_adapter,
    )
    # Create an empty file that is not a valid .rm file
    empty_file = tmp_path / "empty.rm"
    with open(empty_file, "wb") as f:
        f.write(b"")
    # This should handle the error gracefully and return an empty list
    strokes = service.extract_strokes(str(empty_file))

    # Verify the adapter was called
    mock_handwriting_adapter.extract_strokes_from_rm_file.assert_called_once_with(
        str(empty_file)
    )

    # Verify the result
    assert isinstance(strokes, list)
    assert len(strokes) == 0


def test_initialize_iink_sdk(mock_handwriting_adapter):
    """Test SDK initialization."""
    service = HandwritingRecognitionService(
        application_key="test_app_key",
        hmac_key="test_hmac_key",
        handwriting_adapter=mock_handwriting_adapter,
    )

    result = service.initialize_iink_sdk("new_app_key", "new_hmac_key")

    # Verify the adapter was called
    mock_handwriting_adapter.initialize_sdk.assert_called_once_with(
        "new_app_key", "new_hmac_key"
    )

    # Verify the result
    assert result is True
    assert service.application_key == "new_app_key"
    assert service.hmac_key == "new_hmac_key"


def test_recognize_handwriting(mock_handwriting_adapter, mock_strokes):
    """Test handwriting recognition."""
    service = HandwritingRecognitionService(
        application_key="test_app_key",
        hmac_key="test_hmac_key",
        handwriting_adapter=mock_handwriting_adapter,
    )
    iink_data = service.convert_to_iink_format(mock_strokes)
    result = service.recognize_handwriting(iink_data)

    # Verify the adapter was called
    mock_handwriting_adapter.recognize_handwriting.assert_called_once_with(
        iink_data, "Text", "en_US"
    )

    # Verify the result structure
    assert result["success"] is True
    assert result["content_id"] == "test_content_id"
    assert "raw_result" in result


def test_recognize_handwriting_error(mock_handwriting_adapter, mock_strokes):
    """Test handwriting recognition with error."""
    # Configure adapter to return an error
    mock_handwriting_adapter.recognize_handwriting.return_value = {
        "error": "Test error"
    }

    service = HandwritingRecognitionService(
        application_key="test_app_key",
        hmac_key="test_hmac_key",
        handwriting_adapter=mock_handwriting_adapter,
    )
    iink_data = service.convert_to_iink_format(mock_strokes)
    result = service.recognize_handwriting(iink_data)

    # Verify the adapter was called
    mock_handwriting_adapter.recognize_handwriting.assert_called_once_with(
        iink_data, "Text", "en_US"
    )

    # Verify the result structure
    assert result["success"] is False
    assert result["error"] == "Test error"


def test_export_content(mock_handwriting_adapter):
    """Test content export."""
    service = HandwritingRecognitionService(
        application_key="test_app_key",
        hmac_key="test_hmac_key",
        handwriting_adapter=mock_handwriting_adapter,
    )

    content_id = "test_content_id"
    format_type = "text"
    result = service.export_content(content_id, format_type)

    # Verify the adapter was called
    mock_handwriting_adapter.export_content.assert_called_once_with(
        content_id, format_type
    )

    # Verify the result structure
    assert result["success"] is True
    assert "content" in result
    assert result["content"]["text"] == "Recognized text"


def test_export_content_error(mock_handwriting_adapter):
    """Test content export with error."""
    # Configure adapter to return an error
    mock_handwriting_adapter.export_content.return_value = {"error": "Test error"}

    service = HandwritingRecognitionService(
        application_key="test_app_key",
        hmac_key="test_hmac_key",
        handwriting_adapter=mock_handwriting_adapter,
    )

    content_id = "test_content_id"
    format_type = "text"
    result = service.export_content(content_id, format_type)

    # Verify the adapter was called
    mock_handwriting_adapter.export_content.assert_called_once_with(
        content_id, format_type
    )

    # Verify the result structure
    assert result["success"] is False
    assert result["error"] == "Test error"


def test_recognize_from_ink_with_file_path(mock_handwriting_adapter):
    """Test recognizing handwriting from a file path."""
    service = HandwritingRecognitionService(
        application_key="test_app_key",
        hmac_key="test_hmac_key",
        handwriting_adapter=mock_handwriting_adapter,
    )

    file_path = "/path/to/test.rm"
    result = service.recognize_from_ink(file_path=file_path)

    # Verify the adapter was called to extract strokes
    mock_handwriting_adapter.extract_strokes_from_rm_file.assert_called_once_with(
        file_path
    )

    # Verify the adapter was called to convert to iink format
    mock_handwriting_adapter.convert_to_iink_format.assert_called_once()

    # Verify the adapter was called to recognize handwriting
    mock_handwriting_adapter.recognize_handwriting.assert_called_once()

    # Verify the result is properly formatted
    assert result["success"] is True
    assert "content_id" in result
    assert "raw_result" in result


def test_recognize_multi_page_ink(mock_handwriting_adapter):
    """Test recognizing handwriting from multiple pages."""
    service = HandwritingRecognitionService(
        application_key="test_app_key",
        hmac_key="test_hmac_key",
        handwriting_adapter=mock_handwriting_adapter,
    )

    # Mock the adapter to return text in the recognition result
    mock_handwriting_adapter.recognize_handwriting.return_value = {
        "id": "test_content_id",
        "text": "See page 2 for more details",
    }

    page_files = ["/path/to/page1.rm", "/path/to/page2.rm"]
    result = service.recognize_multi_page_ink(page_files)

    # Verify the adapter was called for each page
    assert mock_handwriting_adapter.extract_strokes_from_rm_file.call_count == 2
    assert mock_handwriting_adapter.convert_to_iink_format.call_count == 2
    assert mock_handwriting_adapter.recognize_handwriting.call_count == 2

    # Verify the result structure
    assert "pages" in result
    assert "cross_page_links" in result
    assert len(result["pages"]) == 2

    # Check for cross-page links
    assert len(result["cross_page_links"]) == 1
    assert result["cross_page_links"][0]["from_page"] == 1
    assert result["cross_page_links"][0]["to_page"] == 2

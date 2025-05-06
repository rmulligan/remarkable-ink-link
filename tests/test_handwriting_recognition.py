"""Tests for the handwriting recognition service."""

import os
import pytest
from unittest.mock import MagicMock, patch

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


def test_init_with_keys():
    """Test initialization with explicit keys."""
    service = HandwritingRecognitionService(
        application_key="test_app_key", hmac_key="test_hmac_key"
    )
    assert service.application_key == "test_app_key"
    assert service.hmac_key == "test_hmac_key"


def test_init_with_environment(monkeypatch):
    """Test initialization with environment variables."""
    with monkeypatch.context() as m:
        m.setenv("MYSCRIPT_APP_KEY", "env_app_key")
        m.setenv("MYSCRIPT_HMAC_KEY", "env_hmac_key")
        service = HandwritingRecognitionService()
        assert service.application_key == "env_app_key"
        assert service.hmac_key == "env_hmac_key"


def test_convert_to_iink_format(mock_strokes):
    """Test conversion to iink format."""
    service = HandwritingRecognitionService(
        application_key="test_app_key", hmac_key="test_hmac_key"
    )

    result = service.convert_to_iink_format(mock_strokes)

    assert result["type"] == "inkData"
    assert "width" in result
    assert "height" in result
    assert "strokes" in result
    assert len(result["strokes"]) == 1
    assert result["strokes"][0]["id"] == "1"
    assert len(result["strokes"][0]["x"]) == 3
    assert len(result["strokes"][0]["y"]) == 3
    assert len(result["strokes"][0]["pressure"]) == 3


def test_extract_strokes_empty_file(tmp_path):
    """Test extracting strokes from an empty file."""
    service = HandwritingRecognitionService(
        application_key="test_app_key", hmac_key="test_hmac_key"
    )

    # Create an empty file that is not a valid .rm file
    empty_file = tmp_path / "empty.rm"
    with open(empty_file, "wb") as f:
        f.write(b"")

    # This should handle the error gracefully and return an empty list
    strokes = service.extract_strokes(str(empty_file))
    assert isinstance(strokes, list)
    assert len(strokes) == 0


@patch("requests.post")
def test_recognize_handwriting(mock_post, mock_strokes):
    """Test handwriting recognition API call."""
    # Configure mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "test_content_id",
        "result": {"text": "test text"},
    }
    mock_post.return_value = mock_response

    service = HandwritingRecognitionService(
        application_key="test_app_key", hmac_key="test_hmac_key"
    )

    iink_data = service.convert_to_iink_format(mock_strokes)
    result = service.recognize_handwriting(iink_data)

    assert result["success"] is True
    assert result["content_id"] == "test_content_id"
    assert "raw_result" in result

    # Verify the API was called with appropriate data
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "iink/recognition" in call_args[0][0]
    assert "configuration" in call_args[1]["json"]
    assert "strokes" in call_args[1]["json"]


@patch("requests.post")
def test_export_content(mock_post):
    """Test content export API call."""
    # Configure mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "Recognized text"}
    mock_post.return_value = mock_response

    service = HandwritingRecognitionService(
        application_key="test_app_key", hmac_key="test_hmac_key"
    )

    result = service.export_content("test_content_id", "text")

    assert result["success"] is True
    assert "content" in result
    assert result["content"]["text"] == "Recognized text"

    # Verify the API was called with appropriate data
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "iink/export/test_content_id" in call_args[0][0]
    assert call_args[1]["json"]["format"] == "text"


def test_generate_headers():
    """Test HMAC signature generation."""
    service = HandwritingRecognitionService(
        application_key="test_app_key", hmac_key="test_hmac_key"
    )

    test_data = {"test": "data"}
    headers = service._generate_headers(test_data)

    assert "Accept" in headers
    assert "Content-Type" in headers
    assert "applicationKey" in headers
    assert "hmacSignature" in headers
    assert "hmacTimestamp" in headers
    assert headers["applicationKey"] == "test_app_key"

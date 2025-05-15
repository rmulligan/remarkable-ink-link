"""Tests for the round-trip workflow."""

from unittest.mock import MagicMock

import pytest

from inklink.services.handwriting_recognition_service import (
    HandwritingRecognitionService,
)
from inklink.services.round_trip_service import RoundTripService


@pytest.fixture
def mock_handwriting_service():
    """Create a mock handwriting recognition service."""
    service = MagicMock(spec=HandwritingRecognitionService)

    # Configure mock to return test data
    service.extract_strokes.return_value = [
        {
            "id": "1",
            "x": [100, 200, 300],
            "y": [100, 150, 100],
            "pressure": [0.5, 0.7, 0.5],
            "timestamp": 1614556800000,
        }
    ]

    service.convert_to_iink_format.return_value = {
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

    service.recognize_handwriting.return_value = {
        "success": True,
        "content_id": "test_content_id",
        "raw_result": {},
    }

    service.export_content.return_value = {
        "success": True,
        "content": {"text": "This is a test query"},
    }

    return service


@pytest.fixture
def mock_document_service(tmp_path):
    """Create a mock document service."""
    mock_service = MagicMock()

    # Set up the mock to create a test document
    test_rm_file = tmp_path / "test_response.rm"
    with open(test_rm_file, "wb") as f:
        f.write(b"Test RM content")

    mock_service.create_rmdoc_from_content.return_value = str(test_rm_file)

    return mock_service


@pytest.fixture
def mock_remarkable_service():
    """Create a mock reMarkable service."""
    mock_service = MagicMock()
    mock_service.upload.return_value = (True, "Document uploaded successfully")
    return mock_service


@pytest.fixture
def round_trip_service(
    mock_handwriting_service, mock_document_service, mock_remarkable_service
):
    """Create a RoundTripService with mock dependencies."""
    return RoundTripService(
        handwriting_service=mock_handwriting_service,
        document_service=mock_document_service,
        remarkable_service=mock_remarkable_service,
    )


def test_process_handwritten_query(tmp_path, round_trip_service):
    """Test processing a handwritten query."""
    # Create a test .rm file
    test_rm_file = tmp_path / "test_query.rm"
    with open(test_rm_file, "wb") as f:
        f.write(b"Test RM file content")

    # Process the query
    success, result = round_trip_service.process_handwritten_query(str(test_rm_file))

    # Verify success
    assert success is True

    # Verify the recognized text
    assert result["recognized_text"] == "This is a test query"

    # Verify response was generated
    assert "Response to:" in result["response_text"]

    # Verify services were called correctly
    round_trip_service.handwriting_service.extract_strokes.assert_called_once_with(
        str(test_rm_file)
    )
    round_trip_service.handwriting_service.convert_to_iink_format.assert_called_once()
    round_trip_service.handwriting_service.recognize_handwriting.assert_called_once()
    round_trip_service.handwriting_service.export_content.assert_called_once_with(
        "test_content_id", "text"
    )
    round_trip_service.document_service.create_rmdoc_from_content.assert_called_once()
    round_trip_service.remarkable_service.upload.assert_called_once()


def test_round_trip_error_handling(round_trip_service):
    """Test error handling in the round-trip service."""
    # Configure mock to simulate failure
    round_trip_service.handwriting_service.extract_strokes.return_value = []

    # Process a non-existent file
    success, result = round_trip_service.process_handwritten_query("nonexistent.rm")

    # Verify failure is handled
    assert success is False
    assert "error" in result
    assert "No strokes found" in result["error"]


def test_round_trip_recognition_failure(tmp_path, round_trip_service):
    """Test handling of recognition failure."""
    # Create a test file
    test_rm_file = tmp_path / "test_query.rm"
    with open(test_rm_file, "wb") as f:
        f.write(b"Test RM file content")

    # Configure mock to simulate recognition failure
    round_trip_service.handwriting_service.recognize_handwriting.return_value = {
        "success": False,
        "error": "Recognition API error",
    }

    # Process the query
    success, result = round_trip_service.process_handwritten_query(str(test_rm_file))

    # Verify failure is handled
    assert success is False
    assert "error" in result
    assert "Recognition failed" in result["error"]


def test_round_trip_export_failure(tmp_path, round_trip_service):
    """Test handling of export failure."""
    # Create a test file
    test_rm_file = tmp_path / "test_query.rm"
    with open(test_rm_file, "wb") as f:
        f.write(b"Test RM file content")

    # Configure mock to simulate export failure
    round_trip_service.handwriting_service.export_content.return_value = {
        "success": False,
        "error": "Export API error",
    }

    # Process the query
    success, result = round_trip_service.process_handwritten_query(str(test_rm_file))

    # Verify failure is handled
    assert success is False
    assert "error" in result
    assert "Export failed" in result["error"]


def test_round_trip_document_creation_failure(tmp_path, round_trip_service):
    """Test handling of document creation failure."""
    # Create a test file
    test_rm_file = tmp_path / "test_query.rm"
    with open(test_rm_file, "wb") as f:
        f.write(b"Test RM file content")

    # Configure mock to simulate document creation failure
    round_trip_service.document_service.create_rmdoc_from_content.return_value = None

    # Process the query
    success, result = round_trip_service.process_handwritten_query(str(test_rm_file))

    # Verify failure is handled
    assert success is False
    assert "error" in result
    assert "Failed to create response document" in result["error"]


def test_round_trip_upload_failure(tmp_path, round_trip_service):
    """Test handling of upload failure."""
    # Create a test file
    test_rm_file = tmp_path / "test_query.rm"
    with open(test_rm_file, "wb") as f:
        f.write(b"Test RM file content")

    # Configure mock to simulate upload failure
    round_trip_service.remarkable_service.upload.return_value = (False, "Upload error")

    # Process the query
    success, result = round_trip_service.process_handwritten_query(str(test_rm_file))

    # Verify failure is handled
    assert success is False
    assert "error" in result
    assert "Upload failed" in result["error"]

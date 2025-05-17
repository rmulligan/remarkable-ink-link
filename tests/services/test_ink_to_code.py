#!/usr/bin/env python
"""Tests for the Ink-to-Code Service."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from inklink.services.ink_to_code_service import InkToCodeService


class TestInkToCodeService:
    """Test suite for InkToCodeService."""

    @pytest.fixture
    def mock_handwriting_service(self):
        """Create a mock enhanced handwriting service."""
        mock = Mock()
        mock.process_ink_with_routing.return_value = {
            "success": True,
            "text": "def hello():\n    print('world')",
            "routing": {
                "is_code_content": True,
                "suggested_actions": ["generate_code"],
                "confidence": 0.9,
            },
            "code_detection": {
                "is_code": True,
                "confidence": 0.9,
                "tags": ["code"],
                "language_hints": ["python"],
            },
            "service_results": {
                "generate_code": {
                    "success": True,
                    "code": "def hello():\n    print('world')",
                    "language": "python",
                    "explanation": "A simple hello world function",
                }
            },
        }
        return mock

    @pytest.fixture
    def mock_llm_manager(self):
        """Create a mock LLM service manager."""
        mock = Mock()
        mock.route_task.return_value = {
            "success": True,
            "code": "def hello():\n    print('world')",
            "language": "python",
            "explanation": "A simple hello world function",
        }
        return mock

    @pytest.fixture
    def mock_document_service(self):
        """Create a mock document service."""
        mock = Mock()
        mock.create_rmdoc_from_content.return_value = "/tmp/test.rm"
        return mock

    @pytest.fixture
    def mock_remarkable_service(self):
        """Create a mock remarkable service."""
        mock = Mock()
        mock.upload.return_value = (True, "Upload successful")
        return mock

    @pytest.fixture
    def ink_to_code_service(
        self,
        mock_handwriting_service,
        mock_llm_manager,
        mock_document_service,
        mock_remarkable_service,
    ):
        """Create an ink-to-code service with mocked dependencies."""
        return InkToCodeService(
            handwriting_service=mock_handwriting_service,
            llm_manager=mock_llm_manager,
            document_service=mock_document_service,
            remarkable_service=mock_remarkable_service,
            enable_syntax_highlighting=False,  # Disable for testing
        )

    def test_process_code_query_success(self, ink_to_code_service):
        """Test successful code query processing."""
        success, result = ink_to_code_service.process_code_query("/path/to/file.rm")

        assert success is True
        assert "recognized_text" in result
        assert "generated_code" in result
        assert "document_path" in result
        assert "upload_message" in result
        assert result["generated_code"] == "def hello():\n    print('world')"

    def test_process_code_query_no_code_detected(
        self, ink_to_code_service, mock_handwriting_service
    ):
        """Test processing when no code is detected."""
        # Mock no code detection
        mock_handwriting_service.process_ink_with_routing.return_value = {
            "success": True,
            "text": "This is just regular text",
            "routing": {
                "is_code_content": False,
                "suggested_actions": [],
                "confidence": 0.1,
            },
        }

        success, result = ink_to_code_service.process_code_query("/path/to/file.rm")

        assert success is False
        assert result["error"] == "No code content detected in handwriting"

    def test_process_code_query_recognition_failure(
        self, ink_to_code_service, mock_handwriting_service
    ):
        """Test handling of recognition failure."""
        mock_handwriting_service.process_ink_with_routing.return_value = {
            "success": False,
            "error": "Recognition failed",
        }

        success, result = ink_to_code_service.process_code_query("/path/to/file.rm")

        assert success is False
        assert "Recognition failed" in result["error"]

    def test_generate_code_from_recognition(self, ink_to_code_service):
        """Test code generation from recognition results."""
        recognition_result = {
            "text": "function sort(array)",
            "code_blocks": [
                {
                    "cleaned_content": "function sort(array):\n    return sorted(array)",
                    "language": "python",
                }
            ],
        }

        result = ink_to_code_service._generate_code_from_recognition(recognition_result)

        assert result["success"] is True
        assert result["code"] == "def hello():\n    print('world')"
        assert result["language"] == "python"

    def test_format_code_response(self, ink_to_code_service):
        """Test formatting of code response."""
        recognition_result = {
            "text": "Create a hello world function",
            "code_detection": {"confidence": 0.9, "tags": ["code", "python"]},
        }

        code_gen_result = {
            "code": "def hello():\n    print('Hello, World!')",
            "language": "python",
            "explanation": "This function prints a greeting",
        }

        formatted = ink_to_code_service._format_code_response(
            recognition_result, code_gen_result
        )

        assert formatted["title"] == "Code Generation Response"
        assert len(formatted["structured_content"]) > 3
        assert formatted["metadata"]["detected_language"] == "python"
        assert formatted["metadata"]["code_confidence"] == 0.9

    def test_create_code_document(self, ink_to_code_service):
        """Test document creation."""
        content = {
            "title": "Test Code",
            "structured_content": [
                {"type": "h1", "content": "Code"},
                {"type": "code", "content": "print('test')"},
            ],
        }

        path = ink_to_code_service._create_code_document(content)

        assert path == "/tmp/test.rm"

    def test_process_notebook_pages(self, ink_to_code_service):
        """Test processing multiple notebook pages."""
        page_files = ["/page1.rm", "/page2.rm", "/page3.rm"]

        results = ink_to_code_service.process_notebook_pages(page_files, "notebook-123")

        assert "pages" in results
        assert "code_pages" in results
        assert "total_generated" in results
        assert len(results["pages"]) == 3

    def test_create_combined_response(self, ink_to_code_service):
        """Test creating a combined response document."""
        pages_results = [
            {
                "page_index": 0,
                "result": {
                    "recognized_text": "function one",
                    "generated_code": "def one(): pass",
                },
            },
            {
                "page_index": 1,
                "result": {
                    "recognized_text": "function two",
                    "generated_code": "def two(): pass",
                },
            },
        ]

        path = ink_to_code_service.create_combined_response(
            pages_results, "My Notebook"
        )

        assert path == "/tmp/test.rm"

    def test_process_code_query_with_session_id(self, ink_to_code_service):
        """Test processing with session ID for context."""
        success, result = ink_to_code_service.process_code_query(
            "/path/to/file.rm", session_id="session-123"
        )

        assert success is True
        # Verify session ID was passed through
        ink_to_code_service.handwriting_service.process_ink_with_routing.assert_called_with(
            file_path="/path/to/file.rm", session_id="session-123"
        )

    @patch("inklink.services.ink_to_code_service.os.rename")
    @patch("inklink.services.ink_to_code_service.os.path.exists")
    def test_create_code_document_with_rename(
        self, mock_exists, mock_rename, ink_to_code_service, mock_document_service
    ):
        """Test document creation with file renaming."""
        mock_exists.return_value = True
        mock_document_service.create_rmdoc_from_content.return_value = (
            "/tmp/original.rm"
        )

        content = {"title": "Test", "structured_content": []}
        path = ink_to_code_service._create_code_document(content)

        # Should have renamed the file
        mock_rename.assert_called_once()
        assert path is not None
        assert "code_response_" in path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

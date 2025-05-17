#!/usr/bin/env python
"""Tests for the Code Recognition Service."""

import pytest
from unittest.mock import Mock, patch

from inklink.services.code_recognition_service import CodeRecognitionService
from inklink.services.interfaces import IHandwritingRecognitionService


class TestCodeRecognitionService:
    """Test suite for CodeRecognitionService."""

    @pytest.fixture
    def mock_handwriting_service(self):
        """Create a mock handwriting service."""
        return Mock(spec=IHandwritingRecognitionService)

    @pytest.fixture
    def code_recognition_service(self, mock_handwriting_service):
        """Create a code recognition service with mocked dependencies."""
        return CodeRecognitionService(
            handwriting_service=mock_handwriting_service, enable_auto_detection=True
        )

    def test_detect_code_content_with_explicit_tag(self, code_recognition_service):
        """Test code detection with explicit #code tag."""
        text = "Here's my function #code\ndef hello():\n    print('Hello')"

        result = code_recognition_service.detect_code_content(text)

        assert result["is_code"] is True
        assert result["confidence"] == 1.0
        assert "code" in result["tags"]
        assert len(result["blocks"]) > 0

    def test_detect_code_content_with_pseudocode_tag(self, code_recognition_service):
        """Test code detection with #pseudocode tag."""
        text = (
            "#pseudocode\nfunction sort(array):\n    for i in array:\n        process i"
        )

        result = code_recognition_service.detect_code_content(text)

        assert result["is_code"] is True
        assert result["confidence"] == 1.0
        assert "pseudocode" in result["tags"]

    def test_detect_code_content_auto_detection(self, code_recognition_service):
        """Test automatic code detection without tags."""
        text = "def calculate(x, y):\n    return x + y"

        result = code_recognition_service.detect_code_content(text)

        assert result["is_code"] is True
        assert result["confidence"] > 0.5
        assert "function" in result["patterns"]

    def test_detect_code_content_no_code(self, code_recognition_service):
        """Test with text that doesn't contain code."""
        text = "This is just regular text without any code patterns."

        result = code_recognition_service.detect_code_content(text)

        assert result["is_code"] is False
        assert result["confidence"] == 0.0
        assert len(result["blocks"]) == 0

    def test_language_detection_python(self, code_recognition_service):
        """Test Python language detection."""
        text = "def main():\n    print('Hello')\n    return 0"

        result = code_recognition_service.detect_code_content(text)

        assert "python" in result["language_hints"]

    def test_language_detection_javascript(self, code_recognition_service):
        """Test JavaScript language detection."""
        text = "const greeting = () => {\n    console.log('Hello');\n};"

        result = code_recognition_service.detect_code_content(text)

        assert "javascript" in result["language_hints"]

    def test_extract_code_blocks(self, code_recognition_service):
        """Test extraction of code blocks."""
        text = """
        Here's the first function:

        def first():
            return 1

        And here's the second:

        def second():
            return 2
        """

        blocks = code_recognition_service._extract_code_blocks(text)

        assert len(blocks) >= 2
        assert any("first" in block["content"] for block in blocks)
        assert any("second" in block["content"] for block in blocks)

    def test_recognize_with_code_detection(
        self, code_recognition_service, mock_handwriting_service
    ):
        """Test integrated recognition with code detection."""
        # Mock handwriting recognition response
        mock_handwriting_service.recognize_handwriting.return_value = {
            "success": True,
            "text": "def hello():\n    print('world')",
        }

        result = code_recognition_service.recognize_with_code_detection(
            "/path/to/image.png"
        )

        assert result["success"] is True
        assert "code_detection" in result
        assert result["code_detection"]["is_code"] is True

        # Should have called handwriting recognition
        mock_handwriting_service.recognize_handwriting.assert_called_once()

    def test_process_code_page(
        self, code_recognition_service, mock_handwriting_service
    ):
        """Test processing a code page."""
        # Mock the recognition result
        mock_handwriting_service.recognize_handwriting.return_value = {
            "success": True,
            "text": "#code\ndef factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)",
        }

        result = code_recognition_service.process_code_page("/path/to/page.rm")

        assert result["success"] is True
        assert "code_blocks" in result
        assert result["requires_code_generation"] is True

        # Check the processed blocks
        blocks = result["code_blocks"]
        assert len(blocks) > 0
        assert blocks[0]["needs_generation"] is True
        assert blocks[0]["type"] == "function"

    def test_clean_pseudocode(self, code_recognition_service):
        """Test pseudocode cleaning."""
        text = "#code\n  function  test():\n\t\tdo something\n    return result"

        cleaned = code_recognition_service._clean_pseudocode(text)

        # Should remove tags and standardize indentation
        assert "#code" not in cleaned
        assert "function test():" in cleaned
        assert "    do something" in cleaned
        assert "    return result" in cleaned

    def test_pattern_detection_algorithms(self, code_recognition_service):
        """Test detection of algorithm patterns."""
        text = """
        Algorithm: QuickSort
        Input: array of integers
        Output: sorted array

        Step 1: Choose pivot
        Step 2: Partition array
        Step 3: Recursively sort subarrays
        """

        result = code_recognition_service.detect_code_content(text)

        assert result["is_code"] is True
        assert "algorithm" in result["patterns"]
        assert len(result["blocks"]) > 0
        assert result["blocks"][0]["type"] == "algorithm"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Unit tests for the Google Docs Service."""

import os
import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any, List, Tuple

from inklink.services.google_docs_service import GoogleDocsService
from inklink.adapters.google_adapter import GoogleAPIAdapter


class MockGoogleAPIAdapter:
    """Mock implementation of GoogleAPIAdapter for testing."""
    
    def __init__(self, *args, **kwargs):
        """Initialize with test data."""
        self.extract_doc_id_calls = []
        self.get_metadata_calls = []
        self.export_html_calls = []
        self.export_pdf_calls = []
        self.export_docx_calls = []
        self.list_docs_calls = []
        
        # Default test data
        self.test_doc_id = "test_doc_123"
        self.test_metadata = {
            "name": "Test Document",
            "mimeType": "application/vnd.google-apps.document",
            "createdTime": "2023-01-01T00:00:00.000Z",
            "modifiedTime": "2023-01-02T00:00:00.000Z",
            "owners": [{"displayName": "Test User"}],
            "size": "12345"
        }
        self.test_html = """
        <html>
          <head><title>Test Document</title></head>
          <body>
            <h1>Test Heading</h1>
            <p>Test paragraph with <b>bold text</b>.</p>
            <ul>
              <li>Item 1</li>
              <li>Item 2</li>
            </ul>
            <img src="https://example.com/image.jpg" alt="Test Image">
          </body>
        </html>
        """
        self.test_docs_list = [
            {
                "id": "doc1",
                "name": "Document 1",
                "createdTime": "2023-01-01T00:00:00.000Z",
                "modifiedTime": "2023-01-02T00:00:00.000Z",
                "webViewLink": "https://docs.google.com/document/d/doc1"
            },
            {
                "id": "doc2",
                "name": "Document 2",
                "createdTime": "2023-01-03T00:00:00.000Z",
                "modifiedTime": "2023-01-04T00:00:00.000Z",
                "webViewLink": "https://docs.google.com/document/d/doc2"
            }
        ]
        
        # Configure error modes
        self.should_fail_metadata = False
        self.should_fail_html_export = False
        self.should_fail_pdf_export = False
        self.should_fail_docx_export = False
        self.should_fail_list_docs = False
    
    def extract_doc_id(self, url_or_id: str) -> str:
        """Mock implementation of extract_doc_id."""
        self.extract_doc_id_calls.append(url_or_id)
        
        # Match the specific URL patterns used in tests
        if "docs.google.com/document/d/" in url_or_id:
            # Standard URL format
            if "/d/abc123" in url_or_id:
                return "abc123"
            if "/d/e/abc123" in url_or_id:
                return "abc123"
            if "/d/test_doc_123" in url_or_id:
                return "test_doc_123"
                
        # For invalid URLs in our test cases, return the original
        for bad_url in [
            "https://evil.docs.google.com/document/d/abc123/edit",
            "https://docs.google.com.evil.com/document/d/abc123/edit",
            "https://docs.google.com/spreadsheets/d/abc123/edit",
            "just-a-string",
            "https://example.com/doc",
        ]:
            if url_or_id == bad_url:
                return url_or_id
        
        # Default behavior for anything else
        return url_or_id
    
    def get_document_metadata(self, doc_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Mock implementation of get_document_metadata."""
        self.get_metadata_calls.append(doc_id)
        
        if self.should_fail_metadata:
            return False, {"error": "Failed to fetch metadata"}
            
        return True, self.test_metadata
        
    def export_doc_as_html(self, doc_id: str) -> Tuple[bool, str]:
        """Mock implementation of export_doc_as_html."""
        self.export_html_calls.append(doc_id)
        
        if self.should_fail_html_export:
            return False, "Failed to export as HTML"
            
        return True, self.test_html
    
    def export_doc_as_pdf(self, doc_id: str, output_path: str) -> bool:
        """Mock implementation of export_doc_as_pdf."""
        self.export_pdf_calls.append((doc_id, output_path))
        
        if self.should_fail_pdf_export:
            return False
            
        # Just create an empty file for testing
        with open(output_path, 'w') as f:
            f.write("PDF CONTENT")
            
        return True
    
    def export_doc_as_docx(self, doc_id: str, output_path: str) -> bool:
        """Mock implementation of export_doc_as_docx."""
        self.export_docx_calls.append((doc_id, output_path))
        
        if self.should_fail_docx_export:
            return False
            
        # Just create an empty file for testing
        with open(output_path, 'w') as f:
            f.write("DOCX CONTENT")
            
        return True
    
    def list_documents(self, max_results: int = 10) -> Tuple[bool, List[Dict[str, Any]]]:
        """Mock implementation of list_documents."""
        self.list_docs_calls.append(max_results)
        
        if self.should_fail_list_docs:
            return False, []
            
        return True, self.test_docs_list[:max_results]


@pytest.fixture
def mock_adapter():
    """Provide a mock GoogleAPIAdapter."""
    return MockGoogleAPIAdapter()


@pytest.fixture
def google_docs_service(mock_adapter):
    """Create a GoogleDocsService with a mock adapter."""
    return GoogleDocsService(google_adapter=mock_adapter)


@pytest.fixture
def temp_file_path(tmp_path):
    """Provide a temporary file path."""
    return str(tmp_path / "test_output_file")


def test_fetch_success(google_docs_service, mock_adapter):
    """Test successful document fetch and processing."""
    result = google_docs_service.fetch("https://docs.google.com/document/d/test_doc_123/edit")
    
    # Verify adapter methods were called
    assert mock_adapter.extract_doc_id_calls[-1] == "https://docs.google.com/document/d/test_doc_123/edit"
    assert mock_adapter.get_metadata_calls[-1] == "test_doc_123"
    assert mock_adapter.export_html_calls[-1] == "test_doc_123"
    
    # Verify response structure
    assert result["title"] == "Test Document"
    assert "structured_content" in result
    assert "images" in result
    
    # Check content types
    content_types = [item["type"] for item in result["structured_content"]]
    assert "h1" in content_types
    assert "paragraph" in content_types
    assert "bullet" in content_types
    
    # Check image extraction
    assert len(result["images"]) > 0
    assert result["images"][0]["url"] == "https://example.com/image.jpg"


def test_fetch_metadata_failure(google_docs_service, mock_adapter):
    """Test handling of metadata fetch failure."""
    mock_adapter.should_fail_metadata = True
    result = google_docs_service.fetch("doc123")
    
    # Verify error response
    assert "structured_content" in result
    assert len(result["structured_content"]) == 1
    assert "Could not fetch Google Docs document" in result["structured_content"][0]["content"]
    assert "Failed to get document metadata" in result["structured_content"][0]["content"]


def test_fetch_html_export_failure(google_docs_service, mock_adapter):
    """Test handling of HTML export failure."""
    mock_adapter.should_fail_html_export = True
    result = google_docs_service.fetch("doc123")
    
    # Verify error response
    assert "structured_content" in result
    assert len(result["structured_content"]) == 1
    assert "Could not fetch Google Docs document" in result["structured_content"][0]["content"]
    assert "Failed to export document" in result["structured_content"][0]["content"]


def test_fetch_as_pdf_success(google_docs_service, mock_adapter, temp_file_path):
    """Test successful PDF export."""
    success = google_docs_service.fetch_as_pdf("doc123", temp_file_path)
    
    assert success is True
    assert os.path.exists(temp_file_path)
    assert mock_adapter.export_pdf_calls[-1] == ("doc123", temp_file_path)


def test_fetch_as_pdf_failure(google_docs_service, mock_adapter, temp_file_path):
    """Test handling of PDF export failure."""
    mock_adapter.should_fail_pdf_export = True
    success = google_docs_service.fetch_as_pdf("doc123", temp_file_path)
    
    assert success is False
    assert not os.path.exists(temp_file_path)


def test_fetch_as_docx_success(google_docs_service, mock_adapter, temp_file_path):
    """Test successful DOCX export."""
    success = google_docs_service.fetch_as_docx("doc123", temp_file_path)
    
    assert success is True
    assert os.path.exists(temp_file_path)
    assert mock_adapter.export_docx_calls[-1] == ("doc123", temp_file_path)


def test_fetch_as_docx_failure(google_docs_service, mock_adapter, temp_file_path):
    """Test handling of DOCX export failure."""
    mock_adapter.should_fail_docx_export = True
    success = google_docs_service.fetch_as_docx("doc123", temp_file_path)
    
    assert success is False
    assert not os.path.exists(temp_file_path)


def test_list_documents_success(google_docs_service, mock_adapter):
    """Test successful document listing."""
    docs = google_docs_service.list_documents(max_results=2)
    
    assert len(docs) == 2
    assert docs[0]["name"] == "Document 1"
    assert docs[1]["name"] == "Document 2"
    assert mock_adapter.list_docs_calls[-1] == 2


def test_list_documents_failure(google_docs_service, mock_adapter):
    """Test handling of document listing failure."""
    mock_adapter.should_fail_list_docs = True
    docs = google_docs_service.list_documents()
    
    assert docs == []


def test_error_response_structure():
    """Test the structure of error responses."""
    # Create a new service with a patched adapter for this specific test
    mock_adapter = MockGoogleAPIAdapter()
    service = GoogleDocsService(google_adapter=mock_adapter)
    
    # Replace the adapter's extract_doc_id method to raise an exception
    def raise_error(*args, **kwargs):
        raise Exception("Test error")
        
    # Store the original method to restore after test
    original_method = mock_adapter.extract_doc_id
    mock_adapter.extract_doc_id = raise_error
    
    try:
        result = service.fetch("doc123")
        
        # Verify error response structure
        assert result["title"] == "doc123"  # Should use the input as title
        assert "structured_content" in result
        assert len(result["structured_content"]) == 1
        assert "Could not fetch Google Docs document" in result["structured_content"][0]["content"]
        assert "Test error" in result["structured_content"][0]["content"]
        assert "images" in result
        assert result["images"] == []
    finally:
        # Restore the original method
        mock_adapter.extract_doc_id = original_method
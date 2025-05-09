"""Google Docs integration service."""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple

from inklink.services.interfaces import IGoogleDocsService
from inklink.adapters.google_adapter import GoogleAPIAdapter
from inklink.utils import (
    extract_structured_content,
    validate_and_fix_content,
)

logger = logging.getLogger(__name__)


class GoogleDocsService(IGoogleDocsService):
    """Service to fetch and convert Google Docs documents."""

    def __init__(
        self, 
        credentials_path: Optional[str] = None, 
        token_path: Optional[str] = None,
        google_adapter: Optional[GoogleAPIAdapter] = None
    ):
        """
        Initialize Google Docs service.

        Args:
            credentials_path: Path to OAuth2 client secrets JSON
            token_path: Path to store user credentials
            google_adapter: Optional pre-configured Google API adapter
        """
        # Use provided adapter or create a new one
        self.adapter = google_adapter or GoogleAPIAdapter(
            credentials_path=credentials_path,
            token_path=token_path,
            readonly=True  # Use read-only scope for safety
        )

    def fetch(self, url_or_id: str) -> Dict[str, Any]:
        """
        Fetch a Google Docs document by URL or ID.
        
        Exports the document as HTML and processes it into a structured format
        suitable for document generation.

        Args:
            url_or_id: Google Docs URL or document ID

        Returns:
            Dict with keys: title, structured_content, images
        """
        try:
            # Extract document ID
            doc_id = self.adapter.extract_doc_id(url_or_id)
            logger.debug(f"Extracted Google Docs ID: {doc_id}")
            
            # Get document metadata
            success, metadata = self.adapter.get_document_metadata(doc_id)
            if not success:
                raise ValueError(f"Failed to get document metadata: {metadata}")
                
            # Get document title from metadata
            doc_title = metadata.get("name", "Google Doc")
            logger.debug(f"Document title: {doc_title}")
            
            # Export document as HTML
            success, html_content = self.adapter.export_doc_as_html(doc_id)
            if not success:
                raise ValueError(f"Failed to export document: {html_content}")
                
            # Process HTML into structured content
            content = extract_structured_content(html_content, url_or_id)
            
            # Use document title from metadata
            content["title"] = doc_title
            
            # Validate and ensure content structure is complete
            return validate_and_fix_content(content, url_or_id)

        except Exception as e:
            logger.error(f"Failed to fetch Google Docs document: {e}")
            return self._build_error_response(url_or_id, str(e))
    
    def fetch_as_pdf(self, url_or_id: str, output_path: str) -> bool:
        """
        Fetch a Google Docs document as PDF.
        
        Args:
            url_or_id: Google Docs URL or document ID
            output_path: Path to save the PDF file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract document ID
            doc_id = self.adapter.extract_doc_id(url_or_id)
            
            # Export document as PDF
            return self.adapter.export_doc_as_pdf(doc_id, output_path)
            
        except Exception as e:
            logger.error(f"Failed to fetch Google Docs document as PDF: {e}")
            return False
    
    def fetch_as_docx(self, url_or_id: str, output_path: str) -> bool:
        """
        Fetch a Google Docs document as DOCX.
        
        Args:
            url_or_id: Google Docs URL or document ID
            output_path: Path to save the DOCX file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract document ID
            doc_id = self.adapter.extract_doc_id(url_or_id)
            
            # Export document as DOCX
            return self.adapter.export_doc_as_docx(doc_id, output_path)
            
        except Exception as e:
            logger.error(f"Failed to fetch Google Docs document as DOCX: {e}")
            return False
    
    def list_documents(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        List Google Docs documents.
        
        Args:
            max_results: Maximum number of results to return
            
        Returns:
            List of document metadata dictionaries
        """
        try:
            success, docs = self.adapter.list_documents(max_results=max_results)
            if not success:
                logger.error(f"Failed to list documents: {docs}")
                return []
                
            return docs
            
        except Exception as e:
            logger.error(f"Failed to list Google Docs documents: {e}")
            return []
    
    def _build_error_response(self, url_or_id: str, error_message: str) -> Dict[str, Any]:
        """
        Build a standardized error response.
        
        Args:
            url_or_id: URL or document ID
            error_message: Error message
            
        Returns:
            Structured content dictionary with error information
        """
        return {
            "title": url_or_id,
            "structured_content": [
                {
                    "type": "paragraph",
                    "content": f"Could not fetch Google Docs document {url_or_id}: {error_message}",
                }
            ],
            "images": [],
        }
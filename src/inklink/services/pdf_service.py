"""PDF processing service for Pi Share Receiver."""

import os
import requests
import PyPDF2
from urllib.parse import urlparse
from typing import Dict, Optional, Any
import logging

# Configure logging
logger = logging.getLogger(__name__)

class PDFService:
    """Handles PDF processing operations."""
    
    def __init__(self, temp_dir: str, extract_dir: str):
        """Initialize with directories for temporary and extracted files.
        
        Args:
            temp_dir: Directory for temporary PDF storage
            extract_dir: Directory for PDF content extraction
        """
        self.temp_dir = temp_dir
        self.extract_dir = extract_dir
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(extract_dir, exist_ok=True)

    def is_pdf_url(self, url: str) -> bool:
        """Check if URL points to a PDF file.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is PDF, False otherwise
        """
        # Simple extension check
        if url.lower().endswith('.pdf'):
            return True
        
        # Check content type from headers
        try:
            headers = requests.head(url, allow_redirects=True, timeout=10).headers
            content_type = headers.get('Content-Type', '').lower()
            return 'application/pdf' in content_type
        except Exception as e:
            logger.error(f"Error checking if URL is PDF: {e}")
            return False

    def process_pdf(self, url: str, qr_path: str) -> Optional[Dict[str, Any]]:
        """Download and process PDF from URL.
        
        Args:
            url: The PDF URL to download
            qr_path: Path to QR code image
            
        Returns:
            Dict containing PDF info or None if failed
        """
        try:
            logger.info(f"Processing PDF URL: {url}")
            
            # Create filename for PDF
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename or not filename.lower().endswith('.pdf'):
                filename = f"document_{hash(url)}.pdf"
                
            pdf_path = os.path.join(self.temp_dir, filename)
            
            # Download PDF
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Extract title from PDF metadata or filename
            title = self._extract_pdf_title(pdf_path, url)
            
            return {
                "title": title,
                "pdf_path": pdf_path
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF URL: {e}")
            return None

    def _extract_pdf_title(self, pdf_path: str, url: str) -> str:
        """Extract title from PDF metadata or create from URL.
        
        Args:
            pdf_path: Path to downloaded PDF file
            url: Original URL
            
        Returns:
            Title string
        """
        try:
            # Try to get title from PDF metadata
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                if reader.metadata and reader.metadata.title:
                    return reader.metadata.title
                
            # Fall back to filename from URL
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if filename.lower().endswith('.pdf'):
                filename = filename[:-4]  # Remove .pdf extension
                
            # Format filename as title
            title = filename.replace('_', ' ').replace('-', ' ')
            return title or "PDF Document"
                
        except Exception as e:
            logger.error(f"Error extracting PDF title: {e}")
            return "PDF Document"
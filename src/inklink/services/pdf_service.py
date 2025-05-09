"""PDF processing service for InkLink."""

import os
from urllib.parse import urlparse
from typing import Dict, Optional, Any, List, Tuple
import logging

from inklink.services.interfaces import IPDFService
from inklink.adapters.pdf_adapter import PDFAdapter
from inklink.adapters.http_adapter import HTTPAdapter

# Configure logging
logger = logging.getLogger(__name__)


class PDFService(IPDFService):
    """Handles PDF processing operations."""

    def __init__(
        self, 
        temp_dir: str, 
        extract_dir: str,
        pdf_adapter: Optional[PDFAdapter] = None,
        http_adapter: Optional[HTTPAdapter] = None
    ):
        """
        Initialize with directories for temporary and extracted files.

        Args:
            temp_dir: Directory for temporary PDF storage
            extract_dir: Directory for PDF content extraction
            pdf_adapter: Optional PDF adapter for PDF operations
            http_adapter: Optional HTTP adapter for network operations
        """
        self.temp_dir = temp_dir
        self.extract_dir = extract_dir
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(extract_dir, exist_ok=True)
        
        # Create adapters if not provided
        self.pdf_adapter = pdf_adapter or PDFAdapter(temp_dir=temp_dir)
        self.http_adapter = http_adapter or HTTPAdapter(timeout=30)

    def is_pdf_url(self, url: str) -> bool:
        """
        Check if URL points to a PDF file.

        Args:
            url: URL to check

        Returns:
            True if URL is PDF, False otherwise
        """
        # Simple extension check
        if url.lower().endswith(".pdf"):
            return True

        # Check content type from headers
        try:
            success, headers = self.http_adapter.get(
                url, 
                headers={"Range": "bytes=0-0"}  # Only request header, not content
            )
            
            if not success:
                return False
                
            # If the response is a dict (JSON), check Content-Type header
            if isinstance(headers, dict) and "Content-Type" in headers:
                content_type = headers.get("Content-Type", "").lower()
                return "application/pdf" in content_type
                
            return False
        except Exception as e:
            logger.error(f"Error checking if URL is PDF: {e}")
            return False

    def process_pdf(self, url: str, qr_path: str) -> Optional[Dict[str, Any]]:
        """
        Download and process PDF from URL.

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
            if not filename or not filename.lower().endswith(".pdf"):
                filename = f"document_{hash(url)}.pdf"

            pdf_path = os.path.join(self.temp_dir, filename)

            # Download PDF using HTTP adapter
            logger.debug(f"Downloading PDF from {url} to {pdf_path}")
            download_success = self.http_adapter.download_file(url, pdf_path)
            
            if not download_success:
                logger.error(f"Failed to download PDF from {url}")
                return None

            # Extract title from PDF metadata or filename using PDF adapter
            title = self.pdf_adapter.extract_title(pdf_path, url)
            logger.debug(f"Extracted PDF title: {title}")

            # For now, we only support 'outline' mode (vector processing)
            # If raster mode is needed, it can be re-enabled later
            
            # Return PDF information
            return {"title": title, "pdf_path": pdf_path}

        except Exception as e:
            logger.error(f"Error processing PDF URL: {e}", exc_info=True)
            return None

    def add_watermark(self, pdf_path: str, watermark_path: str, output_path: str) -> bool:
        """
        Add watermark (like a QR code) to each page of a PDF.
        
        Args:
            pdf_path: Path to PDF file
            watermark_path: Path to watermark PDF
            output_path: Path to save watermarked PDF
            
        Returns:
            True if successful, False otherwise
        """
        return self.pdf_adapter.add_watermark(pdf_path, watermark_path, output_path)

    def extract_text(self, pdf_path: str) -> List[str]:
        """
        Extract text from each page of a PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of extracted text strings, one per page
        """
        return self.pdf_adapter.extract_text(pdf_path)

    def convert_to_images(self, 
                       pdf_path: str,
                       output_dir: Optional[str] = None) -> List[str]:
        """
        Convert PDF to images.
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save images (defaults to extract_dir)
            
        Returns:
            List of paths to generated images
        """
        return self.pdf_adapter.convert_to_images(
            pdf_path,
            output_dir=output_dir or self.extract_dir
        )

    def generate_index_notebook(
        self, pages: List[Dict[str, Any]], output_path: str, graph_title: str = "Index Node Graph"
    ) -> bool:
        """
        Generate an index notebook as a PDF containing a node graph with cross-references.

        Args:
            pages: List of dicts, each with keys:
                - 'title': Title of the handwritten page
                - 'summary': Short summary of the page
                - 'page_number': Page number in the notebook
                - 'device_location': Device-specific location or identifier
                - 'links': List of page numbers this page references (optional)
            output_path: Path to save the generated PDF
            graph_title: Title for the node graph

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert pages to nodes and edges format for the adapter
            nodes = []
            edges = []

            for page in pages:
                # Create node with all the page information
                node = {
                    'id': page['page_number'],
                    'label': f"{page['page_number']}: {page['title']}",
                    'title': page['title'],
                    'summary': page.get('summary', ''),
                    'device_location': page.get('device_location', '')
                }
                nodes.append(node)
                
                # Add edges for links
                if 'links' in page:
                    for link_to in page['links']:
                        edges.append((str(page['page_number']), str(link_to)))
            
            # Generate the PDF using the adapter
            return self.pdf_adapter.generate_graph_pdf(
                nodes=nodes,
                edges=edges,
                output_path=output_path,
                title=graph_title,
                include_table=True
            )
            
        except Exception as e:
            logger.error(f"Error generating index notebook: {e}", exc_info=True)
            return False
"""Document conversion service for InkLink.

This service converts web content to reMarkable-compatible documents
using a configurable set of content converters and renderers.
"""

import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

from inklink.config import CONFIG
from inklink.services.converters.html_converter import HTMLConverter
from inklink.services.converters.markdown_converter import MarkdownConverter
from inklink.services.converters.pdf_converter import PDFConverter
from inklink.services.interfaces import (
    IContentConverter,
    IDocumentRenderer,
    IDocumentService,
)
from inklink.services.renderers.hcl_renderer import HCLRenderer
from inklink.utils import ensure_drawj2d_available

logger = logging.getLogger(__name__)


class DocumentService(IDocumentService):
    """Creates reMarkable documents from web content using specialized converters."""

    def __init__(
        self, temp_dir: str, drawj2d_path: Optional[str] = None, pdf_service=None
    ):
        """
        Initialize with directories and paths.

        Args:
            temp_dir: Directory for temporary files
            drawj2d_path: Optional path to drawj2d executable
            pdf_service: Optional PDFService instance for index notebook updates
        """
        self.temp_dir = temp_dir
        self.drawj2d_path = drawj2d_path
        self.pdf_service = pdf_service  # Used for automated index notebook updates
        os.makedirs(temp_dir, exist_ok=True)

        # Check if drawj2d is available
        self.use_drawj2d = ensure_drawj2d_available()
        if not self.use_drawj2d:
            logger.error("drawj2d not available. Document conversion will fail.")
            if not drawj2d_path or not os.path.exists(drawj2d_path):
                logger.error(
                    "No drawj2d executable found. Document conversion will fail."
                )

        # Initialize converters
        self.converters = self._initialize_converters()

        # Initialize renderer
        self.hcl_renderer = HCLRenderer(self.temp_dir, self.drawj2d_path)

    def _initialize_converters(self) -> List[IContentConverter]:
        """Initialize the content converters."""
        return [
            MarkdownConverter(self.temp_dir),
            HTMLConverter(self.temp_dir),
            PDFConverter(self.temp_dir),
        ]

    def _get_converter_for_type(self, content_type: str) -> Optional[IContentConverter]:
        """Get the appropriate converter for the content type."""
        return next(
            (
                converter
                for converter in self.converters
                if converter.can_convert(content_type)
            ),
            None,
        )

    def create_rmdoc_from_content(
        self, url: str, qr_path: str, content: Dict[str, Any]
    ) -> Optional[str]:
        """
        Create reMarkable document from structured content, supporting cross-page links.

        Args:
            url: Source URL for reference
            qr_path: Path to QR code image
            content: Structured content dictionary. Supports both legacy and enhanced formats:
                - Legacy: {"structured_content": [ ... ]}
                - Enhanced: {"pages": [...], "cross_page_links": [...]}

        Returns:
            Path to generated .rm file or None if failed
        """
        try:
            # Ensure we have valid content
            if not content:
                content = {"title": f"Page from {url}", "structured_content": []}

            logger.info(f"Creating document for: {content.get('title', url)}")

            # Prepare content for converter
            converter_content = {
                "url": url,
                "qr_path": qr_path,
                "title": content.get("title", f"Page from {url}"),
                "pages": content.get("pages"),
                "structured_content": content.get("structured_content", []),
                "cross_page_links": content.get("cross_page_links", []),
                "raw_markdown": content.get("raw_markdown"),
                "use_drawj2d": self.use_drawj2d,
            }

            # Get the appropriate converter and convert content
            converter = self._get_converter_for_type("structured")
            if converter:
                result = converter.convert(converter_content, None)
                if result:
                    logger.info(
                        f"Successfully converted to reMarkable format: {result}"
                    )

                    # Update index notebook in background
                    self._update_index_notebook(content)

                    return result
                else:
                    logger.error("Conversion failed using primary converter")
                    # If primary converter fails, try legacy method
                    if self.use_drawj2d:
                        logger.info("Falling back to legacy conversion method...")
                        return self.create_rmdoc_legacy(url, qr_path, content)
                    else:
                        logger.error("No available conversion method.")
                        return None
            else:
                logger.error("No suitable converter found for structured content")
                return None

        except Exception as e:
            logger.error(f"Error creating document: {str(e)}")
            return None

    def create_rmdoc_from_html(
        self, url: str, qr_path: str, html_content: str, title: Optional[str] = None
    ) -> Optional[str]:
        """
        Create reMarkable document directly from HTML content.

        Args:
            url: Source URL for reference
            qr_path: Path to QR code image
            html_content: Raw HTML content
            title: Optional document title

        Returns:
            Path to generated .rm file or None if failed
        """
        if not self.use_drawj2d:
            logger.error("drawj2d not available, cannot convert HTML")
            return None

        try:
            # Prepare content for converter
            converter_content = {
                "url": url,
                "qr_path": qr_path,
                "html_content": html_content,
                "title": title or f"Page from {url}",
                "use_drawj2d": self.use_drawj2d,
            }

            # Get HTML converter and convert content
            converter = self._get_converter_for_type("html")
            if converter:
                result = converter.convert(converter_content, None)

                if result:
                    logger.info(
                        f"Successfully converted HTML to reMarkable format: {result}"
                    )
                    return result
                else:
                    logger.error("HTML conversion failed")
                    return None
            else:
                logger.error("No HTML converter found")
                return None

        except Exception as e:
            logger.error(f"Error converting HTML to document: {str(e)}")
            return None

    def create_pdf_rmdoc(
        self, pdf_path: str, title: str, qr_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Create reMarkable document from PDF file.

        Args:
            pdf_path: Path to PDF file
            title: Document title
            qr_path: Optional path to QR code image

        Returns:
            Path to generated .rm file or None if failed
        """
        try:
            # Prepare content for converter
            converter_content = {
                "pdf_path": pdf_path,
                "title": title,
                "qr_path": qr_path,
                "use_drawj2d": self.use_drawj2d,
            }

            # Get PDF converter and convert content
            converter = self._get_converter_for_type("pdf")
            if converter:
                result = converter.convert(converter_content, None)

                if result:
                    logger.info(
                        f"Successfully converted PDF to reMarkable format: {result}"
                    )
                    return result
                else:
                    logger.error("PDF conversion failed")
                    return None
            else:
                logger.error("No PDF converter found")
                return None

        except Exception as e:
            logger.error(f"Error converting PDF to document: {str(e)}")
            return None

    # Legacy methods preserved for compatibility

    def create_rmdoc_legacy(
        self, url: str, qr_path: str, content: Dict[str, Any]
    ) -> Optional[str]:
        """
        Legacy method to create reMarkable document using HCL and drawj2d.

        This is the standard method for drawj2d-based conversion.

        Args:
            url: Source URL
            qr_path: Path to QR code image
            content: Structured content dictionary

        Returns:
            Path to generated .rm file or None if failed
        """
        try:
            # Ensure drawj2d is available
            if not self.drawj2d_path or not os.path.exists(self.drawj2d_path):
                logger.error("drawj2d path not available for legacy conversion")
                return None

            # Create HCL file
            hcl_path = self.create_hcl(url, qr_path, content)
            if not hcl_path:
                logger.error("Failed to create HCL script")
                return None

            # Prepare content for renderer
            renderer_content = {"hcl_path": hcl_path, "url": url}

            # Render HCL to reMarkable format
            result = self.hcl_renderer.render(renderer_content, None)

            if result:
                logger.info(f"Legacy conversion successful: {result}")
                return result
            else:
                logger.error("Legacy conversion failed")
                return None

        except Exception as e:
            logger.error(f"Error in legacy document creation: {str(e)}")
            return None

    def create_hcl(
        self, url: str, qr_path: str, content: Dict[str, Any]
    ) -> Optional[str]:
        """
        Create HCL script from structured content (legacy method).

        Args:
            url: Source URL
            qr_path: Path to QR code image
            content: Structured content dictionary

        Returns:
            Path to generated HCL file or None if failed
        """
        # This method is preserved as-is for compatibility
        # In a real refactoring, this would be moved to an HCLConverter class
        # For now, we'll keep the original implementation to avoid breaking changes
        from inklink.utils.hcl_render import create_hcl_from_content

        return create_hcl_from_content(url, qr_path, content, self.temp_dir)

    def create_rmdoc(self, hcl_path: str, url: str) -> Optional[str]:
        """
        Convert HCL to Remarkable document.

        Args:
            hcl_path: Path to HCL script
            url: Source URL

        Returns:
            Path to generated .rm file or None if failed
        """
        try:
            # Prepare content for renderer
            renderer_content = {"hcl_path": hcl_path, "url": url}

            # Render HCL to reMarkable format
            return self.hcl_renderer.render(renderer_content, None)

        except Exception as e:
            logger.error(f"Error in create_rmdoc: {e}")
            return None

    def _update_index_notebook(self, content: Dict[str, Any]) -> None:
        """
        Regenerate the index notebook PDF after new content is processed.
        Runs in a background thread to avoid blocking user interactions.

        Args:
            content: Content data used to update the index
        """
        if self.pdf_service is None:
            return

        def update_index_notebook_thread():
            try:
                # Example: Gather all pages info for the index (customize as needed)
                # Here, we use a single-page list for demonstration; in production,
                # aggregate all notebook pages as required.
                pages = [
                    {
                        "title": content.get("title", "Untitled Document"),
                        "summary": content.get("summary", ""),
                        "page_number": 1,
                        "device_location": None,
                        "links": content.get("cross_page_links", []),
                    }
                ]
                output_path = os.path.join(self.temp_dir, "index_notebook.pdf")
                if self.pdf_service:
                    self.pdf_service.generate_index_notebook(
                        pages=pages,
                        output_path=output_path,
                        graph_title="Index Node Graph",
                    )
                logger.info(f"Index notebook PDF updated at {output_path}")
            except Exception as e:
                logger.error(f"Failed to update index notebook: {e}")

        threading.Thread(target=update_index_notebook_thread, daemon=True).start()

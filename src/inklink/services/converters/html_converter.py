"""HTML content converter for InkLink.

This module provides a converter that transforms HTML content
directly into reMarkable-compatible formats.
"""

import logging
import os
import tempfile
from typing import Any, Dict, Optional

from inklink.services.converters.base_converter import BaseConverter
from inklink.utils import convert_html_to_rm

logger = logging.getLogger(__name__)


class HTMLConverter(BaseConverter):
    """Converts HTML content directly to reMarkable format.

    Note: HTML-to-structured-content utilities are intentionally bypassed in this converter.
    We directly convert the HTML to remarkable format for better quality output.
    """

    def can_convert(self, content_type: str) -> bool:
        """Check if this converter can handle the given content type."""
        return content_type == "html"

    def convert(
        self, content: Dict[str, Any], output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Convert HTML content to reMarkable format.

        Args:
            content: Dictionary containing content and metadata
                    Should include:
                    - url: Source URL
                    - html_content: The raw HTML content
                    - title: Content title (optional)
            output_path: Optional explicit output path
        Returns:
            Path to generated .rm file or None if failed
        """
        try:
            url = content.get("url", "")
            html_content = content.get("html_content", "")
            title = content.get("title", f"Page from {url}")
            if not html_content:
                logger.error("No HTML content provided for conversion")
                return None
            # Generate temp HTML file
            with tempfile.NamedTemporaryFile(
                suffix=".html", dir=self.temp_dir, delete=False
            ) as temp_file:
                temp_html_path = temp_file.name
                temp_file.write(html_content.encode("utf-8"))
            # Convert HTML to reMarkable format
            success, result = convert_html_to_rm(html_path=temp_html_path, title=title)
            # Clean up temp file
            try:
                os.unlink(temp_html_path)
            except OSError:
                pass
            if success:
                logger.info(
                    f"Successfully converted HTML to reMarkable format: {result}"
                )
                return result
            else:
                logger.error(f"HTML conversion failed: {result}")
                return None
        except Exception as e:
            logger.error(f"Error converting HTML: {str(e)}")
            return None

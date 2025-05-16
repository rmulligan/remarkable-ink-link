"""Ink content converter for InkLink.

This module provides a converter that creates editable ink strokes from text content,
replacing the old approach of using drawj2d to create static text.
"""

import logging
import os
from typing import Any, Dict, Optional

from inklink.services.converters.base_converter import BaseConverter
from inklink.services.ink_generation_service import get_ink_generation_service
from inklink.utils import retry_operation

logger = logging.getLogger(__name__)


class InkConverter(BaseConverter):
    """Converts text content to editable ink strokes in reMarkable format."""

    def __init__(self, temp_dir: str):
        """Initialize with temporary directory.

        Args:
            temp_dir: Directory for temporary files
        """
        super().__init__(temp_dir)
        self.ink_service = get_ink_generation_service()

    @staticmethod
    def can_convert(content_type: str) -> bool:
        """Check if this converter can handle the given content type."""
        return content_type in ["text", "ink", "editable", "response"]

    def convert(
        self, content: Dict[str, Any], output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Convert text content to editable ink strokes in reMarkable format.

        Args:
            content: Dictionary containing:
                    - text: The text to convert to ink
                    - title: Document title (optional)
                    - url: Source URL (optional)
                    - append_to: Existing .rm file to append to (optional)
            output_path: Optional explicit output path

        Returns:
            Path to generated .rm file or None if failed
        """
        try:
            text = content.get("text", "")
            if not text:
                # Try to extract text from structured content
                structured_content = content.get("structured_content", [])
                for item in structured_content:
                    if item.get("type") == "markdown":
                        text = item.get("content", "")
                        break
                    if item.get("type") == "text":
                        text = item.get("text", "")
                        break

            if not text:
                logger.error("No text content to convert to ink")
                return None

            title = content.get("title", "Ink Document")
            url = content.get("url", "")
            append_to = content.get("append_to")

            # Add title to the document if provided
            if title and not append_to:
                text = f"{title}\n\n{text}"

            # Generate output path if not provided
            if not output_path:
                output_path = self._generate_temp_path("ink", url or title, "rm")

            # Create or append to .rm file
            if append_to and os.path.exists(append_to):
                # Append to existing file
                success = self.ink_service.append_text_to_rm_file(append_to, text)
                if success:
                    return append_to
                logger.error(f"Failed to append ink to {append_to}")
                return None
            else:
                # Create new file
                success = self.ink_service.create_rm_file_with_text(text, output_path)
                if success:
                    return output_path
                logger.error(f"Failed to create ink file at {output_path}")
                return None

        except Exception as e:
            logger.error(f"Error converting text to ink: {str(e)}")
            return None

    def convert_with_retry(
        self, content: Dict[str, Any], output_path: Optional[str] = None
    ) -> Optional[str]:
        """Convert with retry logic for robustness.

        Args:
            content: Content to convert
            output_path: Optional output path

        Returns:
            Path to generated file or None if failed
        """
        return retry_operation(
            self.convert,
            content,
            output_path,
            max_retries=2,
            operation_name="Ink conversion",
        )

"""Syntax highlighted ink content converter for InkLink.

This module provides a converter that creates syntax-highlighted code in reMarkable format,
using the drawj2d tool for colored text rendering.
"""

import logging
import os
import re
import time
from typing import Any, Dict, Optional

from inklink.services.converters.base_converter import BaseConverter
from inklink.services.drawj2d_service import Drawj2dService
from inklink.services.syntax_highlight_compiler_v2 import (
    CodeMetadata,
    Language,
    RenderOptions,
    SyntaxHighlightCompilerV2,
)
from inklink.services.syntax_layout import PageSize

logger = logging.getLogger(__name__)


class SyntaxHighlightedInkConverter(BaseConverter):
    """Converts code content to syntax-highlighted ink in reMarkable format."""

    def __init__(self, temp_dir: str):
        """Initialize with temporary directory.

        Args:
            temp_dir: Directory for temporary files
        """
        super().__init__(temp_dir)
        self.compiler = SyntaxHighlightCompilerV2()
        self.drawj2d_service = Drawj2dService(temp_dir)

    @staticmethod
    def can_convert(content_type: str) -> bool:
        """Check if this converter can handle the given content type."""
        return content_type in ["code", "syntax-highlighted"]

    def convert(
        self, content: Dict[str, Any], output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Convert code content to syntax-highlighted ink in reMarkable format.

        Args:
            content: Dictionary containing:
                    - code: The code to highlight
                    - language: Programming language (python, javascript, etc.)
                    - title: Document title (optional)
                    - filename: Source filename (optional)
                    - author: Author name (optional)
                    - page_size: PageSize enum (optional, defaults to REMARKABLE_2)
                    - show_line_numbers: Whether to show line numbers (optional, default True)
                    - show_metadata: Whether to show metadata header (optional, default True)
            output_path: Optional explicit output path

        Returns:
            Path to generated .rm file or None if failed
        """
        try:
            code = content.get("code", "")
            if not code:
                logger.error("No code content to convert")
                return None

            # Extract metadata
            language_str = content.get("language", "python").lower()
            title = content.get("title", "Code Document")
            filename = content.get("filename")
            author = content.get("author")

            # Map language string to Language enum
            language_map = {
                "python": Language.PYTHON,
                "py": Language.PYTHON,
                "javascript": Language.JAVASCRIPT,
                "js": Language.JAVASCRIPT,
                "java": Language.JAVA,
                "c": Language.C,
                "cpp": Language.CPP,
                "c++": Language.CPP,
                "go": Language.GO,
                "rust": Language.RUST,
                "ruby": Language.RUBY,
                "rb": Language.RUBY,
                "php": Language.PHP,
                "typescript": Language.TYPESCRIPT,
                "ts": Language.TYPESCRIPT,
            }
            language = language_map.get(language_str, Language.PYTHON)

            # Create metadata
            metadata = None
            if filename or author:
                metadata = CodeMetadata(
                    filename=filename,
                    language=language_str.capitalize(),
                    author=author,
                )

            # Configure render options
            page_size = content.get("page_size", PageSize.REMARKABLE_2)
            options = RenderOptions(
                page_size=page_size,
                show_line_numbers=content.get("show_line_numbers", True),
                show_metadata=content.get("show_metadata", True),
                debug_mode=content.get("debug_mode", False),
            )

            # Update compiler options
            self.compiler.options = options

            # Compile code with layout
            hcl_pages = self.compiler.compile_with_layout(code, language, metadata)

            if not hcl_pages:
                logger.error("Failed to compile code to HCL")
                return None

            # Generate output path if not provided
            if not output_path:
                output_path = self._generate_temp_path("syntax", title, "rm")

            # For now, use the first page (TODO: handle multi-page documents)
            if hcl_pages:
                hcl_content = hcl_pages[0]["hcl"]

                # Save HCL to temp file
                hcl_filename = f"syntax_{int(time.time())}.hcl"
                hcl_path = os.path.join(self.temp_dir, hcl_filename)
                with open(hcl_path, "w") as f:
                    f.write(hcl_content)

                # Process with drawj2d
                rm_path = self.drawj2d_service.process_hcl_file(hcl_path, output_path)

                if rm_path:
                    logger.info(f"Created syntax-highlighted document: {rm_path}")
                    return rm_path
                logger.error("Drawj2d processing failed")
                return None

            return None

        except Exception as e:
            logger.error(f"Error creating syntax-highlighted ink: {str(e)}")
            return None

    @staticmethod
    def _detect_language(code: str) -> str:
        """
        Attempt to detect the programming language from code content.

        Args:
            code: Source code

        Returns:
            Detected language name
        """
        # Simple heuristic-based detection
        if re.search(r"^\s*def\s+\w+", code, re.MULTILINE):
            return "python"
        if re.search(r"^\s*function\s+\w+", code, re.MULTILINE):
            return "javascript"
        if re.search(r"^\s*class\s+\w+\s*{", code, re.MULTILINE):
            return "java"
        if re.search(r"#include\s*<", code):
            return "c"
        if re.search(r"fn\s+\w+\s*\(", code):
            return "rust"
        if re.search(r"func\s+\w+\s*\(", code):
            return "go"
        if re.search(r"<\?php", code):
            return "php"
        if re.search(r"^\s*def\s+\w+\s*=", code, re.MULTILINE):
            return "ruby"

        return "text"  # Default fallback

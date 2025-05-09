"""Base content converter class for InkLink.

This module provides the base implementation for content converters
that transform various content types into reMarkable-compatible formats.
"""

import os
import time
import logging
from abc import ABC
from typing import Dict, Any, Optional

from inklink.services.interfaces import IContentConverter
from inklink.config import CONFIG

logger = logging.getLogger(__name__)


class BaseConverter(IContentConverter, ABC):
    """Base implementation for content converters."""
    
    def __init__(self, temp_dir: str):
        """
        Initialize with temporary directory.
        
        Args:
            temp_dir: Directory for temporary files
        """
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)
        
        # Determine Remarkable model ("pro" or "rm2")
        rm_model = CONFIG.get("REMARKABLE_MODEL", "pro").lower()
        self.is_remarkable_pro = rm_model == "pro"
        
        # Page dimensions (pixels) and layout defaults
        self.page_width = CONFIG.get("PAGE_WIDTH", 2160)
        self.page_height = CONFIG.get("PAGE_HEIGHT", 1620)
        self.margin = CONFIG.get("PAGE_MARGIN", 120)
        self.line_height = 40
        
        # Set font settings from CONFIG
        self.heading_font = CONFIG.get("HEADING_FONT", "Liberation Sans")
        self.body_font = CONFIG.get("BODY_FONT", "Liberation Sans")
        self.code_font = CONFIG.get("CODE_FONT", "DejaVu Sans Mono")
    
    def _get_timestamp(self) -> str:
        """Return formatted timestamp."""
        return time.strftime("%Y-%m-%d %H:%M:%S")
    
    def _escape_hcl(self, text: str) -> str:
        """Escape special characters for HCL."""
        if not text:
            return ""
            
        # Escape special characters for Hecl (drawj2d HCL) parsing
        # - backslashes must be doubled
        # - double quotes must be escaped
        # - dollar signs must be escaped to prevent variable substitution
        # - square brackets must be escaped to prevent command substitution
        # - backticks replaced to avoid markup/internal use
        # - newlines replaced by spaces
        s = text.replace("\\", "\\\\")
        s = s.replace("\"", "\\\"")
        s = s.replace("$", "\\$")
        s = s.replace("[", "\\[")
        s = s.replace("]", "\\]")
        s = s.replace("`", "'")
        return s.replace("\n", " ")
    
    def _generate_temp_path(self, prefix: str, url_or_id: str, extension: str) -> str:
        """
        Generate a temporary file path.
        
        Args:
            prefix: File prefix
            url_or_id: URL or unique identifier
            extension: File extension (without dot)
            
        Returns:
            Path to the temporary file
        """
        timestamp = int(time.time())
        filename = f"{prefix}_{hash(url_or_id)}_{timestamp}.{extension}"
        return os.path.join(self.temp_dir, filename)
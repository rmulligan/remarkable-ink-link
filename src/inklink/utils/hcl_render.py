"""HCL rendering utilities for InkLink.

This module provides functions for creating HCL scripts from
structured content for drawj2d to render.
"""

import os
import time
import logging
from typing import Dict, Any, Optional

from inklink.config import CONFIG, HCLResourceConfig

logger = logging.getLogger(__name__)


def create_hcl_from_content(
    url: str,
    qr_path: str,
    content: Dict[str, Any],
    temp_dir: str,
    config: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Create HCL script from structured content.

    Args:
        url: Source URL
        qr_path: Path to QR code image
        content: Structured content dictionary
        temp_dir: Directory for temporary files
        config: Optional configuration dictionary

    Returns:
        Path to generated HCL file or None if failed
    """
    try:
        # Ensure we have valid content, even if minimal
        if not content:
            content = {"title": f"Page from {url}", "structured_content": []}

        logger.info(f"Creating HCL document for: {content.get('title', url)}")

        # Use the page title for the filename, sanitized for filesystem safety
        page_title = content.get("title", f"Page from {url}")
        safe_title = (
            "".join(
                c if c.isalnum() or c in (" ", "_", "-") else "_" for c in page_title
            )
            .strip()
            .replace(" ", "_")
        )
        hcl_filename = f"doc_{safe_title}_{int(time.time())}.hcl"
        hcl_path = os.path.join(temp_dir, hcl_filename)

        # Use provided config or fall back to global CONFIG
        config = config or CONFIG

        # Get page dimensions from config
        page_width = config.get("PAGE_WIDTH", 2160)
        page_height = config.get("PAGE_HEIGHT", 1620)
        margin = config.get("PAGE_MARGIN", 120)

        # Get fonts from config
        heading_font = config.get("HEADING_FONT", "Liberation Sans")

        # This is a simplified stub of the original implementation
        # In a real implementation, this would contain the full HCL generation code
        # that was previously in DocumentService._create_hcl
        with open(hcl_path, "w", encoding="utf-8") as f:
            # Set page size
            f.write(f'puts "size {page_width} {page_height}"\n\n')

            # Set title
            f.write(f'puts "set_font {heading_font} 36"\n')
            f.write('puts "pen black"\n\n')
            f.write(f'puts "text {margin} {margin} \\"{escape_hcl(page_title)}\\""\n')

            # Add sample content (simplified)
            f.write('puts "text 100 200 \\"This is a sample HCL document\\""\n')
            f.write('puts "text 100 300 \\"Created by hcl_render.py\\""\n')

            # Add timestamp
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(
                f'puts "text {margin} {page_height - margin} \\"Generated: {timestamp}\\""\n'
            )

        logger.info(f"Created HCL file: {hcl_path}")
        return hcl_path

    except Exception as e:
        logger.error(f"Error creating HCL document: {e}")
        return None


def escape_hcl(text: str) -> str:
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
    s = s.replace('"', '\\"')
    s = s.replace("$", "\\$")
    s = s.replace("[", "\\[")
    s = s.replace("]", "\\]")
    s = s.replace("`", "'")
    return s.replace("\n", " ")


def render_hcl_resource(config: HCLResourceConfig) -> str:
    """
    Render HCL resource block from configuration.

    Args:
        config: HCL resource configuration

    Returns:
        HCL resource block as string
    """
    result = f'resource "{config.resource_type}" "{config.resource_name}" {{\n'

    # Add attributes
    for key, value in config.attributes.items():
        if isinstance(value, str):
            value_str = f'"{value}"'
        elif isinstance(value, bool):
            value_str = str(value).lower()
        else:
            value_str = str(value)

        result += f"  {key} = {value_str}\n"

    result += "}\n"
    return result

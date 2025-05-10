"""HCL rendering utilities for InkLink.

This module provides functions for creating HCL scripts from
structured content for drawj2d to render.
"""

import os
import time
import logging
import subprocess

from typing import Dict, Any, Optional, List, Tuple

from inklink.config import CONFIG, HCLResourceConfig

logger = logging.getLogger(__name__)


def escape_hcl(text: str) -> str:
    """
    Escape special characters in text for HCL script.

    Args:
        text: String to escape

    Returns:
        Escaped string safe for use in HCL
    """
    if not text:
        return ""

    # Comprehensive escaping for Hecl (drawj2d HCL) parsing
    s = text.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("$", "\\$")
    s = s.replace("[", "\\[")
    s = s.replace("]", "\\]")
    s = s.replace("`", "'")
    s = s.replace("\n", "\\n")
    s = s.replace("\t", "\\t")
    return s


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
        # Use provided config or fall back to global CONFIG
        config = config or CONFIG

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

        # Get page dimensions from config
        page_width = config.get("PAGE_WIDTH", 2160)
        page_height = config.get("PAGE_HEIGHT", 1620)
        margin = config.get("PAGE_MARGIN", 120)
        config.get("LINE_HEIGHT", 40)  # Used in more complex implementations

        # Get fonts from config
        heading_font = config.get("HEADING_FONT", "Liberation Sans")
        config.get("BODY_FONT", "Liberation Sans")  # Used in more complex implementations
        config.get("CODE_FONT", "DejaVu Sans Mono")  # Used in more complex implementations

        # Create the HCL script
        with open(hcl_path, "w", encoding="utf-8") as f:
            # Write header with page setup
            f.write(f"page_width: {page_width}\n")
            f.write(f"page_height: {page_height}\n")
            f.write(f"margin: {margin}\n\n")

            # Add QR code for source URL
            f.write(f"# QR Code for original source\n")
            f.write(f"image\n")
            f.write(f'  path: "{qr_path}"\n')
            f.write(f"  x: {page_width - 200}\n")
            f.write(f"  y: {50}\n")
            f.write(f"  width: 150\n")
            f.write(f"  height: 150\n\n")

            # Add title
            f.write(f"# Document title\n")
            f.write(f"text\n")
            f.write(f'  text: "{escape_hcl(page_title)}"\n')
            f.write(f'  font: "{heading_font}"\n')
            f.write(f"  size: 24\n")
            f.write(f"  x: {margin}\n")
            f.write(f"  y: {margin}\n\n")

            # Add structured content - in a real implementation, this would
            # iterate through the structured content items

            # Placeholder for content rendering
            if content.get("structured_content"):
                # This would be replaced with actual content rendering code
                f.write(f"# Structured content would be rendered here\n")

        return hcl_path

    except Exception as e:
        logger.error(f"Error creating HCL file: {str(e)}")
        return None


def render_hcl_resource(
    hcl_path: str, output_path: str, config: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Render HCL file to a reMarkable lines file using drawj2d.

    Args:
        hcl_path: Path to the HCL file
        output_path: Path where the output .rm file should be saved
        config: Optional configuration dictionary

    Returns:
        True if rendering was successful, False otherwise
    """
    try:
        # Use provided config or fall back to global CONFIG
        config = config or CONFIG

        # Get drawj2d path from config
        drawj2d_path = config.get("DRAWJ2D_PATH", "drawj2d")

        # Run drawj2d to render the HCL file
        logger.info(f"Rendering HCL file {hcl_path} to {output_path}")
        cmd = [drawj2d_path, hcl_path, "-o", output_path]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,  # Don't raise an exception on non-zero return code
        )

        if result.returncode != 0:
            logger.error(
                f"drawj2d failed with code {result.returncode}: {result.stderr}"
            )
            return False

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            logger.error(
                f"Output file {output_path} does not exist or is empty after rendering"
            )
            return False

        logger.info(f"Successfully rendered HCL to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error rendering HCL file: {str(e)}")
        return False


def render_hcl_resource_block(config: HCLResourceConfig) -> str:
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

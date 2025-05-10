"""HCL rendering utilities for InkLink.

This module provides functions for creating HCL scripts from
structured content for drawj2d to render.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List, Tuple

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
        line_height = config.get("LINE_HEIGHT", 40)

        # Get fonts from config
        heading_font = config.get("HEADING_FONT", "Liberation Sans")
        body_font = config.get("BODY_FONT", "Liberation Sans")
        code_font = config.get("CODE_FONT", "DejaVu Sans Mono")

        # Create the HCL script
        with open(hcl_path, "w", encoding="utf-8") as f:
            # Set page size
            f.write(f'puts "size {page_width} {page_height}"\n\n')

            # Initialize font and pen settings
            f.write(f'puts "set_font {heading_font} 36"\n')
            f.write('puts "pen black"\n\n')

            # Starting position
            y_pos = margin

            # Add title
            f.write(f'puts "text {margin} {y_pos} \\"{escape_hcl(page_title)}\\""\n')
            y_pos += line_height * 1.5

            # Add source URL line
            f.write(f'puts "set_font {body_font} 20"\n')
            f.write(f'puts "text {margin} {y_pos} \\"Source: {escape_hcl(url)}\\""\n')
            y_pos += line_height

            # Add horizontal separator
            f.write(
                f'puts "line {margin} {y_pos} {page_width - margin} {y_pos} width=1.0"\n'
            )
            y_pos += line_height * 1.5

            # Add QR code if available
            if qr_path and os.path.exists(qr_path):
                qr_size = 350
                qr_x = page_width - margin - qr_size
                f.write(
                    f'puts "rectangle {qr_x - 5} {y_pos - 5} {qr_size + 10} {qr_size + 10} width=1.0"\n'
                )
                f.write(
                    f'puts "image {qr_x} {y_pos} {qr_size} {qr_size} \\"{qr_path}\\""\n'
                )

            # Process structured content if available
            structured_content = content.get("structured_content", [])
            if structured_content:
                # Ensure we have some space below any QR code
                if qr_path and os.path.exists(qr_path):
                    y_pos += qr_size + line_height

                # Render structured content elements
                for item in structured_content:
                    content_type = item.get("type", "text")
                    content_value = item.get("value", "")

                    if content_type == "heading":
                        level = item.get("level", 1)
                        size = (
                            36
                            if level == 1
                            else (30 if level == 2 else (24 if level == 3 else 20))
                        )
                        f.write(f'puts "set_font {heading_font} {size}"\n')
                        f.write(
                            f'puts "text {margin} {y_pos} \\"{escape_hcl(content_value)}\\""\n'
                        )
                        y_pos += line_height * 1.5

                    elif content_type == "paragraph":
                        f.write(f'puts "set_font {body_font} 20"\n')
                        f.write(
                            f'puts "text {margin} {y_pos} \\"{escape_hcl(content_value)}\\""\n'
                        )
                        y_pos += line_height * 1.2

                    elif content_type == "code":
                        f.write(f'puts "set_font {code_font} 18"\n')
                        f.write(
                            f'puts "text {margin + 20} {y_pos} \\"{escape_hcl(content_value)}\\""\n'
                        )
                        y_pos += line_height
                    elif content_type == "list_item":
                        level = item.get("level", 1)
                        indent = margin + ((level - 1) * 30)
                        f.write(f'puts "set_font {body_font} 20"\n')
                        f.write(
                            f'puts "text {indent} {y_pos} \\"• {escape_hcl(content_value)}\\""\n'
                        )
                        y_pos += line_height
                    elif content_type == "image":
                        img_path = item.get("path", "")
                        if img_path and os.path.exists(img_path):
                            img_width = item.get("width", 800)
                            img_height = item.get("height", 600)
                            f.write(
                                f'puts "image {margin} {y_pos} {img_width} {img_height} \\"{img_path}\\""\n'
                            )
                            y_pos += img_height + line_height

                    elif content_type == "table":
                        # Basic table rendering (simplified)
                        rows = item.get("rows", [])
                        col_width = (
                            (page_width - 2 * margin) / max(len(row) for row in rows)
                            if rows
                            else 100
                        )
                        for row_idx, row in enumerate(rows):
                            for col_idx, cell in enumerate(row):
                                x_pos = margin + (col_idx * col_width)
                                f.write(
                                    f'puts "text {x_pos} {y_pos} \\"{escape_hcl(str(cell))}\\""\n'
                                )
                            y_pos += line_height
                            if row_idx == 0:  # Header row
                                f.write(
                                    f'puts "line {margin} {y_pos} {page_width - margin} {y_pos} width=1.0"\n'
                                )
                                y_pos += line_height / 2
            else:
                # If no structured content, add a placeholder message
                y_pos = margin + 400  # Middle of page
                f.write(f'puts "set_font {body_font} 24"\n')
                f.write(
                    f'puts "text {margin} {y_pos} \\"No content available for this page.\\""\n'
                )

            # Add timestamp at the bottom of the page
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f'puts "set_font {body_font} 16"\n')
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

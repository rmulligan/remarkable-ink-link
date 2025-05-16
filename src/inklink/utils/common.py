"""Common utility functions for InkLink.

This module provides common utility functions used throughout the project.
"""

import logging
import os
import re
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def retry_operation(
    operation: Callable,
    *args,
    operation_name: str = "Operation",
    max_retries: int = 3,
    retry_delay: int = 2,
    **kwargs,
) -> Any:
    """
    Retry an operation with exponential backoff.

    Args:
        operation: The function to retry
        *args: Positional arguments to pass to the operation
        operation_name: Name of the operation for logging
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        **kwargs: Keyword arguments to pass to the operation

    Returns:
        The result of the operation if successful

    Raises:
        The last exception encountered if all retries fail
    """
    attempts = 0
    last_error = None

    while attempts <= max_retries:
        try:
            if attempts > 0:
                logger.info(f"Retry attempt {attempts} for {operation_name}")
            return operation(*args, **kwargs)
        except Exception as e:
            last_error = e
            attempts += 1
            if attempts <= max_retries:
                sleep_time = retry_delay * (2 ** (attempts - 1))  # Exponential backoff
                logger.warning(
                    f"{operation_name} failed, retrying in {sleep_time} seconds: {str(e)}"
                )
                time.sleep(sleep_time)
            else:
                logger.error(
                    f"{operation_name} failed after {max_retries} retries: {str(e)}"
                )
                break

    # Re-raise the last exception if all retries failed
    if last_error:
        raise last_error
    return None


def format_error(error_type: str, message: str, details: Any = None) -> str:
    """
    Format an error message with details.

    Args:
        error_type: Type of error
        message: Error message
        details: Additional error details

    Returns:
        Formatted error string
    """
    error_str = f"ERROR [{error_type}]: {message}"
    if details:
        error_str += f" - {str(details)}"
    return error_str


def ensure_drawj2d_available() -> bool:
    """
    Check if drawj2d is available.

    Returns:
        True if drawj2d is available, False otherwise
    """
    try:
        from inklink.config import CONFIG

        drawj2d_path = CONFIG.get("DRAWJ2D_PATH")
        if (
            drawj2d_path
            and os.path.exists(drawj2d_path)
            and os.access(drawj2d_path, os.X_OK)
        ):
            return True

        # Try to find drawj2d in PATH
        result = subprocess.run(
            ["which", "drawj2d"], capture_output=True, text=True, check=False
        )
        return result.returncode == 0
    except Exception:
        return False


def create_hcl_from_markdown(
    markdown_path: str, output_dir: str, title: str = None
) -> Tuple[bool, str]:
    """
    Create an HCL file from Markdown for use with drawj2d.

    Args:
        markdown_path: Path to markdown file
        output_dir: Directory to store the HCL file
        title: Optional title for the document

    Returns:
        Tuple of (success, result)
        If successful, result is the path to the generated HCL file
        If failed, result is the error message
    """
    try:
        if not os.path.exists(markdown_path):
            return False, f"Markdown file not found: {markdown_path}"

        with open(markdown_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        # Generate HCL file path
        base_name = os.path.basename(markdown_path)
        name, _ = os.path.splitext(base_name)
        hcl_path = os.path.join(output_dir, f"{name}.hcl")

        # Create a simple HCL file with the markdown content
        with open(hcl_path, "w", encoding="utf-8") as f:
            # Set page size based on reMarkable dimensions
            f.write('puts "size 1404 1872"\n\n')

            # Set title if provided
            if title:
                f.write('puts "set_font Liberation Sans 36"\n')
                f.write('puts "pen black"\n')
                f.write(f'puts "text 100 100 \\"{title}\\""\n\n')
                y_pos = 150
            else:
                y_pos = 100

            # Add markdown content
            f.write('puts "set_font Liberation Sans 24"\n')
            f.write('puts "pen black"\n')

            # Process markdown content line by line
            lines = markdown_content.split("\n")
            for line in lines:
                if line.strip():
                    # Escape any double quotes in the line
                    escaped_line = line.replace('"', '\\"')
                    f.write(f'puts "text 100 {y_pos} \\"{escaped_line}\\""\n')
                    y_pos += 30  # Increment y position for next line

        return True, hcl_path
    except Exception as e:
        return False, str(e)


def convert_markdown_to_rm(markdown_path: str, title: str = None) -> Tuple[bool, str]:
    """
    Convert Markdown to reMarkable format using drawj2d.

    Args:
        markdown_path: Path to markdown file
        title: Optional title for the document

    Returns:
        Tuple of (success, result)
        If successful, result is the path to the generated .rm file
        If failed, result is the error message
    """
    try:
        from inklink.config import CONFIG

        # Create a temporary directory for HCL file
        temp_dir = CONFIG.get("TEMP_DIR")
        os.makedirs(temp_dir, exist_ok=True)

        # Create HCL file from markdown
        success, hcl_result = create_hcl_from_markdown(markdown_path, temp_dir, title)
        if not success:
            return False, f"Failed to create HCL from markdown: {hcl_result}"

        hcl_path = hcl_result

        # Generate output path
        base_name = os.path.basename(markdown_path)
        name, _ = os.path.splitext(base_name)
        rm_path = os.path.join(temp_dir, f"{name}.rm")

        # Get drawj2d path
        drawj2d_path = CONFIG.get("DRAWJ2D_PATH")
        if not drawj2d_path or not os.path.exists(drawj2d_path):
            return False, "drawj2d not found"

        # Convert HCL to reMarkable format
        cmd = [drawj2d_path, "-F", "hcl", "-T", "rm", "-rmv6", "-o", rm_path, hcl_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0 and os.path.exists(rm_path):
            return True, rm_path
        return False, f"Conversion failed: {result.stderr}"
    except Exception as e:
        return False, str(e)


def convert_html_to_rm(html_path: str, title: str = None) -> Tuple[bool, str]:
    """
    Convert HTML to reMarkable format using drawj2d.

    Args:
        html_path: Path to HTML file
        title: Optional title for the document

    Returns:
        Tuple of (success, result)
        If successful, result is the path to the generated .rm file
        If failed, result is the error message
    """
    try:
        import tempfile

        from inklink.config import CONFIG

        # Create a temporary directory
        temp_dir = CONFIG.get("TEMP_DIR")
        os.makedirs(temp_dir, exist_ok=True)

        # First try to convert HTML to markdown using html2text
        try:
            import html2text

            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            h = html2text.HTML2Text()
            h.ignore_links = False
            h.body_width = 0  # Don't wrap text
            markdown_content = h.handle(html_content)

            # Create temporary markdown file
            md_path = os.path.join(temp_dir, f"{os.path.basename(html_path)}.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            # Convert markdown to reMarkable format
            return convert_markdown_to_rm(md_path, title)
        except ImportError:
            # html2text not available, try direct conversion
            pass

        # If html2text is not available or conversion failed, create HCL directly
        # Extract text from HTML using simple regex
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Simple regex to extract text (not ideal but works for basic HTML)
        import re

        text_content = re.sub(r"<[^>]*>", " ", html_content)
        text_content = re.sub(r"\s+", " ", text_content).strip()

        # Create temporary text file
        txt_path = os.path.join(temp_dir, f"{os.path.basename(html_path)}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text_content)

        # Create HCL from text
        success, hcl_result = create_hcl_from_markdown(txt_path, temp_dir, title)
        if not success:
            return False, f"Failed to create HCL from HTML: {hcl_result}"

        hcl_path = hcl_result

        # Generate output path
        base_name = os.path.basename(html_path)
        name, _ = os.path.splitext(base_name)
        rm_path = os.path.join(temp_dir, f"{name}.rm")

        # Get drawj2d path
        drawj2d_path = CONFIG.get("DRAWJ2D_PATH")
        if not drawj2d_path or not os.path.exists(drawj2d_path):
            return False, "drawj2d not found"

        # Convert HCL to reMarkable format
        cmd = [drawj2d_path, "-F", "hcl", "-T", "rm", "-rmv6", "-o", rm_path, hcl_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0 and os.path.exists(rm_path):
            return True, rm_path
        return False, f"Conversion failed: {result.stderr}"
    except Exception as e:
        return False, str(e)


def is_safe_url(url: str) -> bool:
    """
    Check if URL is safe to process.

    Args:
        url: URL to check

    Returns:
        True if URL is safe, False otherwise
    """
    # Check for whitespace or control characters
    if any(c.isspace() or ord(c) < 32 for c in url):
        return False

    # Parse URL
    parsed = urlparse(url)

    # Check scheme
    if parsed.scheme not in ("http", "https"):
        return False

    # Check netloc
    if not parsed.netloc:
        return False

    # Check for suspicious or dangerous characters
    unsafe_chars = "<>'\"`;|{}\\^~[]`"
    if any(c in unsafe_chars for c in url):
        return False

    # Check for potentially malicious patterns
    malicious_patterns = [
        "javascript:",
        "data:",
        "vbscript:",
        "file:",
        "about:",
    ]
    for pattern in malicious_patterns:
        if pattern in url.lower():
            return False

    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to make it safe for use in file systems.

    Args:
        filename: The filename to sanitize

    Returns:
        A sanitized filename
    """
    # Remove or replace invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, "_", filename)

    # Limit length to avoid issues with long filenames
    max_length = 255
    if len(sanitized) > max_length:
        name, ext = os.path.splitext(sanitized)
        name = name[: max_length - len(ext)]
        sanitized = name + ext

    # Ensure the filename doesn't start or end with spaces or periods
    sanitized = sanitized.strip(". ")

    # If filename is empty after sanitizing, use a default name
    if not sanitized:
        sanitized = "unnamed"

    return sanitized

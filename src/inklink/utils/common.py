"""Common utility functions for InkLink.

This module provides common utility functions used throughout the project.
"""

import time
import logging
import subprocess
import re
from urllib.parse import urlparse
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

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


def ensure_rcu_available() -> bool:
    """
    Check if RCU (reMarkable Content Uploader) is available.

    Returns:
        True if RCU is available, False otherwise
    """
    try:
        result = subprocess.run(
            ["which", "rcu"], capture_output=True, text=True, check=False
        )
        return result.returncode == 0
    except Exception:
        return False


def convert_markdown_to_rm(markdown_path: str, title: str = None) -> Tuple[bool, str]:
    """
    Convert Markdown to reMarkable format using RCU.

    Args:
        markdown_path: Path to markdown file
        title: Optional title for the document

    Returns:
        Tuple of (success, result)
        If successful, result is the path to the generated .rm file
        If failed, result is the error message
    """
    try:
        # Create RCU command
        cmd = ["rcu", "convert", "--input", markdown_path]

        if title:
            cmd.extend(["--title", title])

        # Run RCU
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            # Extract the output path from result.stdout
            # RCU outputs "Converting to <path>"
            output_lines = result.stdout.strip().split("\n")
            for line in output_lines:
                if "Converting to" in line:
                    output_path = line.split("Converting to", 1)[1].strip()
                    return True, output_path
            return True, "Conversion successful, but output path not found"
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)


def convert_html_to_rm(html_path: str, title: str = None) -> Tuple[bool, str]:
    """
    Convert HTML to reMarkable format using RCU.

    Args:
        html_path: Path to HTML file
        title: Optional title for the document

    Returns:
        Tuple of (success, result)
        If successful, result is the path to the generated .rm file
        If failed, result is the error message
    """
    try:
        # Create RCU command
        cmd = ["rcu", "convert", "--input", html_path]

        if title:
            cmd.extend(["--title", title])

        # Run RCU
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            # Extract the output path from result.stdout
            # RCU outputs "Converting to <path>"
            output_lines = result.stdout.strip().split("\n")
            for line in output_lines:
                if "Converting to" in line:
                    output_path = line.split("Converting to", 1)[1].strip()
                    return True, output_path
            return True, "Conversion successful, but output path not found"
        else:
            return False, result.stderr
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

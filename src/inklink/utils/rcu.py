"""RCU (reMarkable Content Uploader) integration utilities."""

import os
import logging
import subprocess
import platform
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# RCU installation and configuration
RCU_COMMAND = "rcu"
RCU_GITHUB_URL = "https://github.com/j-martens/rcu"


def check_rcu_installed() -> bool:
    """Check if RCU is available on the system PATH.

    Returns:
        bool: True if RCU is installed and accessible
    """
    try:
        # Check if RCU is in PATH
        result = subprocess.run(
            [RCU_COMMAND, "--version"], capture_output=True, text=True, check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def install_rcu() -> bool:
    """Attempt to install RCU.

    Returns:
        bool: True if installation succeeded
    """
    logger.info("Attempting to install RCU...")

    system = platform.system().lower()

    try:
        if system == "linux":
            # Try installing via pip first
            logger.info("Attempting to install RCU via pip...")
            result = subprocess.run(
                ["pip", "install", "rcu"], capture_output=True, text=True, check=False
            )

            if result.returncode == 0:
                logger.info("RCU installed successfully via pip")
                return True

            # If pip fails, try cloning from GitHub
            logger.info("Pip installation failed, trying GitHub...")
            result = subprocess.run(
                ["git", "clone", RCU_GITHUB_URL, "/tmp/rcu"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                install_result = subprocess.run(
                    ["cd", "/tmp/rcu", "&&", "pip", "install", "-e", "."],
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if install_result.returncode == 0:
                    logger.info("RCU installed successfully from GitHub")
                    return True

        # For other systems or if direct installation failed
        logger.warning(
            f"Automatic RCU installation not supported on {system}. "
            f"Please install manually from {RCU_GITHUB_URL}"
        )
        return False

    except Exception as e:
        logger.error(f"Error installing RCU: {e}")
        return False


def ensure_rcu_available() -> bool:
    """Check if RCU is installed and attempt to install if not.

    Returns:
        bool: True if RCU is available after check/installation
    """
    if check_rcu_installed():
        return True

    logger.warning("RCU not found, attempting to install...")
    if install_rcu() and check_rcu_installed():
        return True

    logger.error(
        "RCU is required but not available. "
        f"Please install manually from {RCU_GITHUB_URL}"
    )
    return False


def convert_markdown_to_rm(
    markdown_path: str, output_path: Optional[str] = None, title: Optional[str] = None
) -> Tuple[bool, str]:
    """Convert markdown file to reMarkable format using RCU.

    Args:
        markdown_path: Path to markdown file
        output_path: Optional output path (default: same as input with .rm extension)
        title: Optional title for the document

    Returns:
        Tuple of (success, message or output_path)
    """
    if not ensure_rcu_available():
        return False, "RCU not available"

    if not os.path.exists(markdown_path):
        return False, f"Input file not found: {markdown_path}"

    # Default output path if not provided
    if not output_path:
        base, _ = os.path.splitext(markdown_path)
        output_path = f"{base}.rm"

    # Build command
    cmd = [RCU_COMMAND, "convert", "--input", markdown_path, "--output", output_path]

    # Add title if provided
    if title:
        cmd.extend(["--title", title])

    try:
        # Run conversion
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            if os.path.exists(output_path):
                return True, output_path
            else:
                return False, "Conversion succeeded but output file not found"
        else:
            return False, f"RCU conversion failed: {result.stderr}"

    except Exception as e:
        return False, f"Error running RCU: {e}"


def convert_html_to_rm(
    html_path: str, output_path: Optional[str] = None, title: Optional[str] = None
) -> Tuple[bool, str]:
    """Convert HTML file to reMarkable format using RCU.

    Args:
        html_path: Path to HTML file
        output_path: Optional output path (default: same as input with .rm extension)
        title: Optional title for the document

    Returns:
        Tuple of (success, message or output_path)
    """
    if not ensure_rcu_available():
        return False, "RCU not available"

    if not os.path.exists(html_path):
        return False, f"Input file not found: {html_path}"

    # Default output path if not provided
    if not output_path:
        base, _ = os.path.splitext(html_path)
        output_path = f"{base}.rm"

    # Build command
    cmd = [
        RCU_COMMAND,
        "convert",
        "--html",
        "--input",
        html_path,
        "--output",
        output_path,
    ]

    # Add title if provided
    if title:
        cmd.extend(["--title", title])

    try:
        # Run conversion
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            if os.path.exists(output_path):
                return True, output_path
            else:
                return False, "Conversion succeeded but output file not found"
        else:
            return False, f"RCU conversion failed: {result.stderr}"

    except Exception as e:
        return False, f"Error running RCU: {e}"
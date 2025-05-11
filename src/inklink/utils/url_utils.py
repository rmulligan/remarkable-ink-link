"""URL-related utilities for InkLink.

This module provides functions for handling URLs including
extraction, sanitization, and validation.
"""

import logging
import re
from urllib.parse import urlparse, urljoin, quote

logger = logging.getLogger(__name__)


def extract_url(path: str) -> str:
    """
    Extract URL from path.

    Args:
        path: Path which may contain a URL

    Returns:
        Extracted URL or empty string
    """
    # Try to extract a URL from the path
    # Match "/share/<url>" format
    url_match = re.match(r"^/share/(https?://.+)$", path)
    if url_match:
        return url_match.group(1)

    # Match "/ingest/<url>" format
    url_match = re.match(r"^/ingest/(https?://.+)$", path)
    if url_match:
        return url_match.group(1)

    # Match query parameter format "?url=<url>"
    url_match = re.match(r"^/share\?url=(https?://.+)$", path)
    if url_match:
        return url_match.group(1)

    # Check if the path itself looks like a URL
    if path.startswith("http://") or path.startswith("https://"):
        return path

    return ""


def sanitize_url(url: str) -> str:
    """
    Sanitize URL by encoding unsafe characters.

    Args:
        url: URL to sanitize

    Returns:
        Sanitized URL
    """
    if not url:
        return ""

    # Parse URL into components
    try:
        parsed = urlparse(url)

        # Reconstruct with proper quoting
        # Keep allowed special chars in path (/,:)
        path = quote(parsed.path, safe="/:,")

        # Rebuild URL with properly quoted path
        sanitized = f"{parsed.scheme}://{parsed.netloc}{path}"

        # Add query string if present (also quoted)
        if parsed.query:
            sanitized += f"?{quote(parsed.query, safe='=&')}"

        # Add fragment if present (quoted)
        if parsed.fragment:
            sanitized += f"#{quote(parsed.fragment)}"

        return sanitized

    except Exception as e:
        logger.error(f"Error sanitizing URL: {e}")
        return url  # Return original if parsing fails


def get_hostname(url: str) -> str:
    """
    Extract hostname from URL.

    Args:
        url: URL to extract hostname from

    Returns:
        Hostname or empty string
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return ""

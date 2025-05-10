"""URL utilities for InkLink.

This module provides utilities for handling URLs safely.
"""

import json
import logging
from urllib.parse import urlparse

from inklink.utils import is_safe_url

logger = logging.getLogger(__name__)


def extract_url(post_data: bytes) -> str:
    """
    Extract URL from request data (JSON or plain text).

    Args:
        post_data: Request data

    Returns:
        Extracted URL or None if invalid
    """
    # Try to decode as JSON
    try:
        data = json.loads(post_data.decode("utf-8"))

        if url := data.get("url"):
            # Reject URLs containing any whitespace or control characters
            if any(c.isspace() for c in url):
                return None

            # Trim and parse
            url = url.strip()

            parsed = urlparse(url)
            # Validate scheme, netloc, and allowed characters
            if (
                parsed.scheme in ("http", "https")
                and parsed.netloc
                and is_safe_url(url)
            ):
                return url

    except json.JSONDecodeError:
        pass

    # Try as plain text: decode and validate the raw URL string
    try:
        raw = post_data.decode("utf-8")
    except UnicodeDecodeError:
        return None

    # Reject if any whitespace or control characters present
    if any(c.isspace() for c in raw):
        return None

    # Trim extraneous whitespace at ends
    raw = raw.strip()

    parsed = urlparse(raw)
    # Validate scheme and netloc
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None

    # If the entire URL is safe, return it
    if is_safe_url(raw):
        return raw

    # If there is a '<' suffix, strip it and validate the prefix
    if "<" in raw:
        prefix = raw.split("<", 1)[0]
        parsed_pref = urlparse(prefix)
        if (
            parsed_pref.scheme in ("http", "https")
            and parsed_pref.netloc
            and is_safe_url(prefix)
        ):
            return prefix

    # Not a valid URL
    return None

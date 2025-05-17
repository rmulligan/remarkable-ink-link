"""Response controller for InkLink.

This module provides a controller for handling response retrieval requests.
"""

import logging
from urllib.parse import parse_qs, urlparse

from inklink.controllers.base_controller import BaseController

logger = logging.getLogger(__name__)


class ResponseController(BaseController):
    """Controller for handling response retrieval requests."""

    def handle(self, method: str = "GET", path: str = "") -> None:
        """
        Handle response retrieval requests.

        Args:
            method: HTTP method
            path: Request path
        """
        if method != "GET":
            self.send_error("Method not allowed", status=405)
            return

        # Parse query parameters
        query = urlparse(path).query
        params = parse_qs(query)
        response_id = params.get("response_id", [None])[0]

        # Check if response exists
        if not response_id or response_id not in self.get_server().responses:
            self.send_error("Invalid response_id", status=400)
            return

        # Get response data
        resp = self.get_server().responses[response_id]

        # Sanitize response data before sending to prevent XSS attacks
        sanitized_markdown = (
            resp.get("markdown", "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

        # If raw data is HTML, sanitize it as well
        raw_data = resp.get("raw", "")
        if isinstance(raw_data, str):
            sanitized_raw = (
                raw_data.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#x27;")
            )
        else:
            sanitized_raw = raw_data

        # Send sanitized response data
        self.send_json({"markdown": sanitized_markdown, "raw": sanitized_raw})

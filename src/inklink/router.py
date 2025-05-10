"""URL router for InkLink.

This module provides a router that dispatches HTTP requests to the appropriate controller.
"""

import logging
from http.server import BaseHTTPRequestHandler
from typing import Dict, Any, Tuple, Optional

from inklink.controllers import (
    BaseController,
    AuthController,
    DownloadController,
    ResponseController,
    ShareController,
    IngestController,
    UploadController,
    ProcessController,
)

logger = logging.getLogger(__name__)


class Router:
    """Router for HTTP requests."""

    def __init__(self, services: Dict[str, Any]):
        """
        Initialize with services.

        Args:
            services: Dictionary of service instances
        """
        self.services = services

    def route(
        self, handler: BaseHTTPRequestHandler, method: str, path: str
    ) -> Optional[BaseController]:
        """
        Route HTTP request to the appropriate controller.

        Args:
            handler: BaseHTTPRequestHandler instance
            method: HTTP method
            path: Request path

        Returns:
            Controller or None if no route matches
        """
        # Parse the path
        route, query = self._parse_path(path)
        # Split route into parts if needed for more complex routing in the future

        # Route GET requests
        if method == "GET":
            if route == "/auth":
                return AuthController(handler)
            elif route == "/auth/remarkable":
                return AuthController(handler)
            elif route == "/auth/myscript":
                return AuthController(handler)
            elif route == "/download":
                return DownloadController(handler, self.services)
            elif route == "/response":
                return ResponseController(handler, self.services)

        # Route POST requests
        elif method == "POST":
            if route == "/share":
                return ShareController(handler, self.services)
            elif route == "/ingest":
                return IngestController(handler, self.services)
            elif route == "/upload":
                return UploadController(handler, self.services)
            elif route == "/process":
                return ProcessController(handler, self.services)

        # No route matched
        return None

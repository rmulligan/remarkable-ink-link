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
from inklink.controllers.knowledge_graph_integration_controller import (
    KnowledgeGraphIntegrationController,
)
from inklink.controllers.limitless_controller import (
    LimitlessController,
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
            elif route.startswith("/download/"):
                return DownloadController(handler, self.services)
            elif route.startswith("/response"):
                return ResponseController(handler, self.services)

        # Route POST requests
        elif method == "POST":
            if route == "/auth":
                return AuthController(handler)
            elif route == "/share":
                return ShareController(handler, self.services)
            elif route == "/ingest":
                return IngestController(handler, self.services)
            elif route == "/upload":
                return UploadController(handler, self.services)
            elif route == "/process":
                return ProcessController(handler, self.services)
            # Knowledge Graph routes
            elif route.startswith("/kg/"):
                knowledge_graph_service = self.services.get("knowledge_graph_service")
                kg_integration_service = self.services.get(
                    "knowledge_graph_integration_service"
                )
                if knowledge_graph_service and kg_integration_service:
                    return KnowledgeGraphIntegrationController(
                        kg_integration_service, handler
                    )
            # Limitless Life Log routes
            elif route.startswith("/limitless/"):
                limitless_service = self.services.get("limitless_service")
                limitless_scheduler = self.services.get("limitless_scheduler")
                if limitless_service and limitless_scheduler:
                    return LimitlessController(
                        limitless_service, limitless_scheduler, handler
                    )

        # No route matched
        return None

    def _parse_path(self, path: str) -> Tuple[str, str]:
        """
        Parse path into route and query string.

        Args:
            path: Request path

        Returns:
            Tuple containing the route and query string
        """
        # Split the path into route and query string
        parts = path.split("?", 1)
        route = parts[0]
        query = parts[1] if len(parts) > 1 else ""

        return route, query

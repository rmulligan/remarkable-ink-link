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
    
    def route(self, handler: BaseHTTPRequestHandler, method: str, path: str) -> Optional[BaseController]:
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
        route_parts = route.split("/")
        
        # Route GET requests
        if method == "GET":
            if route == "/auth":
                return AuthController(handler)
            elif route.startswith("/download/"):
                return DownloadController(handler)
            elif route.startswith("/response"):
                return ResponseController(handler)
        
        # Route POST requests
        elif method == "POST":
            if route == "/auth":
                return AuthController(handler)
            elif route == "/auth/remarkable":
                return AuthController(handler)
            elif route == "/auth/myscript":
                return AuthController(handler)
            elif route == "/ingest":
                return IngestController(handler, self.services)
            elif route == "/upload":
                return UploadController(handler)
            elif route == "/process":
                return ProcessController(handler)
            elif route == "/share":
                return ShareController(handler, self.services)
        
        # If no route matches, return None
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
"""Base controller for HTTP endpoints.

This module provides the base controller class for HTTP request handling.
"""

import json
import logging
from abc import ABC, abstractmethod
from http.server import BaseHTTPRequestHandler
from typing import Any, Dict, Optional, TypeVar, cast, Union, Tuple

ServerType = TypeVar("ServerType")
logger = logging.getLogger(__name__)


class BaseController(ABC):
    """Base controller for HTTP endpoints."""
    
    def __init__(self, handler: BaseHTTPRequestHandler):
        """
        Initialize with HTTP handler.
        
        Args:
            handler: BaseHTTPRequestHandler instance
        """
        self.handler = handler
        
    @abstractmethod
    def handle(self, *args, **kwargs) -> None:
        """
        Handle the HTTP request.
        
        Args:
            *args: Variable positional arguments
            **kwargs: Variable keyword arguments
        """
        pass
    
    def get_server(self) -> ServerType:
        """Get the HTTP server instance."""
        return cast(ServerType, self.handler.server)
    
    def send_response(self, status_code: int = 200) -> None:
        """
        Send HTTP response code.
        
        Args:
            status_code: HTTP status code
        """
        self.handler.send_response(status_code)
    
    def send_header(self, keyword: str, value: str) -> None:
        """
        Send HTTP header.
        
        Args:
            keyword: Header name
            value: Header value
        """
        self.handler.send_header(keyword, value)
    
    def end_headers(self) -> None:
        """End HTTP headers."""
        self.handler.end_headers()
    
    def send_json(self, obj: Any, status: int = 200) -> None:
        """
        Send JSON response.
        
        Args:
            obj: Object to serialize as JSON
            status: HTTP status code
        """
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.handler.wfile.write(json.dumps(obj).encode("utf-8"))
    
    def send_html(self, html: str, status: int = 200) -> None:
        """
        Send HTML response.
        
        Args:
            html: HTML content
            status: HTTP status code
        """
        self.send_response(status)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.handler.wfile.write(html.encode("utf-8"))
    
    def send_success(self, message: str) -> None:
        """
        Send success response.
        
        Args:
            message: Success message
        """
        self.send_json({"success": True, "message": message})
    
    def send_error(self, message: str, status: int = 500) -> None:
        """
        Send error response.
        
        Args:
            message: Error message
            status: HTTP status code
        """
        self.send_json({"success": False, "message": message}, status=status)
    
    def read_request_data(self) -> Tuple[bytes, Optional[Dict[str, Any]]]:
        """
        Read request data from the client.
        
        Returns:
            Tuple containing the raw bytes and parsed JSON (if valid)
        """
        content_length = int(self.handler.headers.get("Content-Length", 0))
        raw_data = self.handler.rfile.read(content_length) if content_length > 0 else b""
        
        # Try to parse as JSON
        json_data = None
        try:
            if raw_data:
                json_data = json.loads(raw_data.decode("utf-8"))
        except json.JSONDecodeError:
            pass
            
        return raw_data, json_data
    
    def get_content_type(self) -> str:
        """
        Get the content type of the request.
        
        Returns:
            Content type
        """
        return self.handler.headers.get("Content-Type", "")
    
    def get_accept_header(self) -> str:
        """
        Get the Accept header of the request.
        
        Returns:
            Accept header
        """
        return self.handler.headers.get("Accept", "")
#!/usr/bin/env python3
"""
InkLink Server

Receives URLs via HTTP POST, processes them, and uploads to Remarkable.
"""

import logging
import traceback
from typing import Dict, Optional, TypeVar, Any
from http.server import HTTPServer, BaseHTTPRequestHandler

from inklink.config import CONFIG, setup_logging
from inklink.router import Router
from inklink.services.qr_service import QRCodeService
from inklink.services.pdf_service import PDFService
from inklink.services.web_scraper_service import WebScraperService
from inklink.services.document_service import DocumentService
from inklink.services.remarkable_service import RemarkableService
from inklink.services.ai_service import AIService

# Define a TypeVar for our custom server type
ServerType = TypeVar("ServerType", bound="CustomHTTPServer")

# Set up logging
logger = logging.getLogger("inklink.server")


class URLHandler(BaseHTTPRequestHandler):
    """Handler for URL sharing requests."""
    
    def __init__(self, *args, router=None, **kwargs):
        """
        Initialize with router.
        
        Args:
            *args: Variable positional arguments
            router: Router instance
            **kwargs: Variable keyword arguments
        """
        self.router = router
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        try:
            controller = self.router.route(self, "GET", self.path)
            
            if controller:
                controller.handle("GET", self.path)
            else:
                self._send_error("Invalid endpoint")
        except Exception as e:
            logger.error(f"Error handling GET request: {str(e)}")
            logger.error(traceback.format_exc())
            self._send_error(f"Error handling request: {str(e)}")
    
    def do_POST(self):
        """Handle POST requests."""
        try:
            controller = self.router.route(self, "POST", self.path)
            
            if controller:
                controller.handle("POST", self.path)
            else:
                self._send_error("Invalid endpoint")
        except Exception as e:
            logger.error(f"Error handling POST request: {str(e)}")
            logger.error(traceback.format_exc())
            self._send_error(f"Error handling request: {str(e)}")
    
    def _send_error(self, message: str):
        """Send error response."""
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = f'{{"success": false, "message": "{message}"}}'
        self.wfile.write(response.encode("utf-8"))


class CustomHTTPServer(HTTPServer):
    """Custom HTTP Server with additional attributes for tokens, files, and responses."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize attributes needed by controllers
        self.tokens = {}  # Store authentication tokens
        self.files = {}  # Store uploaded files
        self.responses = {}  # Store responses


def run_server(host: Optional[str] = None, port: Optional[int] = None):
    """Start the HTTP server with dependency injection support."""
    # Use string type for HOST and int type for PORT with defaults
    host_value = host if host is not None else CONFIG.get("HOST", "0.0.0.0")
    port_value = port if port is not None else int(CONFIG.get("PORT", 9999))
    server_address = (host_value, port_value)
    
    # Create services
    services = initialize_services()
    
    # Create router
    router = Router(services)
    
    # Create handler factory
    def handler_factory(*args, **kwargs):
        return URLHandler(*args, router=router, **kwargs)
    
    # Create HTTP server
    httpd = CustomHTTPServer(server_address, handler_factory)
    
    # Setup logging
    logger = setup_logging()
    logger.info(f"InkLink server listening on {host_value}:{port_value}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server")
        httpd.server_close()


def initialize_services() -> Dict[str, Any]:
    """Initialize services for dependency injection."""
    qr_service = QRCodeService(CONFIG["TEMP_DIR"])
    pdf_service = PDFService(CONFIG["TEMP_DIR"], CONFIG["OUTPUT_DIR"])
    web_scraper = WebScraperService()
    document_service = DocumentService(CONFIG["TEMP_DIR"], CONFIG["DRAWJ2D_PATH"])
    remarkable_service = RemarkableService(CONFIG["RMAPI_PATH"], CONFIG["RM_FOLDER"])
    ai_service = AIService()
    
    return {
        "qr_service": qr_service,
        "pdf_service": pdf_service,
        "web_scraper": web_scraper,
        "document_service": document_service,
        "remarkable_service": remarkable_service,
        "ai_service": ai_service,
    }
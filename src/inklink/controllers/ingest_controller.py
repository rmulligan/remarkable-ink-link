"""Ingest controller for InkLink.

This module provides a controller for handling content ingestion from various sources.
"""

import uuid
import logging
from typing import Dict, Any, List

from inklink.controllers.base_controller import BaseController
from inklink.utils import is_safe_url

logger = logging.getLogger(__name__)


class IngestController(BaseController):
    """Controller for handling content ingestion requests."""
    
    def __init__(self, handler, services):
        """
        Initialize with HTTP handler and services.
        
        Args:
            handler: BaseHTTPRequestHandler instance
            services: Dictionary of service instances
        """
        super().__init__(handler)
        self.qr_service = services.get("qr_service")
        self.pdf_service = services.get("pdf_service")
        self.web_scraper = services.get("web_scraper")
        self.document_service = services.get("document_service")
        self.remarkable_service = services.get("remarkable_service")
        self.ai_service = services.get("ai_service")
    
    def handle(self, method: str = "POST", path: str = "") -> None:
        """
        Handle content ingestion requests.
        
        Args:
            method: HTTP method
            path: Request path
        """
        if method != "POST":
            self.send_error("Method not allowed", status=405)
            return
            
        # Get request data
        _, json_data = self.read_request_data()
        
        if not json_data:
            self.send_error("Invalid JSON", status=400)
            return
            
        try:
            # Extract required fields
            content_type = json_data.get("type")
            title = json_data.get("title")
            content = json_data.get("content")
            metadata = json_data.get("metadata", {})
            
            if not content_type or not title or not content:
                self.send_error("Missing required fields", status=400)
                return
                
            # Generate a unique ID for tracking
            content_id = str(uuid.uuid4())
            logger.info(f"Ingested content: type={content_type}, title={title}, id={content_id}")
            
            # Generate QR code if source_url is provided in metadata
            qr_path = ""
            source_url = metadata.get("source_url", "")
            if source_url and is_safe_url(source_url):
                try:
                    qr_path, qr_filename = self.qr_service.generate_qr(source_url)
                    logger.info(f"Generated QR code for source URL: {qr_filename}")
                except Exception as e:
                    logger.warning(f"Failed to generate QR code: {str(e)}")
            
            # Process content based on type
            structured_content = self._process_content_by_type(content_type, content)
            
            # Create content package
            content_package = {
                "title": title,
                "structured_content": structured_content,
                "images": [],
            }
            
            # Add any AI processing if needed
            if metadata.get("process_with_ai", False):
                try:
                    context = {k: v for k, v in metadata.items()}
                    ai_response = self.ai_service.process_query(content, context=context)
                    content_package["ai_summary"] = ai_response
                    logger.info(f"Added AI processing for content: {content_id}")
                except Exception as e:
                    logger.warning(f"AI processing failed: {e}")
            
            # Convert to reMarkable document
            rm_path = self.document_service.create_rmdoc_from_content(
                url=source_url or f"inklink:/{content_id}",
                qr_path=qr_path,
                content=content_package,
            )
            
            if not rm_path:
                self.send_error("Failed to create document", status=500)
                return
                
            # Upload to reMarkable if specified
            upload_success = False
            upload_message = ""
            
            if metadata.get("upload_to_remarkable", True):
                upload_success, upload_message = self.remarkable_service.upload(rm_path, title)
                
                if upload_success:
                    logger.info(f"Uploaded to reMarkable: {title}")
                else:
                    logger.error(f"Failed to upload to reMarkable: {upload_message}")
                    
            # Store response for later retrieval
            self.get_server().responses[content_id] = {
                "content_id": content_id,
                "title": title,
                "structured_content": structured_content,
                "uploaded": upload_success,
                "upload_message": upload_message,
                "rm_path": rm_path,
            }
            
            # Return success status with content ID
            self.send_json({
                "status": "processed",
                "content_id": content_id,
                "title": title,
                "uploaded": upload_success,
                "upload_message": (
                    f"Uploaded to reMarkable: {title}"
                    if upload_success
                    else upload_message
                ),
            })
            
        except Exception as e:
            logger.error(f"Error processing content: {str(e)}")
            self.send_error(str(e), status=400)
    
    def _process_content_by_type(self, content_type: str, content: Any) -> List[Dict[str, Any]]:
        """
        Process content based on its type.
        
        Args:
            content_type: Type of content
            content: Content to process
            
        Returns:
            Structured content
        """
        structured_content = []
        
        if content_type == "web":
            # For web content, use as-is if already structured
            if isinstance(content, list):
                structured_content = content
            else:
                # Default to a single paragraph if content is a string
                structured_content = [{"type": "paragraph", "content": content}]
                
        elif content_type == "note":
            # For plain text notes, convert to paragraphs
            paragraphs = content.split("\n\n")
            structured_content = [
                {"type": "paragraph", "content": p.strip()}
                for p in paragraphs
                if p.strip()
            ]
            
        elif content_type == "shortcut":
            # For Siri shortcuts, handle markdown conversion if needed
            if content.startswith("#"):
                # Simple markdown parsing
                lines = content.split("\n")
                current_item = None
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    if line.startswith("# "):
                        structured_content.append(
                            {"type": "h1", "content": line[2:]}
                        )
                    elif line.startswith("## "):
                        structured_content.append(
                            {"type": "h2", "content": line[3:]}
                        )
                    elif line.startswith("### "):
                        structured_content.append(
                            {"type": "h3", "content": line[4:]}
                        )
                    elif line.startswith("- ") or line.startswith("* "):
                        if current_item and current_item["type"] == "list":
                            current_item["items"].append(line[2:])
                        else:
                            current_item = {"type": "list", "items": [line[2:]]}
                            structured_content.append(current_item)
                    else:
                        structured_content.append(
                            {"type": "paragraph", "content": line}
                        )
            else:
                structured_content = [{"type": "paragraph", "content": content}]
        else:
            # Default handling for unknown content types
            structured_content = [{"type": "paragraph", "content": content}]
            
        return structured_content
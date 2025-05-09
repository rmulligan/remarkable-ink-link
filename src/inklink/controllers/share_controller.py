"""Share controller for InkLink.

This module provides a controller for handling URL sharing requests.
"""

import os
import logging
from urllib.parse import quote

from inklink.controllers.base_controller import BaseController
from inklink.utils.url_utils import extract_url

logger = logging.getLogger(__name__)


class ShareController(BaseController):
    """Controller for handling URL sharing requests."""
    
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
        Handle URL sharing requests.
        
        Args:
            method: HTTP method
            path: Request path
        """
        if method != "POST":
            self.send_error("Method not allowed", status=405)
            return
            
        # Get request data
        raw_data, _ = self.read_request_data()
        
        # Extract URL
        url = extract_url(raw_data)
        
        if not url:
            self.send_error("No valid URL found", status=400)
            return
            
        try:
            logger.info(f"Processing URL: {url}")
            
            # Generate QR code
            qr_path, qr_filename = self.qr_service.generate_qr(url)
            logger.info(f"Generated QR code: {qr_filename}")
            
            # Process URL
            if self.pdf_service.is_pdf_url(url):
                self._handle_pdf_url(url, qr_path)
            else:
                self._handle_webpage_url(url, qr_path)
                
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            self.send_error(f"Error processing request: {str(e)}")
    
    def _handle_pdf_url(self, url: str, qr_path: str) -> None:
        """
        Handle PDF URL processing.
        
        Args:
            url: URL to process
            qr_path: Path to QR code
        """
        try:
            # Process PDF
            result = self.pdf_service.process_pdf(url, qr_path)
            
            if not result:
                self.send_error("Failed to process PDF")
                return
                
            # First try RCU-based conversion method if available
            rm_path = self.document_service.create_pdf_rmdoc(
                result["pdf_path"], result["title"], qr_path
            )
            
            # If RCU conversion failed, try HCL-based method with image support
            if not rm_path:
                hcl_path = self.document_service.create_pdf_hcl(
                    result["pdf_path"], result["title"], qr_path, result.get("images")
                )
                
            # If RCU conversion failed, try legacy conversion
            if not rm_path:
                # Create HCL for the PDF
                hcl_path = self.document_service.create_hcl(
                    url, qr_path, {"title": result["title"], "structured_content": []}
                )
                
                if not hcl_path:
                    self.send_error("Failed to create HCL script for PDF")
                    return
                    
                # Convert to Remarkable document
                rm_path = self.document_service.create_rmdoc_legacy(
                    url, qr_path, {"title": result["title"]}
                )
                
                if not rm_path:
                    self.send_error("Failed to convert PDF to Remarkable format")
                    return
                    
            # Upload to Remarkable
            success, message = self.remarkable_service.upload(rm_path, result["title"])
            
            if success:
                # Provide optional download link for the converted PDF ink document
                
                # Create response message
                message = f"PDF uploaded to Remarkable as native ink: {result['title']}"
                
                # Check if client accepts JSON (modern client)
                accept_header = self.get_accept_header()
                if "application/json" in accept_header:
                    # Return JSON response with download link for new clients
                    fname = os.path.basename(rm_path)
                    download_url = f"/download/{quote(fname)}"
                    self.send_json({
                        "success": True,
                        "message": message,
                        "download": download_url,
                    })
                else:
                    # Return plain text response for backward compatibility
                    self.send_success(message)
            else:
                self.send_error(f"Failed to upload PDF: {message}")
                
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            self.send_error(f"Error processing PDF: {str(e)}")
    
    def _handle_webpage_url(self, url: str, qr_path: str) -> None:
        """
        Handle webpage URL processing.
        
        Args:
            url: URL to process
            qr_path: Path to QR code
        """
        try:
            logger.debug(f"Starting _handle_webpage_url for url={url}, qr_path={qr_path}")
            
            # Scrape content
            logger.debug("Calling web_scraper.scrape")
            content = self.web_scraper.scrape(url)
            logger.debug("web_scraper.scrape completed")
            
            # AI processing of main content
            logger.debug("Calling ai_service.process_query on scraped content")
            main_text = ""
            if isinstance(content.get("content"), str):
                main_text = content["content"]
            elif isinstance(content.get("content"), list):
                # Join all text fields if structured as a list of dicts
                main_text = " ".join(
                    item.get("text", "") if isinstance(item, dict) else str(item)
                    for item in content["content"]
                )
            else:
                main_text = str(content)
                
            try:
                # Extract context: all content fields except the main text
                context = {k: v for k, v in content.items() if k != "content"}
                ai_response = self.ai_service.process_query(main_text, context=context)
                logger.debug(f"AI response: {ai_response}")
                content["ai_summary"] = ai_response
            except Exception as e:
                logger.error(f"AI service failed: {e}")
                content["ai_summary"] = "AI processing failed."
                
            # Use new RCU-based direct conversion
            logger.debug("Calling document_service.create_rmdoc_from_content")
            rm_path = self.document_service.create_rmdoc_from_content(
                url, qr_path, content
            )
            logger.debug(f"document_service.create_rmdoc_from_content returned: {rm_path}")
            
            if not rm_path:
                logger.error("Failed to convert to Remarkable format")
                self.send_error("Failed to convert to Remarkable format")
                return
                
            # Upload to Remarkable
            logger.debug("Calling remarkable_service.upload")
            success, message = self.remarkable_service.upload(rm_path, content["title"])
            logger.debug(f"remarkable_service.upload returned: success={success}, message={message}")
            
            if success:
                # Provide optional download link for the converted document
                
                # Create response message
                message = f"Webpage uploaded to Remarkable: {content['title']}"
                
                # Check if client accepts JSON (modern client)
                accept_header = self.get_accept_header()
                if "application/json" in accept_header:
                    # Return JSON response with download link for new clients
                    fname = os.path.basename(rm_path)
                    download_url = f"/download/{quote(fname)}"
                    self.send_json({
                        "success": True,
                        "message": message,
                        "download": download_url,
                    })
                else:
                    # Return plain text response for backward compatibility
                    self.send_success(message)
                logger.info(f"Webpage uploaded to Remarkable: {content['title']}")
            else:
                logger.error(f"Failed to upload document: {message}")
                self.send_error(f"Failed to upload document: {message}")
                
        except Exception as e:
            logger.error(f"Error processing webpage: {str(e)}")
            self.send_error(f"Error processing webpage: {str(e)}")
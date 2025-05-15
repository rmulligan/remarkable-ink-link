"""Share controller for InkLink.

This module provides a controller for handling URL sharing requests.
"""

import logging
import os
from urllib.parse import quote

from inklink.controllers.base_controller import BaseController
from inklink.pipeline.factory import PipelineFactory
from inklink.pipeline.processor import PipelineContext
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
        self.services = services
        self.pipeline_factory = PipelineFactory(services)

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

            # Create pipeline context
            context = PipelineContext(url=url)

            # Create pipeline for URL
            pipeline = self.pipeline_factory.create_pipeline_for_url(url)

            # Process URL through pipeline
            result_context = pipeline.process(context)

            # Check for errors
            if result_context.has_errors():
                logger.error(f"Errors during processing: {result_context.errors}")
                self.send_error(
                    f"Error processing URL: {result_context.errors[0]['message']}"
                )
                return

            # Process successful results
            if result_context.get_artifact("upload_success", False):
                self._handle_successful_upload(result_context)
            else:
                self.send_error(
                    f"Failed to upload: {result_context.get_artifact('upload_message', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            self.send_error(f"Error processing request: {str(e)}")

    def _handle_successful_upload(self, context: PipelineContext) -> None:
        """
        Handle successful upload result.

        Args:
            context: Processed pipeline context
        """
        # Get results from context
        title = context.get_artifact("document_title", context.url)
        rm_path = context.get_artifact("rm_path", "")
        message = f"Document uploaded to Remarkable: {title}"

        # Check if client accepts JSON (modern client)
        accept_header = self.get_accept_header()
        if "application/json" in accept_header:
            # Return JSON response with download link for new clients
            fname = os.path.basename(rm_path)
            download_url = f"/download/{quote(fname)}"
            self.send_json(
                {
                    "success": True,
                    "message": message,
                    "download": download_url,
                }
            )
        else:
            # Return plain text response for backward compatibility
            self.send_success(message)

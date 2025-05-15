"""Ingest controller for InkLink.

This module provides a controller for handling content ingestion from various sources.
"""

import logging
import uuid
from typing import Any, Dict, List

from inklink.controllers.base_controller import BaseController
from inklink.pipeline.factory import PipelineFactory
from inklink.pipeline.processor import PipelineContext

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
        self.services = services
        self.pipeline_factory = PipelineFactory(services)

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
            # Create pipeline context
            context = PipelineContext(content=json_data)

            # Create pipeline for ingested content
            pipeline = self.pipeline_factory.create_ingest_pipeline()

            # Process content through pipeline
            result_context = pipeline.process(context)

            # Check for errors
            if result_context.has_errors():
                logger.error(f"Errors during processing: {result_context.errors}")
                self.send_error(
                    f"Error processing content: {result_context.errors[0]['message']}"
                )
                return

            # Generate response
            content_id = str(uuid.uuid4())

            # Store response for later retrieval
            self.get_server().responses[content_id] = {
                "content_id": content_id,
                "title": result_context.get_artifact("title", "Untitled"),
                "structured_content": result_context.content.get(
                    "structured_content", []
                ),
                "uploaded": result_context.get_artifact("upload_success", False),
                "upload_message": result_context.get_artifact("upload_message", ""),
                "rm_path": result_context.get_artifact("rm_path", ""),
            }

            # Return success status with content ID
            self.send_json(
                {
                    "status": "processed",
                    "content_id": content_id,
                    "title": result_context.get_artifact("title", "Untitled"),
                    "uploaded": result_context.get_artifact("upload_success", False),
                    "upload_message": result_context.get_artifact("upload_message", ""),
                }
            )

        except Exception as e:
            logger.error(f"Error processing content: {str(e)}")
            self.send_error(str(e), status=400)

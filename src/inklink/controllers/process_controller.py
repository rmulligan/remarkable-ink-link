"""Process controller for InkLink.

This module provides a controller for handling file processing requests.
"""

import logging
import uuid
from typing import Any, Dict

from inklink.controllers.base_controller import BaseController

logger = logging.getLogger(__name__)


class ProcessController(BaseController):
    """Controller for handling file processing requests."""

    def handle(self, method: str = "POST", path: str = "") -> None:
        """
        Handle file processing requests.

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

        # Get file_id
        file_id = json_data.get("file_id")

        # Check if file exists
        if not file_id or file_id not in self.get_server().files:
            self.send_error("Invalid file_id", status=400)
            return

        # Process file (simulate for now)
        response_id = self._process_file(file_id)

        # Send response
        self.send_json({"status": "done", "response_id": response_id})

    def _process_file(self, file_id: str) -> str:
        """
        Process a file and return a response ID.

        Args:
            file_id: ID of the file to process

        Returns:
            Response ID
        """
        # Generate response ID
        response_id = str(uuid.uuid4())

        # For demo: just echo file_id as markdown and raw
        md = f"# Processed file {file_id}\n\nAI response here."
        raw = f"RAW_RESPONSE_FOR_{file_id}"

        # Store response
        self.get_server().responses[response_id] = {
            "markdown": md,
            "raw": raw,
        }

        logger.info(f"Processed file {file_id}, response ID: {response_id}")
        return response_id

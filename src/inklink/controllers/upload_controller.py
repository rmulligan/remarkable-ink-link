"""Upload controller for InkLink.

This module provides a controller for handling file upload requests.
"""

import cgi
import logging
import os
import uuid

from inklink.controllers.base_controller import BaseController

logger = logging.getLogger(__name__)


class UploadController(BaseController):
    """Controller for handling file upload requests."""

    def handle(self, method: str = "POST", path: str = "") -> None:
        """
        Handle file upload requests.

        Args:
            method: HTTP method
            path: Request path
        """
        if method != "POST":
            self.send_error("Method not allowed", status=405)
            return

        # Parse multipart form data
        env = {"REQUEST_METHOD": "POST"}
        fs = cgi.FieldStorage(
            fp=self.handler.rfile,
            headers=self.handler.headers,
            environ=env,
            keep_blank_values=True,
        )

        # Get file
        fileitem = fs["file"] if "file" in fs else None

        if not fileitem or not fileitem.file:
            self.send_error("No file uploaded", status=400)
            return

        # Generate file ID and save the file
        file_id = str(uuid.uuid4())
        upload_dir = "/tmp/inklink_uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{file_id}.rm")

        with open(file_path, "wb") as f:
            f.write(fileitem.file.read())

        # Store file path
        self.get_server().files[file_id] = file_path

        # Send response
        self.send_json({"file_id": file_id})
        logger.info(f"Uploaded file {file_id} to {file_path}")

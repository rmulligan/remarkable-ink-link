"""Download controller for InkLink.

This module provides a controller for handling file download requests.
"""

import logging
import os
import re
from urllib.parse import unquote

from inklink.config import CONFIG
from inklink.controllers.base_controller import BaseController

logger = logging.getLogger(__name__)


class DownloadController(BaseController):
    """Controller for handling file download requests."""

    def handle(self, method: str = "GET", path: str = "") -> None:
        """
        Handle download requests.

        Args:
            method: HTTP method
            path: Request path
        """
        if method != "GET":
            self.send_error("Method not allowed", status=405)
            return

        # Get the filename from the path and sanitize it
        fname = unquote(path[len("/download/") :])

        # Prevent path traversal by removing directory components and only allowing specific characters
        safe_fname = re.sub(r"[^a-zA-Z0-9._-]", "", os.path.basename(fname))

        if not safe_fname:
            self.send_error("Invalid filename", status=400)
            return

        temp_dir = CONFIG.get("TEMP_DIR")
        file_path = os.path.join(temp_dir, safe_fname)

        # Verify the file exists and is within the temp directory
        real_path = os.path.realpath(file_path)
        if not real_path.startswith(os.path.realpath(temp_dir)) or not os.path.isfile(
            real_path
        ):
            self.send_error("File not found", status=404)
            return

        # Send file as attachment
        self.send_response()
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Disposition", f'attachment; filename="{safe_fname}"')
        self.end_headers()

        # Stream file in chunks
        with open(real_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                self.handler.wfile.write(chunk)

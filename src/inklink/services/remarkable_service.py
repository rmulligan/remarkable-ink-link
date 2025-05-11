"""Service for interacting with reMarkable Cloud."""

import os
import logging
from typing import Optional, Tuple, Any

from inklink.services.interfaces import IRemarkableService
from inklink.adapters.rmapi_adapter import RmapiAdapter

# Set up logger
logger = logging.getLogger(__name__)


class RemarkableService(IRemarkableService):
    """Service for interacting with reMarkable Cloud using RmapiAdapter."""

    """Service for interacting with reMarkable Cloud using the RemarkableAdapter."""

    def __init__(self, adapter: RmapiAdapter):
        """
        Initialize with paths and folder.

        Args:
            rmapi_path: Path to rmapi executable
            rm_folder: Folder on reMarkable to upload to
        """
        self.adapter = adapter

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connectivity and authentication to reMarkable cloud via rmapi.

        Returns:
            Tuple of (success, message)
        """
        if self.adapter.ping():
            return True, "OK"
        else:
            return False, "Could not connect to reMarkable Cloud"

    def upload(self, doc_path: str, title: str) -> Tuple[bool, str]:
        """
        Upload document to Remarkable Cloud.

        Args:
            doc_path: Path to document file
            title: Document title

        Returns:
            Tuple of (success, message)
        """
        try:
            logger.debug(f"Starting upload: doc_path={doc_path}, title={title}")

            # Validate inputs
            if not os.path.exists(doc_path):
                error_msg = f"Document not found: {doc_path}"
                logger.error(error_msg)
                return False, error_msg

            # Use the adapter to upload the file
            success, message = self.adapter.upload_file(doc_path, title)

            if success:
                logger.info(f"Document uploaded successfully: {title}")
            else:
                logger.error(f"Upload failed: {message}")

            return success, message

        except Exception as e:
            logger.exception(f"Unexpected error in upload process: {e}")
            return False, str(e)

    def get_notebook(
        self, notebook_id: str, export_format: str = "pdf"
    ) -> Optional[bytes]:
        """
        Retrieve a notebook from the reMarkable cloud using rmapi.

        Args:
            notebook_id: The unique identifier of the notebook
            export_format: The format to export (e.g., "pdf", "zip", "raw")

        Returns:
            The notebook data as bytes, or None if retrieval failed
        """
        try:
            import tempfile

            # Create temporary file for download
            with tempfile.NamedTemporaryFile(
                suffix=f".{export_format}", delete=False
            ) as tmpfile:
                output_path = tmpfile.name

            # Download notebook to temporary file
            success, result = self.adapter.download_file(
                notebook_id, output_path, export_format
            )

            if not success:
                logger.error(f"Failed to download notebook: {result}")
                return None

            # Read file contents
            with open(output_path, "rb") as f:
                data = f.read()

            # Clean up temporary file
            try:
                os.unlink(output_path)
            except Exception:
                pass

            logger.info(f"Notebook {notebook_id} retrieved successfully")
            return data

        except Exception as e:
            logger.error(f"Failed to retrieve notebook: {e}")
            return None

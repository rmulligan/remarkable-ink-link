"""reMarkable Cloud API adapter for InkLink.

This module provides an adapter for interacting with the reMarkable Cloud API
via the rmapi command-line tool.
"""

import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from typing import Any, Dict, List, Optional, Tuple

from inklink.adapters.adapter import Adapter
from inklink.utils import format_error, retry_operation

logger = logging.getLogger(__name__)


class RemarkableAdapter(Adapter):
    """Adapter for reMarkable Cloud API via rmapi."""

    def __init__(self, rmapi_path: str, upload_folder: str = "/"):
        """
        Initialize with rmapi path and upload folder.

        Args:
            rmapi_path: Path to rmapi executable
            upload_folder: Folder on reMarkable to upload to
        """
        self.rmapi_path = rmapi_path
        self.upload_folder = upload_folder

    def ping(self) -> bool:
        """
        Check if rmapi is available and authenticated.

        Returns:
            True if available and authenticated, False otherwise
        """
        try:
            result = subprocess.run(
                [self.rmapi_path, "ls"], capture_output=True, text=True, check=False
            )
            return result.returncode == 0
        except Exception:
            return False

    def list_files(self, folder: str = "/") -> Tuple[bool, List[Dict[str, Any]]]:
        """
        List files in the given folder.

        Args:
            folder: Folder path on reMarkable

        Returns:
            Tuple of (success, file_list)
        """
        try:
            result = subprocess.run(
                [self.rmapi_path, "ls", "-j", folder],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                return False, []

            import json

            try:
                files = json.loads(result.stdout)
                return True, files
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON response from rmapi")
                return False, []

        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return False, []

    def upload_file(self, file_path: str, title: str = None) -> Tuple[bool, str]:
        """
        Upload a file to reMarkable Cloud.

        Args:
            file_path: Path to file to upload
            title: Custom title for the file (optional)

        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate inputs
            if not os.path.exists(file_path):
                error_msg = format_error("input", "File not found", file_path)
                logger.error(error_msg)
                return False, error_msg

            # If rmapi is not available, report error
            if not os.path.exists(self.rmapi_path):
                error_msg = f"rmapi executable not found at {self.rmapi_path}"
                logger.error(error_msg)
                return False, error_msg

            # Use title or filename
            if not title:
                title = os.path.basename(file_path)

            # Sanitize title
            title = self._sanitize_filename(title)

            # Use retry for upload
            return retry_operation(
                self._upload_file_internal,
                file_path,
                title,
                operation_name="reMarkable upload",
            )

        except Exception as e:
            error_msg = format_error("upload", "Failed to upload file", e)
            logger.error(error_msg)
            return False, error_msg

    def _upload_file_internal(self, file_path: str, title: str) -> Tuple[bool, str]:
        """
        Internal method to upload a file to reMarkable Cloud.

        Args:
            file_path: Path to file to upload
            title: Custom title for the file

        Returns:
            Tuple of (success, message)
        """
        # Get file extension
        file_ext = os.path.splitext(file_path)[1].lower()
        safe_path = file_path
        using_temp_file = False

        try:
            # If path contains spaces or special characters, create a temporary file
            if any(c in file_path for c in [" ", "(", ")", "'"]):
                temp_dir = tempfile.gettempdir()
                temp_filename = f"upload_{uuid.uuid4().hex[:8]}{file_ext}"
                safe_path = os.path.join(temp_dir, temp_filename)

                # Copy file to temporary location
                shutil.copy2(file_path, safe_path)
                using_temp_file = True
                logger.info(f"Created temporary file for upload: {safe_path}")

            # Upload with custom filename using -n flag
            cmd = [self.rmapi_path, "put", "-n", title, safe_path, self.upload_folder]
            logger.info(f"Running upload command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            # Clean up temporary file if used
            if using_temp_file and os.path.exists(safe_path):
                os.unlink(safe_path)
                logger.info(f"Removed temporary file: {safe_path}")

            if result.returncode == 0:
                logger.info(f"File uploaded successfully: {title}")
                return True, f"File uploaded to reMarkable: {title}"
            else:
                logger.error(f"Upload failed: {result.stderr or result.stdout}")
                return False, result.stderr or result.stdout or "Upload failed"

        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")

            # Clean up temporary file if used
            if using_temp_file and os.path.exists(safe_path):
                os.unlink(safe_path)
                logger.info(f"Removed temporary file: {safe_path}")

            return False, str(e)

    def download_file(
        self, file_id: str, output_path: str = None, format: str = "pdf"
    ) -> Tuple[bool, str]:
        """
        Download a file from reMarkable Cloud.

        Args:
            file_id: ID of file to download
            output_path: Path to save file to (optional)
            format: Format to download as (pdf, epub, zip)

        Returns:
            Tuple of (success, path_or_error)
        """
        try:
            # Create temp file if no output path provided
            if not output_path:
                with tempfile.NamedTemporaryFile(
                    suffix=f".{format}", delete=False
                ) as tmpfile:
                    output_path = tmpfile.name

            # Build command
            cmd = [
                self.rmapi_path,
                "get",
                file_id,
                output_path,
                "--format",
                format,
            ]

            # Run command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                logger.info(f"File downloaded successfully: {output_path}")
                return True, output_path
            else:
                logger.error(f"Download failed: {result.stderr}")
                return False, result.stderr or "Download failed"

        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            return False, str(e)

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """
        Sanitize filename for reMarkable.

        Args:
            filename: Filename to sanitize

        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")
        return filename

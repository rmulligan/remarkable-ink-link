import os
import subprocess
import logging
import shutil
import uuid
import tempfile
from typing import Optional, Tuple, Any
from .interfaces import IRemarkableService

# Import utility functions for error handling
from inklink.utils import retry_operation, format_error

# Set up logger
logger = logging.getLogger(__name__)


class RemarkableService(IRemarkableService):
    def __init__(self, rmapi_path: str, upload_folder: str = "/"):
        self.rmapi_path = rmapi_path
        self.upload_folder = upload_folder

    # First implementation removed - keeping only the version with retry functionality
    def upload(self, doc_path: str, title: str) -> Tuple[bool, str]:
        """Upload document to Remarkable Cloud"""
        try:
            # Validate inputs
            if not os.path.exists(doc_path):
                error_msg = format_error("input", "Document not found", doc_path)
                logger.error(error_msg)
                return False, error_msg

            # If rmapi is not available, report error
            if not os.path.exists(self.rmapi_path):
                # rmapi tool is required for upload
                error_msg = f"rmapi executable not found at {self.rmapi_path}"
                logger.error(error_msg)
                return False, error_msg

            # Use the upload method with retries from the central utility
            sanitized_title = self._sanitize_filename(title)
            try:
                success, message = retry_operation(
                    self._upload_with_n_flag,
                    doc_path,
                    sanitized_title,
                    operation_name="Remarkable upload",
                )

                if success:
                    logger.info(f"Document uploaded successfully: {title}")
                    return True, f"Document uploaded to Remarkable: {title}"
                else:
                    logger.error(f"Upload failed: {message}")
                    return False, message
            except Exception as e:
                error_msg = format_error("upload", "Failed after multiple attempts", e)
                logger.error(error_msg)
                return False, error_msg

        except Exception as e:
            error_msg = format_error("system", "Unexpected error in upload process", e)
            logger.exception(error_msg)
            return False, error_msg

    def _upload_with_n_flag(self, doc_path: str, title: str) -> Tuple[bool, str]:
        """Upload document to Remarkable Cloud with custom title

        Args:
            doc_path: Path to the document file
            title: Custom title for the document on Remarkable

        Returns:
            Tuple of (success, message)
        """
        import json
        # Get file extension to handle the file correctly
        file_ext = os.path.splitext(doc_path)[1].lower()
        safe_path = doc_path
        using_temp_file = False

        try:
            # If the path contains spaces or special characters, create a temporary file
            if any(c in doc_path for c in [" ", "(", ")", "'"]):
                temp_dir = tempfile.gettempdir()
                temp_filename = f"upload_{uuid.uuid4().hex[:8]}{file_ext}"
                safe_path = os.path.join(temp_dir, temp_filename)

                # Copy the file to the temporary location
                shutil.copy2(doc_path, safe_path)
                using_temp_file = True
                logger.info(f"Created temporary file for upload: {safe_path}")

            # Upload with custom filename using -n flag
            cmd = [self.rmapi_path, "put", "-n", title, safe_path, self.upload_folder]
            logger.info(f"Running upload command with title '{title}': {' '.join(cmd)}")

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                logger.info(f"Command exit code: {result.returncode}")
                if result.stdout:
                    logger.info(f"Command stdout: {result.stdout}")
                if result.stderr:
                    logger.warning(f"Command stderr: {result.stderr}")

                if result.returncode == 0:
                    logger.info(f"Document uploaded with name: {title}")
                else:
                    logger.error(f"Upload failed: {result.stderr or result.stdout}")

                if using_temp_file and os.path.exists(safe_path):
                    os.unlink(safe_path)
                    logger.info(f"Removed temporary file: {safe_path}")
                return result.returncode == 0, f"Document uploaded to Remarkable: {title}"
            except subprocess.SubprocessError as se:
                logger.error(f"Subprocess error: {str(se)}")
                return False, f"Subprocess error: {str(se)}"
        except Exception as e:
            logger.exception(f"Exception in upload method: {e}")
            if using_temp_file and os.path.exists(safe_path):
                os.unlink(safe_path)
                logger.info(f"Removed temporary file after exception: {safe_path}")
            return False, f"Upload preparation error: {str(e)}"

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for Remarkable"""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")
        return filename.strip()

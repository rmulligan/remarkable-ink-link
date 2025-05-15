"""HCL renderer for InkLink.

This module provides a renderer that creates HCL scripts for
the drawj2d tool to generate reMarkable-compatible documents.
"""

import logging
import os
import subprocess
import time
from typing import Any, Dict, Optional

from inklink.config import CONFIG
from inklink.services.interfaces import IDocumentRenderer
from inklink.utils import format_error, retry_operation

logger = logging.getLogger(__name__)


class HCLRenderer(IDocumentRenderer):
    """Creates reMarkable documents from HCL scripts using drawj2d."""

    def __init__(self, temp_dir: str, drawj2d_path: Optional[str] = None):
        """
        Initialize with temporary directory and drawj2d path.

        Args:
            temp_dir: Directory for temporary files
            drawj2d_path: Path to drawj2d executable
        """
        self.temp_dir = temp_dir
        self.drawj2d_path = drawj2d_path or CONFIG.get("DRAWJ2D_PATH")

        # Validate drawj2d executable
        if not self.drawj2d_path or not os.path.exists(self.drawj2d_path):
            logger.warning("drawj2d path not available. HCL rendering will fail.")

    def render(
        self, content: Dict[str, Any], output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Render HCL content to reMarkable format.

        Args:
            content: Dictionary containing:
                     - hcl_path: Path to HCL script
                     - url: Source URL (for generating filenames)
            output_path: Optional explicit output path

        Returns:
            Path to generated .rm file or None if failed
        """
        try:
            hcl_path = content.get("hcl_path")
            url = content.get("url", "")

            if not hcl_path or not os.path.exists(hcl_path):
                logger.error(f"HCL file not found: {hcl_path}")
                return None

            # Generate output path if not provided
            if not output_path:
                timestamp = int(time.time())
                rm_filename = f"rm_{hash(url)}_{timestamp}.rm"
                output_path = os.path.join(self.temp_dir, rm_filename)

            return self._convert_to_remarkable(hcl_path, output_path)

        except Exception as e:
            logger.error(f"Error rendering HCL: {str(e)}")
            return None

    def _convert_to_remarkable(self, hcl_path: str, rm_path: str) -> Optional[str]:
        """
        Convert HCL file to Remarkable format using drawj2d.

        Args:
            hcl_path: Path to HCL script
            rm_path: Path for output reMarkable file

        Returns:
            Path to generated .rm file or None if failed
        """
        try:
            logger.info(f"Starting conversion from {hcl_path} to {rm_path}")

            # Validate drawj2d executable
            if not os.path.isfile(self.drawj2d_path) or not os.access(
                self.drawj2d_path, os.X_OK
            ):
                logger.error(
                    f"drawj2d executable not found or not executable at: {self.drawj2d_path}"
                )
                return None

            # Log drawj2d version for compatibility checking
            try:
                version_cmd = [self.drawj2d_path, "--version"]
                version_result = subprocess.run(
                    version_cmd, capture_output=True, text=True, check=False
                )
                logger.info(f"drawj2d version: {version_result.stdout.strip()}")
            except Exception as e:
                logger.warning(f"Could not determine drawj2d version: {e}")

            # Input validation
            if not os.path.exists(hcl_path):
                error_msg = format_error("input", "HCL file not found", hcl_path)
                logger.error(error_msg)
                return None

            # Ensure output directory exists
            output_dir = os.path.dirname(rm_path)
            if not os.path.exists(output_dir):
                logger.info(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)

            # Use parameters for raw reMarkable page format
            # -Trm: Target is raw reMarkable page format
            # -rmv6: Use version 6 file format
            # -o: Specify output file
            # Explicitly specify frontend as HCL and output type RM
            cmd = [
                self.drawj2d_path,
                "-F",
                "hcl",
                "-T",
                "rm",
                "-rmv6",
                "-o",
                rm_path,
                hcl_path,
            ]
            logger.info(f"Conversion command: {' '.join(cmd)}")

            # Define the conversion function that will be retried if it fails
            def run_conversion(cmd_args):
                logger.info(f"Running drawj2d conversion: {' '.join(cmd_args)}")

                # Running the conversion using subprocess.run for better error handling
                result = subprocess.run(cmd_args, capture_output=True, text=True)
                logger.info(f"Command stdout: {result.stdout}")
                logger.info(f"Command stderr: {result.stderr}")

                if result.returncode != 0:
                    raise RuntimeError(
                        f"drawj2d conversion failed: Exit code {result.returncode}, stderr: {result.stderr}"
                    )

                if not os.path.exists(rm_path):
                    logger.error(
                        f"Output file missing: {rm_path}, even though command reported success"
                    )
                    raise FileNotFoundError(
                        f"Expected output file not created: {rm_path}"
                    )
                else:
                    file_size = os.path.getsize(rm_path)
                    logger.info(
                        f"Output file successfully created: {rm_path} ({file_size} bytes)"
                    )
                    if file_size < 50:
                        logger.error(
                            f"Output file size is suspiciously small: {file_size} bytes. Possible conversion error."
                        )
                        raise ValueError(f"Output file too small: {file_size} bytes")
                    with open(rm_path, "rb") as rf:
                        preview = rf.read(100)
                    logger.info(f"Output file preview (first 100 bytes): {preview}")

                return rm_path

            # Use retry operation for running the conversion
            return retry_operation(
                run_conversion,
                cmd,
                operation_name="Document conversion",
                max_retries=2,  # Only retry a couple of times for conversion
            )
        except Exception as e:
            logger.error(format_error("conversion", "Failed to convert document", e))
            return None

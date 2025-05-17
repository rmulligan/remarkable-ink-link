"""Service for interacting with drawj2d to generate colored ink from HCL scripts.

This service provides a high-level interface for:
1. Converting HCL scripts to reMarkable documents using drawj2d
2. Managing drawj2d configuration and execution
3. Handling color syntax highlighting for source code
"""

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from inklink.config import CONFIG

logger = logging.getLogger(__name__)


class Drawj2dService:
    """Service for generating reMarkable documents using drawj2d."""

    def __init__(self, drawj2d_path: Optional[str] = None):
        """
        Initialize the drawj2d service.

        Args:
            drawj2d_path: Optional path to drawj2d executable
        """
        self.drawj2d_path = drawj2d_path or CONFIG.get("DRAWJ2D_PATH", "drawj2d")

        # Verify drawj2d is available
        if not self._verify_drawj2d():
            raise RuntimeError(f"drawj2d not found at: {self.drawj2d_path}")

    def _verify_drawj2d(self) -> bool:
        """Verify that drawj2d is available and executable."""
        try:
            result = subprocess.run(
                [self.drawj2d_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def process_hcl(
        self,
        hcl_path: str,
        output_format: str = "rmdoc",
        output_path: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Process an HCL file with drawj2d to generate reMarkable format.

        Args:
            hcl_path: Path to the HCL script file
            output_format: Output format (rm, rmdoc, pdf, etc.)
            output_path: Optional output path (auto-generated if not provided)

        Returns:
            Tuple of (success, result dict) where result contains:
                - output_path: Path to generated file
                - stdout: Command output
                - stderr: Command errors
                - duration: Processing time in seconds
        """
        try:
            # Verify input file exists
            if not os.path.exists(hcl_path):
                return False, {"error": f"HCL file not found: {hcl_path}"}

            # Generate output path if not provided
            if not output_path:
                base_name = Path(hcl_path).stem
                output_ext = "rmdoc" if output_format == "rmdoc" else "rm"
                output_path = os.path.join(
                    os.path.dirname(hcl_path), f"{base_name}.{output_ext}"
                )

            # Build drawj2d command
            cmd = [
                self.drawj2d_path,
                "-F",
                "hcl",  # Input format is HCL
                "-T",
                output_format,  # Output format
                "-o",
                output_path,
                hcl_path,  # Output file
            ]

            logger.info(f"Executing drawj2d: {' '.join(cmd)}")

            # Execute drawj2d
            start_time = os.times()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                check=True,
            )
            end_time = os.times()

            duration = end_time.elapsed - start_time.elapsed

            if result.returncode == 0:
                logger.info(f"drawj2d processed successfully: {output_path}")
                return True, {
                    "output_path": output_path,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "duration": duration,
                }
            logger.error(f"drawj2d failed with code {result.returncode}")
            return False, {
                "error": f"drawj2d failed with code {result.returncode}",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": duration,
            }

        except subprocess.TimeoutExpired:
            logger.error("drawj2d command timed out")
            return False, {"error": "drawj2d command timed out"}
        except Exception as e:
            logger.error(f"Error running drawj2d: {e}")
            return False, {"error": str(e)}

    @staticmethod
    def create_test_hcl(output_dir: Optional[str] = None) -> str:
        """
        Create a basic test HCL file for verification.

        Args:
            output_dir: Directory to save the test file (temp dir if not provided)

        Returns:
            Path to the created test HCL file
        """
        if not output_dir:
            output_dir = tempfile.gettempdir()

        test_hcl_path = os.path.join(output_dir, "test_basic.hcl")

        # Create test HCL content as specified in the plan
        hcl_content = """# test_basic.hcl
font LinesMono 3.0
m 10 10
pen black
text {Hello reMarkable!}
m 10 20
text {This is drawj2d.}
"""

        with open(test_hcl_path, "w") as f:
            f.write(hcl_content)

        logger.info(f"Created test HCL file: {test_hcl_path}")
        return test_hcl_path

    def render_syntax_highlighted_code(
        self, code: str, language: str, output_format: str = "rmdoc", **options
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Render syntax-highlighted code to reMarkable format.

        This is a placeholder for the full syntax highlighting pipeline
        that will be implemented in later phases.

        Args:
            code: Source code to render
            language: Programming language
            output_format: Output format (rm, rmdoc)
            **options: Additional options (font_size, color_scheme, etc.)

        Returns:
            Tuple of (success, result dict)
        """
        # For now, just create a simple HCL with the code
        with tempfile.NamedTemporaryFile(mode="w", suffix=".hcl", delete=False) as f:
            f.write(f"# Code in {language}\n")
            f.write("font LinesMono 3.0\n")
            f.write("m 10 10\n")
            f.write("pen black\n")

            # Simple line-by-line rendering for now
            y_pos = 10
            for line in code.split("\n"):
                if line.strip():  # Skip empty lines for now
                    f.write(f"m 10 {y_pos}\n")
                    # Escape braces in the text
                    escaped_line = line.replace("{", "{{").replace("}", "}}")
                    f.write(f"text {{{escaped_line}}}\n")
                y_pos += 10

            hcl_path = f.name

        # Process with drawj2d
        success, result = self.process_hcl(hcl_path, output_format)

        # Clean up temp file
        try:
            os.unlink(hcl_path)
        except OSError as e:
            self.logger.warning(f"Failed to delete temp file {hcl_path}: {e}")

        return success, result


# Singleton instance
_drawj2d_service = None


def get_drawj2d_service() -> Drawj2dService:
    """Get the singleton drawj2d service instance."""
    global _drawj2d_service
    if _drawj2d_service is None:
        _drawj2d_service = Drawj2dService()
    return _drawj2d_service

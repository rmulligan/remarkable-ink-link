"""Handwriting recognition adapter for InkLink.

This module provides an adapter for handwriting recognition services
using Claude's vision capabilities through the CLI tool.
"""

import os
import logging
import tempfile
from typing import Dict, Any, Optional, List, Tuple

from inklink.adapters.adapter import Adapter
from inklink.adapters.claude_vision_adapter import ClaudeVisionAdapter

logger = logging.getLogger(__name__)


class HandwritingAdapter(Adapter):
    """Adapter for handwriting recognition using Claude Vision CLI."""

    def __init__(self, claude_command: str = None, model: str = None, **kwargs):
        """
        Initialize with CLI command info.

        Args:
            claude_command: Command to invoke Claude CLI
            model: Claude model to use (if needed)
        """
        self.claude_command = claude_command or os.environ.get(
            "CLAUDE_COMMAND", "claude"
        )
        self.model = model

        # Create the Claude Vision adapter
        self.vision_adapter = ClaudeVisionAdapter(
            claude_command=self.claude_command, model=self.model
        )
        self.initialized = self.vision_adapter.is_available()

        if self.initialized:
            logger.info("Claude Vision adapter initialized successfully")
        else:
            logger.warning(
                "Claude Vision adapter initialization failed or CLI not available"
            )

    def ping(self) -> bool:
        """
        Check if the handwriting recognition service is available.

        Returns:
            True if available and initialized, False otherwise
        """
        return self.vision_adapter.is_available() if self.vision_adapter else False

    def initialize_sdk(self, claude_command: str, model: str = None) -> bool:
        """
        Initialize the adapter with a new command/model.

        Args:
            claude_command: Command to invoke Claude CLI
            model: Claude model to use (optional)

        Returns:
            True if initialized successfully, False otherwise
        """
        # Store the values
        self.claude_command = claude_command
        if model:
            self.model = model

        # Reinitialize the adapter
        self.vision_adapter = ClaudeVisionAdapter(
            claude_command=self.claude_command, model=self.model
        )
        self.initialized = self.vision_adapter.is_available()

        if self.initialized:
            logger.info("Claude Vision adapter initialized successfully")
            return True
        else:
            logger.warning("Claude Vision adapter initialization failed")
            return False

    def extract_strokes_from_rm_file(self, rm_file_path: str) -> List[Dict[str, Any]]:
        """
        Extract strokes from a reMarkable file.

        This function is maintained for compatibility with existing code,
        but the Claude Vision approach will render the file to an image
        rather than use the strokes directly.

        Args:
            rm_file_path: Path to .rm file

        Returns:
            List of stroke dictionaries
        """
        try:
            # Import rmscene for parsing .rm files
            try:
                import rmscene
                from rmscene.scene_stream import read_tree
                from rmscene.scene_items import Line
            except ImportError:
                logger.error("rmscene not installed - cannot parse .rm files")
                return []

            # Parse .rm file using current rmscene API (v0.7.0+)
            with open(rm_file_path, "rb") as f:
                try:
                    # Try using the newer rmscene API
                    scene_tree = read_tree(f)

                    # Convert strokes to a simple format
                    strokes = []

                    # Find all Line items in the tree
                    for item_id, item in scene_tree.items.items():
                        if isinstance(item, Line):
                            # Extract x, y, pressure and timestamps for each point
                            x_points = []
                            y_points = []
                            pressures = []
                            timestamps = []

                            for point in item.points:
                                x_points.append(point.x)
                                y_points.append(point.y)
                                pressures.append(point.pressure)
                                # Use 't' attribute for timestamp in newer API
                                timestamps.append(point.t if hasattr(point, "t") else 0)

                            # Create stroke in simple format
                            stroke = {
                                "id": str(item_id),
                                "x": x_points,
                                "y": y_points,
                                "p": pressures,
                                "t": timestamps,
                                "color": (
                                    str(item.color)
                                    if hasattr(item, "color")
                                    else "#000000"
                                ),
                                "width": (
                                    float(item.pen.value)
                                    if hasattr(item, "pen")
                                    else 2.0
                                ),
                            }

                            strokes.append(stroke)

                    if strokes:
                        logger.info(
                            f"Extracted {len(strokes)} strokes using current rmscene API"
                        )
                        return strokes
                    else:
                        logger.warning(
                            "No strokes found in file using current rmscene API"
                        )

                except Exception as scene_tree_error:
                    logger.error(
                        f"Failed to use current rmscene API: {scene_tree_error}"
                    )
                    return []

            return []

        except Exception as e:
            logger.error(f"Failed to extract strokes from .rm file: {e}")
            return []

    def render_rm_file(self, rm_file_path: str) -> str:
        """
        Render a reMarkable file to a PNG image.

        Args:
            rm_file_path: Path to the .rm file

        Returns:
            Path to the rendered PNG image
        """
        try:
            from handwriting_model.render_rm_file import (
                load_rm_file,
                extract_strokes,
                render_strokes,
            )

            # Create temp file for output
            fd, output_path = tempfile.mkstemp(suffix=".png")
            os.close(fd)

            # Load and render the file
            scene = load_rm_file(rm_file_path)
            if not scene:
                raise ValueError(f"Failed to load .rm file: {rm_file_path}")

            strokes = extract_strokes(scene)

            # Use default reMarkable dimensions
            width = 1404  # Default reMarkable width
            height = 1872  # Default reMarkable height
            dpi = 300  # Default rendering DPI

            render_strokes(strokes, output_path, width, height, dpi)
            logger.info(f"Rendered .rm file to {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"Error rendering .rm file: {e}")
            raise

    def recognize_handwriting(
        self,
        image_path: str,
        content_type: str = "Text",
        language: str = "en_US",
    ) -> Dict[str, Any]:
        """
        Process image and return recognition results.

        Args:
            image_path: Path to the rendered image
            content_type: Content type (Text, Diagram, Math, etc.)
            language: Language code

        Returns:
            Recognition results
        """
        # Get appropriate prompt based on content type
        prompt = self._get_content_type_prompt(content_type, language)

        # Process with Claude Vision
        success, result = self.vision_adapter.process_image(
            image_path, prompt, content_type
        )

        if success:
            import time

            result_id = f"vision-{int(time.time())}"
            return {
                "success": True,
                "content_id": result_id,
                "result": result,
                "content_type": content_type,
            }
        else:
            return {"success": False, "error": result}

    def _get_content_type_prompt(self, content_type: str, language: str) -> str:
        """
        Get appropriate prompt based on content type and language.

        Args:
            content_type: Content type (Text, Diagram, Math)
            language: Language code

        Returns:
            Tailored prompt for Claude
        """
        lang_prefix = ""
        if language and language != "en_US":
            lang_prefix = f"The content is written in {language}. "

        if not content_type or content_type.lower() == "text":
            return f"{lang_prefix}Please transcribe the handwritten text in this image. Maintain the formatting structure as much as possible."
        elif content_type.lower() == "math":
            return f"{lang_prefix}Please transcribe the handwritten mathematical content in this image. Represent equations using LaTeX notation."
        elif content_type.lower() == "diagram":
            return f"{lang_prefix}Please describe the diagram or drawing in this image. Identify key elements, connections, and any labeled components."
        else:
            return f"{lang_prefix}Please transcribe the content in this image, preserving its structure and meaning."

    def export_content(
        self, content_id: str, format_type: str = "text"
    ) -> Dict[str, Any]:
        """
        Export recognized content in the specified format.

        Args:
            content_id: Content ID from recognition result
            format_type: Format type (text, json, etc.)

        Returns:
            Exported content
        """
        try:
            # If content_id is a string, try to parse it as JSON
            if isinstance(content_id, str):
                try:
                    import json

                    content = json.loads(content_id)
                except (json.JSONDecodeError, TypeError):
                    # If not valid JSON, return as is
                    return {"content": content_id, "format": format_type}
            else:
                content = content_id

            # Extract the main recognition result
            text = ""
            if isinstance(content, dict):
                if "result" in content:
                    text = content["result"]
                elif "content" in content:
                    text = content["content"]
            else:
                text = str(content)

            return {"content": text, "format": format_type}

        except Exception as e:
            logger.error(f"Failed to export content: {e}")
            return {"error": str(e)}

    def process_rm_file(
        self, rm_file_path: str, content_type: str = "Text", language: str = "en_US"
    ) -> Dict[str, Any]:
        """
        Process a reMarkable file and return recognized text.

        Args:
            rm_file_path: Path to .rm file
            content_type: Content type (Text, Diagram, Math, etc.)
            language: Language code

        Returns:
            Recognition results
        """
        try:
            # Check if file exists
            if not os.path.exists(rm_file_path):
                logger.error(f"File not found: {rm_file_path}")
                return {"error": "File not found"}

            # Render the .rm file to an image
            image_path = self.render_rm_file(rm_file_path)

            try:
                # Process the image with Claude Vision
                result = self.recognize_handwriting(image_path, content_type, language)
                return result
            finally:
                # Clean up the temporary image file
                if os.path.exists(image_path):
                    os.unlink(image_path)

        except Exception as e:
            logger.error(f"Failed to process .rm file: {e}")
            return {"error": str(e)}

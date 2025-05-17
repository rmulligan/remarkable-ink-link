"""Handwriting recognition service using Claude Vision CLI."""

import logging
import os
import re
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import requests

from inklink.adapters.claude_vision_adapter import ClaudeVisionAdapter
from inklink.config import CONFIG
from inklink.services.interfaces import IHandwritingRecognitionService
from inklink.utils import format_error

logger = logging.getLogger(__name__)


class HandwritingRecognitionService(IHandwritingRecognitionService):
    """
    Service for handwriting recognition using Claude Vision CLI.
    Uses the ClaudeVisionAdapter to interact with Claude's vision capabilities.
    """

    def __init__(
        self,
        claude_command: Optional[str] = None,
        model: Optional[str] = None,
        handwriting_adapter: Optional[ClaudeVisionAdapter] = None,
    ):
        """
        Initialize the handwriting recognition service.

        Args:
            claude_command: Optional command to invoke Claude CLI
            model: Optional model specification for Claude CLI
            handwriting_adapter: Optional pre-configured adapter
        """
        # Get command from environment variables or config
        self.claude_command = (
            claude_command
            or os.environ.get("CLAUDE_COMMAND")
            or CONFIG.get("CLAUDE_COMMAND", "/home/ryan/.claude/local/claude")
        )
        self.model = (
            model or os.environ.get("CLAUDE_MODEL") or CONFIG.get("CLAUDE_MODEL", "")
        )

        logger.info("Using Claude Vision CLI for handwriting recognition")

        # Use provided adapter or create a new one
        self.adapter = handwriting_adapter or ClaudeVisionAdapter(
            claude_command=self.claude_command, model=self.model
        )

        if not self.adapter.ping():
            logger.warning(
                "Claude CLI not available or configured correctly; handwriting recognition may not function"
            )

    def classify_region(self, image_path: str) -> str:
        """
        Classify a region as 'text', 'math', or 'diagram' based on content.
        Uses a simple prompt to Claude Vision.

        Args:
            image_path: Path to rendered image

        Returns:
            Content type classification ("Text", "Math", or "Diagram")
        """
        if not self.adapter.ping():
            # Default to Text if classification is not available
            return "Text"

        result = self.adapter.recognize_handwriting(
            image_path, "classification", "en_US"
        )

        if result.get("success", False):
            text = result.get("result", "").strip().lower()
            if "math" in text:
                return "Math"
            if "diagram" in text:
                return "Diagram"
            return "Text"
        else:
            # Default to Text on failure
            return "Text"

    def initialize_api(self, claude_command: str, model: str = None) -> bool:
        """
        Initialize the adapter with a new command/model.

        Args:
            claude_command: Command to invoke Claude CLI
            model: Claude model specification (optional)

        Returns:
            True if initialized successfully, False otherwise
        """
        try:
            self.claude_command = claude_command
            if model:
                self.model = model

            # Use the adapter to initialize
            success = self.adapter.initialize_sdk(claude_command, model)

            if success:
                logger.info("Claude Vision CLI initialized successfully")
            else:
                logger.error("Failed to initialize Claude Vision CLI")

            return success

        except Exception as e:
            logger.error(f"Error initializing Claude Vision CLI: {e}")
            return False

    # Alias for backward compatibility
    initialize_iink_sdk = initialize_api

    # NOTE: The convert_to_iink_format method has been removed here as it was duplicated.
    # The full implementation is provided later in this file.

    def extract_strokes(self, rm_file_path: str) -> List[Dict[str, Any]]:
        """
        Extract strokes from a reMarkable file.

        This is maintained for compatibility but isn't directly used
        for recognition with Claude Vision.

        Args:
            rm_file_path: Path to .rm file

        Returns:
            List of stroke dictionaries
        """
        try:
            # Use the adapter to extract strokes
            strokes = self.adapter.extract_strokes_from_rm_file(rm_file_path)

            if strokes:
                logger.info(f"Extracted {len(strokes)} strokes from {rm_file_path}")
            else:
                logger.warning(f"No strokes extracted from {rm_file_path}")

            return strokes

        except Exception as e:
            logger.error(f"Error extracting strokes from {rm_file_path}: {e}")
            return []

    def recognize_handwriting(
        self,
        image_path: str,
        content_type: str = "Text",
        language: str = "en_US",
    ) -> Dict[str, Any]:
        """
        Process an image through Claude Vision CLI and return recognition results.

        Args:
            image_path: Path to the image file
            content_type: Content type (Text, Diagram, Math, etc.)
            language: Language code

        Returns:
            Recognition results
        """
        try:
            if not self.adapter.ping():
                raise ValueError(
                    "Claude CLI not available; cannot recognize handwriting"
                )

            # Use the adapter to recognize handwriting
            result = self.adapter.recognize_handwriting(
                image_path, content_type, language
            )

            # Handle error cases
            if not result.get("success", False):
                logger.error(
                    f"Recognition failed: {result.get('error', 'Unknown error')}"
                )
                return {
                    "success": False,
                    "error": result.get("error", "Recognition failed"),
                }

            # Format the result for consistency
            return {
                "success": True,
                "content_id": result.get("content_id", ""),
                "text": result.get("result", ""),
                "raw_result": result,
            }

        except (ValueError, KeyError, TypeError) as e:
            error_msg = format_error("recognition", "Data processing error", e)
            logger.error(error_msg)
            return {"success": False, "error": str(e)}
        except requests.exceptions.RequestException as e:
            error_msg = format_error(
                "recognition", "Network error during recognition", e
            )
            logger.error(error_msg)
            return {"success": False, "error": str(e)}
        except Exception as e:
            error_msg = format_error(
                "recognition", "Unexpected error during recognition", e
            )
            logger.error(error_msg)
            return {"success": False, "error": str(e)}

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
            if not self.adapter.ping():
                raise ValueError("Claude CLI not available; cannot export content")

            # Use the adapter to export content
            result = self.adapter.export_content(content_id, format_type)

            # Handle error cases
            if "error" in result:
                logger.error(f"Export failed: {result['error']}")
                return {"success": False, "error": result["error"]}

            logger.info(f"Export successful: {format_type}")
            return {"success": True, "content": result}

        except ValueError as e:
            error_msg = format_error("export", "Validation error", e)
            logger.error(error_msg)
            return {"success": False, "error": str(e)}
        except KeyError as e:
            error_msg = format_error("export", "Missing required data", e)
            logger.error(error_msg)
            return {"success": False, "error": str(e)}
        except Exception as e:
            error_msg = format_error("export", "Unexpected export error", e)
            logger.error(error_msg)
            return {"success": False, "error": str(e)}

    def recognize_from_ink(
        self,
        ink_data: Optional[bytes] = None,
        file_path: Optional[str] = None,
        content_type: Optional[str] = None,
        language: str = "en_US",
    ) -> Dict[str, Any]:
        """
        High-level method: Accepts ink data or file path, renders to image,
        and performs recognition with Claude Vision CLI.

        Args:
            ink_data: Binary ink data
            file_path: Path to .rm file
            content_type: Content type (Text, Diagram, Math) or 'auto'
            language: Language code

        Returns:
            Recognition results
        """
        try:
            # Handle the case where ink_data is provided (save to temp file)
            if ink_data is not None:
                fd, temp_path = tempfile.mkstemp(suffix=".rm")
                os.close(fd)
                with open(temp_path, "wb") as f:
                    f.write(ink_data)
                use_path = temp_path
            elif file_path is not None:
                use_path = file_path
            else:
                raise ValueError("Either ink_data or file_path must be provided")

            try:
                # Process the file with the adapter
                result = self.adapter.process_rm_file(
                    use_path, content_type or "Text", language
                )
                return result
            finally:
                # Clean up temporary file if created
                if ink_data is not None and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except Exception as e:
                        logger.warning(f"Failed to remove temporary file: {e}")

        except Exception as e:
            logger.error(f"Handwriting recognition pipeline failed: {e}")
            return {"success": False, "error": str(e)}

    def recognize_multi_page_ink(
        self,
        page_files: List[str],
        language: str = "en_US",
        user_links: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Recognize handwriting from multiple page files, maintaining per-page and cross-page context.

        Args:
            page_files: List of file paths, each representing a handwritten page
            language: Language code for recognition
            user_links: Optional user-defined cross-page links, e.g.,
                [{"from_page": 1, "to_page": 2, "type": "reference", "label": "See Figure 1"}]

        Returns:
            Structured content with per-page items and cross-page links
        """
        if not page_files:
            return {"pages": [], "cross_page_links": []}

        structured_pages = []
        cross_page_links = user_links[:] if user_links else []

        # Render all pages to images
        rendered_images = []
        try:
            for rm_file in page_files:
                image_path = self.adapter.render_rm_file(rm_file)
                rendered_images.append(image_path)

            # Generate a prompt for multi-page processing
            prompt = f"""
            I'm sharing multiple pages from a handwritten notebook written in {language}.
            Please transcribe the content, maintaining context between pages.
            Treat these as continuous content from the same document.
            Clearly indicate where each page begins and ends by using "PAGE X:" markers.
            """

            # Use the adapter to process multiple images at once if supported
            if hasattr(self.adapter.vision_adapter, "process_multiple_images"):
                success, combined_result = (
                    self.adapter.vision_adapter.process_multiple_images(
                        rendered_images, prompt, maintain_context=True
                    )
                )

                if not success:
                    return {"success": False, "error": combined_result}

                # Process the combined result - split into pages by markers
                page_sections = self._split_multi_page_result(
                    combined_result, len(page_files)
                )

                for i, page_content in enumerate(page_sections):
                    structured_pages.append(
                        {
                            "page_number": i + 1,
                            "items": [{"type": "text", "content": page_content}],
                            "metadata": {},
                        }
                    )

                    # Look for cross-references
                    ref_matches = re.findall(
                        r"(see|refer to) page (\d+)", page_content, re.IGNORECASE
                    )
                    for _, ref_page in ref_matches:
                        ref_page_num = int(ref_page)
                        if 1 <= ref_page_num <= len(page_files) and ref_page_num != (
                            i + 1
                        ):
                            link = {
                                "from_page": i + 1,
                                "to_page": ref_page_num,
                                "type": "auto_reference",
                                "label": f"Reference to page {ref_page_num}",
                            }
                            cross_page_links.append(link)
            else:
                # Process pages individually
                for i, image_path in enumerate(rendered_images):
                    # page_prompt = f"Please transcribe the handwritten content on this page (Page {i + 1})."  # Currently unused
                    result = self.adapter.recognize_handwriting(
                        image_path, "Text", language
                    )

                    if result.get("success", False):
                        content = result.get("result", "")
                        structured_pages.append(
                            {
                                "page_number": i + 1,
                                "items": [{"type": "text", "content": content}],
                                "metadata": {},
                            }
                        )
                    else:
                        structured_pages.append(
                            {
                                "page_number": i + 1,
                                "items": [
                                    {
                                        "type": "error",
                                        "content": result.get(
                                            "error", "Recognition failed"
                                        ),
                                    }
                                ],
                                "metadata": {},
                            }
                        )

            # Remove duplicate links
            seen = set()
            unique_links = []
            for link in cross_page_links:
                key = (
                    link["from_page"],
                    link["to_page"],
                    link.get("type"),
                    link.get("label"),
                )
                if key not in seen:
                    unique_links.append(link)
                    seen.add(key)

            return {
                "success": True,
                "pages": structured_pages,
                "cross_page_links": unique_links,
            }

        except Exception as e:
            logger.error(f"Error processing multiple pages: {e}")
            return {"success": False, "error": str(e)}

        finally:
            # Clean up rendered images
            for image_path in rendered_images:
                try:
                    if os.path.exists(image_path):
                        os.unlink(image_path)
                except Exception:
                    pass

    def convert_to_iink_format(self, strokes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert reMarkable strokes to MyScript Web API compatible format

        Note: Despite the method name, this formats data for the REST API, not an SDK.
        The method name is kept for backward compatibility.

        Args:
            strokes: List of stroke dictionaries extracted from reMarkable file

        Returns:
            Dictionary formatted for MyScript Web API
        """
        try:
            if not strokes:
                logger.warning("No strokes provided for conversion to iink format")
                return {"type": "Raw Content", "strokes": []}

            # Use the adapter to convert strokes to iink format
            if hasattr(self.adapter, "convert_to_iink_format"):
                return self.adapter.convert_to_iink_format(strokes)

            # Fallback implementation if adapter doesn't provide this method
            iink_strokes = []
            for stroke in strokes:
                points = stroke.get("points", [])

                # Extract x, y coordinates and convert to iink format
                # iink format expects x, y pairs in a flat array
                if points:
                    x_points = [point.get("x", 0) for point in points]
                    y_points = [point.get("y", 0) for point in points]

                    # Interleave x and y coordinates
                    flattened_points = []
                    for x, y in zip(x_points, y_points):
                        flattened_points.extend([x, y])

                    iink_stroke = {
                        "id": stroke.get("id", ""),
                        "x": x_points,
                        "y": y_points,
                        "t": [p.get("timestamp", 0) for p in points],
                        "p": [p.get("pressure", 1.0) for p in points],
                    }

                    iink_strokes.append(iink_stroke)

            return {
                "type": "Raw Content",
                "strokes": iink_strokes,
                "width": CONFIG.get("PAGE_WIDTH", 1404),
                "height": CONFIG.get("PAGE_HEIGHT", 1872),
            }

        except Exception as e:
            logger.error(f"Error converting strokes to iink format: {e}")
            return {"type": "Raw Content", "strokes": [], "error": str(e)}

    @staticmethod
    @staticmethod
    def _split_multi_page_result(result: str, page_count: int) -> List[str]:
        """
        Split a multi-page result into individual pages.

        Args:
            result: Combined result text
            page_count: Expected number of pages

        Returns:
            List of page contents
        """
        # Look for page markers in the text
        page_markers = re.findall(r"(?:Page|PAGE) (\d+)(?::|\.|\n)", result)

        if len(page_markers) >= page_count - 1:
            # We have enough page markers to split
            sections = []
            current_pos = 0

            for i in range(1, page_count + 1):
                marker = f"Page {i}:" if i > 1 else None
                alt_marker = f"PAGE {i}:" if i > 1 else None

                # Find the start of this page
                if marker:
                    marker_pos = result.find(marker, current_pos)
                    alt_marker_pos = result.find(alt_marker, current_pos)
                    if marker_pos != -1 and (
                        alt_marker_pos == -1 or marker_pos < alt_marker_pos
                    ):
                        start_pos = marker_pos + len(marker)
                    elif alt_marker_pos != -1:
                        start_pos = alt_marker_pos + len(alt_marker)
                    else:
                        # No marker found, use current position
                        start_pos = current_pos
                else:
                    start_pos = 0

                # Find the start of the next page
                next_marker = f"Page {i + 1}:" if i < page_count else None
                next_alt_marker = f"PAGE {i + 1}:" if i < page_count else None

                if next_marker:
                    next_pos = result.find(next_marker, start_pos)
                    alt_next_pos = result.find(next_alt_marker, start_pos)
                    if next_pos != -1 and (
                        alt_next_pos == -1 or next_pos < alt_next_pos
                    ):
                        end_pos = next_pos
                    elif alt_next_pos != -1:
                        end_pos = alt_next_pos
                    else:
                        # No next marker found, use the end of the string
                        end_pos = len(result)
                else:
                    end_pos = len(result)

                # Extract the page content and clean it
                page_content = result[start_pos:end_pos].strip()
                sections.append(page_content)
                current_pos = end_pos

            return sections
        # Not enough page markers, divide evenly
        avg_length = len(result) // page_count
        return [
            result[i * avg_length : (i + 1) * avg_length].strip()
            for i in range(page_count)
        ]
